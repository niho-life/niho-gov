"""
GCS操作 + Vision API 非同期バッチ処理
大量ページを安定して処理するための実装
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from google.cloud import storage
from google.cloud import vision_v1
from google.api_core import retry
from google.api_core.exceptions import GoogleAPIError

import config

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GCSClient:
    """Google Cloud Storage クライアント"""
    
    def __init__(self):
        self.client = storage.Client(project=config.GCP_PROJECT_ID)
    
    def upload_file(self, local_path: Path, bucket_name: str, blob_name: str) -> str:
        """
        ローカルファイルをGCSにアップロード
        
        Returns:
            GCS URI (gs://bucket/blob)
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        logger.info(f"📤 アップロード中: {local_path} → gs://{bucket_name}/{blob_name}")
        blob.upload_from_filename(str(local_path))
        
        gcs_uri = f"gs://{bucket_name}/{blob_name}"
        logger.info(f"✓ アップロード完了: {gcs_uri}")
        
        return gcs_uri
    
    def download_blobs(self, bucket_name: str, prefix: str, local_dir: Path) -> List[Path]:
        """
        GCSからプレフィックスに一致するすべてのblobをダウンロード
        
        Returns:
            ダウンロードしたファイルパスのリスト
        """
        bucket = self.client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        downloaded = []
        for blob in blobs:
            if blob.name.endswith('/'):
                continue  # ディレクトリはスキップ
            
            local_path = local_dir / Path(blob.name).name
            logger.info(f"📥 ダウンロード中: {blob.name}")
            blob.download_to_filename(str(local_path))
            downloaded.append(local_path)
        
        logger.info(f"✓ {len(downloaded)}ファイルをダウンロード完了")
        return downloaded
    
    def list_blobs(self, bucket_name: str, prefix: str) -> List[str]:
        """プレフィックスに一致するblob名を取得"""
        bucket = self.client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs if not blob.name.endswith('/')]


class VisionAsyncClient:
    """
    Vision API 非同期バッチ処理クライアント
    
    大量ページのPDFを安定して処理するため、GCS経由の非同期APIを使用
    """
    
    def __init__(self):
        self.client = vision_v1.ImageAnnotatorClient()
        self.gcs = GCSClient()
        self.job_history = []
    
    def submit_async_job(
        self,
        input_gcs_uri: str,
        output_gcs_prefix: str,
        batch_size: int = None,
        mime_type: str = "application/pdf"
    ) -> str:
        """
        非同期OCRジョブを送信
        
        Args:
            input_gcs_uri: 入力PDFのGCS URI (gs://bucket/file.pdf)
            output_gcs_prefix: 出力先GCSプレフィックス (gs://bucket/output/)
            batch_size: 1出力ファイルあたりのページ数
            mime_type: 入力ファイルのMIMEタイプ
        
        Returns:
            operation name (ジョブID)
        """
        if batch_size is None:
            batch_size = config.VISION_BATCH_SIZE
        
        # 入力設定
        gcs_source = vision_v1.GcsSource(uri=input_gcs_uri)
        input_config = vision_v1.InputConfig(
            gcs_source=gcs_source,
            mime_type=mime_type
        )
        
        # 出力設定
        gcs_destination = vision_v1.GcsDestination(uri=output_gcs_prefix)
        output_config = vision_v1.OutputConfig(
            gcs_destination=gcs_destination,
            batch_size=batch_size
        )
        
        # 機能設定（DOCUMENT_TEXT_DETECTION = 表・レイアウト認識強化）
        feature = vision_v1.Feature(
            type_=vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION
        )
        
        # リクエスト作成
        async_request = vision_v1.AsyncAnnotateFileRequest(
            input_config=input_config,
            features=[feature],
            output_config=output_config
        )
        
        logger.info(f"🚀 非同期ジョブ送信中: {input_gcs_uri}")
        logger.info(f"   出力先: {output_gcs_prefix}")
        logger.info(f"   バッチサイズ: {batch_size}ページ/ファイル")
        
        # 非同期ジョブ送信
        operation = self.client.async_batch_annotate_files(
            requests=[async_request]
        )
        
        job_id = operation.operation.name
        logger.info(f"✓ ジョブ送信完了: {job_id}")
        
        # 履歴記録
        self.job_history.append({
            "job_id": job_id,
            "input_uri": input_gcs_uri,
            "output_prefix": output_gcs_prefix,
            "submitted_at": datetime.now().isoformat(),
            "status": "RUNNING"
        })
        
        return job_id
    
    def wait_for_job(
        self,
        operation,
        timeout: int = None,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        ジョブ完了を待機
        
        Args:
            operation: submit_async_jobの戻り値（operation object）
            timeout: タイムアウト秒数
            poll_interval: ポーリング間隔秒数
        
        Returns:
            ジョブ結果
        """
        if timeout is None:
            timeout = config.VISION_TIMEOUT
        
        logger.info(f"⏳ ジョブ完了待機中... (タイムアウト: {timeout}秒)")
        
        start_time = time.time()
        
        try:
            result = operation.result(timeout=timeout)
            elapsed = time.time() - start_time
            logger.info(f"✅ ジョブ完了 ({elapsed:.1f}秒)")
            return {"status": "SUCCESS", "elapsed_seconds": elapsed}
        
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ ジョブ失敗: {e}")
            return {"status": "FAILED", "error": str(e), "elapsed_seconds": elapsed}
    
    def process_pdf(
        self,
        local_pdf_path: Path,
        job_name: str = None
    ) -> Dict[str, Any]:
        """
        PDFを処理する完全なワークフロー
        
        1. GCSにアップロード
        2. 非同期ジョブ送信
        3. 完了待機
        4. 結果JSONをダウンロード
        
        Args:
            local_pdf_path: ローカルPDFパス
            job_name: ジョブ名（省略時はファイル名から生成）
        
        Returns:
            処理結果とダウンロードしたファイルパス
        """
        if job_name is None:
            job_name = local_pdf_path.stem
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. GCSにアップロード
        blob_name = f"input/{job_name}_{timestamp}.pdf"
        input_uri = self.gcs.upload_file(
            local_pdf_path,
            config.GCS_INPUT_BUCKET,
            blob_name
        )
        
        # 2. 出力先プレフィックス
        output_prefix = f"gs://{config.GCS_OUTPUT_BUCKET}/{config.GCS_OUTPUT_PREFIX}{job_name}_{timestamp}/"
        
        # 3. 非同期ジョブ送信
        operation = self.client.async_batch_annotate_files(
            requests=[vision_v1.AsyncAnnotateFileRequest(
                input_config=vision_v1.InputConfig(
                    gcs_source=vision_v1.GcsSource(uri=input_uri),
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
        
        job_id = operation.operation.name
        logger.info(f"🚀 ジョブ送信: {job_id}")
        
        # 4. 完了待機
        result = self.wait_for_job(operation)
        
        if result["status"] != "SUCCESS":
            return result
        
        # 5. 結果JSONをダウンロード
        output_local_dir = config.OCR_RAW_DIR / job_name
        output_local_dir.mkdir(exist_ok=True)
        
        downloaded = self.gcs.download_blobs(
            config.GCS_OUTPUT_BUCKET,
            f"{config.GCS_OUTPUT_PREFIX}{job_name}_{timestamp}/",
            output_local_dir
        )
        
        result["downloaded_files"] = [str(p) for p in downloaded]
        result["output_dir"] = str(output_local_dir)
        result["job_id"] = job_id
        result["input_uri"] = input_uri
        result["output_prefix"] = output_prefix
        
        return result


def process_pdf_with_retry(
    local_pdf_path: Path,
    max_retries: int = None
) -> Dict[str, Any]:
    """
    リトライ付きPDF処理
    
    Args:
        local_pdf_path: ローカルPDFパス
        max_retries: 最大リトライ回数
    
    Returns:
        処理結果
    """
    if max_retries is None:
        max_retries = config.VISION_MAX_RETRIES
    
    client = VisionAsyncClient()
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 処理試行 {attempt + 1}/{max_retries}")
            result = client.process_pdf(local_pdf_path)
            
            if result["status"] == "SUCCESS":
                return result
            
            logger.warning(f"⚠️ 試行 {attempt + 1} 失敗: {result.get('error', 'Unknown')}")
            
            # 指数バックオフ
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 10
                logger.info(f"⏳ {wait_time}秒後にリトライ...")
                time.sleep(wait_time)
        
        except GoogleAPIError as e:
            logger.error(f"❌ API エラー: {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 10
                time.sleep(wait_time)
    
    return {"status": "FAILED", "error": f"Max retries ({max_retries}) exceeded"}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python gcs_vision_client.py <pdf_path>")
        print("       python gcs_vision_client.py --test")
        sys.exit(1)
    
    if sys.argv[1] == "--test":
        # GCS接続テスト
        gcs = GCSClient()
        print(f"✅ GCS接続OK: プロジェクト {config.GCP_PROJECT_ID}")
    else:
        pdf_path = Path(sys.argv[1])
        result = process_pdf_with_retry(pdf_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
