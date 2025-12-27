# json_converter.py
import re, json
from helpers import dump_json, simple_logger

logger = simple_logger(__name__)

def amount_to_int(s):
    if s is None: return None
    s = str(s)
    s = s.replace('，',',').replace('、',',')
    s = s.replace('△','-').replace('−','-').replace('－','-')
    s = ''.join(c for c in s if c.isdigit() or c in '-,')
    s = s.replace(',','')
    try:
        return int(s) if s!='' else None
    except:
        return None

def extract_category(text):
    m = re.search(r'（款）\\s*([0-9０-９]+).*?（項）\\s*([0-9０-９]+).*?（目）\\s*([0-9０-９]+)', text)
    if m:
        return {'kuan': m.group(1), 'kou': m.group(2), 'moku': m.group(3)}
    return {'kuan':None,'kou':None,'moku':None}

def extract_name_and_department(lines):
    name=None; dept=None
    for i,l in enumerate(lines):
        t = l['text']
        if '◎' in t and i+1 < len(lines):
            name = lines[i+1]['text'].strip()
            # search for 課 or 局 nearby
            for j in range(i+1, min(i+5,len(lines))):
                if '課' in lines[j]['text'] or '局' in lines[j]['text']:
                    dept = lines[j]['text'].strip()
                    break
            break
    if not name:
        # fallback: first non-empty line
        for l in lines:
            if l['text'].strip():
                name = l['text'].strip(); break
    return name, dept

def find_budget_total(lines):
    for i,l in enumerate(lines):
        if '（単位：千円' in l['text'] or '事業費' in l['text'] or '一般財源' in l['text']:
            # search nearby for number
            for j in range(i, min(i+6, len(lines))):
                m = re.search(r'([△\\-\\d,，０-９]+)', lines[j]['text'])
                if m:
                    return amount_to_int(m.group(1))
    # fallback: search whole page
    for l in reversed(lines):
        m = re.search(r'([△\\-\\d,，０-９]{2,})', l['text'])
        if m:
            v = amount_to_int(m.group(1))
            if v and v > 100:
                return v
    return None

def build_project_from_block(block, page_num):
    lines = block.get('lines', [])
    text = "\n".join([l['text'] for l in lines])
    category = extract_category(text)
    name, dept = extract_name_and_department(lines)
    total = find_budget_total(lines)
    # find simple budget details from in-text patterns
    details=[]
    for l in lines:
        m = re.search(r'(\\d+)節\\s*(.+?)\\s+([△\\-\\d,，０-９]+)', l['text'])
        if m:
            sec = int(m.group(1)); item = m.group(2).strip(); amt = amount_to_int(m.group(3))
            details.append({'section':sec,'item':item,'amount':amt})
    project = {
        'id': f"P{page_num:04d}",
        'source_page': page_num,
        'confidence': None,
        'flags': [],
        'category': category,
        'name': name,
        'department': dept,
        'description': [text[:200]],
        'budget': {'unit':'千円','total': total},
        'budget_details': details,
        'raw_text': text
    }
    return project
