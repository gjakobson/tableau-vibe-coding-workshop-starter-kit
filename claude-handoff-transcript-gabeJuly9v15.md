# Workshop Run Transcript Export (for Claude)

This is a clean handoff transcript of the `/start-workshop` run for user `gabeJuly9v15`, including the Python snippets used to execute the flow.

## Session Context

- Workspace: `tableau-vibe-coding-workshop-starter-kit`
- User name: `gabeJuly9v15`
- Workspace name: `gabejuly9v15`
- Selected model: `Sales_Cloud_00Dfj00000UhjS1EAJ`
- Selected options: `1-3` (calc/metric + visualizations + dashboard)
- Theme: `sales pipeline`

## Step-by-Step Execution Transcript

1) Read required reference file:
- `Reference Files/ref-pitfalls.md`

2) Auth check script run:
- `_check_auth.py`
- Result: `AUTH_OK_NO_DC: https://orgfarm-de51d92008.my.salesforce.com (Data Cloud scope unavailable)`
- Proceeded with Salesforce-only Semantics/Viz flow.

3) User identity set:
- Input: `gabeJuly9v15`

4) Workspace discovery:
- Script: `_find_or_create_workspace.py`
- Result: `FOUND_WORKSPACE: gabejuly9v15`

5) Model list:
- Script: `_list_models.py`
- Result included:
  - `1. Sales_Cloud [Sales_Cloud_00Dfj00000UhjS1EAJ]`

6) Model inspection:
- Script: `_inspect_model.py`
- Confirmed Opportunity object, existing calculated fields, and metrics.

7) Build run (Options 1/2/3, Sales pipeline):
- Stage 1: `_gabejuly9v15_stage1.py`
  - Built model manifest and KPI map.
  - Created calc: `gabejuly9v15_avg_probability_clc` (if missing).
  - First metric POST failed with:
    - `The [timeDimensionReference] field is missing.`
  - Applied one fix + one retry:
    - Added `timeDimensionReference` from calculated date dimension.
  - Created metric: `gabejuly9v15_avg_probability_mtc`.
  - KPI selection: `['Total Sales', 'Win Rate', '# of Opportunities', 'Weighted Pipeline Value']`

- Stage 2: `_gabejuly9v15_stage2.py`
  - Clone source viz 1:
    - `Pipeline_Performance_Trend` -> `gabejuly9v15_pipeline_trend_v2`
  - Clone source viz 2:
    - `Open_Pipeline_by_Opportunity_Stage` -> `gabejuly9v15_pipeline_by_stage_v2`
  - For each clone:
    - allow-list payload
    - strip read-only fields
    - POST create
    - render validation with temporary one-viz dashboard (HTTP 201)
    - temp dashboard deleted

- Stage 3: `_gabejuly9v15_stage3.py`
  - Built dashboard:
    - `gabejuly9v15_sales_pipeline_dashboard`
  - Added KPI row from metric `apiName` values.
  - Added viz widgets using cloned viz names/IDs from Stage 2.
  - POST/PATCH success with render validation log line.

---

## Python Snippet: Auth Check (`_check_auth.py`)

```python
import json
import subprocess
from pathlib import Path

import requests

cfg = json.loads(Path("next_config.json").read_text()) if Path("next_config.json").exists() else {}
target_org = cfg.get("target_org", "workshop")

tok = subprocess.run(
    ["sf", "org", "auth", "show-access-token", "--target-org", target_org, "--json"],
    capture_output=True,
    text=True,
)
org = subprocess.run(
    ["sf", "org", "display", "--target-org", target_org, "--json"],
    capture_output=True,
    text=True,
)

if tok.returncode != 0:
    tok = subprocess.run(
        ["sf", "force", "org", "display", "--target-org", target_org, "--verbose", "--json"],
        capture_output=True,
        text=True,
    )

if tok.returncode != 0 or org.returncode != 0:
    print("SF_AUTH_FAILED: login missing or invalid org alias")
else:
    sf_token = json.loads(tok.stdout)["result"]["accessToken"]
    sf_instance = json.loads(org.stdout)["result"]["instanceUrl"]
    r2 = requests.post(
        sf_instance + "/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:salesforce:grant-type:external:cdp",
            "subject_token": sf_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        },
    )
    if not r2.ok:
        print("AUTH_OK_NO_DC: " + sf_instance + " (Data Cloud scope unavailable)")
    else:
        print("AUTH_OK: " + sf_instance)
```

## Python Snippet: Stage 1 (Manifest + Calc + Metric)

```python
# key payloads from _gabejuly9v15_stage1.py
payload = {
    "apiName": CALC_API,
    "label": f"Average Probability-{USER_NAME}",
    "description": "Average opportunity close probability percentage for sales pipeline monitoring.",
    "expression": "[Opportunity].[Probability]",
    "aggregationType": "Average",
    "dataType": "Percentage",
    "level": "Row",
}

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
```

## Python Snippet: Stage 2 (Clone + Allow-list + Render Gate)

```python
ALLOW = {"name", "label", "description", "dataSource", "workspace", "fields", "interactions", "view", "visualSpecification"}

raw = strip_ro(src.json())
payload = {k: raw[k] for k in ALLOW if k in raw}
payload["name"] = target_name
payload["label"] = target_label
payload["workspace"] = {"name": WORKSPACE}
payload["dataSource"] = {"name": MODEL, "type": "SemanticModel"}

created = requests.post(f"{base_viz}/tableau/visualizations", headers=hdrs, json=payload)

# Render proof gate: temp one-viz dashboard must return HTTP 201
rv = requests.post(f"{base_viz}/tableau/dashboards", headers=hdrs, json=temp_payload)
if rv.status_code != 201:
    raise SystemExit(1)
```

## Python Snippet: Stage 3 (Dashboard + KPI Row + Rewire)

```python
for i, lbl in enumerate(kpi_labels[:4], 1):
    src = metric_map[lbl]
    widgets[f"kpi_{i}"] = {
        "type": "metric",
        "source": {"id": src["id"], "name": src["apiName"]},
        "parameters": {
            "metricOption": {"sdmApiName": MODEL, "sdmId": model_id},
            "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
        },
    }

viz1, viz2 = s2["created"][0], s2["created"][1]
widgets["viz_1"] = {"type": "visualization", "source": {"id": viz1["id"], "name": viz1["name"]}}
widgets["viz_2"] = {"type": "visualization", "source": {"id": viz2["id"], "name": viz2["name"]}}

payload = {
    "label": DASH_LABEL,
    "name": DASH_NAME,
    "workspaceIdOrApiName": WORKSPACE,
    "widgets": widgets,
    "layouts": [...],
}
```

## Final Artifacts Created

- Calculated field: `gabejuly9v15_avg_probability_clc`
- Metric: `gabejuly9v15_avg_probability_mtc`
- Visualization: `gabejuly9v15_pipeline_trend_v2`
- Visualization: `gabejuly9v15_pipeline_by_stage_v2`
- Dashboard: `gabejuly9v15_sales_pipeline_dashboard`

## Files Generated During Run

- `_check_auth.py`
- `_find_or_create_workspace.py`
- `_list_models.py`
- `_inspect_model.py`
- `_gabejuly9v15_stage1.py`
- `_stage1_output.json`
- `_gabejuly9v15_stage2.py`
- `_stage2_output.json`
- `_gabejuly9v15_stage3.py`

