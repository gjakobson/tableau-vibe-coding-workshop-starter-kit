import json
import subprocess
import time
from pathlib import Path

import requests

USER_NAME = "gabeJuly9v15"
USER_SLUG = USER_NAME.lower()
WORKSPACE = USER_SLUG
MODEL = "Sales_Cloud_00Dfj00000UhjS1EAJ"
BASE_CALC = f"{USER_SLUG}_avg_probability"
CALC_API = f"{BASE_CALC}_clc"
METRIC_API = f"{BASE_CALC}_mtc"


def sf_auth(target_org: str):
    tok = subprocess.run(
        ["sf", "org", "auth", "show-access-token", "--target-org", target_org, "--json"],
        capture_output=True,
        text=True,
    )
    if tok.returncode == 0:
        tok_json = json.loads(tok.stdout)
    else:
        tok_json = json.loads(
            subprocess.check_output(
                ["sf", "force", "org", "display", "--target-org", target_org, "--verbose", "--json"],
                text=True,
            )
        )
    org_json = json.loads(subprocess.check_output(["sf", "org", "display", "--target-org", target_org, "--json"], text=True))
    return tok_json["result"]["accessToken"], org_json["result"]["instanceUrl"]


cfg = json.loads(Path("next_config.json").read_text()) if Path("next_config.json").exists() else {}
target_org = cfg.get("target_org", "workshop")
sf_token, sf_instance = sf_auth(target_org)
hdrs = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
base_sem = f"{sf_instance}/services/data/v65.0"
t0 = time.time()

print("PRELIGHT")
print("Files/paths touched: _gabejuly9v15_stage1.py, _stage1_output.json")
print("Execution mode: existing script")
print("New files to create: _stage1_output.json")

r = requests.get(f"{base_sem}/ssot/semantic/models/{MODEL}", headers=hdrs, params={"includeModelContent": True})
r.raise_for_status()
model = r.json()
print("[OK] checklist: manifest built")

calc_measures = {c.get("apiName"): c for c in model.get("semanticCalculatedMeasurements", [])}
calc_dims = {c.get("apiName"): c for c in model.get("semanticCalculatedDimensions", [])}
date_calc_dim = next((c.get("apiName") for c in model.get("semanticCalculatedDimensions", []) if c.get("dataType") in ("Date", "DateTime")), None)
if not date_calc_dim:
    date_calc_dim = "Today"
metrics_resp = requests.get(f"{base_sem}/ssot/semantic/models/{MODEL}/metrics", headers=hdrs)
metrics_resp.raise_for_status()
metrics = metrics_resp.json().get("metrics", [])
metric_by_label = {m.get("label"): {"apiName": m.get("apiName"), "id": m.get("id")} for m in metrics}

if CALC_API not in calc_measures:
    payload = {
        "apiName": CALC_API,
        "label": f"Average Probability-{USER_NAME}",
        "description": "Average opportunity close probability percentage for sales pipeline monitoring.",
        "expression": "[Opportunity].[Probability]",
        "aggregationType": "Average",
        "dataType": "Percentage",
        "decimalPlace": 2,
        "directionality": "Up",
        "displayCategory": "Continuous",
        "level": "Row",
        "isVisible": True,
        "shouldTreatNullsAsZeros": False,
        "sortOrder": "Ascending",
        "sentiment": "SentimentTypeUpIsGood",
    }
    print("[OK] payload fields printed: calculated-measurement", json.dumps({"apiName": payload["apiName"], "aggregationType": payload["aggregationType"]}))
    c_resp = requests.post(f"{base_sem}/ssot/semantic/models/{MODEL}/calculated-measurements", headers=hdrs, json=payload)
    if not c_resp.ok:
        print("[ERROR] endpoint:", f"{base_sem}/ssot/semantic/models/{MODEL}/calculated-measurements")
        print("[ERROR] payload fragment:", json.dumps({"apiName": payload["apiName"], "label": payload["label"]}))
        print("[ERROR] response body:", c_resp.text)
        raise SystemExit(1)
    print("[OK] checklist: POST once (calc)")
else:
    print("[WARN] calc already exists; skipping create")

if METRIC_API not in {m.get("apiName") for m in metrics}:
    metric_payload = {
        "apiName": METRIC_API,
        "label": f"Average Probability-{USER_NAME}",
        "description": "Average opportunity close probability percentage for sales pipeline monitoring.",
        "measurementReference": {"calculatedFieldApiName": CALC_API},
        "timeDimensionReference": {"calculatedFieldApiName": date_calc_dim},
        "aggregationType": "Average",
        "isCumulative": False,
        "timeGrains": ["Month", "Quarter", "Year"],
    }
    print("[OK] payload fields printed: metric", json.dumps({"apiName": metric_payload["apiName"], "aggregationType": metric_payload["aggregationType"]}))
    m_resp = requests.post(f"{base_sem}/ssot/semantic/models/{MODEL}/metrics", headers=hdrs, json=metric_payload)
    if not m_resp.ok:
        print("[ERROR] endpoint:", f"{base_sem}/ssot/semantic/models/{MODEL}/metrics")
        print("[ERROR] payload fragment:", json.dumps({"apiName": metric_payload["apiName"], "label": metric_payload["label"]}))
        print("[ERROR] response body:", m_resp.text)
        raise SystemExit(1)
    print("[OK] checklist: POST once (metric)")
else:
    print("[WARN] metric already exists; skipping create")

metrics_after = requests.get(f"{base_sem}/ssot/semantic/models/{MODEL}/metrics", headers=hdrs).json().get("metrics", [])
metric_by_label = {m.get("label"): {"apiName": m.get("apiName"), "id": m.get("id")} for m in metrics_after}
selected_labels = ["Total Sales", "Win Rate", "# of Opportunities", "Weighted Pipeline Value"]
selected = [x for x in selected_labels if x in metric_by_label]
print("Selected KPI tiles:", selected)
print("[OK] checklist: render validated (N/A stage1)")

out = {
    "sf_instance": sf_instance,
    "workspace": WORKSPACE,
    "model": MODEL,
    "calc_api": CALC_API,
    "metric_api": METRIC_API,
    "metric_by_label": metric_by_label,
    "selected_kpis": selected,
    "elapsed_seconds": round(time.time() - t0, 2),
}
Path("_stage1_output.json").write_text(json.dumps(out, indent=2))
print(f"[OK] phase status: stage1 complete in {out['elapsed_seconds']}s")
