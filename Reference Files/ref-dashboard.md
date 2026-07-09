# Reference: Dashboard (STEP N — v66.0)

Read this file when building or patching a Tableau Next dashboard.

---

## STEP N — Dashboard (CONFIRMED WORKING)

### KPI row policy (required)

Before assembling visualization widgets:
1. Fetch metric IDs for the selected model.
2. If metrics exist, include a top KPI row with up to 4 metric tiles.
3. Only skip KPI row when no metrics are available or metric IDs cannot be resolved.
4. If skipped, print an explicit skip reason before marking dashboard complete.

```python
import uuid

# SLDS 2.0 design tokens
_SLDS_BRAND    = "#0176D3"
_SLDS_SURFACE  = "#FFFFFF"
_SLDS_PAGE_BG  = "#F4F6F9"
_SLDS_BORDER   = "#DDDBDA"
_SLDS_RADIUS   = 4

CARD_STYLE   = {"backgroundColor": _SLDS_SURFACE, "borderColor": _SLDS_BORDER,
                "borderEdges": ["all"], "borderRadius": _SLDS_RADIUS, "borderWidth": 1}
FILTER_STYLE = {"backgroundColor": _SLDS_SURFACE, "borderColor": _SLDS_BORDER,
                "borderEdges": ["all"], "borderRadius": _SLDS_RADIUS, "borderWidth": 1}

# ── Widget helpers ─────────────────────────────────────────────────────────────

def dash_metric(name, metric_api_name, metric_id, sdm_name, sdm_id, show_chart=True):
    return {"actions": [], "name": name, "type": "metric",
            "parameters": {"metricOption": {"layout": {"componentVisibility": {
                                "comparison": True, "insights": False, "details": True,
                                "title": True, "value": True, "chart": show_chart}},
                           "sdmApiName": sdm_name, "sdmId": sdm_id},
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "widgetStyle": CARD_STYLE},
            "source": {"id": metric_id, "name": metric_api_name}}

def dash_viz(name, viz_api_name, viz_id):
    return {"actions": [], "name": name, "type": "visualization",
            "parameters": {"receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "widgetStyle": CARD_STYLE},
            "source": {"id": viz_id, "name": viz_api_name}}

def dash_date_filter(name, label, calc_date_dim_api, sdm_name, sdm_id):
    # No initialValues — dashboard opens unfiltered so D3 extensions render the full dataset on load
    return {"actions": [], "name": name, "type": "filter", "label": label,
            "parameters": {"filterOption": {"dataType": "Date", "fieldName": calc_date_dim_api, "selectionType": "multiple"},
                           "isLabelHidden": False,
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "viewType": "list", "widgetStyle": FILTER_STYLE},
            "source": {"id": sdm_id, "name": sdm_name}}

def dash_toggle_filter(name, label, field_api, sdo_api, sdm_name, sdm_id, single=False):
    # Only use for fields with ≤4 distinct values — 5+ values overflow horizontally
    return {"actions": [], "name": name, "type": "filter", "label": label,
            "parameters": {"defaultStyle": {"fontColor": _SLDS_BRAND, "textStyle": []},
                           "selectedStyle": {"backgroundColor": _SLDS_BRAND, "fontColor": "#FFFFFF", "textStyle": []},
                           "textStyle": {"alignmentX": "center", "alignmentY": "center", "fontSize": 13},
                           "filterOption": {"dataType": "Text", "fieldName": field_api, "objectName": sdo_api,
                                            "selectionType": "single" if single else "multiple"},
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "viewType": "toggle", "widgetStyle": FILTER_STYLE},
            "source": {"id": sdm_id, "name": sdm_name}}

def dash_text(name, text, bold=True, size="24px", color="#181818"):
    return {"actions": [], "name": name, "type": "text",
            "parameters": {"conditionalFormattingRules": [],
                           "content": [{"attributes": {"bold": bold, "color": color, "size": size},
                                        "insert": text, "rules": []}, {"insert": "\n", "rules": []}],
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []}}}

def dash_container(name):
    """Bordered background card — position dash_text_inner + dash_viz_inner on top at same coords."""
    return {"actions": [], "name": name, "type": "container",
            "parameters": {"widgetStyle": {"backgroundColor": _SLDS_SURFACE, "borderColor": _SLDS_BORDER,
                                           "borderEdges": ["all"], "borderRadius": _SLDS_RADIUS, "borderWidth": 1}}}

def dash_text_inner(name, text, description="", desc_color="#706E6B"):
    """Title + description inside a dash_container. White bg, no border."""
    content = [{"attributes": {"bold": True, "color": "#032D60", "size": "14px"}, "insert": text, "rules": []},
               {"insert": "\n", "rules": []}]
    if description:
        content += [{"attributes": {"color": desc_color, "size": "11px"}, "insert": description, "rules": []},
                    {"insert": "\n", "rules": []}]
    return {"actions": [], "name": name, "type": "text",
            "parameters": {"conditionalFormattingRules": [], "content": content,
                           "widgetStyle": {"backgroundColor": _SLDS_SURFACE, "borderEdges": []},
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []}}}

def dash_viz_inner(name, viz_api_name, viz_id, legend_position="Bottom"):
    """Viz inside a dash_container. No border — container provides it."""
    return {"actions": [], "name": name, "type": "visualization",
            "parameters": {"legendPosition": legend_position,
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "widgetStyle": {"backgroundColor": _SLDS_SURFACE, "borderEdges": []}},
            "source": {"id": viz_id, "name": viz_api_name}}

def dash_pos(name, col, row, colspan, rowspan):
    return {"name": name, "column": col, "row": row, "colspan": colspan, "rowspan": rowspan}
```

---

## Unified card pattern (container + label + viz)

```python
# Container spans the full card. Label takes the top 3 rows. Viz takes the rest.
widgets["container_trend"] = dash_container("container_trend")
page_cells.append(dash_pos("container_trend", 2, 10, 45, 13))   # full card

widgets["label_trend"] = dash_text_inner("label_trend", "Balance Trend",
    description="Aggregate pipeline value over time...")
page_cells.append(dash_pos("label_trend", 2, 10, 45, 3))         # top 3 rows

widgets["viz_1"] = dash_viz_inner("viz_1", viz_api, viz_id)
page_cells.append(dash_pos("viz_1", 2, 13, 45, 10))              # bottom 10 rows
```

**Outer margin rule**: With `columnCount=72`, reserve col 1 and col 72 as gutters. Run all content through cols 2–71.

---

## POST dashboard

```python
widgets_dict = {}
page_cells   = []

# Title
widgets_dict["text_1"] = dash_text("text_1", f"{COMPANY_NAME} — {USE_CASE}", bold=True, size="28px")
page_cells.append(dash_pos("text_1", 2, 0, 70, 2))

# Date filter
widgets_dict["filter_date"] = dash_date_filter("filter_date", "Date Range", "Activity_Date_clc", model_api_name, model_id)
page_cells.append(dash_pos("filter_date", 2, 2, 20, 2))

# Metric tiles
metrics_to_show = [
    ("metric_1", "total_pipeline_value_md", metric_ids["Total Pipeline Value"]),
    ("metric_2", "win_rate_md",             metric_ids["Win Rate"]),
    ("metric_3", "average_deal_size_md",    metric_ids["Average Deal Size"]),
    ("metric_4", "quota_attainment_md",     metric_ids["Quota Attainment"]),
]
n = len(metrics_to_show)
metric_cols = 70 // n
for i, (mname, mapi, mid) in enumerate(metrics_to_show):
    widgets_dict[mname] = dash_metric(mname, mapi, mid, model_api_name, model_id)
    page_cells.append(dash_pos(mname, 2 + i * metric_cols, 5, metric_cols, 9))

# Viz grid (2×2)
viz_grid = [
    ("viz_1", viz1.get("apiName") or viz1.get("name"), viz1["id"],  2, 15, 34, 13),
    ("viz_2", viz2.get("apiName") or viz2.get("name"), viz2["id"], 38, 15, 34, 13),
]
for vname, vapi, vid, col, row, cs, rs in viz_grid:
    if vid:
        widgets_dict[vname] = dash_viz(vname, vapi, vid)
        page_cells.append(dash_pos(vname, col, row, cs, rs))

DASH_LABEL = f"{COMPANY_NAME} — {USE_CASE} Overview"
DASH_NAME  = f"{WORKSPACE_NAME}_dashboard"
dash_payload = {
    "label": DASH_LABEL,
    "name":  DASH_NAME,
    "description": f"Auto-generated dashboard for {COMPANY_NAME} {USE_CASE}.",
    "workspaceIdOrApiName": WORKSPACE_NAME,
    "style": {"widgetStyle": {"backgroundColor": _SLDS_PAGE_BG, "borderColor": _SLDS_BORDER,
                               "borderEdges": [], "borderRadius": 0, "borderWidth": 1}},
    "widgets": widgets_dict,   # MUST be dict, not list
    "layouts": [{
        "name": "default", "columnCount": 72, "rowHeight": 16, "maxWidth": 1440,
        "pages": [{"name": str(uuid.uuid4()), "label": "Overview", "widgets": page_cells}],  # UUID required
        "style": {"backgroundColor": _SLDS_PAGE_BG, "cellSpacingX": 16, "cellSpacingY": 16,
                  "gutterColor": _SLDS_PAGE_BG},   # {} causes blank canvas
    }],
    # DO NOT include "customViews" — causes JSON_PARSER_ERROR
}

resp = requests.post(f"{BASE_VIZ}/tableau/dashboards", headers=SF_HDRS, json=dash_payload)
if resp.ok:
    print(f"  ✅ Dashboard: {DASH_NAME}  id={resp.json().get('id')}")
else:
    print(f"  ⚠️  Dashboard failed: {resp.status_code} {resp.text[:300]}")
```

---

## PATCH existing dashboard (add widgets)

```python
def clean_widget(w):
    w = {k: v for k, v in w.items() if k not in ("id", "status", "label")}
    if "source" in w and w.get("type") != "extension":
        w["source"] = {k: v for k, v in w["source"].items() if k not in ("label", "type")}
    return w

r = requests.get(f"{BASE_VIZ}/tableau/dashboards/{DASH_NAME}", headers=SF_HDRS)
dash = r.json()
widgets = {k: clean_widget(dict(w)) for k, w in dash["widgets"].items()}
cells   = [{k: v for k, v in c.items() if k != "id"}
           for c in dash["layouts"][0]["pages"][0]["widgets"]]

max_row = max(c["row"] + c["rowspan"] for c in cells)
# ... add new widgets and cells ...

resp = requests.patch(f"{BASE_VIZ}/tableau/dashboards/{DASH_NAME}", headers=SF_HDRS,
    json={
        "label": dash["label"],                            # required — omitting causes 500
        "name":  dash["name"],
        "description": dash.get("description", ""),
        "workspaceIdOrApiName": dash["workspaceIdOrApiName"],  # required
        "style": dash["style"],
        "widgets": widgets,
        "layouts": [{
            "name": dash["layouts"][0]["name"],
            "columnCount": dash["layouts"][0]["columnCount"],
            "rowHeight": dash["layouts"][0]["rowHeight"],
            "maxWidth": dash["layouts"][0]["maxWidth"],
            "pages": [{"name": dash["layouts"][0]["pages"][0]["name"],
                       "label": dash["layouts"][0]["pages"][0]["label"],
                       "widgets": cells}],
            "style": dash["layouts"][0]["style"],
        }],
    })
```
