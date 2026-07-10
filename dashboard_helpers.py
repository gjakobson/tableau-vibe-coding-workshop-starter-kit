"""Confirmed-working Tableau Next dashboard payload builders (API v66.0).

Import and call these directly:

    from dashboard_helpers import dash_metric, dash_viz, dash_date_filter, \
        dash_toggle_filter, dash_text, dash_container, dash_text_inner, \
        dash_viz_inner, dash_pos, create_dashboard, patch_dashboard, clean_widget

Do not redefine these functions inline and do not hand-construct a dashboard
payload dict from scratch. Two failure modes this module exists to prevent,
both seen in live runs:
  - using "workspace" instead of the required "workspaceIdOrApiName" key
  - "widgets" built as a list instead of the required dict keyed by widget name

See Reference Files/ref-dashboard.md for layout conventions (KPI row policy,
column/row grid, outer margin rule).
"""
import uuid
import requests

# SLDS 2.0 design tokens
_SLDS_BRAND   = "#0176D3"
_SLDS_SURFACE = "#FFFFFF"
_SLDS_PAGE_BG = "#F4F6F9"
_SLDS_BORDER  = "#DDDBDA"
_SLDS_RADIUS  = 4

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
    # Only use for fields with <=4 distinct values — 5+ values overflow horizontally
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


def create_dashboard(sf_hdrs, base_viz, label, name, description, workspace_name,
                      widgets_dict, page_cells,
                      column_count=72, row_height=16, max_width=1440,
                      page_label="Overview", layout_style=None):
    """POST a new dashboard. Returns the parsed JSON response, or None on failure.

    widgets_dict: dict keyed by widget name (NOT a list — the API rejects a list).
    page_cells: list of dash_pos(...) results.
    """
    dash_payload = {
        "label": label,
        "name": name,
        "description": description,
        "workspaceIdOrApiName": workspace_name,
        "style": {"widgetStyle": {"backgroundColor": _SLDS_PAGE_BG, "borderColor": _SLDS_BORDER,
                                   "borderEdges": [], "borderRadius": 0, "borderWidth": 1}},
        "widgets": widgets_dict,
        "layouts": [{
            "name": "default", "columnCount": column_count, "rowHeight": row_height, "maxWidth": max_width,
            "pages": [{"name": str(uuid.uuid4()), "label": page_label, "widgets": page_cells}],  # UUID required
            "style": layout_style or {"backgroundColor": _SLDS_PAGE_BG, "cellSpacingX": 16, "cellSpacingY": 16,
                                       "gutterColor": _SLDS_PAGE_BG},   # {} causes blank canvas
        }],
        # DO NOT include "customViews" — causes JSON_PARSER_ERROR
    }
    resp = requests.post(f"{base_viz}/tableau/dashboards", headers=sf_hdrs, json=dash_payload)
    if resp.ok:
        result = resp.json()
        print(f"  [OK] Dashboard: {name}  id={result.get('id')}")
        return result
    print(f"  [ERROR] Dashboard '{name}': {resp.status_code} {resp.text[:400]}")
    return None


def clean_widget(w):
    w = {k: v for k, v in w.items() if k not in ("id", "status", "label")}
    if "source" in w and w.get("type") != "extension":
        w["source"] = {k: v for k, v in w["source"].items() if k not in ("label", "type")}
    return w


def patch_dashboard(sf_hdrs, base_viz, dashboard_name, widgets_dict, page_cells):
    """PATCH an existing dashboard, replacing its widgets/layout with the given ones.

    Fetches the current dashboard first to preserve label/description/style/layout
    metadata that the API requires on PATCH but that callers shouldn't have to
    re-supply. Returns the parsed JSON response, or None on failure.
    """
    r = requests.get(f"{base_viz}/tableau/dashboards/{dashboard_name}", headers=sf_hdrs)
    if not r.ok:
        print(f"  [ERROR] Fetch '{dashboard_name}': {r.status_code} {r.text[:400]}")
        return None
    dash = r.json()
    resp = requests.patch(f"{base_viz}/tableau/dashboards/{dashboard_name}", headers=sf_hdrs,
        json={
            "label": dash["label"],                            # required — omitting causes 500
            "name": dash["name"],
            "description": dash.get("description", ""),
            "workspaceIdOrApiName": dash["workspaceIdOrApiName"],  # required
            "style": dash["style"],
            "widgets": widgets_dict,
            "layouts": [{
                "name": dash["layouts"][0]["name"],
                "columnCount": dash["layouts"][0]["columnCount"],
                "rowHeight": dash["layouts"][0]["rowHeight"],
                "maxWidth": dash["layouts"][0]["maxWidth"],
                "pages": [{"name": dash["layouts"][0]["pages"][0]["name"],
                           "label": dash["layouts"][0]["pages"][0]["label"],
                           "widgets": page_cells}],
                "style": dash["layouts"][0]["style"],
            }],
        })
    if resp.ok:
        result = resp.json()
        print(f"  [OK] Dashboard patched: {dashboard_name}")
        return result
    print(f"  [ERROR] Patch '{dashboard_name}': {resp.status_code} {resp.text[:400]}")
    return None
