#!/usr/bin/env python3
"""
鎌倉市予算書OCRパイプライン v2.0 - 完全版

GCS非同期処理 + KMeansクラスタリング + Document AIフォールバック

使用方法:
    # 全工程を実行
    python pipeline.py input/議会費.pdf
    
    # 特定工程のみ実行
    python pipeline.py input/議会費.pdf --step upload
    python pipeline.py input/議会費.pdf --step ocr
    python pipeline.py input/議会費.pdf --step parse
    python pipeline.py input/議会費.pdf --step convert
    python pipeline.py input/議会費.pdf --step retry
    
    # ローカルモード（GCSを使わない）
    python pipeline.py input/議会費.pdf --local
    
    # ドライラン（コスト確認のみ）
    python pipeline.py input/議会費.pdf --dry-run

必要な環境変数:
    GOOGLE_APPLICATION_CREDENTIALS: サービスアカウントキーのパス
    GCP_PROJECT_ID: GCPプロジェクトID
    GCS_INPUT_BUCKET: 入力バケット名
    GCS_OUTPUT_BUCKET: 出力バケット名
    DOCUMENT_AI_PROCESSOR_ID: (オプション) Document AIプロセッサID
"""
import argparse
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

# ローカルモジュール
import config

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineContext:
    """パイプライン実行コンテキスト"""
    
    def __init__(self, pdf_path: Path, job_name: str = None):
        self.pdf_path = pdf_path
        self.job_name = job_name or pdf_path.stem
        self.run_id = f"{self.job_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 作業ディレクトリ
        self.work_dir = config.OUTPUT_DIR / self.run_id
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # 結果
        self.results = {
            "run_id": self.run_id,
            "job_name": self.job_name,
            "pdf_path": str(pdf_path),
            "started_at": datetime.now().isoformat(),
            "steps": {}
        }
        
        # ログファイル
        self.log_path = config.LOGS_DIR / f"{self.run_id}.json"
    
    def save_log(self):
        """ログを保存"""
        self.results["finished_at"] = datetime.now().isoformat()
        def to_jsonable(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, dict):
                return {k: to_jsonable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [to_jsonable(v) for v in obj]
            if isinstance(obj, tuple):
                return [to_jsonable(v) for v in obj]
            return obj

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(to_jsonable(self.results), f, ensure_ascii=False, indent=2)
        logger.info(f"📋 ログ保存: {self.log_path}")


def get_pdf_page_count(pdf_path: Path) -> int:
    """PDFのページ数を取得"""
    from pdf2image import pdfinfo_from_path
    try:
        info = pdfinfo_from_path(str(pdf_path))
        return info.get("Pages", 0)
    except Exception:
        return 0


def estimate_cost(page_count: int) -> Dict[str, Any]:
    """コストを見積もり"""
    gcv_cost = page_count * config.COST_PER_1000_PAGES_GCV / 1000
    
    # 10%がDocument AIで再処理と仮定
    docai_pages = int(page_count * 0.1)
    docai_cost = docai_pages * config.COST_PER_1000_PAGES_DOCAI / 1000
    
    return {
        "page_count": page_count,
        "gcv_cost": gcv_cost,
        "gcv_cost_with_free_tier": max(0, gcv_cost - 1.50),  # 月1000ページ無料
        "docai_pages_estimate": docai_pages,
        "docai_cost_estimate": docai_cost,
        "total_estimate": gcv_cost + docai_cost
    }


def step_upload(ctx: PipelineContext) -> Dict[str, Any]:
    """Step 1: PDFをGCSにアップロード"""
    logger.info("=" * 60)
    logger.info("📤 Step 1: GCSアップロード")
    logger.info("=" * 60)
    
    from gcs_vision_client import GCSClient
    
    gcs = GCSClient()
    blob_name = f"input/{ctx.run_id}.pdf"
    gcs_uri = gcs.upload_file(ctx.pdf_path, config.GCS_INPUT_BUCKET, blob_name)
    
    result = {
        "status": "success",
        "gcs_uri": gcs_uri,
        "blob_name": blob_name
    }
    
    ctx.results["gcs_input_uri"] = gcs_uri
    logger.info(f"✅ アップロード完了: {gcs_uri}")
    
    return result


def step_ocr(ctx: PipelineContext, local_mode: bool = False) -> Dict[str, Any]:
    """Step 2: Vision API OCR実行"""
    logger.info("=" * 60)
    logger.info("🔍 Step 2: Vision API OCR")
    logger.info("=" * 60)
    
    if local_mode:
        # ローカルモード: 同期APIを使用
        return step_ocr_local(ctx)
    
    # GCSモード: 非同期APIを使用
    from gcs_vision_client import VisionAsyncClient
    
    client = VisionAsyncClient()
    
    gcs_input_uri = ctx.results.get("gcs_input_uri")
    if not gcs_input_uri:
        # アップロードがスキップされた場合
        gcs_input_uri = f"gs://{config.GCS_INPUT_BUCKET}/input/{ctx.run_id}.pdf"
    
    output_prefix = f"gs://{config.GCS_OUTPUT_BUCKET}/{config.GCS_OUTPUT_PREFIX}{ctx.run_id}/"
    
    # ジョブ送信
    from google.cloud import vision_v1
    
    operation = client.client.async_batch_annotate_files(
        requests=[vision_v1.AsyncAnnotateFileRequest(
            input_config=vision_v1.InputConfig(
                gcs_source=vision_v1.GcsSource(uri=gcs_input_uri),
                mime_type="application/pdf"
            ),
            features=[vision_v1.Feature(
                type_=vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION
            )],
            output_config=vision_v1.OutputConfig(
                gcs_destination=vision_v1.GcsDestination(uri=output_prefix),
                batch_size=config.VISION_BATCH_SIZE
            )
        )]
    )
    
    logger.info(f"🚀 ジョブ送信: {operation.operation.name}")
    logger.info(f"⏳ 完了待機中... (タイムアウト: {config.VISION_TIMEOUT}秒)")
    
    # 完了待機
    start_time = time.time()
    try:
        operation.result(timeout=config.VISION_TIMEOUT)
        elapsed = time.time() - start_time
        logger.info(f"✅ OCR完了 ({elapsed:.1f}秒)")
    except Exception as e:
        logger.error(f"❌ OCR失敗: {e}")
        return {"status": "failed", "error": str(e)}
    
    # 結果ダウンロード
    from gcs_vision_client import GCSClient
    gcs = GCSClient()
    
    ocr_output_dir = ctx.work_dir / "ocr_raw"
    ocr_output_dir.mkdir(exist_ok=True)
    
    downloaded = gcs.download_blobs(
        config.GCS_OUTPUT_BUCKET,
        f"{config.GCS_OUTPUT_PREFIX}{ctx.run_id}/",
        ocr_output_dir
    )
    
    result = {
        "status": "success",
        "elapsed_seconds": elapsed,
        "output_prefix": output_prefix,
        "downloaded_files": [str(f) for f in downloaded],
        "ocr_output_dir": str(ocr_output_dir)
    }
    
    ctx.results["ocr_output_dir"] = str(ocr_output_dir)
    
    return result


def step_ocr_local(ctx: PipelineContext) -> Dict[str, Any]:
    """ローカルモードでのOCR（同期API）"""
    from google.cloud import vision_v1
    from pdf2image import convert_from_path
    import io
    
    logger.info("📸 ローカルモード: PDF→画像→同期API")
    
    # PDF→画像変換
    images = convert_from_path(str(ctx.pdf_path), dpi=config.PDF_DPI if hasattr(config, 'PDF_DPI') else 300)
    logger.info(f"📄 {len(images)}ページを変換")
    
    client = vision_v1.ImageAnnotatorClient()
    
    ocr_output_dir = ctx.work_dir / "ocr_raw"
    ocr_output_dir.mkdir(exist_ok=True)
    
    all_responses = []
    
    for i, img in enumerate(images):
        page_num = i + 1
        logger.info(f"  OCR中: ページ {page_num}/{len(images)}")
        
        # 画像をバイトに変換
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        content = img_byte_arr.getvalue()
        
        # OCR実行
        image = vision_v1.Image(content=content)
        response = client.document_text_detection(
            image=image,
            image_context=vision_v1.ImageContext(
                language_hints=config.OCR_LANGUAGE_HINTS
            )
        )
        
        # レスポンスを保存
        page_result = {
            "responses": [{
                "fullTextAnnotation": {
                    "text": response.full_text_annotation.text if response.full_text_annotation else "",
                    "pages": []
                }
            }]
        }
        
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                page_data = {
                    "width": page.width,
                    "height": page.height,
                    "blocks": []
                }
                
                for block in page.blocks:
                    block_data = {"paragraphs": []}
                    for para in block.paragraphs:
                        para_data = {"words": []}
                        for word in para.words:
                            word_data = {
                                "symbols": [{"text": s.text} for s in word.symbols],
                                "boundingBox": {
                                    "vertices": [
                                        {"x": v.x, "y": v.y}
                                        for v in word.bounding_box.vertices
                                    ]
                                },
                                "confidence": word.confidence
                            }
                            para_data["words"].append(word_data)
                        block_data["paragraphs"].append(para_data)
                    page_data["blocks"].append(block_data)
                
                page_result["responses"][0]["fullTextAnnotation"]["pages"].append(page_data)
        
        all_responses.append(page_result)
        
        # 個別ページを保存
        page_path = ocr_output_dir / f"page_{page_num:03d}_ocr.json"
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump(page_result, f, ensure_ascii=False, indent=2)
    
    # 全ページを1ファイルにも保存
    combined_path = ocr_output_dir / "output-1-to-end.json"
    combined = {"responses": []}
    for resp in all_responses:
        combined["responses"].extend(resp["responses"])
    
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    
    ctx.results["ocr_output_dir"] = str(ocr_output_dir)
    
    return {
        "status": "success",
        "pages_processed": len(images),
        "ocr_output_dir": str(ocr_output_dir)
    }


def step_parse(ctx: PipelineContext) -> Dict[str, Any]:
    """Step 3: レイアウト復元"""
    logger.info("=" * 60)
    logger.info("📐 Step 3: レイアウト復元")
    logger.info("=" * 60)
    
    from layout_reconstructor_v2 import process_gcv_output
    
    ocr_output_dir = Path(ctx.results.get("ocr_output_dir", ctx.work_dir / "ocr_raw"))
    structured_dir = ctx.work_dir / "structured"
    structured_dir.mkdir(exist_ok=True)
    
    # OCR結果JSONを探す
    ocr_files = list(ocr_output_dir.glob("*.json"))
    
    if not ocr_files:
        logger.error("OCR結果ファイルが見つかりません")
        return {"status": "failed", "error": "No OCR files found"}
    
    all_results = []
    
    for ocr_file in ocr_files:
        logger.info(f"処理中: {ocr_file.name}")
        results = process_gcv_output(ocr_file, structured_dir)
        all_results.extend(results)
    
    ctx.results["structured_dir"] = str(structured_dir)
    ctx.results["pages_parsed"] = len(all_results)
    
    # 統計
    avg_conf = sum(r["stats"]["avg_confidence"] for r in all_results) / len(all_results) if all_results else 0
    cid_count = sum(1 for r in all_results if r["stats"]["has_cid_issue"])
    
    logger.info(f"✅ パース完了: {len(all_results)}ページ")
    logger.info(f"   平均信頼度: {avg_conf:.2%}")
    logger.info(f"   CID問題: {cid_count}ページ")
    
    return {
        "status": "success",
        "pages_parsed": len(all_results),
        "avg_confidence": avg_conf,
        "cid_issues": cid_count,
        "structured_dir": str(structured_dir)
    }


def step_convert(ctx: PipelineContext) -> Dict[str, Any]:
    """Step 4: JSON変換"""
    logger.info("=" * 60)
    logger.info("📝 Step 4: JSON変換")
    logger.info("=" * 60)
    
    from json_converter_v2 import build_final_output, save_final_output
    
    structured_dir = Path(ctx.results.get("structured_dir", ctx.work_dir / "structured"))
    final_dir = ctx.work_dir / "final"
    final_dir.mkdir(exist_ok=True)
    
    structured_files = sorted(structured_dir.glob("*_structured.json"))
    
    if not structured_files:
        logger.error("構造化ファイルが見つかりません")
        return {"status": "failed", "error": "No structured files found"}
    
    output = build_final_output(structured_files, str(ctx.pdf_path))
    saved = save_final_output(output, final_dir, ctx.job_name)
    
    ctx.results["final_dir"] = str(final_dir)
    ctx.results["output_files"] = {k: str(v) for k, v in saved.items()}
    ctx.results["validation_summary"] = output["metadata"]["validation_summary"]
    
    return {
        "status": "success",
        "output_files": saved,
        "validation_summary": output["metadata"]["validation_summary"]
    }


def step_retry(ctx: PipelineContext) -> Dict[str, Any]:
    """Step 5: Document AIで再処理"""
    logger.info("=" * 60)
    logger.info("🔄 Step 5: Document AI再処理")
    logger.info("=" * 60)
    
    if not config.DOCUMENT_AI_ENABLED:
        logger.warning("Document AIが有効化されていません。スキップします。")
        return {"status": "skipped", "reason": "Document AI not enabled"}
    
    from docai_fallback import get_pages_for_retry, process_retry_pages
    
    # 最終JSONを読み込み
    final_dir = Path(ctx.results.get("final_dir", ctx.work_dir / "final"))
    json_files = list(final_dir.glob("*.json"))
    
    if not json_files:
        return {"status": "failed", "error": "No final JSON found"}
    
    with open(json_files[0], "r", encoding="utf-8") as f:
        final_data = json.load(f)
    
    projects = final_data.get("projects", [])
    
    # 再処理が必要なページを特定
    retry_pages = get_pages_for_retry(projects)
    
    if not retry_pages:
        logger.info("再処理が必要なページはありません")
        return {"status": "success", "retry_pages": 0}
    
    logger.info(f"再処理対象: {len(retry_pages)}ページ")
    
    # Document AIで再処理
    updated_projects = process_retry_pages(ctx.pdf_path, retry_pages, projects)
    
    # 更新されたJSONを保存
    final_data["projects"] = updated_projects
    final_data["metadata"]["docai_retry"] = {
        "pages": retry_pages,
        "count": len(retry_pages)
    }
    
    updated_path = final_dir / f"{ctx.job_name}_docai_updated.json"
    with open(updated_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 更新完了: {updated_path}")
    
    return {
        "status": "success",
        "retry_pages": len(retry_pages),
        "updated_file": str(updated_path)
    }


def run_pipeline(
    pdf_path: Path,
    steps: List[str] = None,
    local_mode: bool = False,
    dry_run: bool = False,
    assume_yes: bool = False,
) -> Dict[str, Any]:
    """
    パイプラインを実行
    """
    all_steps = ["upload", "ocr", "parse", "convert", "retry"]
    
    if steps is None:
        steps = all_steps
    
    # ローカルモードではアップロードをスキップ
    if local_mode and "upload" in steps:
        steps = [s for s in steps if s != "upload"]
    
    # コンテキスト作成
    ctx = PipelineContext(pdf_path)
    
    print("=" * 60)
    print("🏛️  鎌倉市予算書OCRパイプライン v2.0")
    print("=" * 60)
    print(f"📄 入力: {pdf_path}")
    print(f"🔧 実行ステップ: {', '.join(steps)}")
    print(f"📁 作業ディレクトリ: {ctx.work_dir}")
    print(f"🆔 実行ID: {ctx.run_id}")
    print()
    
    # ページ数とコスト見積もり
    page_count = get_pdf_page_count(pdf_path)
    cost = estimate_cost(page_count)
    
    print("💰 コスト見積もり:")
    print(f"   ページ数: {cost['page_count']}")
    print(f"   GCV コスト: ${cost['gcv_cost']:.4f} (無料枠後: ${cost['gcv_cost_with_free_tier']:.4f})")
    print(f"   Document AI (推定): ${cost['docai_cost_estimate']:.4f}")
    print(f"   合計 (推定): ${cost['total_estimate']:.4f}")
    print()
    
    if dry_run:
        print("ℹ️  ドライランモード: 実行せずに終了")
        return {"status": "dry_run", "cost": cost}
    
    # 確認
    if assume_yes:
        confirm = "y"
    else:
        if not sys.stdin.isatty():
            print("エラー: 非対話環境のため確認入力ができません。`--yes` を付けて実行してください。")
            return {"status": "cancelled"}
        confirm = input("続行しますか？ (y/N): ")
    if confirm.lower() != "y":
        print("キャンセルしました")
        return {"status": "cancelled"}
    
    start_time = time.time()
    
    try:
        # 各ステップを実行
        if "upload" in steps:
            ctx.results["steps"]["upload"] = step_upload(ctx)
        
        if "ocr" in steps:
            ctx.results["steps"]["ocr"] = step_ocr(ctx, local_mode=local_mode)
        
        if "parse" in steps:
            ctx.results["steps"]["parse"] = step_parse(ctx)
        
        if "convert" in steps:
            ctx.results["steps"]["convert"] = step_convert(ctx)
        
        if "retry" in steps:
            ctx.results["steps"]["retry"] = step_retry(ctx)
        
        ctx.results["status"] = "success"
        
    except Exception as e:
        logger.exception(f"パイプラインエラー: {e}")
        ctx.results["status"] = "failed"
        ctx.results["error"] = str(e)
    
    elapsed = time.time() - start_time
    ctx.results["elapsed_seconds"] = elapsed
    
    # ログ保存
    ctx.save_log()
    
    # 完了メッセージ
    print()
    print("=" * 60)
    print(f"{'🎉' if ctx.results['status'] == 'success' else '❌'} パイプライン完了")
    print("=" * 60)
    print(f"⏱️  実行時間: {elapsed:.1f}秒")
    print(f"📁 出力: {ctx.work_dir}")
    print(f"📋 ログ: {ctx.log_path}")
    
    if "validation_summary" in ctx.results:
        vs = ctx.results["validation_summary"]
        print()
        print("📊 結果サマリー:")
        print(f"   総数: {vs['total']}")
        print(f"   有効: {vs['valid']} ({vs['valid']/max(vs['total'],1)*100:.1f}%)")
        print(f"   要レビュー: {vs['needs_review']}")
    
    return ctx.results


def main():
    parser = argparse.ArgumentParser(
        description="鎌倉市予算書OCRパイプライン v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python pipeline.py input/議会費.pdf
  python pipeline.py input/議会費.pdf --local
  python pipeline.py input/議会費.pdf --step ocr --step parse
  python pipeline.py input/議会費.pdf --dry-run
        """
    )
    
    parser.add_argument("pdf_path", type=Path, help="入力PDFファイル")
    parser.add_argument(
        "--step",
        action="append",
        choices=["upload", "ocr", "parse", "convert", "retry"],
        help="実行するステップ（複数指定可）"
    )
    parser.add_argument("--local", action="store_true", help="ローカルモード（GCSを使わない）")
    parser.add_argument("--dry-run", action="store_true", help="コスト見積もりのみ")
    parser.add_argument("--yes", action="store_true", help="確認プロンプトを省略して続行する")
    
    args = parser.parse_args()
    
    if not args.pdf_path.exists():
        print(f"エラー: ファイルが見つかりません: {args.pdf_path}")
        sys.exit(1)
    
    result = run_pipeline(
        pdf_path=args.pdf_path,
        steps=args.step,
        local_mode=args.local,
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )
    
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
