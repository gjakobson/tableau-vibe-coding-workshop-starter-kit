# Reference: Viz Actions (STEP M2 — v66.0)

Read this file when the user wants to assign a click action to a visualization.

---

## Two action types — choose based on user intent

| User intent | Action type | Viz type to create |
|---|---|---|
| "Log a call", "assign a task", "send email" on an opportunity/account/contact | `recordaction` | **Action Table** — see below |
| Open a URL, open a list view, open an external page | `navigate` | Any viz — bar chart, table, etc. |

Actions that fire on mark click live in `interactions`, **not** `actions`. The `actions` array always stays `[]`.

---

## Action type 1 — Salesforce Action (`recordaction`) — CONFIRMED WORKING

**When the user asks to click on a record and trigger a Salesforce action, always create an Action Table.**
This is the only pattern confirmed to work reliably.

**Confirmed structure** (from `detail_chart_fg_republished`, 2026-05-28):
```
mode: "Visualization"   ← NOT "Table"
mark type: "Text"
marks.ALL.isAutomatic: true
marks.ALL.showMarkLabels: true
rows: [all dim fields including record ID]
columns: []
measureValues: []
measures → marks.ALL.encodings with type: "Label"
record ID appears TWICE:
    1. In rows (the clickable column)
    2. As a "Detail" encoding in marks.ALL.encodings (so recordId resolves at click time)
allHeaders mergeRepeatedCells: true  (Visualization mode)
axis: {}  (empty — no axis config in this layout)
```

**Why `Global.LogACall` is greyed out on User records**: Log a Call works on Opportunity, Account, and Contact — NOT User. Always use Opportunity (or Account/Contact) as the entity.

```python
import json

def fk(field_name, object_name):
    """Field key for recordaction — raw JSON string on write."""
    return json.dumps({"displayCategory": "Discrete", "fieldName": field_name,
        "objectName": object_name, "role": "Dimension", "type": "Field",
        "disambiguationIndex": 0}, separators=(",", ":"))

def sf_recordaction(record_id_field_name, record_id_object_name, sf_actions):
    """
    sf_actions — confirmed Salesforce action API names:
        "Global.LogACall"  — Log a Call  (Opportunity / Account / Contact only, NOT User)
        "Global.NewTask"   — New Task
        "Global.SendEmail" — Send Email
    """
    fkey = fk(record_id_field_name, record_id_object_name)
    return {
        "actionType": "recordaction", "eventType": "click",
        "parameters": {
            "actions":  [{"apiName": a} for a in sf_actions],
            "field":    {"fieldKey": fkey},
            "recordId": {"fieldKey": fkey},
        },
    }

def create_action_table(label, name, sdm_name, workspace_name,
                        id_field, id_object, id_label,
                        extra_dims, measures, sf_actions):
    """
    id_field / id_object / id_label:
        The SF record ID. e.g. "Opportunity_Id1" / "Opportunity1" / "Opportunity ID"
        Appears on rows (clickable) AND as a Detail encoding (recordId resolution).

    extra_dims: list of (fieldName, objectName, label) tuples.
        e.g. [("Opportunity_Stage1","Opportunity1","Stage"),
              ("Account_Name1","Account1","Account Name")]

    measures: list of (fieldName, objectName_or_None, function, label) tuples.
        Rendered as Label encodings (value columns in the table).
        e.g. [("Total_Amount","Opportunity1","Sum","Total Amount"),
              ("Weighted_Pipeline_clc",None,"Sum","Weighted Pipeline")]
    """
    fields = {}
    fields["F_id"] = {"type": "Field", "fieldName": id_field, "objectName": id_object,
                      "role": "Dimension", "displayCategory": "Discrete", "label": id_label}
    for i, (fn, obj, lbl) in enumerate(extra_dims):
        fields[f"F_d{i}"] = {"type": "Field", "fieldName": fn, "objectName": obj,
                              "role": "Dimension", "displayCategory": "Discrete", "label": lbl}
    # Record ID a second time as Detail encoding — enables recordId resolution at click time
    fields["F_id2"] = {"type": "Field", "fieldName": id_field, "objectName": id_object,
                       "role": "Dimension", "displayCategory": "Discrete", "label": id_label}
    for i, (fn, obj, func, lbl) in enumerate(measures):
        f = {"type": "Field", "fieldName": fn, "function": func,
             "role": "Measure", "displayCategory": "Continuous", "label": lbl}
        if obj: f["objectName"] = obj
        fields[f"F_m{i}"] = f

    dim_row_keys = ["F_id"] + [f"F_d{i}" for i in range(len(extra_dims))]
    measure_keys = [f"F_m{i}" for i in range(len(measures))]
    encodings = (
        [{"fieldKey": "F_id2", "type": "Detail"}] +
        [{"fieldKey": k, "type": "Label"} for k in measure_keys]
    )

    return {
        "label": label, "name": name,
        "description": f"Action table: click {id_label} to trigger Salesforce action.",
        "dataSource": {"name": sdm_name, "type": "SemanticModel"},
        "workspace":  {"name": workspace_name},
        "fields": fields,
        "interactions": [sf_recordaction(id_field, id_object, sf_actions)],
        "view": {
            "label": f"{label} View", "name": f"{name}_view",
            "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}},
        },
        "visualSpecification": {
            "rows": dim_row_keys, "columns": [], "measureValues": [],
            "forecasts": {}, "legends": {},
            "marks": {"ALL": {
                "encodings": encodings,
                "isAutomatic": True,
                "stack": {"isAutomatic": True, "isStacked": False},
                "type": "Text",
            }},
            "mode": "Visualization", "referenceLines": {},
            "style": {
                "allHeaders": {
                    "columns": {"mergeRepeatedCells": True, "showIndex": False},
                    "rows":    {"mergeRepeatedCells": True, "showIndex": False},
                    "fields":  {k: {"hiddenValues": [], "isVisible": True, "showMissingValues": False}
                                for k in dim_row_keys},
                },
                "axis": {},
                "fieldLabels": {"columns": {"showDividerLine": False, "showLabels": True},
                                "rows":    {"showDividerLine": False, "showLabels": True}},
                "fit": "Standard",
                "fonts": {"actionableHeaders": {"color": "#0250D9", "size": 13},
                          "axisTickLabels": {"color": "#2E2E2E", "size": 13},
                          "fieldLabels": {"color": "#2E2E2E", "size": 13},
                          "headers": {"color": "#2E2E2E", "size": 13},
                          "legendLabels": {"color": "#2E2E2E", "size": 13},
                          "markLabels": {"color": "#2E2E2E", "size": 13},
                          "marks": {"color": "#2E2E2E", "size": 13}},
                "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"},
                          "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
                "marks": {"ALL": {"color": {"color": ""}, "isAutomaticSize": True,
                                  "label": {"canOverlapLabels": False,
                                            "marksToLabel": {"type": "All"}, "showMarkLabels": True},
                                  "range": {"reverse": True},
                                  "size": {"isAutomatic": True, "type": "Pixel", "value": 13}}},
                "panes": {k: {"defaults": {"format": {"numberFormatInfo": {
                    "decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": True,
                    "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}}
                    for k in measure_keys},
                "referenceLines": {},
                "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
                "showDataPlaceholder": False, "title": {"isVisible": True},
            },
        },
    }

# Example — Opportunity action table with Log a Call:
payload = create_action_table(
    label="Open Opportunities", name=f"{model_api_name}_open_opps_action",
    sdm_name=model_api_name, workspace_name=workspace_name,
    id_field="Opportunity_Id1", id_object="Opportunity1", id_label="Opportunity ID",
    extra_dims=[
        ("Opportunity_Stage1", "Opportunity1", "Stage"),
        ("Account_Name1",      "Account1",     "Account Name"),
        ("Account_Type1",      "Account1",     "Account Type"),
    ],
    measures=[
        ("Total_Amount",          "Opportunity1", "Sum", "Total Amount"),
        ("Avg_Probability_clc",   None,           "Avg", "Avg Probability"),
        ("Weighted_Pipeline_clc", None,           "Sum", "Weighted Pipeline"),
    ],
    sf_actions=["Global.LogACall"],
)
resp = requests.post(f"{BASE_VIZ}/tableau/visualizations", headers=SF_HDRS, json=payload)
```

**Entity reference — confirmed SF ID field names:**

| Entity | SF ID field | objectName | Log a Call? |
|---|---|---|---|
| Opportunity | `Opportunity_Id1` | `Opportunity1` | ✅ Yes |
| Account | `Account_Id` | `Account` | ✅ Yes |
| Contact | `Contact_Id` | `Contact` | ✅ Yes |
| User / Rep | `User_Id` | `User` | ❌ No — greyed out |

---

## Action type 2 — Navigate to URL (`navigate`)

Use for opening any URL. Works on any viz type. Use `{{fieldApiName}}` to substitute the clicked value at runtime.

```python
def viz_url_interaction(field_name, object_name, field_label, url,
                        action_label="Open URL", display_category="Discrete"):
    """
    Encoding: both field and destination.target are raw JSON strings on write.
    GET returns destination.target HTML-entity-encoded — do NOT use that format on write.
    """
    field_json = json.dumps({
        "displayCategory": display_category, "fieldName": field_name,
        "label": field_label, "objectName": object_name,
        "role": "Dimension", "type": "Field", "disambiguationIndex": 0,
    }, separators=(",", ":"))
    url_json = json.dumps({"url": [url]}, separators=(",", ":"))
    return {
        "actionType": "navigate", "eventType": "click",
        "parameters": {
            "destination": {"target": url_json, "type": "url"},
            "field": field_json,
            "label": action_label,
        },
    }

# Common URL patterns:
#   Open record:    "/lightning/r/Opportunity/{{Opportunity_Id1}}/view"
#   Open list:      "/lightning/o/Opportunity/list"
#   New task:       "/lightning/o/Task/new?defaultFieldValues=WhatId={{Opportunity_Id1}}"
```

---

## Apply to an existing viz via PATCH

```python
def patch_viz_interactions(viz_name, interactions, base_viz_url, headers):
    """Viz PATCH requires full payload — interactions-only PATCH is rejected."""
    r = requests.get(f"{base_viz_url}/tableau/visualizations/{viz_name}", headers=headers)
    r.raise_for_status()
    viz = r.json()
    viz["interactions"] = interactions
    for key in ("id", "createdBy", "createdDate", "lastModifiedBy", "lastModifiedDate",
                "permissions", "sourceVersion"):
        viz.pop(key, None)
    for block in ("dataSource", "workspace"):
        if block in viz:
            viz[block] = {k: v for k, v in viz[block].items() if k in ("name", "type")}
    if "view" in viz:
        viz["view"].pop("id", None); viz["view"].pop("isOriginal", None)
    for f in viz.get("fields", {}).values():
        f.pop("id", None)
    resp = requests.patch(f"{base_viz_url}/tableau/visualizations/{viz_name}",
                          headers=headers, json=viz)
    if resp.ok:
        print(f"  ✅ Action applied to {viz_name}")
    else:
        print(f"  ❌ {resp.status_code} {resp.text[:300]}")
```

When adding actions at creation time, include `interactions` directly in the viz payload — no separate PATCH needed.
