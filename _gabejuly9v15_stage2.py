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
SOURCES = [
    ("Pipeline_Performance_Trend", f"{USER_SLUG}_pipeline_trend_v2", f"Pipeline Trend-{USER_NAME}"),
    ("Open_Pipeline_by_Opportunity_Stage", f"{USER_SLUG}_pipeline_by_stage_v2", f"Pipeline by Stage-{USER_NAME}"),
]
ALLOW = {"name", "label", "description", "dataSource", "workspace", "fields", "interactions", "view", "visualSpecification"}


def sf_auth(target_org: str):
    tok = subprocess.run(["sf", "org", "auth", "show-access-token", "--target-org", target_org, "--json"], capture_output=True, text=True)
    tok_json = json.loads(tok.stdout) if tok.returncode == 0 else json.loads(subprocess.check_output(["sf", "force", "org", "display", "--target-org", target_org, "--verbose", "--json"], text=True))
    org_json = json.loads(subprocess.check_output(["sf", "org", "display", "--target-org", target_org, "--json"], text=True))
    return tok_json["result"]["accessToken"], org_json["result"]["instanceUrl"]


def strip_ro(x):
    if isinstance(x, dict):
        bad = {"id", "status", "isOriginal", "createdDate", "createdBy", "lastModifiedDate", "lastModifiedBy", "url", "permissions", "sourceVersion"}
        return {k: strip_ro(v) for k, v in x.items() if k not in bad}
    if isinstance(x, list):
        return [strip_ro(i) for i in x]
    return x


cfg = json.loads(Path("next_config.json").read_text()) if Path("next_config.json").exists() else {}
sf_token, sf_instance = sf_auth(cfg.get("target_org", "workshop"))
hdrs = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
base_viz = f"{sf_instance}/services/data/v66.0"
t0 = time.time()
print("PRELIGHT")
print("Files/paths touched: _gabejuly9v15_stage2.py, _stage1_output.json, _stage2_output.json")
print("Execution mode: existing script")
print("New files to create: _stage2_output.json")

all_v = requests.get(f"{base_viz}/tableau/visualizations", headers=hdrs, params={"limit": 200}).json().get("visualizations", [])
for _, target_name, _ in SOURCES:
    for v in [x for x in all_v if x.get("name") == target_name and (x.get("workspace") or {}).get("name", "").lower() == WORKSPACE]:
        requests.delete(f"{base_viz}/tableau/visualizations/{v['name']}", headers=hdrs)

out = {"created": []}
for idx, (source_name, target_name, target_label) in enumerate(SOURCES, 1):
    src = requests.get(f"{base_viz}/tableau/visualizations/{source_name}", headers=hdrs)
    if not src.ok:
        print("[ERROR] Missing required source visualization:", source_name)
        raise SystemExit(1)
    raw = strip_ro(src.json())
    payload = {k: raw[k] for k in ALLOW if k in raw}
    payload["name"] = target_name
    payload["label"] = target_label
    payload["workspace"] = {"name": WORKSPACE}
    payload["dataSource"] = {"name": MODEL, "type": "SemanticModel"}
    print("[OK] checklist: payload fields printed", json.dumps({"name": payload["name"], "source": source_name, "keys": sorted(payload.keys())}))
    created = requests.post(f"{base_viz}/tableau/visualizations", headers=hdrs, json=payload)
    if not created.ok:
        print("[ERROR] endpoint:", f"{base_viz}/tableau/visualizations")
        print("[ERROR] payload fragment:", json.dumps({"name": payload["name"], "label": payload["label"]}))
        print("[ERROR] response body:", created.text)
        raise SystemExit(1)
    vj = created.json()
    if not vj.get("name"):
        print("[ERROR] response missing name for", target_name)
        raise SystemExit(1)
    print("[OK] checklist: POST once")
    temp_name = f"{target_name}_render_temp"
    temp_payload = {
        "name": temp_name,
        "label": f"render-{target_label}",
        "description": "temp render validation",
        "workspaceIdOrApiName": WORKSPACE,
        "style": {"widgetStyle": {"backgroundColor": "#F4F6F9", "borderColor": "#DDDBDA", "borderEdges": [], "borderRadius": 0, "borderWidth": 1}},
        "widgets": {"viz_1": {"actions": [], "name": "viz_1", "type": "visualization", "parameters": {"receiveFilterSource": {"filterMode": "all", "widgetIds": []}, "widgetStyle": {"backgroundColor": "#FFFFFF", "borderColor": "#DDDBDA", "borderEdges": ["all"], "borderRadius": 4, "borderWidth": 1}}, "source": {"id": vj["id"], "name": vj["name"]}}},
        "layouts": [{"name": "default", "columnCount": 72, "rowHeight": 16, "maxWidth": 1440, "pages": [{"name": str(uuid.uuid4()), "label": "Overview", "widgets": [{"name": "viz_1", "column": 2, "row": 3, "colspan": 68, "rowspan": 24}]}], "style": {"backgroundColor": "#F4F6F9", "cellSpacingX": 16, "cellSpacingY": 16, "gutterColor": "#F4F6F9"}}],
    }
    rv = requests.post(f"{base_viz}/tableau/dashboards", headers=hdrs, json=temp_payload)
    if rv.status_code != 201:
        print("[ERROR] endpoint:", f"{base_viz}/tableau/dashboards")
        print("[ERROR] payload fragment:", json.dumps({"name": temp_name, "viz": vj["name"]}))
        print("[ERROR] response body:", rv.text)
        raise SystemExit(1)
    requests.delete(f"{base_viz}/tableau/dashboards/{temp_name}", headers=hdrs)
    print("[OK] checklist: render validated")
    print(f"[OK] phase status: viz{idx} complete in {round(time.time()-t0,2)}s")
    out["created"].append({"source": source_name, "name": vj["name"], "id": vj["id"], "label": vj.get("label", target_label)})

Path("_stage2_output.json").write_text(json.dumps(out, indent=2))
