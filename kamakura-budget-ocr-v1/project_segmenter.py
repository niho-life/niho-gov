# project_segmenter.py
# 事業ブロックの開始/終了を判断してブロック単位で切り出す（単純ヒューリスティック）
import re, json
from helpers import dump_json, simple_logger
logger = simple_logger(__name__)

def is_kumoku_line(text):
    return bool(re.search(r'（款）|（項）|（目）', text))

def is_header_marker(text):
    return '◎' in text or '事業名' in text

def is_purpose_label(text):
    return '事業の目的' in text or '【事業の目的' in text

def segment_projects(struct):
    lines = struct.get('lines', [])
    projects = []
    current = {'lines': [], 'tables': []}
    for i,ln in enumerate(lines):
        text = ln.get('text','')
        if is_kumoku_line(text) and current['lines']:
            projects.append(current)
            current = {'lines': [ln], 'tables': []}
        else:
            current['lines'].append(ln)
    if current['lines']:
        projects.append(current)
    # attach tables to projects (simple heuristic: table.start between lines index)
    # Here we skip complex mapping and assume tables live within their page block
    return projects

def extract_blocks_from_struct(struct):
    blocks = segment_projects(struct)
    # produce minimal block object
    out = []
    for idx,b in enumerate(blocks, start=1):
        text = "\n".join([l['text'] for l in b['lines']])
        out.append({'block_id': idx, 'text': text, 'lines': b['lines']})
    return out
