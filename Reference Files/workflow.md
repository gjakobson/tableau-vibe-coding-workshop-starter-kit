# Dashboard Creation Workflow

> **Back to main skill:** [SKILL.md](SKILL.md)

**CRITICAL**: When creating dashboards, ALWAYS follow this workflow in order. Templates are MANDATORY for both visualizations and dashboards.

## Overview

This workflow ensures you discover available data, select appropriate chart types, use production-quality templates, and create dashboards that comply with the Tableau Next API.

## Fast Path Execution (One-Pass Build)

Use this mode when users ask for multiple steps at once (for example charts + dashboard + custom viz in one request). Keep speed high, but enforce these gates:

1. **Single model source of truth**: resolve one `SDM apiName` and exact field apiNames once, then reuse.
2. **No cross-org carryover**: never reuse model IDs/field apiNames from previous runs.
3. **Incremental validation**: POST first visualization, verify success, then continue.
4. **Fail fast**: if any viz payload fails, stop and fix immediately before creating more artifacts.
5. **Structured edits only**: avoid regex mutation of metadata/scripts when direct JSON/API updates are available.
6. **Dashboard last**: only build dashboard after all required visualizations have succeeded and returned `name` values.
7. **Aggregation semantics lock**: for calculated measures, set `function` to the SDM `aggregationType` mapping; never force `Sum` for `UserAgg`/aggregate calcs unless SDM confirms `Sum`.
8. **Renderability gate**: after creating visualization #1, place it in dashboard context and confirm it renders before creating the rest.
9. **Model identity lock**: abort if any script step switches away from the selected model apiName.
10. **Time budget lock**: discovery/mapping <= 90s, first viz create+render <= 120s, each extra viz <= 90s, dashboard assembly <= 90s, optional extension deploy+attach <= 180s.
11. **Retry cap lock**: one retry max per failed API call after an explicit fix; if still failing, stop and ask user.
12. **Capability probe lock**: run one up-front endpoint capability check (for example submetric support) and skip unsupported branches for the rest of run.
13. **No large ad-hoc scripts**: do not create monolithic orchestration scripts in normal runs; prefer existing templates/utilities and compact stage-scoped scripts.
14. **Question minimization**: if user already gave selections/theme/chart type, do not ask extra planning questions before execution.
15. **Progress contract**: after each phase, print elapsed time and artifacts created; abort immediately when a phase exceeds budget.
16. **Template-first lock**: before writing viz/dashboard code, read `ref-viz.md` + `ref-dashboard.md` and locate at least one working in-repo example.
17. **No ad-hoc payloads**: do not hand-build visualization/dashboard JSON when a known working template exists.
18. **Sequential viz lock**: visualization N+1 cannot be created until visualization N passes success + `name` + render checks.
19. **Dashboard gate lock**: dashboard creation/patching is forbidden until all required visualizations pass render validation.
20. **Same-run identifier lock**: reference only visualization `name` values returned from successful POST responses in the current run.
21. **Failure output lock**: on first blocking failure, emit endpoint, payload fragment, response body, and next action, then stop.
22. **KPI row requirement**: when model metrics are available, dashboard must include a top KPI row (up to 4 metric widgets) before chart widgets.
23. **KPI skip reason requirement**: if KPI row is skipped, emit explicit reason (e.g., no metrics found, metric IDs unresolved) before dashboard completion.
24. **Metrics-first planning lock**: when dashboard is in scope, select 4-6 KPI metrics from existing model metrics before creating any new calculated fields/metrics.
25. **New-metric exception lock**: only create new metrics when explicitly requested by user or when existing metrics cannot adequately cover the selected theme.
26. **Field manifest lock**: before any visualization POST, build one in-memory manifest from selected model metadata (SDOs, dimensions, measurements, calculated fields, and aggregation types) and resolve all payload fields from it.
27. **Unresolved field hard fail**: if any requested visualization field cannot be resolved from the manifest, stop and report the exact missing field; do not guess, alias, or auto-edit field apiNames.
28. **No diagnostic side-scripts lock**: in normal run mode, do not create ad-hoc `_get_*` helper scripts for field discovery; perform one manifest preflight and reuse it across the run.
29. **Inline execution allowance lock**: when "no new files" constraints apply, execute API steps inline (`python -c`, `python` heredoc, or `curl`) rather than creating files; no-file mode is not a valid reason to stop execution.
30. **Chart intent immutability lock**: after declaring visualization plan, do not change chart purpose/field set/mark type as a fallback to force success. Stop and report failure unless user explicitly approves a new chart intent.
31. **Render-proof dashboard gate lock**: dashboard creation or patching is blocked until every required visualization includes explicit render validation proof from this run.
32. **Mandatory preflight message lock**: before execution, emit a separate preflight block with intended file/path touches, execution mode, and explicit `New files to create: none` when no-file constraints are active.
33. **Structural checklist lock**: for options 1-3, enforce and print this sequence per visualization: manifest built, payload field bindings printed, single POST attempt, render validation result, then continue or stop.
34. **Violation abort lock**: if any hard lock is violated in-session, abort immediately and report the violation; do not continue with corrective improvisation in the same run.

If a gate fails, do not continue the one-pass run blindly; repair at the failing step and resume.

```mermaid
graph TD
    START[Start] --> DISCOVER[Phase 1: Discover SDMs]
    DISCOVER --> SELECT[Phase 2: Select Chart Type]
    SELECT --> TEMPLATE[Phase 3: Choose Template]
    TEMPLATE --> CREATE[Phase 4: Create Visualizations]
    CREATE --> DASHBOARD[Phase 5: Build Dashboard]
    DASHBOARD --> POST[Phase 6: POST to API]
    POST --> DONE[Dashboard Created!]
```

## Phase 1: Discover Available SDMs

**Goal:** List all available Semantic Data Models and understand what data is available.

### List All SDMs

**Via Script:**
```bash
python scripts/discover_sdm.py --list
```

**Via API:**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json"
```

**Response Structure:**
```json
{
  "semantic_models": [
    {
      "id": "sdm_12345",
      "apiName": "Sales_Analytics_Model",
      "label": "Sales Analytics",
      "description": "Complete sales performance metrics",
      "dataspace": "default"
    }
  ]
}
```

**What to extract:** SDM `apiName` for next steps

### Get Detailed SDM Definition

**Via Script:**
```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

**Via API:**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/{{SDM_NAME}}" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Response Structure:**
```json
{
  "apiName": "Sales_Analytics_Model",
  "label": "Sales Analytics",
  "semanticDataObjects": [
    {
      "apiName": "Opportunity",
      "label": "Opportunities",
      "semanticDimensions": [
        {"apiName": "Region", "label": "Region", "dataType": "Text"},
        {"apiName": "Close_Date", "dataType": "DateTime"}
      ],
      "semanticMeasurements": [
        {"apiName": "Amount", "label": "Amount", "aggregationType": "Sum"}
      ]
    }
  ],
  "semanticCalculatedMeasurements": [
    {"apiName": "Total_Sales_clc", "label": "Total Sales", "aggregationType": "Sum"},
    {"apiName": "Win_Rate_clc", "label": "Win Rate", "aggregationType": "UserAgg"}
  ],
  "semanticCalculatedDimensions": [
    {"apiName": "Days_to_Close_Bucket_clc", "label": "Days to Close (Bucket)", "dataType": "Text"}
  ]
}
```

**What to extract:**
- **Data objects**: `semanticDataObjects[].apiName` (e.g., "Opportunity")
- **Dimensions** (for grouping): `semanticDimensions[]` → text, date fields
- **Measures** (for aggregation): `semanticMeasurements[]` → numeric fields with `aggregationType`
- **Calculated measures**: `semanticCalculatedMeasurements[]` → use `aggregationType` directly as `function`
- **Calculated dimensions**: `semanticCalculatedDimensions[]` → text/boolean fields with `_clc` suffix

**Key:** `semanticCalculatedMeasurements[].aggregationType` is the exact value to use as `function` in field definitions. Never assume `"Sum"` — always read it from the SDM.

## Phase 2: Select Chart Type

**Goal:** Choose the appropriate chart type based on your data pattern and visualization goal.

Use the decision matrix from [templates-guide.md](templates-guide.md) to select the right chart type:

| Data Pattern | Field Combination | Recommended Chart Type | Template |
|--------------|------------------|----------------------|----------|
| **Trend over time** | 1 Date Dimension + 1 Measure | Line Chart | `trend_over_time` |
| **Multi-series trend** | 1 Date Dimension + 1 Measure + 1 Dimension | Multi-Series Line Chart | `multi_series_line` |
| **Comparison/Ranking** | 1 String Dimension + 1 Measure | Horizontal Bar Chart (sorted descending) | `revenue_by_category` |
| **Part-to-Whole (< 5 values)** | 1 Dimension (< 5 unique values) + 1 Measure | Donut Chart | `market_share_donut` |
| **Part-to-Whole (≥ 5 values)** | 1 Dimension (≥ 5 unique values) + 1 Measure | Stacked Bar Chart | `stacked_bar_by_dimension` |
| **Part-to-Whole with Breakdown** | 2 Dimensions + 1 Measure | Stacked Bar Chart | `stacked_bar_by_dimension` |
| **Two-dimensional analysis** | 2 Dimensions + 2 Measures | Dot Matrix | `dot_matrix` |
| **Correlation** | 2 Continuous Measures | Scatter Plot | `scatter_correlation` |
| **Funnel/Stage Analysis** | 1 Stage Dimension + 1 Measure | Funnel Chart | `conversion_funnel` |
| **Heatmap** | 2 Dimensions + 1 Measure | Heatmap | `heatmap_grid` |
| **Detailed Table** | Multiple Dimensions + Measures | Table (sorted) | `top_n_leaderboard` |

**Decision Rules:**
- **Never use Pie Chart** — Use Donut Chart instead (better for < 5 slices)
- **Bar Charts are automatically sorted descending** by measure (templates handle this) + **add color_dim when 2+ dimensions available**
- **Line Charts use Year + Month hierarchy AUTOMATICALLY** — Templates handle this via `date_functions` (DatePartYear + DatePartMonth). No manual configuration needed.
- **Always add color encodings** when multiple dimensions available — Use optional `color_dim` field in templates
- **Date Dimensions** → Always use Line Chart for trends (prefer `multi_series_line` with `color_dim` if dimension available)
- **Stage/Status fields** → Prefer Bar Chart over Funnel (bar charts are more versatile)
- **2 Measures** → Use Scatter Plot with Detail + Color encodings to show correlation

See [templates-guide.md](templates-guide.md) for the complete decision matrix with examples.

## Phase 3: Choose Template

**Goal:** Select the appropriate visualization template or use auto-select.

### Option 1: Auto-Select Chart Type (Recommended)

The system can automatically detect your data pattern and select the appropriate template:

```bash
python scripts/apply_viz_template.py \
  --sdm Sales_Model \
  --date Close_Date \
  --measure Total_Amount \
  --auto-select \
  --auto-match \
  --name Sales_Trend \
  --workspace My_Workspace \
  --post
```

The system will automatically detect "1 Date Dimension + 1 Measure" and select `trend_over_time` template (Line Chart). If a dimension is also available, it will prefer `multi_series_line` with color_dim for better visualization.

**With color encoding:**
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --category Region \
  --amount Total_Amount \
  --color-dim Opportunity_Type \
  --name Revenue_by_Region \
  --workspace My_Workspace \
  --post
```

This adds Color encoding + legend automatically (test harness pattern).

### Option 2: Explicit Template Selection

**List available templates:**
```bash
python scripts/apply_viz_template.py --list-templates
```

**Preview template requirements:**
```bash
python scripts/apply_viz_template.py --preview revenue_by_category
```

**Create from template:**
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --category Region \
  --amount Total_Amount \
  --name Revenue_by_Region \
  --label "Revenue by Region" \
  --workspace My_Workspace \
  --post
```

**Auto-match fields** (when field names are obvious):
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --auto-match \
  --name Revenue_Bar \
  --workspace My_Workspace \
  --post
```

The template will search for fields like "Amount", "Revenue", "Total", etc. and match them automatically.

See [templates-guide.md](templates-guide.md) for the complete template catalog.

## Phase 4: Create Visualizations

**Goal:** Create all visualizations needed for your dashboard BEFORE creating the dashboard.

**CRITICAL**: Always use visualization templates instead of manually building visualization JSON. Templates ensure proper field structure, encodings, sorting, and API compliance.

### Create Each Visualization

For each visualization needed:
1. Use `apply_viz_template.py` with `--auto-select` and `--auto-match` when possible
2. Or explicitly choose template from [templates-guide.md](templates-guide.md) based on data pattern
3. **NEVER manually build visualization JSON** — always use templates

### Validate Before POSTing

```bash
python scripts/validate_viz.py viz.json
```

### POST Visualization to API

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @viz.json
```

**Response:**
```json
{
  "id": "viz_abc123",
  "name": "Revenue_by_Region",
  "label": "Revenue by Region",
  "url": "https://{instance}.salesforce.com/analytics/visualization/viz_abc123"
}
```

### Note Visualization API Names

**IMPORTANT:** Note the API names (`name` field) of all created visualizations — you'll need these for the dashboard in Phase 5.

## Phase 5: Build Dashboard Using Pattern

**Goal:** Create dashboard JSON using a production-ready pattern that ensures proper layout and API compliance.

**CRITICAL**: Always use dashboard patterns/templates instead of manually building dashboard JSON. Dashboard patterns ensure proper layout, widget structure, and API compliance.

### Choose Dashboard Pattern

Review available dashboard patterns:

1. **`f_layout`** — Metrics in left sidebar, visualizations in F-pattern
   - Best for: Executive dashboards with KPIs prominently displayed
   - **REQUIRES metrics** - Do not use if no metrics available

2. **`z_layout`** — Metrics in top row, visualizations in Z-pattern  
   - Best for: Operational dashboards with metrics at top, OR visualizations-only dashboards
   - **OPTIONAL metrics** - Only pattern that gracefully handles no metrics

3. **`vertical_metrics`** — Full-width metrics stacked vertically, multi-page
   - Best for: Metrics-focused dashboards with many KPIs
   - **REQUIRES metrics** - Designed for metrics only

4. **`horizontal_metrics`** — Metrics in horizontal rows, multi-page
   - Best for: Balanced dashboards with metrics and visualizations
   - **REQUIRES metrics** - Designed for metrics

5. **`performance_overview`** — Large metric left, smaller metrics right, time navigation
   - Best for: Performance dashboards with time-based navigation
   - **REQUIRES metrics** - primary_metric is mandatory

### Auto-Select Pattern (Recommended)

```bash
python scripts/generate_dashboard_pattern.py \
  --auto-select-pattern \
  --name {{DASHBOARD_NAME}} \
  --workspace-name {{WORKSPACE}} \
  --sdm-name {{SDM_NAME}} \
  --viz {{VIZ_1}} {{VIZ_2}} ... \
  --metrics {{METRIC_1}} {{METRIC_2}} ... \
  --filter fieldName={{FIELD}} objectName={{OBJECT}} dataType={{TYPE}} \
  -o dashboard.json
```

Auto-select logic:
- **Metrics + Visualizations** → `f_layout` (metrics left sidebar, vizzes right)
- **Metrics only** → `vertical_metrics` (full-width stacked)
- **Visualizations only** → `z_layout` (only pattern that handles no metrics)

### Explicit Pattern Selection

```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --name Sales_Dashboard \
  --label "Sales Dashboard" \
  --workspace-name My_WS \
  --sdm-name Sales_Model \
  --title-text "Sales Performance" \
  --metrics Total_Revenue_mtc Win_Rate_mtc \
  --viz Revenue_Bar Pipeline_Funnel \
  --filter fieldName=Account_Industry objectName=Opportunity dataType=Text \
  -o dashboard.json
```

**Pattern-specific arguments:**
- **f_layout/z_layout**: `--title-text "Dashboard Title"`
- **vertical_metrics**: `--metrics-per-page 4 --pages "Page 1" "Page 2"`
- **horizontal_metrics**: `--metrics-per-row 4 --pages "Page 1" "Page 2"`
- **performance_overview**: `--primary-metric Total_Revenue_mtc --secondary-metrics Win_Rate_mtc Pipeline_Count_mtc --pages "Week" "Month" "Day"`

**Reference previously created visualizations by API name** (from Phase 4).

See [templates-guide.md](templates-guide.md) for complete pattern documentation.

## Phase 6: POST Dashboard to API

**Goal:** Create the dashboard in Salesforce.

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/dashboards?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

**Response:**
```json
{
  "id": "dash_abc123",
  "name": "Sales_Dashboard",
  "label": "Sales Dashboard",
  "url": "https://{instance}.salesforce.com/analytics/dashboard/dash_abc123"
}
```

## Why This Order Matters

- **SDM First**: Ensures you know what data is available before designing
- **Pattern Selection**: Dashboard layout drives which visualizations are needed
- **Templates Required**: Both visualization and dashboard templates ensure API compliance and quality
- **Visualizations Before Dashboard**: Dashboard references visualization API names, so they must exist first

## Next Steps

- See [templates-guide.md](templates-guide.md) for complete template catalog and decision matrix
- See [scripts-guide.md](scripts-guide.md) for detailed script usage
- See [troubleshooting.md](troubleshooting.md) if you encounter errors
- See [chart-catalog.md](chart-catalog.md) for full JSON templates
