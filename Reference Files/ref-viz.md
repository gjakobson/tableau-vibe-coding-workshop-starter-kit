# Reference: Visualizations (STEP M — v66.0)

Read this file when creating or modifying Tableau Next visualizations via API.

---

## STEP M — Visualizations (CONFIRMED WORKING — v66.0)

**Do not write these functions inline. Import them:**

```python
from viz_helpers import (
    calc_measure, calc_dim, raw_measure, raw_dim, raw_date_dim,
    axis_number, axis_date, pane_format, build_viz_style,
    create_visualization,
)
```

`viz_helpers.py` (repo root) is the confirmed-working payload builder — every
required key (`legends`, `marks.stack`, `marks.isAutomaticSize`, `style.fonts`,
etc.) was only discovered by trial and error against the live API. Redefining
these functions from memory, or hand-building a `visualSpecification` dict
yourself, reliably drops one of those keys and produces the exact 400-error
loop this module exists to prevent. If you think a helper is missing a case
you need, edit `viz_helpers.py` itself — don't fork the logic inline.

```python
BASE_VIZ = f"{sf_instance}/services/data/v66.0"

# ── Example visualizations ─────────────────────────────────────────────────────
pipeline_trend = create_visualization(
    SF_HDRS, BASE_VIZ,
    label="Pipeline Value — Monthly Trend", name=f"{model_api_name}_pipeline_trend",
    sdm_name=model_api_name, workspace_name=workspace_name,
    fields_dict={"F1": calc_measure("Total_Pipeline_Value_clc", "Pipeline Value ($)"),
                 "F2": calc_dim("Activity_Date_clc", "Month", is_date=True)},
    rows=["F1"], columns=["F2"], mark_type="Circle",
    style=build_viz_style(axis_dict={**axis_number("F1", "Pipeline Value"), **axis_date("F2")},
                          pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"), reverse_range=False),
)

pipeline_by_region = create_visualization(
    SF_HDRS, BASE_VIZ,
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

**Axis fields must be continuous**: any field that gets an `axis_number()` / `axis_date()` entry MUST be `displayCategory: "Continuous"`. A discrete field under an axis config is rejected with `INVALID_VISUALIZATION_METADATA: axis can have only continuous fields`. Consequences for date trends:
- A **calculated** date dim → `calc_dim(date_field, is_date=True)` (continuous, no objectName needed).
- A **raw** date column on an object → `raw_date_dim(field, object_name)` — NOT `raw_dim()`, which is always discrete. This is the exact mismatch that fails a "sales over time by close date" chart: `raw_dim("CloseDate", "Opportunity")` + `axis_date("F2")` → discrete field on an axis → rejected.
- If you genuinely want discrete date buckets (categorical months), do the opposite: keep the field discrete and give it an `allHeaders.fields` entry via `build_viz_style(dim_row_keys=[...])`, with NO axis entry.

**Sorting**: `sortOrders` only works for `mode="Table"` — cannot sort bar/line charts via API.

**Viz POST response key is `name`, not `apiName`** — always extract as:
```python
viz_name = result.get("apiName") or result.get("name")
```

---

## Hard fail validation rules (do not skip)

1. **Aggregation compatibility**: for calculated measures, derive `function` from SDM `aggregationType` mapping. Do not force `function="Sum"` on `UserAgg`/aggregate calcs unless SDM metadata explicitly resolves to `Sum`.
2. **First-viz render gate**: after creating the first visualization, validate it renders in dashboard context before creating additional visualizations.
3. **Model lock**: abort if any payload uses an `sdmName` different from the selected model for this run.
4. **Structured edits only**: never use regex/string replacement to mutate metadata XML or component source when structured payload/write operations are available.
5. **Phase timing budget**: first visualization create+render must complete within 120s; each additional visualization must complete within 90s. If exceeded, stop and report a blocking timeout.
6. **Retry cap — hard-enforced count, not a guideline**: a maximum of 2 total `create_visualization()` calls are allowed per visualization (1 original + 1 retry after a concrete, manifest-backed field/payload correction). Before every call beyond the first for the same visualization, print `RETRY 1/1 for <name>: <what changed and why>`. If the 2nd call also fails, print `VIOLATION: retry cap exceeded for <name>` and STOP — do not edit the payload a 3rd time. Report the failing response body to the user and ask how to proceed.
7. **No giant orchestration scripts, no ad-hoc filenames**: do not generate large combined scripts for discovery+viz+dashboard in this step. Never write files named like `_build_*.py`, `_simple_*.py`, `_temp_*.py`, or similar ad-hoc/throwaway names — these are a sign the payload is being reconstructed from scratch instead of imported from `viz_helpers.py`.
8. **Import, don't reconstruct**: `from viz_helpers import ...` and call the functions directly. Reading `ref-viz.md`/`ref-dashboard.md` prose and then retyping a similar-looking payload dict does not satisfy this rule — it is the exact failure mode `viz_helpers.py` exists to prevent.
9. **No ad-hoc JSON**: never hand-construct a `visualSpecification`/`fields`/`style` dict by typing out its keys. If `create_visualization()` raises a validation error you can't resolve within the retry cap (#6), stop — do not start improvising missing keys one at a time against the API's error messages.
10. **Sequential gate**: do not create visualization #2+ until visualization #1 passes POST success, `name` extraction, and render validation.
11. **Failure contract**: on first blocking failure, print endpoint, payload fragment, response body, and exact next action, then stop.
12. **UserAgg function lock**: if a calculated measure has SDM `aggregationType="UserAgg"`, do not apply a visualization-level function (`Avg`/`Sum`/etc.) on that field. Block the run if payload generation attempts a secondary aggregation.
13. **Field-manifest lock**: before the first visualization POST, construct a single in-memory field manifest from the selected model (SDOs, dimensions, measurements, calculated fields, aggregation types) and resolve every viz field from that manifest only.
14. **Unresolved-field hard fail**: if any viz field is unresolved in the manifest, stop immediately and print the unresolved field names; do not issue visualization POST with guessed replacements. A field name typed from memory of a "typical" naming pattern (e.g. guessing `Opportunities_clc` instead of confirming `Number_of_Opportunities_clc` in the manifest) is a guessed replacement, even if it's your first attempt.
15. **No diagnostic side-scripts**: during normal execution, do not generate or run ad-hoc `_get_*` discovery scripts for field lookups; use one preflight manifest function/path.
16. **Inline execution allowance**: under no-new-file constraints, run visualization/API operations inline (`python -c`, heredoc, or `curl`) that import from `viz_helpers.py`, instead of writing new helper files; this constraint does not permit blocking on execution, and it does not permit redefining `viz_helpers.py`'s functions inline instead of importing them.
17. **Chart intent immutability**: once a visualization intent is declared (goal + key fields + mark type), do not switch to a different fallback chart to pass API validation unless the user explicitly approves intent change.
18. **Render proof requirement**: for each required visualization, capture explicit render-validation evidence in dashboard context before continuing to dashboard assembly.
19. **Preflight declaration requirement**: before creating visualizations, print a standalone preflight declaration listing touched files/paths and confirming whether new files will be created.
20. **Checklist execution requirement**: per visualization, print `payload fields`, execute one POST, print response/result, then print render-validation evidence; do not continue silently.
21. **Violation abort requirement**: if any hard rule is broken, stop immediately and report the exact violated rule instead of attempting in-session recovery loops.
