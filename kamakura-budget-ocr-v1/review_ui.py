# review_ui.py
# 非常にシンプルなレビューワ。productionでは認証・CSRFなど必須。
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import json, os
from config import FINAL_JSON, OCR_RAW_DIR

app = Flask(__name__)

TEMPLATE_INDEX = """
<!doctype html>
<title>OCR Review</title>
<h2>OCR Review - Low confidence / flagged records</h2>
<ul>
{% for p in projects %}
  <li>
    <a href="{{ url_for('review', proj_id=loop.index0) }}">{{ p['name'] or p['id'] }} (page {{ p['source_page'] }})</a>
    - flags: {{ p['flags'] }}
  </li>
{% endfor %}
</ul>
"""

TEMPLATE_REVIEW = """
<!doctype html>
<title>Review {{proj['id']}}</title>
<h3>{{proj['name']}} ({{proj['id']}}) - page {{proj['source_page']}}</h3>
<p>Flags: {{proj['flags']}}</p>
<form method="post">
  <label>Name</label><br>
  <input name="name" value="{{proj['name']}}" style="width:60%"><br>
  <label>Department</label><br>
  <input name="dept" value="{{proj.get('department','') }}" style="width:60%"><br>
  <label>Total (千円)</label><br>
  <input name="total" value="{{proj.get('budget',{}).get('total','') }}" style="width:20%"><br>
  <label>Notes</label><br>
  <textarea name="notes" style="width:60%;height:120px">{{proj.get('notes','')}}</textarea><br>
  <button type="submit">Save</button>
</form>
<p><a href="{{url_for('index')}}">Back</a></p>
"""

def load_projects():
    if not os.path.exists(FINAL_JSON):
        return []
    with open(FINAL_JSON, 'r', encoding='utf-8') as f:
        j = json.load(f)
    return j.get('projects', [])

def save_projects(projects):
    if not os.path.exists(FINAL_JSON):
        base = {'metadata': {}, 'projects': projects}
    else:
        base = json.load(open(FINAL_JSON, 'r', encoding='utf-8'))
        base['projects'] = projects
    json.dump(base, open(FINAL_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

@app.route("/")
def index():
    projects = load_projects()
    flagged = [p for p in projects if p.get('flags')]
    return render_template_string(TEMPLATE_INDEX, projects=flagged)

@app.route("/review/<int:proj_id>", methods=['GET','POST'])
def review(proj_id):
    projects = load_projects()
    if proj_id < 0 or proj_id >= len(projects):
        return "Not found", 404
    proj = projects[proj_id]
    if request.method == 'POST':
        proj['name'] = request.form.get('name')
        proj['department'] = request.form.get('dept')
        try:
            total = int(request.form.get('total'))
            proj['budget']['total'] = total
        except:
            pass
        proj['notes'] = request.form.get('notes')
        # clear flags after manual review
        proj['flags'] = []
        save_projects(projects)
        return redirect(url_for('index'))
    return render_template_string(TEMPLATE_REVIEW, proj=proj)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
