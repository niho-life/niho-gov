from helpers import simple_logger
logger = simple_logger(__name__)

def validate_project(proj):
    flags=[]
    total = proj.get('budget',{}).get('total')
    details = proj.get('budget_details', [])
    sum_details = sum([d.get('amount',0) or 0 for d in details])
    if total is None:
        flags.append('MISSING_TOTAL')
    else:
        tol = max(int(total * 0.01), 1)
        if abs(total - sum_details) > tol:
            flags.append('BUDGET_MISMATCH')
    if not proj.get('department'):
        flags.append('MISSING_DEPARTMENT')
    return flags

def compute_confidence(proj):
    # naive: if budget exists + name exists -> higher
    score = 0.0
    if proj.get('name'): score += 0.3
    if proj.get('budget',{}).get('total') is not None: score += 0.4
    if proj.get('budget_details'): score += 0.3
    return round(score,2)
