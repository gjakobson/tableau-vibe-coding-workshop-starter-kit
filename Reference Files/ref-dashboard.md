# Reference: Dashboard (STEP N — v66.0)

Read this file when building or patching a Tableau Next dashboard.

---

## Dashboard Composition Best Practices

KPI metric tiles:
- Default to 4-6 KPI tiles for workshop dashboards.
- Prefer existing model metrics first; only create new metrics for explicit user requests or clear theme coverage gaps.
- For sales pipeline dashboards, prefer: Total Sales, Win Rate, # of Opportunities, Weighted Pipeline Value, Open Opportunities.
- Distribute KPI tiles evenly across columns 2-71.

Default layout pattern:
- Row 0-2: title
- Row 3-11: KPI metric tiles
- Row 13+: visualization grid

Example KPI row placement:
```python
metric_width = 70 // 4
for i in range(4):
    page_cells.append(dash_pos(f"kpi_{i+1}", 2 + i * metric_width, 3, metric_width, 9))
```

Do not ship a dashboard with only one KPI tile unless the user explicitly requests that layout.

---

## STEP N — Dashboard (CONFIRMED WORKING)

### KPI row policy (required)

Before assembling visualization widgets:
1. Fetch metric IDs for the selected model.
2. If metrics exist, include a top KPI row with up to 4 metric tiles.
3. Only skip KPI row when no metrics are available or metric IDs cannot be resolved.
4. If skipped, print an explicit skip reason before marking dashboard complete.

**Do not write these functions inline. Import them:**

```python
from dashboard_helpers import (
    dash_metric, dash_viz, dash_date_filter, dash_toggle_filter,
    dash_text, dash_container, dash_text_inner, dash_viz_inner, dash_pos,
    create_dashboard, patch_dashboard, clean_widget,
)
```

`dashboard_helpers.py` (repo root) is the confirmed-working payload builder.
Two mistakes it exists to prevent, both seen in live runs: using `"workspace"`
instead of the required `"workspaceIdOrApiName"` key, and building `widgets`
as a list instead of the required dict keyed by widget name. Redefining these
functions from memory reintroduces exactly those mistakes. If a helper is
missing a case you need, edit `dashboard_helpers.py` itself — don't fork the
logic inline.

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

# Viz grid (2×2) — vids MUST be distinct; see Identifier-resolution uniqueness rule below
viz_grid = [
    ("viz_1", viz1.get("apiName") or viz1.get("name"), viz1["id"],  2, 15, 34, 13),
    ("viz_2", viz2.get("apiName") or viz2.get("name"), viz2["id"], 38, 15, 34, 13),
]
assert len({v[2] for v in viz_grid}) == len(viz_grid), "duplicate visualization id resolved — dashboard would show the same chart twice"
for vname, vapi, vid, col, row, cs, rs in viz_grid:
    if vid:
        widgets_dict[vname] = dash_viz(vname, vapi, vid)
        page_cells.append(dash_pos(vname, col, row, cs, rs))

DASH_LABEL = f"{COMPANY_NAME} — {USE_CASE} Overview"
DASH_NAME  = f"{WORKSPACE_NAME}_dashboard"
create_dashboard(SF_HDRS, BASE_VIZ, label=DASH_LABEL, name=DASH_NAME,
                  description=f"Auto-generated dashboard for {COMPANY_NAME} {USE_CASE}.",
                  workspace_name=WORKSPACE_NAME, widgets_dict=widgets_dict, page_cells=page_cells)
```

---

## PATCH existing dashboard (add widgets)

```python
r = requests.get(f"{BASE_VIZ}/tableau/dashboards/{DASH_NAME}", headers=SF_HDRS)
dash = r.json()
widgets = {k: clean_widget(dict(w)) for k, w in dash["widgets"].items()}
cells   = [{k: v for k, v in c.items() if k != "id"}
           for c in dash["layouts"][0]["pages"][0]["widgets"]]

max_row = max(c["row"] + c["rowspan"] for c in cells)
# ... add new widgets and cells to `widgets` / `cells` ...

patch_dashboard(SF_HDRS, BASE_VIZ, dashboard_name=DASH_NAME, widgets_dict=widgets, page_cells=cells)
```

---

## Hard fail validation rules (do not skip)

1. **Import, don't reconstruct**: `from dashboard_helpers import ...` and call the functions directly. Reading this file's prose and then retyping a similar-looking payload dict does not satisfy this rule.
2. **No ad-hoc filenames**: never write files named like `_build_*.py`, `_simple_*.py`, `_temp_*.py`, or similar throwaway names for dashboard assembly — these are a sign the payload is being reconstructed from scratch instead of imported from `dashboard_helpers.py`.
3. **Retry cap — hard-enforced count**: a maximum of 2 total `create_dashboard()`/`patch_dashboard()` calls are allowed per dashboard (1 original + 1 retry after a concrete correction). Before the 2nd call, print `RETRY 1/1 for <dashboard_name>: <what changed and why>`. If it also fails, print `VIOLATION: retry cap exceeded for <dashboard_name>` and STOP — report the failing response body to the user instead of continuing to patch the payload.
4. **Identifier-resolution uniqueness lock**: whenever visualization or metric IDs are resolved via a list/GET-by-name call for use in a dashboard payload, print each resolved `(name, id)` pair and verify every ID is unique across the distinct assets being referenced (see the `assert` in the POST example above). If two distinct names resolve to the same ID, the lookup/filter is broken — stop immediately, print the exact endpoint and params used, and fix the lookup before building the dashboard payload. Never assume a list/GET endpoint supports a `name` filter unless that filter is documented in this file — confirm the response actually narrowed to one matching item.
5. **`workspaceIdOrApiName`, never `workspace`**: the dashboard payload key is `workspaceIdOrApiName` (a string), not `workspace` (an object) — that is the visualization payload's key, not the dashboard's. Confusing the two is the most common cause of a first-attempt `JSON_PARSER_ERROR` on dashboard creation.
6. **`widgets` is a dict, not a list**: keyed by widget name, matching the `name` field inside each widget.
