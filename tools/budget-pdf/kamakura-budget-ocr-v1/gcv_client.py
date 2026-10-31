# gcv_client.py
# 非同期ジョブ送信 and 出力ダウンロード
from google.cloud import vision_v1
from google.cloud import storage
import os, time
from helpers import ensure_dir, dump_json, now_ts, simple_logger
from config import BATCH_SIZE, TIMEOUT_SECONDS

logger = simple_logger(__name__)

def async_vision_pdf(input_gcs_uri, output_gcs_prefix, batch_size=BATCH_SIZE, mime_type="application/pdf"):
    client = vision_v1.ImageAnnotatorClient()
    gcs_source = {"uri": input_gcs_uri}
    input_config = {"gcs_source": gcs_source, "mime_type": mime_type}
    gcs_destination = {"uri": output_gcs_prefix}
    output_config = {"gcs_destination": gcs_destination, "batch_size": batch_size}
    features = [{"type_": vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION}]
    request = {"input_config": input_config, "features": features, "output_config": output_config}
    logger.info("Submitting GCV async job for %s", input_gcs_uri)
    operation = client.async_batch_annotate_files(requests=[request])
    logger.info("Operation name: %s", operation.operation.name)
    try:
        operation.result(timeout=TIMEOUT_SECONDS)
    except Exception as e:
        logger.error("Operation failed or timed out: %s", e)
        raise
    logger.info("GCV job finished.")
    return operation

def download_output_files(output_gcs_prefix, local_outdir):
    storage_client = storage.Client()
    if not output_gcs_prefix.startswith("gs://"):
        raise ValueError("output_gcs_prefix must be gs://")
    parts = output_gcs_prefix[5:].split("/",1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts)>1 else ""
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    os.makedirs(local_outdir, exist_ok=True)
    files = []
    for blob in blobs:
        if not blob.name.endswith(".json"):
            continue
        dest = os.path.join(local_outdir, os.path.basename(blob.name))
        logger.info("Downloading %s -> %s", blob.name, dest)
        blob.download_to_filename(dest)
        files.append(dest)
    return files
