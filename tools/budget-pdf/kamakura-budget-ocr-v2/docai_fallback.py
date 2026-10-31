"""
Document AI フォールバック処理
GCVで精度が低いページをDocument AIで再処理
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

import config

logger = logging.getLogger(__name__)


class DocumentAIClient:
    """
    Document AI クライアント
    
    GCVで失敗したページの再処理に使用
    """
    
    def __init__(self):
        self.enabled = config.DOCUMENT_AI_ENABLED
        self.processor_id = config.DOCUMENT_AI_PROCESSOR_ID
        self.project_id = config.GCP_PROJECT_ID
        self.location = config.GCP_LOCATION
        
        if self.enabled:
            from google.cloud import documentai_v1 as documentai
            self.client = documentai.DocumentProcessorServiceClient()
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
    
    def process_document(
        self,
        content: bytes,
        mime_type: str = "application/pdf"
    ) -> Optional[Dict[str, Any]]:
        """
        ドキュメントを処理
        
        Args:
            content: ドキュメントのバイナリ
            mime_type: MIMEタイプ
        
        Returns:
            処理結果
        """
        if not self.enabled:
            logger.warning("Document AI is not enabled")
            return None
        
        from google.cloud import documentai_v1 as documentai
        
        # リクエスト作成
        raw_document = documentai.RawDocument(
            content=content,
            mime_type=mime_type
        )
        
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document
        )
        
        # 処理実行
        result = self.client.process_document(request=request)
        document = result.document
        
        # 結果をパース
        return self._parse_document(document)
    
    def _parse_document(self, document) -> Dict[str, Any]:
        """
        Document AIの結果をパース
        """
        result = {
            "text": document.text,
            "pages": [],
            "entities": [],
            "tables": []
        }
        
        # ページ情報
        for page in document.pages:
            page_data = {
                "page_number": page.page_number,
                "dimension": {
                    "width": page.dimension.width,
                    "height": page.dimension.height
                },
                "paragraphs": [],
                "tables": []
            }
            
            # 段落
            for paragraph in page.paragraphs:
                text = self._get_text_from_layout(paragraph.layout, document.text)
                page_data["paragraphs"].append({
                    "text": text,
                    "confidence": paragraph.layout.confidence
                })
            
            # テーブル
            for table in page.tables:
                table_data = self._parse_table(table, document.text)
                page_data["tables"].append(table_data)
                result["tables"].append(table_data)
            
            result["pages"].append(page_data)
        
        # エンティティ（Form Parserの場合）
        for entity in document.entities:
            result["entities"].append({
                "type": entity.type_,
                "text": entity.mention_text,
                "confidence": entity.confidence
            })
        
        return result
    
    def _get_text_from_layout(self, layout, full_text: str) -> str:
        """
        レイアウトからテキストを抽出
        """
        text_segments = []
        for segment in layout.text_anchor.text_segments:
            start = int(segment.start_index) if segment.start_index else 0
            end = int(segment.end_index)
            text_segments.append(full_text[start:end])
        return "".join(text_segments)
    
    def _parse_table(self, table, full_text: str) -> Dict[str, Any]:
        """
        テーブルをパース
        """
        rows = []
        
        for row in table.header_rows:
            cells = []
            for cell in row.cells:
                text = self._get_text_from_layout(cell.layout, full_text)
                cells.append({
                    "text": text.strip(),
                    "confidence": cell.layout.confidence
                })
            rows.append({"type": "header", "cells": cells})
        
        for row in table.body_rows:
            cells = []
            for cell in row.cells:
                text = self._get_text_from_layout(cell.layout, full_text)
                cells.append({
                    "text": text.strip(),
                    "confidence": cell.layout.confidence
                })
            rows.append({"type": "body", "cells": cells})
        
        return {"rows": rows}


def should_retry_with_docai(project: Dict[str, Any]) -> bool:
    """
    Document AIで再処理すべきかを判定
    """
    flags = project.get("validation", {}).get("flags", [])
    confidence = project.get("confidence", 1.0)
    
    # 再処理条件
    conditions = [
        config.FLAG_SUM_MISMATCH in flags,
        config.FLAG_CID_DETECTED in flags,
        confidence < config.CONFIDENCE_THRESHOLD_REVIEW,
        config.FLAG_MISSING_BUDGET in flags
    ]
    
    return any(conditions)


def get_pages_for_retry(projects: List[Dict[str, Any]]) -> List[int]:
    """
    再処理が必要なページ番号を取得
    """
    retry_pages = []
    
    for project in projects:
        if should_retry_with_docai(project):
            retry_pages.append(project.get("source_page", 0))
    
    return sorted(set(retry_pages))


def merge_docai_results(
    original: Dict[str, Any],
    docai_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Document AI の結果をオリジナルにマージ
    
    Document AI の結果を優先するフィールド:
    - budget.total
    - budget_details
    - テーブルデータ
    """
    merged = original.copy()
    
    # 信頼度が高い場合のみマージ
    docai_pages = docai_result.get("pages", [])
    if not docai_pages:
        return merged
    
    # テーブルからの予算抽出
    for table in docai_result.get("tables", []):
        budget_info = extract_budget_from_docai_table(table)
        if budget_info:
            if budget_info.get("total"):
                merged["budget"]["total"] = budget_info["total"]
            if budget_info.get("details"):
                merged["budget_details"] = budget_info["details"]
    
    # マージフラグを追加
    merged["docai_merged"] = True
    
    # 再検証
    from json_converter_v2 import validate_project
    validation = validate_project(merged)
    merged["validation"] = {
        "is_valid": validation.is_valid,
        "flags": validation.flags,
        "messages": validation.messages,
        "auto_corrected": validation.auto_corrected
    }
    
    return merged


def extract_budget_from_docai_table(table: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Document AI のテーブルから予算情報を抽出
    """
    result = {"total": None, "details": []}
    
    for row in table.get("rows", []):
        cells = row.get("cells", [])
        if len(cells) < 2:
            continue
        
        first_cell = cells[0].get("text", "")
        
        # 事業費行
        if "事業費" in first_cell:
            for cell in cells[1:]:
                try:
                    amount = int(cell.get("text", "").replace(",", "").replace("，", ""))
                    if amount > 0:
                        result["total"] = amount
                        break
                except ValueError:
                    continue
        
        # 内訳行（節番号がある行）
        import re
        section_match = re.match(r'(\d+)節', first_cell)
        if section_match or row.get("type") == "body":
            item_text = first_cell
            amount = None
            
            # 最後の数値セルを金額として採用
            for cell in reversed(cells):
                try:
                    amount = int(cell.get("text", "").replace(",", "").replace("，", ""))
                    if amount > 0:
                        break
                except ValueError:
                    continue
            
            if amount and item_text:
                detail = {"item": item_text, "amount": amount}
                if section_match:
                    detail["section"] = int(section_match.group(1))
                result["details"].append(detail)
    
    return result if result["total"] or result["details"] else None


def process_retry_pages(
    pdf_path: Path,
    retry_pages: List[int],
    original_projects: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    指定ページをDocument AIで再処理
    
    Args:
        pdf_path: 元PDFのパス
        retry_pages: 再処理するページ番号リスト
        original_projects: 元のプロジェクトリスト
    
    Returns:
        更新されたプロジェクトリスト
    """
    if not retry_pages:
        return original_projects
    
    client = DocumentAIClient()
    
    if not client.enabled:
        logger.warning("Document AI is not enabled. Skipping retry.")
        return original_projects
    
    logger.info(f"🔄 Document AIで再処理: {len(retry_pages)}ページ")
    
    # PDFを読み込み
    with open(pdf_path, "rb") as f:
        content = f.read()
    
    # Document AIで処理
    try:
        docai_result = client.process_document(content)
    except Exception as e:
        logger.error(f"Document AI処理エラー: {e}")
        return original_projects
    
    # 結果をマージ
    updated_projects = []
    page_to_docai = {
        p["page_number"]: p
        for p in docai_result.get("pages", [])
    }
    
    for project in original_projects:
        page_num = project.get("source_page", 0)
        
        if page_num in retry_pages and page_num in page_to_docai:
            docai_page = page_to_docai[page_num]
            merged = merge_docai_results(project, {"pages": [docai_page], "tables": docai_result.get("tables", [])})
            updated_projects.append(merged)
            logger.info(f"  ✓ ページ {page_num} をマージ")
        else:
            updated_projects.append(project)
    
    return updated_projects


if __name__ == "__main__":
    # テスト
    print(f"Document AI enabled: {config.DOCUMENT_AI_ENABLED}")
    
    if config.DOCUMENT_AI_ENABLED:
        client = DocumentAIClient()
        print(f"Processor: {client.processor_name}")
