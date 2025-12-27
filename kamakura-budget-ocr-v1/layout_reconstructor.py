# layout_reconstructor.py
import json, os, glob
import numpy as np
from sklearn.cluster import KMeans
from helpers import dump_json, simple_logger
from config import PAGE_Y_TOLERANCE_RATIO

logger = simple_logger(__name__)

def group_words_to_lines(words, page_height):
    y_tol = max(8, int(page_height * PAGE_Y_TOLERANCE_RATIO))
    words_sorted = sorted(words, key=lambda w: (w['top'], w['left']))
    lines = []
    current = []
    current_y = None
    for w in words_sorted:
        if current_y is None:
            current=[w]; current_y = w['top']
        elif abs(w['top'] - current_y) <= y_tol:
            current.append(w)
        else:
            lines.append(sorted(current, key=lambda x: x['left']))
            current=[w]; current_y = w['top']
    if current:
        lines.append(sorted(current, key=lambda x: x['left']))
    out_lines=[]
    for l in lines:
        text = " ".join([c['text'] for c in l])
        left = min(c['left'] for c in l)
        top = min(c['top'] for c in l)
        right = max(c['right'] for c in l)
        out_lines.append({'text':text,'left':left,'top':top,'right':right,'words':l})
    return out_lines

def detect_table_blocks(lines):
    import re
    table_blocks=[]
    i=0
    while i < len(lines):
        def is_numeric_line(ln): return bool(re.search(r'[0-9０-９,，△\\-]+', ln['text']))
        if is_numeric_line(lines[i]):
            start=i
            while i < len(lines) and is_numeric_line(lines[i]):
                i+=1
            end=i
            if end-start>=2:
                table_blocks.append((start,end))
        else:
            i+=1
    return table_blocks

def cluster_columns(lines, start,end, max_k=6):
    xs=[]
    words=[]
    for ln in lines[start:end]:
        for w in ln['words']:
            xs.append([w['left']])
            words.append(w)
    if len(xs)==0:
        return []
    xs_arr=np.array(xs)
    best_k=2
    prev_inertia=None
    for k in range(2, min(max_k, len(xs_arr))+1):
        km=KMeans(n_clusters=k, random_state=0).fit(xs_arr)
        if prev_inertia is None:
            prev_inertia = km.inertia_
            best_k = k
        else:
            drop = prev_inertia - km.inertia_
            if drop < 1e-3:
                break
            prev_inertia = km.inertia_
            best_k = k
    km=KMeans(n_clusters=best_k, random_state=0).fit(xs_arr)
    cols=[[] for _ in range(best_k)]
    for idx,label in enumerate(km.labels_):
        cols[label].append(words[idx])
    cols_sorted = sorted(cols, key=lambda c: np.mean([w['left'] for w in c]) if len(c)>0 else 1e9)
    return cols_sorted

def reconstruct_page(parsed_page_json, out_struct_json, page_height=3000):
    with open(parsed_page_json, 'r', encoding='utf-8') as f:
        words = json.load(f)
    lines = group_words_to_lines(words, page_height)
    tables_idx = detect_table_blocks(lines)
    tables=[]
    for (s,e) in tables_idx:
        cols = cluster_columns(lines,s,e)
        rows=[]
        for ln in lines[s:e]:
            row = []
            for col in cols:
                if len(col)==0:
                    row.append('')
                    continue
                col_mean = np.mean([w['left'] for w in col])
                candidate = min(ln['words'], key=lambda w: abs(w['left']-col_mean))
                row.append(candidate['text'])
            rows.append(row)
        tables.append({'start':s,'end':e,'cols':len(cols),'rows':rows})
    out = {'lines':lines,'tables':tables}
    dump_json(out, out_struct_json)
    return out

def batch_reconstruct(parsed_dir, out_dir, page_height=3000):
    os.makedirs(out_dir, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(parsed_dir,"page_*.json"))):
        name = os.path.basename(p).replace(".json","")
        outp = os.path.join(out_dir, name + "_struct.json")
        reconstruct_page(p, outp, page_height)
    logger.info("Layout reconstruction finished.")
