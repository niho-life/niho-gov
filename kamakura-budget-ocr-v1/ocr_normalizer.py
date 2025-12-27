# ocr_normalizer.py
# GCV JSON -> per-page word list (text, left, top, right, bottom, conf)
import json, os, glob
from helpers import dump_json, simple_logger
logger = simple_logger(__name__)

def parse_gcv_json_file(json_path, out_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    responses = data.get('responses', [])
    out_files = []
    page_global_idx = 0
    for resp in responses:
        fta = resp.get('fullTextAnnotation', {})
        pages = fta.get('pages', [])
        for p_idx, page in enumerate(pages):
            page_global_idx += 1
            words = []
            for block in page.get('blocks', []):
                for para in block.get('paragraphs', []):
                    for word in para.get('words', []):
                        txt = ''.join([s.get('text','') for s in word.get('symbols', [])]).strip()
                        if txt == "":
                            continue
                        bbox = word.get('boundingBox', {}).get('vertices', [])
                        xs = [v.get('x',0) for v in bbox]
                        ys = [v.get('y',0) for v in bbox]
                        left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
                        conf = word.get('confidence', None)
                        words.append({'text': txt, 'left': left, 'top': top, 'right': right, 'bottom': bottom, 'conf': conf})
            if not words:
                logger.info("Page %d: no words extracted", page_global_idx)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"page_{page_global_idx:05d}.json")
            dump_json(words, out_path)
            out_files.append(out_path)
    return out_files

def parse_all(input_dir, out_dir):
    for jfile in sorted(glob.glob(os.path.join(input_dir,"*.json"))):
        parse_gcv_json_file(jfile, out_dir)
    logger.info("Normalization done.")
