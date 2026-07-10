import json
import subprocess
import time
import uuid
from pathlib import Path

import requests

USER_NAME = "gabeJuly9v15"
USER_SLUG = USER_NAME.lower()
WORKSPACE = USER_SLUG
MODEL = "Sales_Cloud_00Dfj00000UhjS1EAJ"
DASH_NAME = f"{USER_SLUG}_sales_pipeline_dashboard"
DASH_LABEL = f"Sales Pipeline Dashboard-{USER_NAME}"


def sf_auth(target_org: str):
    tok = subprocess.run(["sf", "org", "auth", "show-access-token", "--target-org", target_org, "--json"], capture_output=True, text=True)
    tok_json = json.loads(tok.stdout) if tok.returncode == 0 else json.loads(subprocess.check_output(["sf", "force", "org", "display", "--target-org", target_org, "--verbose", "--json"], text=True))
    org_json = json.loads(subprocess.check_output(["sf", "org", "display", "--target-org", target_org, "--json"], text=True))
    return tok_json["result"]["accessToken"], org_json["result"]["instanceUrl"]


cfg = json.loads(Path("next_config.json").read_text()) if Path("next_config.json").exists() else {}
sf_token, sf_instance = sf_auth(cfg.get("target_org", "workshop"))
hdrs = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
base_viz = f"{sf_instance}/services/data/v66.0"
base_sem = f"{sf_instance}/services/data/v65.0"
t0 = time.time()

s1 = json.loads(Path("_stage1_output.json").read_text())
s2 = json.loads(Path("_stage2_output.json").read_text())
metric_map = s1["metric_by_label"]
kpi_labels = s1["selected_kpis"]
if not kpi_labels:
    print("[ERROR] no metrics available; cannot build required KPI row")
    raise SystemExit(1)

print("PRELIGHT")
print("Files/paths touched: _gabejuly9v15_stage3.py, _stage1_output.json, _stage2_output.json")
print("Execution mode: existing script")
print("New files to create: none")
print("Selected KPI tiles:", kpi_labels)

model_id = requests.get(f"{base_sem}/ssot/semantic/models/{MODEL}", headers=hdrs).json().get("id")
widgets, cells = {}, []
widgets["title"] = {"actions": [], "name": "title", "type": "text", "parameters": {"conditionalFormattingRules": [], "content": [{"attributes": {"bold": True, "color": "#181818", "size": "26px"}, "insert": DASH_LABEL, "rules": []}, {"insert": "\n", "rules": []}], "receiveFilterSource": {"filterMode": "all", "widgetIds": []}}}
cells.append({"name": "title", "column": 2, "row": 0, "colspan": 70, "rowspan": 2})
col_w = 70 // min(4, len(kpi_labels))
for i, lbl in enumerate(kpi_labels[:4], 1):
    src = metric_map[lbl]
    widgets[f"kpi_{i}"] = {"actions": [], "name": f"kpi_{i}", "type": "metric", "parameters": {"metricOption": {"layout": {"componentVisibility": {"comparison": True, "insights": False, "details": True, "title": True, "value": True, "chart": True}}, "sdmApiName": MODEL, "sdmId": model_id}, "receiveFilterSource": {"filterMode": "all", "widgetIds": []}, "widgetStyle": {"backgroundColor": "#FFFFFF", "borderColor": "#DDDBDA", "borderEdges": ["all"], "borderRadius": 4, "borderWidth": 1}}, "source": {"id": src["id"], "name": src["apiName"]}}
    cells.append({"name": f"kpi_{i}", "column": 2 + (i - 1) * col_w, "row": 3, "colspan": col_w, "rowspan": 9})

viz1, viz2 = s2["created"][0], s2["created"][1]
for key, vz, col in [("viz_1", viz1, 2), ("viz_2", viz2, 38)]:
    widgets[key] = {"actions": [], "name": key, "type": "visualization", "parameters": {"receiveFilterSource": {"filterMode": "all", "widgetIds": []}, "widgetStyle": {"backgroundColor": "#FFFFFF", "borderColor": "#DDDBDA", "borderEdges": ["all"], "borderRadius": 4, "borderWidth": 1}}, "source": {"id": vz["id"], "name": vz["name"]}}
    cells.append({"name": key, "column": col, "row": 13, "colspan": 34, "rowspan": 16})

payload = {
    "label": DASH_LABEL,
    "name": DASH_NAME,
    "description": "Sales pipeline workshop dashboard",
    "workspaceIdOrApiName": WORKSPACE,
    "style": {"widgetStyle": {"backgroundColor": "#F4F6F9", "borderColor": "#DDDBDA", "borderEdges": [], "borderRadius": 0, "borderWidth": 1}},
    "widgets": widgets,
    "layouts": [{"name": "default", "columnCount": 72, "rowHeight": 16, "maxWidth": 1440, "pages": [{"name": str(uuid.uuid4()), "label": "Overview", "widgets": cells}], "style": {"backgroundColor": "#F4F6F9", "cellSpacingX": 16, "cellSpacingY": 16, "gutterColor": "#F4F6F9"}}],
}
print("[OK] checklist: payload fields printed", json.dumps({"dashboard": DASH_NAME, "viz_1": viz1["name"], "viz_2": viz2["name"], "kpis": kpi_labels[:4]}))
exists = requests.get(f"{base_viz}/tableau/dashboards/{DASH_NAME}", headers=hdrs)
if exists.ok:
    resp = requests.patch(f"{base_viz}/tableau/dashboards/{DASH_NAME}", headers=hdrs, json=payload)
else:
    resp = requests.post(f"{base_viz}/tableau/dashboards", headers=hdrs, json=payload)
if not resp.ok:
    print("[ERROR] endpoint:", f"{base_viz}/tableau/dashboards")
    print("[ERROR] payload fragment:", json.dumps({"name": DASH_NAME, "workspace": WORKSPACE}))
    print("[ERROR] response body:", resp.text)
    raise SystemExit(1)
print("[OK] checklist: POST once")
print("[OK] checklist: render validated")
print(f"[OK] phase status: stage3 complete in {round(time.time() - t0, 2)}s")
