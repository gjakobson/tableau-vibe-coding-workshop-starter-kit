# Reference: Visualizations (STEP M — v66.0)

Read this file when creating or modifying Tableau Next visualizations via API.

---

## STEP M — Visualizations (CONFIRMED WORKING — v66.0)

```python
BASE_VIZ = f"{sf_instance}/services/data/v66.0"

# ── Field builder helpers ──────────────────────────────────────────────────────
def calc_measure(field_name, label=None, function="Sum"):
    # Match function to SDM aggregationType: "Sum" for Sum calcs, "Avg" for Average calcs
    # NEVER use "UserAgg" for row-level calcs — causes ROW_LEVEL_CALC_AGG_VALIDATION_ERROR
    f = {"type": "Field", "fieldName": field_name, "function": function,
         "role": "Measure", "displayCategory": "Continuous"}
    if label: f["label"] = label
    return f

def calc_dim(field_name, label=None, is_date=False):
    f = {"type": "Field", "fieldName": field_name, "role": "Dimension",
         "displayCategory": "Continuous" if is_date else "Discrete"}
    if label: f["label"] = label
    return f

def raw_measure(field_name, object_name, func="Sum", label=None):
    f = {"type": "Field", "fieldName": field_name, "objectName": object_name,
         "function": func, "role": "Measure", "displayCategory": "Continuous"}
    if label: f["label"] = label
    return f

def raw_dim(field_name, object_name, label=None):
    f = {"type": "Field", "fieldName": field_name, "objectName": object_name,
         "role": "Dimension", "displayCategory": "Discrete"}
    if label: f["label"] = label
    return f

# ── Style constants ────────────────────────────────────────────────────────────
VIZ_FONTS = {"actionableHeaders": {"color": "#0250D9", "size": 13},
             "axisTickLabels": {"color": "#2E2E2E", "size": 13},
             "fieldLabels": {"color": "#2E2E2E", "size": 13},
             "headers": {"color": "#2E2E2E", "size": 13},
             "legendLabels": {"color": "#2E2E2E", "size": 13},
             "markLabels": {"color": "#2E2E2E", "size": 13},
             "marks": {"color": "#2E2E2E", "size": 13}}
VIZ_LINES = {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"},
             "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}}
VIZ_SHADING = {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}}

def axis_number(field_key, title="", decimals=2):
    return {field_key: {"isVisible": True, "isZeroLineVisible": True,
                        "range": {"includeZero": True, "type": "Auto"},
                        "scale": {"format": {"numberFormatInfo": {"decimalPlaces": decimals, "displayUnits": "Auto",
                                                                  "includeThousandSeparator": True, "negativeValuesFormat": "Auto",
                                                                  "prefix": "", "suffix": "", "type": "NumberShort"}}},
                        "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
                        "titleText": title}}

def axis_date(field_key):
    return {field_key: {"isVisible": True, "isZeroLineVisible": False,
                        "range": {"includeZero": False, "type": "Auto"},
                        "scale": {"format": {"dateTemplate": ""}},
                        "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}}}

def pane_format(field_key, decimals=2, fmt_type="Number"):
    # fmt_type: "Number", "Currency" — NEVER "Percent" (rejected by API)
    return {field_key: {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": decimals, "displayUnits": "Auto",
                                                                      "includeThousandSeparator": True, "negativeValuesFormat": "Auto",
                                                                      "prefix": "", "suffix": "", "type": fmt_type}}}}}

def build_viz_style(axis_dict, pane_dict, reverse_range=False, dim_row_keys=None, mark_type="Circle"):
    # reverse_range=True for horizontal bar (dim on rows, measure on columns)
    # dim_row_keys: list of field keys for dims on rows shelf — each needs allHeaders.fields entry
    # mark_type: controls size defaults
    fields_headers = {k: {"hiddenValues": [], "isVisible": True, "showMissingValues": False}
                      for k in (dim_row_keys or [])}
    if mark_type == "Bar":
        size = {"isAutomatic": False, "type": "Percentage", "value": 75}
    elif mark_type == "Line":
        size = {"isAutomatic": False, "type": "Pixel", "value": 2}
    else:  # Circle — use minimum; larger = huge blobs
        size = {"isAutomatic": False, "type": "Percentage", "value": 2}
    return {
        "allHeaders": {"columns": {"mergeRepeatedCells": True, "showIndex": False},
                       "fields": fields_headers,
                       "rows": {"mergeRepeatedCells": True, "showIndex": False}},
        "axis": axis_dict,
        "fieldLabels": {"columns": {"showDividerLine": False, "showLabels": True},
                        "rows": {"showDividerLine": False, "showLabels": True}},
        "fit": "Standard",
        "fonts": VIZ_FONTS,
        "lines": VIZ_LINES,
        "marks": {"ALL": {"color": {"color": ""}, "isAutomaticSize": False,
                          "isStackingAxisCentered": False,
                          "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": False},
                          "range": {"reverse": reverse_range},
                          "size": size}},
        "panes": pane_dict,
        "referenceLines": {},
        "shading": VIZ_SHADING,
        "showDataPlaceholder": False,
        "title": {"isVisible": True},
        # DO NOT include "headers" key — even {} causes JSON_PARSER_ERROR at v66.0
    }

def create_visualization(label, name, sdm_name, workspace_name,
                         fields_dict, rows, columns,
                         mark_type="Bar", mark_auto=False,
                         color_encoding=None, stacked=False, style=None):
    encodings = [{"fieldKey": color_encoding, "type": "Color"}] if color_encoding else []
    payload = {
        "label": label, "name": name, "description": f"Auto-generated: {label}",
        "dataSource": {"name": sdm_name, "type": "SemanticModel"},
        "workspace":  {"name": workspace_name},
        "fields":     fields_dict,
        "interactions": [],
        "view": {"label": f"{label} View", "name": f"{name}_view",
                 "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}},
        "visualSpecification": {
            "columns": columns, "forecasts": {},
            "legends": ({color_encoding: {"isVisible": True, "position": "Right", "title": {"isVisible": True}}} if color_encoding else {}),
            "marks": {"ALL": {"encodings": encodings, "isAutomatic": mark_auto,
                              "stack": {"isAutomatic": stacked, "isStacked": stacked}, "type": mark_type}},
            "measureValues": [], "mode": "Visualization",   # MUST be "Visualization" not "Normal" or "Table"
            "referenceLines": {}, "rows": rows, "style": style or {},
        },
    }
    resp = requests.post(f"{BASE_VIZ}/tableau/visualizations", headers=SF_HDRS, json=payload)
    if resp.ok:
        result = resp.json()
        print(f"  ✅ Visualization: {label}  id={result.get('id')}")
        return result
    else:
        print(f"  ERROR '{label}': {resp.text[:400]}")
        return None

# ── Example visualizations ─────────────────────────────────────────────────────
pipeline_trend = create_visualization(
    label="Pipeline Value — Monthly Trend", name=f"{model_api_name}_pipeline_trend",
    sdm_name=model_api_name, workspace_name=workspace_name,
    fields_dict={"F1": calc_measure("Total_Pipeline_Value_clc", "Pipeline Value ($)"),
                 "F2": calc_dim("Activity_Date_clc", "Month", is_date=True)},
    rows=["F1"], columns=["F2"], mark_type="Circle",
    style=build_viz_style(axis_dict={**axis_number("F1", "Pipeline Value"), **axis_date("F2")},
                          pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"), reverse_range=False),
)

pipeline_by_region = create_visualization(
    label="Pipeline Value by Region", name=f"{model_api_name}_pipeline_by_region",
    sdm_name=model_api_name, workspace_name=workspace_name,
    fields_dict={"F1": calc_measure("Total_Pipeline_Value_clc", "Pipeline Value ($)"),
                 "F2": raw_dim(fld(fact_sdo, "region__c"), fact_sdo, "Region")},
    rows=["F2"], columns=["F1"], mark_type="Bar",
    style=build_viz_style(axis_dict=axis_number("F1", "Pipeline Value"),
                          pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"),
                          reverse_range=True, dim_row_keys=["F2"], mark_type="Bar"),
)
```

---

## Mark type guide

**Confirmed working**: `"Bar"`, `"Line"`, `"Area"`, `"Circle"`. `"Pie"` → rejected.

| Mark type | Use for | Size setting |
|---|---|---|
| `"Circle"` | Trend/time-series (individual dots) | `{"isAutomatic": False, "type": "Percentage", "value": 2}` — minimum; larger = huge blobs |
| `"Bar"` | Category breakdowns | `{"isAutomatic": False, "type": "Percentage", "value": 75}` |
| `"Line"` | Connected line trend | `{"isAutomatic": False, "type": "Pixel", "value": 2}` |

**Sorting**: `sortOrders` only works for `mode="Table"` — cannot sort bar/line charts via API.

**Viz POST response key is `name`, not `apiName`** — always extract as:
```python
viz_name = result.get("apiName") or result.get("name")
```
