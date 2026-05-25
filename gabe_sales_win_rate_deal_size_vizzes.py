import json, requests, sys, warnings
warnings.filterwarnings('ignore')
from pathlib import Path

_DIR = str(Path(__file__).parent)

cfg = json.loads(Path("next_config.json").read_text())

r = requests.post(cfg["sf_login_url"] + "/services/oauth2/token", data={
    "grant_type": "refresh_token", "client_id": cfg["client_id"],
    "client_secret": cfg["client_secret"], "refresh_token": cfg["refresh_token"],
})
r.raise_for_status()
sf_token    = r.json()["access_token"]
sf_instance = r.json()["instance_url"]
SF_HDRS  = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
BASE_VIZ = f"{sf_instance}/services/data/v66.0"

model_api_name = "Gabe_Sales_Data_Sample"
workspace_name = "Gabe_Workspace"

# ── Style helpers ──────────────────────────────────────────────────────────────

VIZ_FONTS = {
    "actionableHeaders": {"color": "#0250D9", "size": 13},
    "axisTickLabels":    {"color": "#2E2E2E", "size": 13},
    "fieldLabels":       {"color": "#2E2E2E", "size": 13},
    "headers":           {"color": "#2E2E2E", "size": 13},
    "legendLabels":      {"color": "#2E2E2E", "size": 13},
    "markLabels":        {"color": "#2E2E2E", "size": 13},
    "marks":             {"color": "#2E2E2E", "size": 13},
}
VIZ_LINES = {
    "axisLine":             {"color": "#C9C9C9"},
    "fieldLabelDividerLine":{"color": "#C9C9C9"},
    "separatorLine":        {"color": "#C9C9C9"},
    "zeroLine":             {"color": "#C9C9C9"},
}
VIZ_SHADING = {
    "backgroundColor": "#FFFFFF",
    "banding": {"rows": {"color": "#E5E5E5"}},
}


def calc_measure(field_name, label=None, function="Avg"):
    f = {"type": "Field", "fieldName": field_name, "function": function,
         "role": "Measure", "displayCategory": "Continuous"}
    if label:
        f["label"] = label
    return f


def raw_dim(field_name, object_name, label=None):
    f = {"type": "Field", "fieldName": field_name, "objectName": object_name,
         "role": "Dimension", "displayCategory": "Discrete"}
    if label:
        f["label"] = label
    return f


def axis_number(field_key, title="", decimals=2):
    return {field_key: {
        "isVisible": True, "isZeroLineVisible": True,
        "range": {"includeZero": True, "type": "Auto"},
        "scale": {"format": {"numberFormatInfo": {
            "decimalPlaces": decimals, "displayUnits": "Auto",
            "includeThousandSeparator": True, "negativeValuesFormat": "Auto",
            "prefix": "", "suffix": "", "type": "NumberShort"}}},
        "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
        "titleText": title,
    }}


def pane_format(field_key, decimals=2, fmt_type="Number"):
    return {field_key: {"defaults": {"format": {"numberFormatInfo": {
        "decimalPlaces": decimals, "displayUnits": "Auto",
        "includeThousandSeparator": True, "negativeValuesFormat": "Auto",
        "prefix": "", "suffix": "", "type": fmt_type,
    }}}}}


def build_style(axis_dict, pane_dict, dim_row_keys=None):
    fields_headers = {
        k: {"hiddenValues": [], "isVisible": True, "showMissingValues": False}
        for k in (dim_row_keys or [])
    }
    return {
        "allHeaders": {
            "columns": {"mergeRepeatedCells": True, "showIndex": False},
            "fields":  fields_headers,
            "rows":    {"mergeRepeatedCells": True, "showIndex": False},
        },
        "axis":        axis_dict,
        "fieldLabels": {
            "columns": {"showDividerLine": False, "showLabels": True},
            "rows":    {"showDividerLine": False, "showLabels": True},
        },
        "fit":    "Standard",
        "fonts":  VIZ_FONTS,
        "lines":  VIZ_LINES,
        "marks": {"ALL": {
            "color":               {"color": ""},
            "isAutomaticSize":     False,
            "isStackingAxisCentered": False,
            "label": {"canOverlapLabels": False,
                      "marksToLabel": {"type": "All"},
                      "showMarkLabels": False},
            "range": {"reverse": True},   # dim on rows → horizontal bar
            "size":  {"isAutomatic": False, "type": "Percentage", "value": 75},
        }},
        "panes":              pane_dict,
        "referenceLines":     {},
        "shading":            VIZ_SHADING,
        "showDataPlaceholder": False,
        "title": {"isVisible": True},
    }


def create_viz(label, name, fields_dict, rows, columns, mark_type="Bar", style=None):
    payload = {
        "label":       label,
        "name":        name,
        "description": f"Auto-generated: {label}",
        "dataSource":  {"name": model_api_name, "type": "SemanticModel"},
        "workspace":   {"name": workspace_name},
        "fields":      fields_dict,
        "interactions": [],
        "view": {
            "label": f"{label} View",
            "name":  f"{name}_view",
            "viewSpecification": {
                "filters":    [],
                "sortOrders": {"columns": [], "fields": {}, "rows": []},
            },
        },
        "visualSpecification": {
            "columns":      columns,
            "forecasts":    {},
            "legends":      {},
            "marks": {"ALL": {
                "encodings":   [],
                "isAutomatic": False,
                "stack":       {"isAutomatic": False, "isStacked": False},
                "type":        mark_type,
            }},
            "measureValues": [],
            "mode":          "Visualization",
            "referenceLines": {},
            "rows":          rows,
            "style":         style or {},
        },
    }
    resp = requests.post(f"{BASE_VIZ}/tableau/visualizations", headers=SF_HDRS, json=payload)
    if resp.ok:
        result = resp.json()
        print(f"  ✅ {label}  id={result.get('id')}")
        return result
    else:
        print(f"  ❌ {label}: {resp.status_code} {resp.text[:400]}")
        return None


# ── Win Rate by Owner ──────────────────────────────────────────────────────────
win_by_owner = create_viz(
    label="Win Rate by Owner",
    name=f"{model_api_name}_win_rate_by_owner",
    fields_dict={
        "F1": calc_measure("Win_Rate_clc", "Win Rate (%)", function="Avg"),
        "F2": raw_dim("Full_Name", "User", "Owner"),
    },
    rows=["F2"], columns=["F1"],
    style=build_style(
        axis_dict=axis_number("F1", "Win Rate (%)", decimals=1),
        pane_dict=pane_format("F1", decimals=1, fmt_type="Number"),
        dim_row_keys=["F2"],
    ),
)

# ── Win Rate by Primary Industry ───────────────────────────────────────────────
win_by_industry = create_viz(
    label="Win Rate by Primary Industry",
    name=f"{model_api_name}_win_rate_by_industry",
    fields_dict={
        "F1": calc_measure("Win_Rate_clc", "Win Rate (%)", function="Avg"),
        "F2": raw_dim("Primary_Industry", "Account", "Primary Industry"),
    },
    rows=["F2"], columns=["F1"],
    style=build_style(
        axis_dict=axis_number("F1", "Win Rate (%)", decimals=1),
        pane_dict=pane_format("F1", decimals=1, fmt_type="Number"),
        dim_row_keys=["F2"],
    ),
)

# ── Deal Size by Owner ─────────────────────────────────────────────────────────
deal_by_owner = create_viz(
    label="Deal Size by Owner",
    name=f"{model_api_name}_deal_size_by_owner",
    fields_dict={
        "F1": calc_measure("Deal_Size_clc", "Deal Size ($)", function="Avg"),
        "F2": raw_dim("Full_Name", "User", "Owner"),
    },
    rows=["F2"], columns=["F1"],
    style=build_style(
        axis_dict=axis_number("F1", "Deal Size ($)", decimals=0),
        pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"),
        dim_row_keys=["F2"],
    ),
)

# ── Deal Size by Primary Industry ──────────────────────────────────────────────
deal_by_industry = create_viz(
    label="Deal Size by Primary Industry",
    name=f"{model_api_name}_deal_size_by_industry",
    fields_dict={
        "F1": calc_measure("Deal_Size_clc", "Deal Size ($)", function="Avg"),
        "F2": raw_dim("Primary_Industry", "Account", "Primary Industry"),
    },
    rows=["F2"], columns=["F1"],
    style=build_style(
        axis_dict=axis_number("F1", "Deal Size ($)", decimals=0),
        pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"),
        dim_row_keys=["F2"],
    ),
)

print("\nDone.")
