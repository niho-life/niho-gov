# helpers.py
import os, json, logging, time
from datetime import datetime

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def now_ts():
    return datetime.utcnow().isoformat() + "Z"

def dump_json(obj, path):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def simple_logger(name=__name__):
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        f = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        h.setFormatter(f)
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger
