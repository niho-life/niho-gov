"""
改善版JSON変換モジュール
詳細な検証ロジック + 自動補正 + フラグ付け
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

import config


@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    flags: List[str]
    messages: List[str]
    auto_corrected: bool = False


def extract_category(text: str) -> Optional[Dict[str, Any]]:
    """
    款・項・目を抽出
    """
    pattern = config.PATTERNS["category_full"]
    match = re.search(pattern, text)
    
    if not match:
        return None
    
    # 全角数字を半角に
    def to_half_width(s):
        return s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    
    return {
        "kuan": {"code": int(to_half_width(match.group(1))), "name": match.group(2).strip()},
        "kou": {"code": int(to_half_width(match.group(3))), "name": match.group(4).strip()},
        "moku": {"code": int(to_half_width(match.group(5))), "name": match.group(6).strip()}
    }


def extract_department(text: str) -> str:
    """
    担当課を抽出
    """
    # まず【】内を探す
    bracket_match = re.search(config.PATTERNS["department_bracket"], text)
    if bracket_match:
        return bracket_match.group(1).strip()
    
    # 「〇〇課」パターン
    dept_match = re.search(config.PATTERNS["department"], text)
    if dept_match:
        return dept_match.group(1).strip()
    
    return ""


def extract_project_name(lines: List[Dict[str, Any]]) -> str:
    """
    事業名を抽出
    """
    for i, line in enumerate(lines):
        line_text = line.get("text", "")
        
        # ◎を含む行の次の行が事業名
        if "◎" in line_text and i + 1 < len(lines):
            next_line = lines[i + 1].get("text", "")
            
            # 担当課部分を除去
            dept_match = re.search(config.PATTERNS["department_bracket"], next_line)
            if dept_match:
                name = next_line[:dept_match.start()].strip()
            else:
                # 「〇〇課」で分割
                parts = re.split(r'\s+(?=\S+課)', next_line)
                name = parts[0].strip()
            
            # ゴミ文字を除去
            name = re.sub(config.PATTERNS["garbage"], '', name).strip()
            
            if name:
                return name
    
    return ""


def extract_purpose(text: str) -> Dict[str, str]:
    """
    事業の目的（対象・意図・効果）を抽出
    """
    purpose = {"target": "", "intent": "", "effect": ""}
    
    # 対象
    match = re.search(r'対象\s*(.+?)(?=意図|効果|事業の内容|$)', text, re.DOTALL)
    if match:
        purpose["target"] = match.group(1).strip().split('\n')[0]
    
    # 意図
    match = re.search(r'意図\s*(.+?)(?=効果|事業の内容|$)', text, re.DOTALL)
    if match:
        purpose["intent"] = match.group(1).strip().replace('\n', '')
    
    # 効果
    match = re.search(r'効果\s*(.+?)(?=事業の内容|【|$)', text, re.DOTALL)
    if match:
        purpose["effect"] = match.group(1).strip().replace('\n', '')
    
    return purpose


def extract_description(text: str) -> List[str]:
    """
    事業の内容を抽出（箇条書き）
    """
    descriptions = []
    
    # 「事業の内容」セクションを探す
    match = re.search(r'事業の内容[】\s]*(.+?)(?=事業費|予算内訳|$)', text, re.DOTALL)
    if match:
        content = match.group(1)
        # 箇条書きを抽出
        items = re.findall(r'[・•](.+?)(?=[・•]|$)', content, re.DOTALL)
        for item in items:
            cleaned = item.strip().replace('\n', '')
            if cleaned:
                descriptions.append(cleaned)
    
    return descriptions


def extract_prev_year_page(text: str) -> str:
    """
    前年度該当ページを抽出
    """
    match = re.search(config.PATTERNS["prev_year"], text)
    if match:
        page = match.group(1).strip()
        # 文字化けを修正
        page = re.sub(r'[Pp]', 'P', page)
        page = re.sub(r'[lI]', '1', page)
        page = re.sub(r'〜|~', '～', page)
        return page
    return ""


def determine_project_type(name: str, text: str) -> str:
    """
    事業タイプを判定
    """
    if "職員給与費" in name or "対象となる職員" in text:
        return "salary"
    if "政務活動費" in name:
        return "allowance"
    return "normal"


def calculate_budget_tolerance(total: int) -> int:
    """
    予算検証の許容誤差を計算
    
    許容誤差 = max(total * 1%, 1千円)
    """
    return max(int(total * config.BUDGET_TOLERANCE_PERCENT), config.BUDGET_TOLERANCE_MIN)


def validate_project(project: Dict[str, Any]) -> ValidationResult:
    """
    プロジェクトデータを検証
    
    Returns:
        ValidationResult
    """
    flags = []
    messages = []
    auto_corrected = False
    
    # 1. 必須フィールドチェック
    if not project.get("name"):
        flags.append(config.FLAG_MISSING_NAME)
        messages.append("事業名が抽出できませんでした")
    
    if not project.get("department"):
        flags.append(config.FLAG_MISSING_DEPARTMENT)
        messages.append("担当課が抽出できませんでした")
    
    budget = project.get("budget", {})
    if not budget.get("total") or budget.get("total") == 0:
        flags.append(config.FLAG_MISSING_BUDGET)
        messages.append("事業費が抽出できませんでした")
    
    # 2. 予算合計チェック
    total = budget.get("total", 0)
    details = project.get("budget_details", [])
    details_sum = sum(d.get("amount", 0) for d in details)
    
    if total and details_sum:
        tolerance = calculate_budget_tolerance(total)
        diff = abs(total - details_sum)
        
        if diff > tolerance:
            flags.append(config.FLAG_SUM_MISMATCH)
            messages.append(f"予算合計不一致: total={total}, sum={details_sum}, diff={diff}")
            
            # 自動補正の試行（内訳が1つ欠けている場合）
            if total > details_sum and len(details) > 0:
                # 差分を「その他」として追加
                project["budget_details"].append({
                    "item": "（自動補正: 未抽出分）",
                    "amount": total - details_sum,
                    "line_confidence": 0.5,
                    "auto_corrected": True
                })
                auto_corrected = True
                messages.append(f"自動補正: 差分 {total - details_sum} を追加")
    
    # 3. 信頼度チェック
    confidence = project.get("confidence", 1.0)
    if confidence < config.CONFIDENCE_THRESHOLD_REVIEW:
        flags.append(config.FLAG_LOW_CONFIDENCE)
        messages.append(f"信頼度が低い: {confidence:.2%}")
    
    # 4. CID問題チェック
    if project.get("has_cid_issue"):
        flags.append(config.FLAG_CID_DETECTED)
        messages.append("PDFフォント問題（CID）が検出されました")
    
    is_valid = len([f for f in flags if f not in [config.FLAG_LOW_CONFIDENCE]]) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        flags=flags,
        messages=messages,
        auto_corrected=auto_corrected
    )


def calculate_overall_confidence(
    structured_data: Dict[str, Any],
    project: Dict[str, Any]
) -> float:
    """
    総合信頼度を計算（フィールド別重み付け）
    """
    confidences = {}
    
    # 名前
    name_conf = structured_data.get("stats", {}).get("avg_confidence", 0.5) if project.get("name") else 0.0
    confidences["name"] = name_conf
    
    # 担当課
    dept_conf = 0.9 if project.get("department") else 0.0
    confidences["department"] = dept_conf
    
    # 予算総額
    if project.get("budget", {}).get("total"):
        confidences["budget_total"] = structured_data.get("stats", {}).get("avg_confidence", 0.7)
    else:
        confidences["budget_total"] = 0.0
    
    # 予算内訳
    details = project.get("budget_details", [])
    if details:
        detail_confs = [d.get("line_confidence", 0.5) for d in details]
        confidences["budget_details"] = sum(detail_confs) / len(detail_confs)
    else:
        confidences["budget_details"] = 0.0
    
    # 目的
    purpose = project.get("purpose", {})
    if any(purpose.values()):
        confidences["purpose"] = 0.8
    else:
        confidences["purpose"] = 0.0
    
    # 重み付け平均
    total_weight = 0
    weighted_sum = 0
    
    for field, conf in confidences.items():
        weight = config.CONFIDENCE_WEIGHTS.get(field, 0.1)
        weighted_sum += conf * weight
        total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def generate_project_id(
    category: Optional[Dict[str, Any]],
    page_num: int,
    text_hash: str = None
) -> str:
    """
    プロジェクトIDを生成
    
    形式: R07-{款}-{項}-{目}-{ページ}
    """
    fiscal_year = "R07"
    
    if category:
        kuan = category["kuan"]["code"]
        kou = category["kou"]["code"]
        moku = category["moku"]["code"]
        base_id = f"{fiscal_year}-{kuan:02d}-{kou:02d}-{moku:02d}-{page_num:03d}"
    else:
        base_id = f"{fiscal_year}-XX-XX-XX-{page_num:03d}"
    
    return base_id


def convert_structured_to_project(
    structured_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    構造化データを最終的なプロジェクトJSONに変換
    """
    page_num = structured_data.get("page_number", 0)
    full_text = structured_data.get("full_text", "")
    lines = structured_data.get("lines", [])
    
    # 基本情報を抽出
    category = extract_category(full_text)
    department = extract_department(full_text)
    name = extract_project_name(lines)
    project_type = determine_project_type(name, full_text)
    
    # テキストハッシュ（差分検出用）
    text_hash = hashlib.sha1(full_text.encode()).hexdigest()[:8]
    
    project = {
        "id": generate_project_id(category, page_num, text_hash),
        "text_hash": text_hash,
        "source_page": page_num,
        "source_bbox": None,  # 必要に応じて追加
        "category": category,
        "name": name,
        "department": department,
        "type": project_type,
        "prev_year_page": extract_prev_year_page(full_text),
        "has_cid_issue": structured_data.get("stats", {}).get("has_cid_issue", False)
    }
    
    # 事業タイプ別の情報
    if project_type == "normal":
        project["purpose"] = extract_purpose(full_text)
        project["description"] = extract_description(full_text)
    elif project_type == "salary":
        # 職員給与費ページ
        match = re.search(r'対象となる職員[】\s]*\n*(\S+)', full_text)
        if match:
            project["target_staff"] = match.group(1)
        
        staff_match = re.search(r'(一般職職員|会計年度.+?職員)\s*(\d+)人', full_text)
        if staff_match:
            project["staff_count"] = f"{staff_match.group(1)} {staff_match.group(2)}人"
    
    # 予算情報
    budget_total = structured_data.get("budget_total")
    budget_details = structured_data.get("budget_details", [])
    details_sum = structured_data.get("budget_details_sum", 0)
    
    # 予算総額の決定（total優先、なければ内訳合計）
    final_total = budget_total or details_sum
    
    project["budget"] = {
        "total": final_total,
        "total_from_details": details_sum,
        "unit": "千円",
        "revenue": {
            "national_prefectural": 0,
            "local_bond": 0,
            "other": 0,
            "general": final_total
        }
    }
    
    project["budget_details"] = budget_details
    
    # 信頼度計算
    project["confidence"] = calculate_overall_confidence(structured_data, project)
    
    # 検証
    validation = validate_project(project)
    project["validation"] = {
        "is_valid": validation.is_valid,
        "flags": validation.flags,
        "messages": validation.messages,
        "auto_corrected": validation.auto_corrected
    }
    
    return project


def build_final_output(
    structured_files: List[Path],
    source_file: str = None
) -> Dict[str, Any]:
    """
    全構造化ファイルから最終JSONを構築
    """
    projects = []
    validation_summary = {
        "total": 0,
        "valid": 0,
        "with_flags": 0,
        "auto_corrected": 0,
        "needs_review": 0,
        "flags_count": {}
    }
    
    print(f"📝 最終JSON構築: {len(structured_files)}ファイル")
    
    for sf in sorted(structured_files):
        try:
            with open(sf, "r", encoding="utf-8") as f:
                structured = json.load(f)
            
            project = convert_structured_to_project(structured)
            projects.append(project)
            
            # 統計更新
            validation_summary["total"] += 1
            
            validation = project.get("validation", {})
            if validation.get("is_valid"):
                validation_summary["valid"] += 1
            
            flags = validation.get("flags", [])
            if flags:
                validation_summary["with_flags"] += 1
                for flag in flags:
                    validation_summary["flags_count"][flag] = \
                        validation_summary["flags_count"].get(flag, 0) + 1
            
            if validation.get("auto_corrected"):
                validation_summary["auto_corrected"] += 1
            
            if project.get("confidence", 1.0) < config.CONFIDENCE_THRESHOLD_REVIEW:
                validation_summary["needs_review"] += 1
            
            # 進捗表示
            status = "✓" if validation.get("is_valid") else f"⚠ {','.join(flags[:2])}"
            print(f"  {status} P{project['source_page']:03d}: {project['name'][:25]}")
            
        except Exception as e:
            print(f"  ✗ エラー ({sf.name}): {e}")
            validation_summary["total"] += 1
    
    # 最終出力構造
    output = {
        "metadata": {
            **config.METADATA,
            "extracted_at": datetime.now().isoformat(),
            "source_file": source_file or "unknown",
            "validation_summary": validation_summary
        },
        "projects": projects
    }
    
    return output


def save_final_output(
    output: Dict[str, Any],
    output_dir: Path,
    base_name: str = "kamakura_budget"
) -> Dict[str, Path]:
    """
    最終出力を各形式で保存
    
    Returns:
        保存されたファイルパスの辞書
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_files = {}
    
    # 1. 完全なJSON
    json_path = output_dir / f"{base_name}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    saved_files["json"] = json_path
    
    # 2. JSONL（1行1レコード）
    jsonl_path = output_dir / f"{base_name}_{timestamp}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for project in output["projects"]:
            f.write(json.dumps(project, ensure_ascii=False) + "\n")
    saved_files["jsonl"] = jsonl_path
    
    # 3. 要レビューリスト
    flagged = [p for p in output["projects"] if p.get("validation", {}).get("flags")]
    if flagged:
        review_path = output_dir / f"{base_name}_review_{timestamp}.json"
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump({
                "count": len(flagged),
                "projects": flagged
            }, f, ensure_ascii=False, indent=2)
        saved_files["review"] = review_path
    
    # 4. サマリー
    summary = output["metadata"]["validation_summary"]
    print(f"\n{'='*50}")
    print(f"📊 最終結果サマリー")
    print(f"{'='*50}")
    print(f"総数: {summary['total']}")
    print(f"有効: {summary['valid']} ({summary['valid']/max(summary['total'],1)*100:.1f}%)")
    print(f"フラグ付き: {summary['with_flags']}")
    print(f"自動補正: {summary['auto_corrected']}")
    print(f"要レビュー: {summary['needs_review']}")
    
    if summary["flags_count"]:
        print(f"\nフラグ内訳:")
        for flag, count in sorted(summary["flags_count"].items(), key=lambda x: -x[1]):
            print(f"  {flag}: {count}")
    
    print(f"\n💾 保存先:")
    for name, path in saved_files.items():
        print(f"  {name}: {path}")
    
    return saved_files


if __name__ == "__main__":
    import sys
    
    # 構造化ファイルを処理
    structured_files = sorted(config.OCR_STRUCTURED_DIR.glob("*_structured.json"))
    
    if not structured_files:
        print("構造化ファイルが見つかりません")
        sys.exit(1)
    
    output = build_final_output(structured_files)
    saved = save_final_output(output, config.FINAL_DIR)
