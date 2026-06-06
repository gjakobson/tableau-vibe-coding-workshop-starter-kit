# Reference: Semantic Data Model (SDM)

Read this file when the user wants to add calculated fields, metrics, relationships, or build a new SDM from scratch.

---

## CONCIERGE OPTIMIZATION — DESIGN PRINCIPLES

Apply all of these before writing any SDM code.

### 1. Field Descriptions — most important input to Concierge

Rules:
1. **Under 255 characters** — hard limit
2. **No abbreviations** — write every term in full
3. **State the business purpose** — what question does this field answer?
4. **Include the grain** — "one row per sales rep per month"
5. **Assign roles** — every field must be Dimension or Measure
6. **Name = intent** — rename ambiguous fields before describing them

**Good field description:**
> `Total dollar value of open opportunities owned by this sales rep in the given month. Use to track pipeline volume trends and compare performance across regions and deal segments.`

**Good metric description:**
> `Tracks total dollar value of open opportunities each month. Rising values indicate healthy pipeline activity. Declining values suggest reduced prospecting, deal slippage, or increased churn from the pipeline.`

**Good SDO description:**
> `Monthly opportunity pipeline activity. One row per sales rep per month. Use to analyze pipeline value, win rates, and deal stage trends by region, segment, and product line.`

### 2. identifyingDimension — who the metric is about

- **Always use a *name* field** — never an ID field. `Rep Name`, not `Rep ID`
- **Must be a dimension from a joined dimension table**
- **Must also appear in `additionalDimensions`** — or API returns 400
- One per metric; choose the entity the persona cares most about

### 3. insightsDimensionsReferences — what Concierge uses to explain WHY

- Include 3–5 meaningful business dimensions (region, segment, product type, client tier)
- Never include ID fields or date fields
- All dims here MUST also be in `additionalDimensions` — API returns 400 otherwise
- Less is more — 3 well-chosen dims produce better AI explanations than 8 noisy ones

### 4. Insight types — select by metric type

| Insight type | Flow | Rate | Snapped | Notes |
|---|---|---|---|---|
| `CurrentTrend` | ✅ | ✅ | ✅ | Always include |
| `TrendChangeAlert` | ✅ | ✅ | ✅ | Detects signal onset — critical |
| `ComparisonToExpectedRangeAlert` | ✅ | ✅ | ✅ | Always include |
| `TopContributors` | ✅ | ✅ | ✅ | Always include |
| `BottomContributors` | ✅ | ✅ | — | |
| `TopDrivers` | ✅ | ✅ | — | |
| `TopDetractors` | ✅ | ✅ | — | |
| `ConcentratedContributionAlert` | ✅ | — | — | |
| `RecordLevelTable` | — | — | ✅ | |
| `OutlierDetection` | ✅ | ✅ | — | |

Minimum set that always works: `CurrentTrend`, `TrendChangeAlert`, `ComparisonToExpectedRangeAlert`, `TopContributors`.

### 5. singularNoun / pluralNoun — how Concierge narrates insights

| Metric type | singularNoun | pluralNoun |
|---|---|---|
| Dollar amount | `"dollar"` | `"dollars"` |
| Count of deals/opps | `"deal"` | `"deals"` |
| Count of accounts | `"account"` | `"accounts"` |
| Rate / percentage | `"percent"` | `"percent"` |
| Score | `"point"` | `"points"` |
| Headcount / reps | `"rep"` | `"reps"` |

### 6. timeGrains — choose by data granularity

| Use case | Recommended timeGrains |
|---|---|
| Monthly banking (default) | `["Month", "Quarter", "Year"]` |
| Weekly reporting or activity | `["Week", "Month", "Quarter"]` |
| Daily balances / transactions | `["Day", "Week", "Month"]` |

Omit grains finer than your data — daily grain on monthly data returns misleading Concierge answers.

### 7. Field visibility

Set `isVisible: False` on:
- ID / foreign key fields (link tables but should not surface in AI answers)
- Technical date keys (`month_key__c`, `year__c`)
- Composite / helper fields created for join logic

### 8. Field count discipline

- Fact table: 8–12 fields max (3–4 dims + 4–6 measures + date + hidden IDs)
- Dimension table: 5–8 fields max

### 9. Concierge question engineering — design the questions first

| Pattern | Example | What it shows |
|---|---|---|
| Single entity, single answer | "Show me pipeline coverage by region this quarter" | Basic KPI lookup |
| Slice by dimension | "How do win rates compare across deal segments?" | Breakdown |
| Filter applied | "Show me open pipeline in the West last month" | NL filtering |
| Multi-entity comparison | "Compare quota attainment across my top three regions" | Ranking |
| Multi-step breakdown | "Show me pipeline by rep and deal stage for Q1" | Complex |
| Semantic learning | "Which reps are underperformers?" → define threshold | Calc field on the fly |

**Confirmed failure patterns — never include these:**

| Question type | Failure mode |
|---|---|
| Root cause / "why" — "Why is pipeline declining?" | Content policy rejection |
| Cross-filter comparison against a benchmark | NL2SQ error: `Unsupported function: equals` |
| Ambiguous field reference | NL2SQ error: `Missing reference` |

**Safe frames**: "Which X has the highest/lowest Y?", "Show me Y by X", "What is Y vs prior period?", "Which X are underperforming?"

**Naming rule**: Do NOT prefix calc fields with "Average" — Concierge auto-prepends "Avg." producing "Avg. Average Win Rate". Use plain nouns: `"Win Rate"`, not `"Average Win Rate"`.

### 10. Post-build step — enable Analytics Agent Readiness (manual)

After the script runs, coach the user:
> "Open your new semantic model in Data 360 → Settings → Analytics Agent Readiness → toggle ON. This activates the Agentforce / Concierge panel on all metric and dashboard pages."

### 11. Business Preferences — the "system prompt" for Concierge

Rules: each preference starts with `#`, max 300 chars, max 50 preferences per model. Less = faster Concierge.

```
# When users ask about 'pipeline', they mean open opportunities weighted by probability, not total contract value
# When asked about 'top performers' or 'best reps', rank by Closed Won revenue descending for the most recent quarter
# AE is short for Account Executive. Sales reps and AEs refer to the same role
# When discussing win rates, a rate below 25% indicates underperformance for {Company Name}
# When a user asks about 'declining' metrics without specifying a time period, compare the most recent 3 months to the prior 3 months
# {Company Name} uses 'segment' to refer to deal size tiers: SMB, Mid-Market, and Enterprise
# When asked about deal size or average deal size, refer to the Average Deal Size metric, not total pipeline value
# When users say 'this quarter', they mean the current calendar quarter, not the fiscal quarter
```

**API path — CONFIRMED WORKING:**
```python
BUSINESS_PREFERENCES = "\n\n".join(["# <preference one>", "# <preference two>"])
resp = requests.patch(
    f"{BASE_SEM}/ssot/semantic/models/{model_api_name}",
    headers=SF_HDRS,
    json={"businessPreferences": BUSINESS_PREFERENCES},
)
```

**This is a standard automated step in all demo scripts — do NOT list it as a manual step in the demo guide.**

---

## STEP 7 — FULL CODE: Semantic Data Model

### Step C — GET model to discover auto-generated field apiNames (REQUIRED)

Always GET the model before adding fields — never assume apiNames from memory.

```python
r = requests.get(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}",
                 headers=SF_HDRS, params={"includeModelContent": True})
r.raise_for_status()
full_model = r.json()

field_api = {}
for sdo in full_model.get("semanticDataObjects", []):
    sdo_key = sdo["apiName"]
    field_api[sdo_key] = {}
    for f in sdo.get("semanticMeasurements", []) + sdo.get("semanticDimensions", []):
        field_api[sdo_key][f["dataObjectFieldName"]] = f["apiName"]

def fld(sdo_key, dlo_field):
    name = field_api.get(sdo_key, {}).get(dlo_field)
    if not name:
        raise ValueError(f"SDM field not found: {sdo_key}.{dlo_field}")
    return name
```

### Step D — POST calculated measurements

Calc measurements accept `"Currency"` and `"Percentage"` dataTypes (unlike raw SDO measurements).

```python
fact_sdo = sdo_api_names["Opportunities"]

calc_measurements = [
    {
        "apiName":         "Total_Pipeline_Value_clc",
        "label":           "Total Pipeline Value",
        "description":     "Sum of open opportunity amounts in a given period. Use to track pipeline volume and coverage trends.",
        "expression":      f"[{fact_sdo}].[{fld(fact_sdo, 'amount__c')}]",
        "aggregationType": "Sum",
        "dataType":        "Currency",
        "decimalPlace":    2,
        "directionality":  "Up",
        "displayCategory": "Continuous",
        "level":           "Row",
        "isVisible":       True,
        "shouldTreatNullsAsZeros": False,
        "sortOrder":       "Ascending",
        "sentiment":       "SentimentTypeUpIsGood",
    },
]

for calc in calc_measurements:
    resp = requests.post(
        f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/calculated-measurements",
        headers=SF_HDRS, json=calc,
    )
    if not resp.ok:
        print(f"ERROR calc '{calc['label']}': {resp.text}"); sys.exit(1)
    print(f"  ✅ Calc measurement: {calc['apiName']}")
```

### Step E — POST calculated date dimension (date-shift formula — always use this)

```python
date_sdo   = fact_sdo
date_field = fld(fact_sdo, 'close_date__c')

date_shift_expr = (
    f"DATEADD('day', "
    f"DATEDIFF('day', {{MAX([{date_sdo}].[{date_field}])}}, "
    f"DATETRUNC('month', TODAY())), "
    f"[{date_sdo}].[{date_field}])"
)

calc_dimensions = [
    {
        "apiName":         "Activity_Date_clc",
        "label":           "Activity Date",
        "description":     "Primary time dimension. Dates are dynamically shifted so the most recent data always aligns with the current month.",
        "expression":      date_shift_expr,
        "dataType":        "Date",
        "displayCategory": "Discrete",
        "level":           "Row",   # CONFIRMED: "Row" works even with {MAX(...)} LOD syntax
        "isVisible":       True,
        "sortOrder":       "None",
    },
]

for dim in calc_dimensions:
    resp = requests.post(
        f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/calculated-dimensions",
        headers=SF_HDRS, json=dim,
    )
    if not resp.ok:
        print(f"ERROR dim '{dim['label']}': {resp.text}"); sys.exit(1)
    print(f"  ✅ Calc date dimension: {dim['apiName']}")
```

**Tableau formula quick reference:**
- Aggregation: `SUM([SDO].[field])`, `AVG(...)`, `COUNT(...)`, `COUNTD(...)`, `MAX(...)`, `MIN(...)`
- Date: `TODAY()`, `DATEADD('month', 3, [SDO].[date])`, `DATEDIFF('day', start, end)`, `DATETRUNC('month', [SDO].[date])`
- Logic: `IF [cond] THEN [val] ELSE [default] END`
- LOD: `{MAX([SDO].[field])}` — curly braces = FIXED aggregate across all rows
- Filter operators: `Equals`, `CurrentMonth`, `PreviousMonth`, `Last30Days`, `Last90Days`, `GreaterThan`, `Between`

### Step F — POST Semantic Metrics

```python
def dim_ref(sdo, dlo_field):
    return {"tableFieldReference": {"fieldApiName": fld(sdo, dlo_field), "tableApiName": sdo}}

def all_insight_types():
    return [{"enabled": True, "type": t} for t in [
        "TopContributors", "ComparisonToExpectedRangeAlert", "TrendChangeAlert",
        "BottomContributors", "ConcentratedContributionAlert", "TopDrivers",
        "TopDetractors", "CurrentTrend", "OutlierDetection", "RecordLevelTable",
    ]]

dim_sdo      = sdo_api_names["Sales Reps"]
rep_name_ref = dim_ref(dim_sdo, "rep_name__c")

metric_dims = [
    dim_ref(fact_sdo, "region__c"),
    dim_ref(fact_sdo, "segment__c"),
    dim_ref(fact_sdo, "rep_id__c"),
    dim_ref(dim_sdo,  "rep_name__c"),   # MUST be here because it's in identifyingDimension
    dim_ref(dim_sdo,  "region__c"),
]

metrics = [
    {
        "apiName":     "total_pipeline_value_md",
        "label":       "Total Pipeline Value",
        "description": "Total dollar value of open opportunities in a given period.",
        "measurementReference":   {"calculatedFieldApiName": "Total_Pipeline_Value_clc"},
        "timeDimensionReference": {"calculatedFieldApiName": "Activity_Date_clc"},
        "aggregationType": "Sum",
        "isCumulative":    False,
        "timeGrains":      ["Month", "Quarter", "Year"],
        "additionalDimensions": metric_dims,
        "insightsSettings": {
            "identifyingDimension": {"identifierDimensionReference": rep_name_ref},
            "insightTypes": all_insight_types(),
            "insightsDimensionsReferences": [
                rep_name_ref,
                dim_ref(fact_sdo, "region__c"),
                dim_ref(fact_sdo, "segment__c"),
            ],
            "singularNoun": "dollar",
            "pluralNoun":   "dollars",
            "sentiment":    "SentimentTypeUpIsGood",
        },
    },
]

for metric in metrics:
    resp = requests.post(
        f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/metrics",
        headers=SF_HDRS, json=metric,
    )
    if not resp.ok:
        print(f"ERROR metric '{metric['label']}': {resp.text[:300]}")

# Fetch metric IDs after creation (needed for dashboard metric widgets)
r = requests.get(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/metrics", headers=SF_HDRS)
metric_ids = {m["label"]: m["id"] for m in r.json().get("metrics", [])}
```

### Step G — POST relationship

```python
resp = requests.post(
    f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/relationships",
    headers=SF_HDRS,
    json={
        "leftSemanticDefinitionApiName":  fact_sdo,
        "rightSemanticDefinitionApiName": dim_sdo,
        "joinType": "Auto",    # MUST be "Auto" at model level — explicit types only for logical views
        "criteria": [{
            "joinOperator":             "EqualsIgnoreCase",
            "leftFieldType":            "TableField",
            "leftSemanticFieldApiName":  fld(fact_sdo, "rep_id__c"),
            "rightFieldType":           "TableField",
            "rightSemanticFieldApiName": fld(dim_sdo, "rep_id__c"),
        }]
    },
)
if not resp.ok:
    print(f"ERROR relationship: {resp.text}")
```

### Step H — Validate

```python
resp = requests.get(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/validate", headers=SF_HDRS)
if resp.ok:
    print(f"  isValid={resp.json().get('isValid')}")
```

### Step — Link SDM to workspace

```python
resp = requests.post(
    f"{BASE_SEM}/tableau/workspaces/{workspace_name}/assets",
    headers=SF_HDRS,
    json={"assetId": model_id, "assetType": "SemanticModel", "assetUsageType": "Referenced"},
)
if resp.status_code == 201:
    print(f"  ✅ SDM linked to workspace: {workspace_name}")
```

### Confirmed Enum Values

| Field | Confirmed values |
|---|---|
| `dataObjectType` | `"Dmo"`, `"Dlo"`, `"Cio"` |
| `displayCategory` | `"Discrete"`, `"Continuous"` |
| `directionality` | `"Up"`, `"Down"`, `None` |
| `aggregationType` (measurements) | `"None"`, `"Sum"`, `"Average"`, `"Min"`, `"Max"`, `"Count"`, `"UserAgg"` |
| `dataType` (SDO raw) | `"Text"`, `"Number"`, `"Date"`, `"DateTime"`, `"Boolean"` (NOT Currency/Percentage) |
| `dataType` (calc fields) | `"Text"`, `"Number"`, `"Date"`, `"Currency"`, `"Percentage"`, `"Boolean"` |
| `joinType` (model-level) | `"Auto"` only |
| `joinType` (logical views) | `"Left"`, `"Right"`, `"Inner"`, `"Outer"` |
| `timeGrains` | `"Day"`, `"Week"`, `"Month"`, `"Quarter"`, `"Year"` |
| `sentiment` (calc fields) | `"SentimentTypeUpIsGood"`, `"SentimentTypeUpIsBad"`, `"SentimentTypeNone"` |
| `level` (calc fields) | `"Row"`, `"AggregateFunction"` |

### Optional Steps

**Step I — Parameters:**
```python
parameters = [{"apiName": "Target_Pipeline_Amount_prm", "label": "Target Pipeline Amount",
               "description": "Threshold for flagging underperforming sales reps.",
               "dataType": "Number", "defaultValue": "500000"}]
for param in parameters:
    resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/parameters",
                         headers=SF_HDRS, json=param)
# Reference in expression: [Parameters].[Target_Pipeline_Amount_prm]
```

**Step J — Submetrics:**
```python
submetric = {"apiName": "enterprise_pipeline_value_sub", "label": "Enterprise Pipeline Value",
             "description": "...",
             "filters": [{"fieldReference": {"tableFieldReference": {"fieldApiName": fld(fact_sdo, "segment__c"), "tableApiName": fact_sdo}},
                          "operator": "Equals", "values": ["Enterprise"]}]}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/metrics/{PARENT_METRIC_API_NAME}/submetrics",
                     headers=SF_HDRS, json=submetric)
```

**Step K — Logical Views:**
```python
# Explicit LEFT JOIN:
lv_payload = {"apiName": "Rep_Activity_lv", "label": "Rep Activity View", "description": "...",
              "joins": [{"leftSemanticDefinitionApiName": fact_sdo, "rightSemanticDefinitionApiName": dim_sdo,
                         "joinType": "Left",
                         "criteria": [{"joinOperator": "EqualsIgnoreCase", "leftFieldType": "TableField",
                                       "leftSemanticFieldApiName": fld(fact_sdo, "rep_id__c"),
                                       "rightFieldType": "TableField",
                                       "rightSemanticFieldApiName": fld(dim_sdo, "rep_id__c")}]}]}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/logical-tables",
                     headers=SF_HDRS, json=lv_payload)

# Union:
union_payload = {"apiName": "All_Regions_lv", "label": "All Regions", "description": "...",
                 "union": {"semanticDataObjectApiNames": [east_sdo, west_sdo]}}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/logical-tables",
                     headers=SF_HDRS, json=union_payload)
```

**Step L — Groups and Bins:**
```python
group = {"apiName": "Deal_Segment_Group_grp", "label": "Deal Segment Group", "description": "...",
         "sourceFieldReference": {"tableFieldReference": {"fieldApiName": fld(fact_sdo, "segment__c"), "tableApiName": fact_sdo}},
         "groups": [{"label": "Enterprise", "values": ["ENT", "CORP"]}, {"label": "Mid-Market", "values": ["MM"]}],
         "otherLabel": "SMB"}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/groups", headers=SF_HDRS, json=group)

bin_p = {"apiName": "Deal_Amount_Bin_bin", "label": "Deal Size Bucket", "description": "...",
          "sourceFieldReference": {"tableFieldReference": {"fieldApiName": fld(fact_sdo, "amount__c"), "tableApiName": fact_sdo}},
          "binCount": 5}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/bins", headers=SF_HDRS, json=bin_p)
```
