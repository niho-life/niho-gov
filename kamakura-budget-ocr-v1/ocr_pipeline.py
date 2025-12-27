# ocr_pipeline.py
import argparse, os, glob, json
from helpers import ensure_dir, dump_json, simple_logger, now_ts
from config import OCR_RAW_DIR, PARSED_DIR, STRUCT_DIR, FINAL_JSON, LOG_DIR, LOCAL_WORKDIR, GCV_OUTPUT_PREFIX
from gcv_client import async_vision_pdf, download_output_files
from ocr_normalizer import parse_gcv_json_file
from layout_reconstructor import batch_reconstruct
from project_segmenter import extract_blocks_from_struct
from json_converter import build_project_from_block
from validator import validate_project, compute_confidence

logger = simple_logger(__name__)

def run_pipeline(gcs_input, gcs_output_prefix, local):
    # prepare dirs
    ensure_dir(local)
    ocr_raw = OCR_RAW_DIR
    parsed = PARSED_DIR
    struct = STRUCT_DIR
    ensure_dir(ocr_raw); ensure_dir(parsed); ensure_dir(struct); ensure_dir(os.path.dirname(FINAL_JSON)); ensure_dir(LOG_DIR)

    # 1. submit GCV job
    async_vision_pdf(gcs_input, gcs_output_prefix)

    # 2. download outputs
    files = download_output_files(gcs_output_prefix, ocr_raw)

    # 3. normalize -> parsed
    for f in files:
        parse_gcv_json_file(f, parsed)

    # 4. layout reconstruct -> struct
    batch_reconstruct(parsed, struct)

    # 5. segment & build projects
    projects=[]
    for sfile in sorted(glob.glob(os.path.join(struct, "*_struct.json"))):
        # load struct
        struct_obj = json.load(open(sfile, 'r', encoding='utf-8'))
        page_idx = int(os.path.basename(sfile).split('_')[1])
        blocks = extract_blocks_from_struct(struct_obj)
        for b in blocks:
            proj = build_project_from_block(b, page_idx)
            flags = validate_project(proj)
            proj['flags'] = flags
            proj['confidence'] = compute_confidence(proj)
            projects.append(proj)

    # 6. write final
    final = {'metadata': {'extracted_at': now_ts()}, 'projects': projects}
    dump_json(final, FINAL_JSON)
    logger.info("Final JSON written to %s", FINAL_JSON)
    # also write csvs if needed
    print("Pipeline done. Projects:", len(projects))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gcs_input', required=True, help='gs://bucket/file.pdf')
    parser.add_argument('--gcs_output_prefix', required=True, help='gs://bucket/prefix/')
    parser.add_argument('--local', default='./output', help='local workdir')
    args = parser.parse_args()
    run_pipeline(args.gcs_input, args.gcs_output_prefix, args.local)
