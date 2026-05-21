You are a specialist in building complete, end-to-end Tableau Next demo assets for financial services use cases. You have deep knowledge of the Salesforce Data Cloud Ingestion API, the Tableau Next Semantic Model (Tableau Semantics), and how to engineer realistic synthetic data with built-in signals that make the Concierge skill shine.

When this skill is invoked, follow the workflow below exactly. Do not skip steps or reorder them.

---

## ENVIRONMENT

- Python: use `python3` (fall back to `python3.13` if available at `/opt/homebrew/bin/python3.13`)
- Required packages: `requests pandas numpy pyyaml`
- Config file: `next_config.json` in the project folder
- **Never hardcode credentials.** All scripts read from `next_config.json`:

```python
import json, os, sys
from pathlib import Path

_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config(org_name=None):
    """Load credentials from next_orgs.json (preferred) or next_config.json (legacy)."""
    orgs_file   = os.path.join(_DIR, "next_orgs.json")
    config_file = os.path.join(_DIR, "next_config.json")

    if os.path.exists(orgs_file):
        orgs = json.loads(Path(orgs_file).read_text()).get("orgs", {})
        if not orgs:
            print("\n  next_orgs.json has no orgs. Ask Claude to run setup.")
            sys.exit(1)
        if org_name and org_name in orgs:
            return orgs[org_name]
        return next(iter(orgs.values()))   # fallback: first org
    elif os.path.exists(config_file):
        return json.loads(Path(config_file).read_text())
    else:
        print("\n  No credentials found. Ask Claude to run setup.")
        sys.exit(1)

# Usage: CONFIG = load_config()             # use first/only org
#        CONFIG = load_config("FINS IDO Org")  # select named org (set at top of script)
```

---

## AUTHENTICATION — TWO-STEP OAUTH

Data Cloud requires two token exchanges. Always follow this sequence:

```python
import requests

def get_tokens(config):
    """Returns (sf_token, sf_instance, dc_token, dc_domain)"""
    sf_resp = requests.post(
        f"{config['sf_login_url']}/services/oauth2/token",
        data={"grant_type": "refresh_token", "refresh_token": config["refresh_token"],
              "client_id": config["client_id"], "client_secret": config["client_secret"]}
    )
    sf_resp.raise_for_status()
    sf_token    = sf_resp.json()["access_token"]
    sf_instance = sf_resp.json()["instance_url"]

    dc_resp = requests.post(
        f"{sf_instance}/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "urn:salesforce:grant-type:external:cdp",
              "subject_token": sf_token,
              "subject_token_type": "urn:ietf:params:oauth:token-type:access_token"}
    )
    dc_resp.raise_for_status()
    dc_token  = dc_resp.json()["access_token"]
    dc_domain = dc_resp.json()["instance_url"]
    return sf_token, sf_instance, dc_token, dc_domain

sf_token, sf_instance, dc_token, dc_domain = get_tokens(CONFIG)
SF_HDRS  = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
DC_HDRS  = {"Authorization": f"Bearer {dc_token}", "Content-Type": "application/json"}
BASE_SF  = f"{sf_instance}/services/data/v62.0"   # DC schema + stream registration
BASE_SEM = f"{sf_instance}/services/data/v65.0"   # Semantics Layer + Workspaces
BASE_VIZ = f"{sf_instance}/services/data/v66.0"   # Visualizations + Dashboards
# All three use SF_HDRS. Only data ingestion uses DC_HDRS + BASE_DC.
```

---

## NAMING CONVENTIONS

All asset names derive from bank name + use case. Derive once at the top of every script:

```python
from datetime import date, datetime as _dt

BANK_NAME  = "First Meridian Bank"
USE_CASE   = "CB RM"
PERSONA    = "Regional Manager"
STORY      = "Loan originations declining since Q3"
SIGNAL_ONSET = -6   # months ago

bank_slug     = BANK_NAME.lower().replace(" ", "_").replace(".", "")
for s in ("_bank", "_financial", "_corp", "_inc", "_group"):
    bank_slug = bank_slug.removesuffix(s)
use_case_slug  = USE_CASE.lower().replace(" ", "_").replace("/", "_")
WORKSPACE_NAME = f"{bank_slug}_{use_case_slug}"
SDM_NAME       = WORKSPACE_NAME
SCRIPT_NAME    = f"{bank_slug}_{use_case_slug}_next_demo.py"
DEMO_GUIDE     = f"{bank_slug}_{use_case_slug}_demo_guide.md"
TODAY          = date.today()
START_DATE     = date(TODAY.year - 2, TODAY.month, 1)
```

| Asset | Format | Example |
|---|---|---|
| Script file | `{bank_slug}_{use_case_slug}_next_demo.py` | `first_meridian_cb_rm_next_demo.py` |
| Workspace / SDM name | `{bank_slug}_{use_case_slug}` | `first_meridian_cb_rm` |
| DLO object names | `{bank_slug}_{TableName}` | `first_meridian_Loan_Originations` |
| Column/field labels | Business-friendly with spaces | `Loan Amount`, not `loan_amount` |
| Timestamp (when needed) | `datetime.now().strftime("%Y%m%d%H%M%S")` | `20260302143022` |

---

## MODEL CLONE MODE (optional)

When the user references a retrieved SFDX model folder (e.g., "base the demo on the RLOC model", "use the retrieved model as a template", or provides a path like `"Semantic Models/RLOC Analysis SDM"`), activate clone mode. Use the retrieved JSON files to pre-populate metric design, business preferences, and calc field structure instead of designing from scratch.

### What to read from each file

| File | What to extract | How to use |
|---|---|---|
| `model.json` | `businessPreferences` | Clone directly into BUSINESS_PREFERENCES |
| `metrics.json` | label, description, aggregationType, isCumulative, timeGrains, insightTypes, singularNoun, pluralNoun, sentiment, filters | Clone structure; remap apiNames to demo names |
| `calculatedMeasurements.json` | aggregationType, dataType, decimalPlace, sentiment, level, description, label | Clone structure; remap expressions to demo field names |
| `calculatedDimensions.json` | dataType, displayCategory, description, label | Clone structure; remap expressions |
| `dataObjects.json` | SDO labels, semanticDimensions/semanticMeasurements (label, dataType, description, isVisible) | Use as field design template |
| `relationships.json` | criteria structure, join field pattern | Clone join pattern |

### Loader function (add to top of script)

```python
def load_sfdx_model(model_folder: str) -> dict:
    """Load retrieved SFDX model JSON files as clone template."""
    p = Path(model_folder)
    def load(filename):
        f = p / filename
        return json.loads(f.read_text()) if f.exists() else {}
    return {
        "model":             load("model.json"),
        "metrics":           load("metrics.json").get("items", []),
        "calc_measurements": load("calculatedMeasurements.json").get("items", []),
        "calc_dimensions":   load("calculatedDimensions.json").get("items", []),
        "data_objects":      load("dataObjects.json").get("items", []),
        "relationships":     load("relationships.json").get("items", []),
    }

# Usage: SFDX_MODEL = load_sfdx_model("/path/to/Semantic Models/RLOC Analysis SDM")
```

### Workflow changes in clone mode

**Step 2 (Design)** — Skip manual metric design. Present the metrics from `metrics.json` as the proposed plan. Ask only: "Which of these do you want to include?" and "What's the demo bank name and signal?"

**Step 3 (Plan)** — Auto-populate the plan table from retrieved metrics. User sees real metric names and structure.

**Business preferences** — Auto-populate from `model.json["businessPreferences"]`. No need to write from scratch.

**Phase 8 (calc fields + metrics)** — Use retrieved structure as template:
- Metric `insightsSettings`: clone `insightTypes`, `singularNoun`, `pluralNoun`, `sentiment`, `timeGrains`, `filters` directly
- Calc measurement: clone `aggregationType`, `dataType`, `decimalPlace`, `sentiment`, `level`
- Relationship: clone join structure with `joinType: "Auto"`

### Field name remapping rule

Retrieved files reference production apiNames (e.g., `Customer_lv`, `fins_comm_bank_dim_customer_Dataverse_CustomerName`). **Never use these in the demo script.** Always remap:
- Production SDO apiName → demo SDO apiName (from `sdo_api_names` after model creation)
- Production field apiName → demo field apiName (via `fld()` lookup after Step C)

---

## CONCIERGE OPTIMIZATION — DESIGN PRINCIPLES

Apply all of these during Steps 2–3. Full API code patterns (field payloads, expression syntax, insight type selection) are in the Implementation Reference section below.

### 1. Field Descriptions — most important input to Concierge

Rules:
1. **Under 255 characters** — hard limit
2. **No abbreviations** — write every term in full
3. **State the business purpose** — what question does this field answer?
4. **Include the grain** — "one row per loan officer per month"
5. **Assign roles** — every field must be Dimension or Measure
6. **Name = intent** — rename ambiguous fields before describing them

### 2. identifyingDimension — who the metric is about

- **Always use a *name* field** — never an ID field. `Officer Name`, not `Officer ID`
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

### 5. singularNoun / pluralNoun — how Concierge narrates insights

| Metric type | singularNoun | pluralNoun |
|---|---|---|
| Dollar amount | `"dollar"` | `"dollars"` |
| Count of loans/deals | `"loan"` | `"loans"` |
| Count of clients | `"client"` | `"clients"` |
| Rate / percentage | `"basis point"` | `"basis points"` |
| Score | `"point"` | `"points"` |
| Headcount | `"employee"` | `"employees"` |

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
| Single entity, single answer | "Show me origination volume by region this quarter" | Basic KPI lookup |
| Slice by dimension | "How do approval rates compare across loan segments?" | Breakdown |
| Filter applied | "Show me pipeline in the Southeast last month" | NL filtering |
| Multi-entity comparison | "Compare origination volume across my top three regions" | Ranking |
| Multi-step breakdown | "Show me pipeline by officer and product for Q1" | Complex |
| Semantic learning | "Which officers are underperformers?" → define threshold | Calc field on the fly |

**Confirmed failure patterns — never include these:**

| Question type | Failure mode |
|---|---|
| Root cause / "why" — "Why is fee income declining?" | Content policy rejection |
| Cross-filter comparison against a benchmark | NL2SQ error: `Unsupported function: equals` |
| Ambiguous field reference | NL2SQ error: `Missing reference` |

**Safe frames**: "Which X has the highest/lowest Y?", "Show me Y by X", "What is Y vs prior period?", "Which X are underperforming?"

**Naming rule**: Do NOT prefix calc fields with "Average" — Concierge auto-prepends "Avg." producing "Avg. Average Wallet Share". Use plain nouns: `"Wallet Share"`, not `"Average Wallet Share"`.

### 10. Post-build step — enable Analytics Agent Readiness (manual)

After the script runs, coach the user:
> "Open your new semantic model in Data 360 → Settings → Analytics Agent Readiness → toggle ON. This activates the Agentforce / Concierge panel on all metric and dashboard pages."

### 11. Business Preferences — the "system prompt" for Concierge

| Layer | Purpose | Example |
|---|---|---|
| Field description | What the data IS (objective) | "Total dollar value of commercial loans originated in the given month." |
| Business preference | How this bank USES it (contextual) | "When users ask about 'top performers', sort by Origination Volume descending." |

Rules: each preference starts with `#`, max 300 chars, max 50 preferences per model. Less = faster Concierge. Full template and API code in the Implementation Reference section below.

---

## STEP 1 — AUTHENTICATE TO SALESFORCE + DATA CLOUD

**This is always the first step.** Tell the user:

> "First, let me check if we can connect to your Salesforce org."

Then follow this flow:

---

### 1a — Check for credentials file

Use the Read tool to check for credentials in this order:
1. `next_orgs.json` in the project folder
2. `next_config.json` in the project folder

**If neither file exists** — go to Step 1c (collect credentials from scratch).

**If `next_orgs.json` exists**, read it. Structure:
```json
{
  "orgs": {
    "Friendly Name A": { ...credentials... },
    "Friendly Name B": { ...credentials... }
  }
}
```
- **1 org**: use it automatically.
- **2+ orgs**: present a numbered list and ask the user to choose. Wait for reply before continuing.

Store the selected config as `CONFIG` and `ORG_NAME`.

**If only `next_config.json` exists** — use it as-is. Set `ORG_NAME = None`.

---

### 1b — Verify authentication

Once you have a config, run this inline Python to test it:

```python
import json, requests
from pathlib import Path

cfg = json.loads(Path("next_config.json").read_text())  # or next_orgs.json equivalent

# Step 1: SF token
r = requests.post(f"{cfg['sf_login_url']}/services/oauth2/token", data={
    "grant_type": "refresh_token",
    "client_id": cfg["client_id"],
    "client_secret": cfg["client_secret"],
    "refresh_token": cfg["refresh_token"],
})
if not r.ok:
    print(f"SF_AUTH_FAILED: {r.status_code} {r.text[:200]}")
else:
    sf_token    = r.json()["access_token"]
    sf_instance = r.json()["instance_url"]
    # Step 2: Data Cloud token
    r2 = requests.post(f"{sf_instance}/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "urn:salesforce:grant-type:external:cdp",
              "subject_token": sf_token,
              "subject_token_type": "urn:ietf:params:oauth:token-type:access_token"})
    if not r2.ok:
        print(f"DC_AUTH_FAILED: {r2.status_code} {r2.text[:200]}")
    else:
        print(f"AUTH_OK: {sf_instance}")
```

**If auth succeeds** — tell the user:

> "Connected to [sf_instance]."

Then immediately ask:

> "How would you like to build this demo?
>
> 1. **Build from scratch** — I'll generate synthetic data, load it into Data Cloud, and build a complete workspace, semantic model, and dashboard automatically.
> 2. **Use your existing data** — I'll explore what's already in your org, show you your existing semantic models and data, and help you build new metrics, visualizations, and dashboards on top of it.
>
> Reply with 1 or 2."

Wait for the user's reply before proceeding.
- If **1**: continue to STEP 2 (gather demo requirements) as normal.
- If **2**: continue to STEP 2-DISCOVER (org discovery flow — defined below).

**If auth fails** — tell the user the credentials are stale or incorrect and go to Step 1c to collect fresh ones.

---

### 1c — Collect credentials (only if no file exists or auth failed)

> "Before I build your demo, I need your Salesforce and Data Cloud connection details. You'll only need to enter these once."

Ask for:
- A friendly name for this org (e.g., "Demo Shared Org", "First Meridian Sandbox")
- Salesforce login URL (default: `https://login.salesforce.com`)
- Connected App client ID (consumer key)
- Connected App client secret (consumer secret)
- Refresh token (from OAuth authorization — run `next_auth.py` if needed)
- Data Cloud domain (the `*.c360a.salesforce.com` domain from Data Cloud Setup)
- Data Cloud ingestion connector name (short name, e.g. `tableau_next_demo`)

Connected App must have scopes: `cdp_ingest_api`, `cdp_query_api`, `full` or `api`, `sfap_api`.

Save as `next_orgs.json`:
```json
{
  "orgs": {
    "{Friendly Name}": {
      "sf_login_url": "https://login.salesforce.com",
      "client_id": "<consumer key>",
      "client_secret": "<consumer secret>",
      "refresh_token": "<OAuth refresh token>",
      "data_cloud_domain": "<your-dc-domain (no https://)>",
      "ingestion_connector_name": "tableau_next_demo",
      "connector_sf_id": ""
    }
  }
}
```

Do not proceed until auth succeeds.

**Then gather demo requirements.** Parse first, ask second.

---

## STEP 2-DISCOVER — ORG DISCOVERY MODE (only if user chose option 2)

### 2d-a — List existing semantic models

Run this to fetch all semantic models in the org:

```python
import json, requests, warnings
warnings.filterwarnings('ignore')
from pathlib import Path

cfg = json.loads(Path('next_config.json').read_text())
r = requests.post(f"{cfg['sf_login_url']}/services/oauth2/token", data={
    'grant_type': 'refresh_token', 'client_id': cfg['client_id'],
    'client_secret': cfg['client_secret'], 'refresh_token': cfg['refresh_token'],
})
sf_token    = r.json()['access_token']
sf_instance = r.json()['instance_url']
SF_HDRS = {'Authorization': f'Bearer {sf_token}', 'Content-Type': 'application/json'}
BASE_SEM = f'{sf_instance}/services/data/v65.0'

r2 = requests.get(f'{BASE_SEM}/ssot/semantic/models', headers=SF_HDRS, params={'limit': 50})
models = r2.json().get('semanticModels', r2.json().get('records', []))
for i, m in enumerate(models, 1):
    print(f"{i}. {m.get('label', m.get('name', ''))}  [{m.get('apiName', '')}]  — {m.get('description', '(no description)')[:80]}")
```

Present the results as a numbered list to the user:

> "Here are the semantic models in your org:
>
> 1. **Gabe's Bank — Deposits** [gabes_bank_deposits] — Demo semantic model for...
> 2. **Gabe Sales Data Sample** [Gabe_Sales_Data_Sample] — ...
>
> Which one would you like to work with? Reply with the number."

Wait for the user's selection before proceeding.

---

### 2d-b — Inspect the selected model

Once the user picks a model, fetch its full contents:

```python
model_api_name = "<selected model apiName>"

r = requests.get(f'{BASE_SEM}/ssot/semantic/models/{model_api_name}',
                 headers=SF_HDRS, params={'includeModelContent': True})
m = r.json()

print('=== DATA OBJECTS ===')
for sdo in m.get('semanticDataObjects', []):
    print(f"  {sdo['label']} ({sdo['apiName']})")
    print(f"    Dimensions:  {[f['label'] for f in sdo.get('semanticDimensions', [])]}")
    print(f"    Measures:    {[f['label'] for f in sdo.get('semanticMeasurements', [])]}")

print('\n=== CALCULATED FIELDS ===')
for c in m.get('semanticCalculatedMeasurements', []):
    print(f"  [Measure] {c['label']} — {c.get('description','')[:80]}")
for c in m.get('semanticCalculatedDimensions', []):
    print(f"  [Dimension] {c['label']} — {c.get('description','')[:80]}")

print('\n=== METRICS ===')
r2 = requests.get(f'{BASE_SEM}/ssot/semantic/models/{model_api_name}/metrics', headers=SF_HDRS)
for met in r2.json().get('metrics', []):
    print(f"  {met['label']} ({met['apiName']})  type={met.get('aggregationType','')}  grains={met.get('timeGrains','')}")
```

Present a clean summary to the user:

> "Here's what's in **[Model Label]**:
>
> **Data objects:** [list]
> **Calculated fields:** [list]
> **Metrics:** [list]
>
> What would you like to do?
>
> 1. Add a new calculated field
> 2. Add a new metric
> 3. Create new visualizations
> 4. Build a new dashboard
> 5. Do multiple of the above
>
> Reply with one or more numbers."

Wait for the user's reply before proceeding.

---

### 2d-c — Execute the user's choice

**If they want new calculated fields or metrics** — ask what business question they want to answer, then design and POST the field/metric using the patterns in the Implementation Reference (Steps D, E, F). Use the existing model's `model_api_name`, `sdo_api_names`, and `field_api` lookup — GET the model first to populate these.

**If they want new visualizations** — ask which metrics or fields to visualize, design the viz, and POST using Step M patterns. Link to the existing workspace.

**If they want a new dashboard** — ask which metrics and vizzes to include, then build and POST using Step N patterns.

**Always fetch the current model state before making any additions** — never assume field apiNames from memory. Always GET the model and rebuild the `field_api` lookup before referencing any field.

**Parse first**: Extract everything you can from what the user already said. Only ask for what's still missing. If the user's opening message contains bank name + persona + story, skip straight to STEP 2 and present the plan — do not ask for confirmation of things you already know.

**Minimum to proceed to plan** (everything else has a sensible default):
- Bank or company name
- Target persona (e.g., Commercial Banking RM, Wealth Advisor, Branch Manager)
- Story / narrative (what is declining, growing, or at risk)

**Defaults if not provided** (state these in the plan, the user can change them):
- Metrics: derive 4–6 from the persona + story
- Dimensions: Region, Segment, Product Type
- Signal onset: 6 months ago, 30% severity, declining

**If something is truly ambiguous**, ask one focused question — not a list.

---

## STEP 2 — CLASSIFY METRICS + DESIGN THE DATA MODEL (internal — feeds Step 3)

### Metric classification

| Type | Signal words | Data pattern | Aggregation | Concierge caveat |
|---|---|---|---|---|
| **Flow** | volume, count, originations, revenue, applications | 1 row per entity per period; value = event | `Sum` | None |
| **Rate / Average** | rate, ratio, score, %, yield, NPS | 1 row per entity per period; value = pre-computed ratio | `Average` | SUM would be wrong |
| **Snapped** | balance, AUM, outstanding, pipeline, headcount, active X | 1 row per entity per period; value = state at month-end | `Sum` (on latest row only) | ⚠️ Summing 12 months = 12× actual value |

**Snapped trap**: The data looks like flow (one row per month) but represents a *state*. The correct answer is always the most recent month's value.

**Handling snapped metrics in the SDM:**
- Option A: submetric filtered to `CurrentMonth` / `PreviousMonth`
- Option B (preferred — date-shift safe): LOD expression
  ```
  if [Adjusted_Date_clc] = { EXCLUDE :max([Adjusted_Date_clc])} then [fact_sdo].[balance_field] end
  ```
  This returns the balance only on the most-recent-date row; `Sum` then returns just that value.

### Multi-table data model

Always use 2–3 related tables:

| Table | Role | Grain | Typical metrics |
|---|---|---|---|
| `Fact_[Activity]` | Core fact | 1 row per entity per month | Volume, revenue, count |
| `Dim_Client` | Client/account dimension | 1 row per client | Segment, tier, tenure |
| `Dim_Product` | Product dimension | 1 row per product | Category, rate, term |

**Add `Dim_Date` when there are 2+ fact tables** (shared time spine):
```python
dates = pd.date_range(START_DATE, END_DATE, freq="MS")
dim_date = pd.DataFrame({
    "date":       [d.date() for d in dates],
    "month_key":  [int(d.strftime("%Y%m")) for d in dates],
    "year":       [d.year for d in dates],
    "quarter":    [((d.month - 1) // 3) + 1 for d in dates],
    "month_name": [d.strftime("%B") for d in dates],
})
```
Without `Dim_Date`, Concierge cannot compare metrics from different fact tables across the same time period.

**Signal design (same ramp as Pulse):**
```python
def signal_ramp(d, onset=SIGNAL_ONSET, duration=6):
    mft = (d.year - TODAY.year) * 12 + (d.month - TODAY.month)
    if mft <= onset: return 0.0
    return min(1.0, (mft - onset) / duration)
```

---

## STEP 3 — PRESENT THE PLAN & GET ONE CONFIRMATION

Present a complete build plan. This is the **only confirmation checkpoint** before writing and running code.

Format:

> **Here's what I'll build for [Bank Name]:**
>
> **Persona:** [persona]
> **Story:** [narrative]
> **Signal:** Decline starts [N] months ago, ramps to full effect today
>
> **Metrics:**
>
> | Metric | Type | SDM Aggregation | Concierge note |
> |---|---|---|---|
> | Loan Origination Volume | Flow | Sum | YTD or any period |
> | Approval Rate | Rate | Average | Use "current" language |
> | Portfolio Balance | Snapped | Sum (latest month) | Ask "current balance" |
>
> **Data Model:**
>
> | Table | Grain | Key Fields |
> |---|---|---|
> | Fact_[X] | monthly per [entity] | … |
> | Dim_Client | per client | … |
>
> **Sample Concierge questions:**
> - "Which region has the lowest origination volume this quarter?"
> - "Show me my top clients by portfolio balance."
>
> **Files:**
> - `{bank_slug}_{use_case_slug}_next_demo.py`
> - `{bank_slug}_{use_case_slug}_demo_guide.md`
>
> Reply **go** to build, or tell me what to change.

**Do not write any code until the user replies "go" (or equivalent).**

---

## STEP 4 — WRITE THE PYTHON SCRIPT

Name: `{bank_slug}_{use_case_slug}_next_demo.py`

### Complete script skeleton — always use this structure:

```python
#!/usr/bin/env python3
import json, sys, uuid, os, requests, subprocess, tempfile
import pandas as pd
import numpy as np
import time as _time
from datetime import date, datetime as _dt
from pathlib import Path

# ── Demo parameters ──────────────────────────────────────────────────────────
BANK_NAME     = "{Bank Name}"
USE_CASE      = "{Use Case}"
PERSONA       = "{Persona}"
STORY         = "{Story}"
SIGNAL_ONSET  = -6

# Derived names
bank_slug      = BANK_NAME.lower().replace(" ", "_").replace(".", "")
for s in ("_bank", "_financial", "_corp", "_inc", "_group"):
    bank_slug = bank_slug.removesuffix(s)
use_case_slug  = USE_CASE.lower().replace(" ", "_").replace("/", "_")
WORKSPACE_NAME = f"{bank_slug}_{use_case_slug}"
SDM_NAME       = WORKSPACE_NAME
SCRIPT_NAME    = f"{bank_slug}_{use_case_slug}_next_demo.py"
DEMO_GUIDE     = f"{bank_slug}_{use_case_slug}_demo_guide.md"
TODAY          = date.today()
START_DATE     = date(TODAY.year - 2, TODAY.month, 1)

CONCIERGE_QUESTIONS = []   # populate with 6–10 demo questions when writing Phase 8 code; printed at end of run + used in demo guide
METRICS_META        = []   # populate alongside metric definitions: {"name": ..., "type": ..., "concierge_note": ...}
VIZ_META            = []   # populate alongside viz definitions: {"label": ..., "type": ..., "talking_points": [...]}

# ── Diagnostics ───────────────────────────────────────────────────────────────
_SCRIPT_START = _time.time()
_PHASE_TIMES  = {}

def _ts(): return _dt.now().strftime("%H:%M:%S")
def ok(m):   print(f"  [{_ts()}] ✅ {m}")
def info(m): print(f"  [{_ts()}] ℹ️  {m}")
def die(m, r=None):
    print(f"\n  ❌ FAILED: {m}")
    if r is not None: print(f"  HTTP {r.status_code}: {r.text[:400]}")
    sys.exit(1)

def phase(n, label):
    _PHASE_TIMES[str(n)] = (_time.time(), label)
    print(f"\n[{n}/11] {label}...")

def mac_notify(title, message):
    try:
        script = f'display notification "{message}" with title "{title}" sound name "Glass"'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".applescript", delete=False) as f:
            f.write(script); fpath = f.name
        subprocess.run(["osascript", fpath], check=False, capture_output=True)
        os.unlink(fpath)
    except Exception:
        pass

# ── Auth ──────────────────────────────────────────────────────────────────────
ORG_NAME = "{Friendly Org Name}"   # from next_orgs.json; set to None to use first org
CONFIG   = load_config(ORG_NAME)
sf_token, sf_instance, dc_token, dc_domain = get_tokens(CONFIG)
SF_HDRS  = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
DC_HDRS  = {"Authorization": f"Bearer {dc_token}", "Content-Type": "application/json"}
BASE_SF  = f"{sf_instance}/services/data/v62.0"
BASE_SEM = f"{sf_instance}/services/data/v65.0"
BASE_VIZ = f"{sf_instance}/services/data/v66.0"

# ── Deployment plan ────────────────────────────────────────────────────────────
print(f"\n{'='*66}")
print(f"  DEPLOYMENT PLAN — {BANK_NAME} — {USE_CASE}")
print(f"  {'─'*62}")
print(f"  Phase 1   Generate synthetic data          ~5s")
print(f"  Phase 2   Register DC schema + streams     ~15s")
print(f"  Phase 3   Wait for DLO ACTIVE              ~30–120s")
print(f"  Phase 4   Submit bulk ingest jobs          ~30s")
print(f"  Phase 5   Wait for data to process         ~5–10 min")
print(f"  Phase 6   Create workspace                 ~5s")
print(f"  Phase 7   Build Semantic Data Model        ~30s")
print(f"  Phase 8   Calculated fields + metrics      ~30s")
print(f"  Phase 9   Create visualizations            ~20s")
print(f"  Phase 10  Build dashboard                  ~10s")
print(f"  Phase 11  Validate + write demo guide      ~10s")
print(f"  {'─'*62}")
print(f"  Total estimate: 8–15 minutes")
print(f"  TIP: Minimize this terminal and do other work.")
print(f"       A Mac notification will fire when the demo is ready.")
print(f"{'='*66}\n")

# ── PHASE 1: Generate synthetic data ──────────────────────────────────────────
phase(1, "Generating synthetic data")
# ... build DataFrames for each table

# ── PHASE 2: Register DC schema + create streams ──────────────────────────────
phase(2, "Registering Data Cloud schema + streams")
# See Implementation Reference — STEP 5 for full schema + stream code

# ── PHASE 3: Wait for DLO ACTIVE ──────────────────────────────────────────────
phase(3, "Waiting for DLO ACTIVE")
# See Implementation Reference — _dlo_active()

# ── PHASE 4: Submit bulk ingest jobs (all tables, then poll) ──────────────────
phase(4, "Submitting bulk ingest jobs")
# See Implementation Reference — bulk_ingest_submit()

# ── PHASE 5: Wait for Data Cloud to process ───────────────────────────────────
phase(5, "Waiting for Data Cloud to process (5–10 min — normal)")
# See Implementation Reference — wait_for_bulk_job()

# ── PHASE 6: Create workspace ─────────────────────────────────────────────────
phase(6, "Creating workspace")
r = requests.get(f"{BASE_SEM}/tableau/workspaces", headers=SF_HDRS)
existing = {w["name"]: w["id"] for w in r.json().get("workspaces", [])}
if WORKSPACE_NAME in existing:
    requests.delete(f"{BASE_SEM}/tableau/workspaces/{WORKSPACE_NAME}", headers=SF_HDRS)
r = requests.post(f"{BASE_SEM}/tableau/workspaces", headers=SF_HDRS,
                  json={"label": WORKSPACE_NAME, "description": f"Demo workspace for {BANK_NAME} {USE_CASE}."})
r.raise_for_status()
workspace_name = r.json()["name"]   # capture slug — don't assume it equals WORKSPACE_NAME
workspace_id   = r.json()["id"]
ok(f"Workspace created: {workspace_name}")

# ── PHASE 7: Build Semantic Data Model ────────────────────────────────────────
phase(7, "Building Semantic Data Model")
# See Implementation Reference — STEP 7, Steps A–H

# ── PHASE 8: Calculated fields + metrics ──────────────────────────────────────
phase(8, "Adding calculated fields + metrics")
# See Implementation Reference — Steps D, E, F, G, H

# ── PHASE 9: Create visualizations ────────────────────────────────────────────
phase(9, "Creating visualizations")
# See Implementation Reference — STEP M

# ── PHASE 10: Create dashboard ────────────────────────────────────────────────
phase(10, "Building dashboard")
# See Implementation Reference — STEP N

# ── PHASE 11: Validate SDM + write demo guide ─────────────────────────────────
phase(11, "Validating SDM + writing demo guide")
# SDM validation: Implementation Reference → STEP 7, Step H (GET /validate)
# Demo guide generation: Implementation Reference → STEP 8 (build_demo_guide function)

# ── Done ──────────────────────────────────────────────────────────────────────
_total = int(_time.time() - _SCRIPT_START)
print(f"\n{'='*66}")
print(f"  ✅ DEMO BUILD COMPLETE — {BANK_NAME} — {USE_CASE}")
print(f"  Open: {sf_instance}/tableau/workspace/{workspace_name}")
print(f"  Guide: {DEMO_GUIDE}")
print(f"  Total: {_total//60}m {_total%60}s")
print(f"{'='*66}\n")
print("Concierge questions:")
for q in CONCIERGE_QUESTIONS:
    print(f'  • "{q}"')
print(f"\nTo tear down: python3 next_teardown.py  (workspace: {WORKSPACE_NAME})")

mac_notify("Tableau Demo Builder", f"{BANK_NAME} \u2014 {USE_CASE} demo is ready!")

# Write to demo registry (used by next_teardown.py)
_reg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "next_demos.json")
try:
    registry = json.loads(Path(_reg).read_text()) if Path(_reg).exists() else []
    registry = [d for d in registry if d.get("workspace_name") != WORKSPACE_NAME]
    registry.append({"label": f"{BANK_NAME} \u2014 {USE_CASE}", "workspace_name": WORKSPACE_NAME,
                     "dc_prefix": bank_slug, "built_on": date.today().isoformat(), "script": SCRIPT_NAME})
    Path(_reg).write_text(json.dumps(registry, indent=2))
except Exception:
    pass
```

### Data generation defaults

- History: 24 months (START_DATE = date(TODAY.year - 2, TODAY.month, 1))
- Fact table grain: one row per entity (advisor, client, loan officer) per month
- Dimension tables: static (no date column)
- Always include in fact table: `Date` (date), `Month Key` (int YYYYMM), `Year` (int), `Quarter` (int 1–4), `Month` (string)
- Submit ALL bulk jobs before waiting for any — saves 30–60s per extra table

**Bulk API overview**: 3 steps per table: POST job → PUT CSV batches → PATCH to close. See Implementation Reference for `bulk_ingest_submit()` and `wait_for_bulk_job()` functions.

---

## STEP 5 — SCHEMA REGISTRATION + STREAM CREATION

Full code in the Implementation Reference section below (STEP 5).

Pattern: look up connector SF ID from config → PUT schema (merge with existing; strip read-only fields) → POST one stream per schema object (only PK field in `dataLakeFieldInputRepresentations`) → poll `_dlo_active()` per stream before ingesting.

---

## STEP 6 — RUN THE SCRIPT

After writing the script, run it immediately:
```bash
/opt/homebrew/bin/python3.13 <script_name>.py
```

Report each phase as it completes. If an error occurs, diagnose it, fix the script, and re-run.

---

## STEP 7 — CREATE TABLEAU SEMANTIC MODEL

Full code in the Implementation Reference section below (STEP 7, Steps A–H and optional I–N).

**8-step core flow:**
1. DELETE existing model if found (idempotent)
2. POST model with `agentEnabled: True`, `dataObjectType: "Dlo"`, `app: workspace_name`
3. GET model to discover auto-generated field apiNames (like `Loan_Amount1`, `Date3`)
4. POST calculated measurements (use `"Currency"`/`"Percentage"` here — accepted ✅)
5. POST calculated date dimension (use date-shift formula)
6. POST semantic metrics (MUST use `calculatedFieldApiName` — `tableFieldReference` is silently ignored)
7. POST relationship (`joinType: "Auto"`)
8. Validate — GET `/validate`

Then POST SDM id to workspace `/assets` to link it.

---

## STEP 8 — GENERATE DEMO GUIDE

Full Python code in the Implementation Reference section below (STEP 8).

Always auto-generate from BANK_NAME, PERSONA, STORY, metric list, visualization list, and CONCIERGE_QUESTIONS. Do not use placeholder text. Print Concierge questions at end of script run — they are the SE's demo script.

---

## COMMON PITFALLS — TOP 10

1. **PATCH on main model URL is a FULL REPLACE** — always use sub-resource POST endpoints for sub-entities
2. **Semantic Metrics MUST use `calculatedFieldApiName`** — `tableFieldReference` is silently ignored
3. **SDO `semanticMeasurements` must use `dataType: "Number"` for IngestAPI DLOs** — `"Currency"` rejected
4. **PUT schema is a FULL REPLACE** — GET first, strip read-only fields (`availabilityStatus` etc.), merge, then PUT
5. **Dashboard `widgets` is a dict, not a list** — array causes 500 error
6. **Dashboard page `name` must be UUID** — plain strings cause blank canvas
7. **Dashboard layout `style` must include `cellSpacingX/Y`** — `{}` causes blank canvas
8. **All dims in `insightsSettings` must also be in `additionalDimensions`** — missing causes 400
9. **`agentEnabled: True` is not enough for Concierge** — user must enable Analytics Agent Readiness in UI
10. **`style.headers` must be omitted entirely** — even `{}` causes `JSON_PARSER_ERROR` at v66.0 (see pitfall #32)

Full list of 57 pitfalls in the Implementation Reference section below.

---

---

# IMPLEMENTATION REFERENCE

*Confirmed working code. Use this section when writing any API code.*

---

## MODEL CLONE MODE — APPLYING RETRIEVED METRICS IN PHASE 8

When `SFDX_MODEL` is loaded, use this pattern to apply retrieved metric settings instead of hardcoding:

```python
# Clone insightsSettings from retrieved metric (remapping field refs to demo apiNames)
def clone_insights_settings(src_metric, identifying_field_ref, dims_refs):
    """
    src_metric: one item from SFDX_MODEL["metrics"]
    identifying_field_ref: demo dim_ref() for the identifying dimension
    dims_refs: list of demo dim_ref() for additional dimensions
    """
    src = src_metric.get("insightsSettings", {})
    return {
        "identifyingDimension": {"identifierDimensionReference": identifying_field_ref},
        "insightTypes": src.get("insightTypes", []),  # clone enabled/disabled flags exactly
        "insightsDimensionsReferences": dims_refs,
        "singularNoun": src.get("singularNoun", "dollar"),
        "pluralNoun":   src.get("pluralNoun", "dollars"),
        "sentiment":    src.get("sentiment", "SentimentTypeUpIsGood"),
    }

# Clone metric shell from retrieved metric
def clone_metric(src_metric, calc_measurement_api_name, date_calc_api_name, additional_dims, insights_settings):
    """Build a metric payload using retrieved structure."""
    return {
        "apiName":     src_metric["apiName"].replace("_mtc", "_mtc"),  # keep suffix convention
        "label":       src_metric["label"],
        "description": src_metric.get("description", ""),
        "measurementReference":   {"calculatedFieldApiName": calc_measurement_api_name},
        "timeDimensionReference": {"calculatedFieldApiName": date_calc_api_name},
        "aggregationType":  src_metric.get("aggregationType", "Sum"),
        "isCumulative":     src_metric.get("isCumulative", False),
        "timeGrains":       src_metric.get("timeGrains", ["Month", "Quarter", "Year"]),
        "filters":          src_metric.get("filters", []),
        "filterLogic":      src_metric.get("filterLogic", ""),
        "additionalDimensions": additional_dims,
        "insightsSettings": insights_settings,
    }

# Apply business preferences from retrieved model
def apply_business_preferences(model_api_name, sfdx_model, sf_hdrs, base_sem):
    prefs = sfdx_model["model"].get("businessPreferences", "")
    if not prefs:
        return
    resp = requests.patch(
        f"{base_sem}/ssot/semantic/models/{model_api_name}",
        headers=sf_hdrs,
        json={"businessPreferences": prefs},
    )
    if resp.ok:
        ok("Business preferences cloned from retrieved model")
    else:
        info(f"Business preferences (non-fatal): {resp.status_code} {resp.text[:300]}")
```

---

## CONCIERGE OPTIMIZATION — FULL CODE DETAIL

### Field Descriptions — examples

**Good field description** (put this quality of description on EVERY field):
> `Total dollar value of commercial loans originated by this loan officer in the given month. Use to track origination volume trends and compare performance across regions and segments.`

**Good metric description** (`description` in metric payload):
> `Tracks total dollar value of commercial loans originated each month. Rising values indicate healthy pipeline activity. Declining values suggest reduced client engagement or tighter credit conditions.`

**Good SDO description** (`semanticDataObjects[].description`):
> `Monthly loan origination activity. One row per loan officer per month. Use to analyze origination volume, approval rates, and pipeline trends by region, segment, and product type.`

### Insight Type Selection by Metric Type

| Insight type | Flow | Rate | Snapped | Notes |
|---|---|---|---|---|
| `CurrentTrend` | ✅ | ✅ | ✅ | Always include |
| `TrendChangeAlert` | ✅ | ✅ | ✅ | Critical for signal demos |
| `ComparisonToExpectedRangeAlert` | ✅ | ✅ | ✅ | Always include |
| `TopContributors` | ✅ | ✅ | ✅ | Always include |
| `BottomContributors` | ✅ | ✅ | — | |
| `TopDrivers` | ✅ | ✅ | — | |
| `TopDetractors` | ✅ | ✅ | — | |
| `ConcentratedContributionAlert` | ✅ | — | — | |
| `RecordLevelTable` | — | — | ✅ | |
| `OutlierDetection` | ✅ | ✅ | — | |

Minimum set that always works: `CurrentTrend`, `TrendChangeAlert`, `ComparisonToExpectedRangeAlert`, `TopContributors`.

### Business Preferences Template (set in UI after script runs)

```
# When users ask about 'pipeline', they mean the Portfolio Balance metric, which is a point-in-time balance as of month-end

# When asked about 'top performers' or 'best officers', rank by Origination Volume descending for the most recent quarter

# RM is short for Relationship Manager. Loan officers and RMs refer to the same role

# When discussing approval rates, a rate below 65% indicates underperformance for {Bank Name}

# When a user asks about 'declining' metrics without specifying a time period, compare the most recent 3 months to the prior 3 months

# {Bank Name} uses 'segment' to refer to client industry verticals: Commercial, Middle Market, and Corporate

# When asked about deal size or loan size, refer to the Average Deal Size metric, not the total origination volume

# When users say 'this quarter', they mean the current calendar quarter, not the fiscal quarter
```

**UI path**: Data 360 → Semantic Model → [model] → Settings → Business Preferences → add each preference as a new `#`-prefixed line.

**API path — CONFIRMED WORKING (tested 2026-03-13):**
```python
# Call after SDM validation and workspace link (end of Phase 8 / Step H)
# Preferences are joined with double newline — each starts with "#"
BUSINESS_PREFERENCES = "\n\n".join([
    "# <preference one>",
    "# <preference two>",
    # ...up to 50; each max 300 chars
])
resp = requests.patch(
    f"{BASE_SEM}/ssot/semantic/models/{model_api_name}",
    headers=SF_HDRS,
    json={"businessPreferences": BUSINESS_PREFERENCES},
)
if resp.ok:
    ok("Business preferences applied to SDM")
else:
    info(f"Business preferences (non-fatal): {resp.status_code} {resp.text[:300]}")
```

**This is now a standard automated step in all demo scripts — do NOT list it as a manual step in the demo guide.**

### Calc Measurement Naming Rule

Do NOT prefix fields with "Average" — Concierge auto-prepends "Avg." in axis labels, producing "Avg. Average Wallet Share". Name fields as plain nouns: `"Wallet Share"` not `"Average Wallet Share"`, `"Products per Client"` not `"Average Products per Client"`.

---

## STEP 5 — FULL CODE: Schema Registration + Stream Creation

### 5a — Look up connector SF ID

```python
CONN_NAME = CONFIG["ingestion_connector_name"]   # e.g. "tableau_next_demo"

if "connector_sf_id" not in CONFIG:
    r = requests.get(f"{BASE_SF}/ssot/connections", headers=SF_HDRS,
                     params={"connectorType": "IngestApi", "limit": 50})
    r.raise_for_status()
    for conn in r.json().get("connections", []):
        if conn["name"].startswith(CONN_NAME):
            CONFIG["connector_sf_id"]    = conn["id"]
            CONFIG["connector_uuid_name"] = conn["name"]
            break
    with open(CONFIG_FILE, "w") as f:
        json.dump(CONFIG, f, indent=2)

CONN_SF_ID = CONFIG["connector_sf_id"]
CONN_UUID  = CONFIG["connector_uuid_name"]
```

### 5b — Register schema (PUT replaces ALL schemas — always include existing + new)

**IMPORTANT**: The schema PUT endpoint (`/ssot/connections/{id}/schema`) only accepts `name`, `label`, and `dataType` per field. Do NOT include `isPrimaryKey` or `isEventTime` — these cause `JSON_PARSER_ERROR`. Declare the primary key only in the stream's `dataLakeFieldInputRepresentations` (Step 5c).

```python
# Get current schema first
r = requests.get(f"{BASE_SF}/ssot/connections/{CONN_SF_ID}/schema", headers=SF_HDRS)
r.raise_for_status()
existing_schemas = r.json().get("schemas", [])

# Strip read-only fields before merging (keep only: name, label, schemaType, fields)
# NOTE: only name, label, dataType are accepted per field — isPrimaryKey/isEventTime cause JSON_PARSER_ERROR
def clean_schema(s):
    clean = {k: s[k] for k in ("name", "label", "schemaType") if k in s}
    clean["fields"] = [
        {k: f[k] for k in ("name", "label", "dataType") if k in f}
        for f in s.get("fields", [])
    ]
    return clean

cleaned_existing = [clean_schema(s) for s in existing_schemas]

# Build new schema objects. Object names must use underscores.
# Only name, label, dataType per field — isPrimaryKey/isEventTime belong in stream creation (Step 5c), NOT here.
new_schemas = [
    {
        "name": "Demo_Fact_Originations",
        "label": "Demo_Fact_Originations",
        "schemaType": "IngestApi",
        "fields": [
            {"name": "record_id",   "label": "record_id",   "dataType": "Text"},
            {"name": "close_date",  "label": "close_date",  "dataType": "Date"},
            {"name": "loan_amount", "label": "loan_amount", "dataType": "Number"},
            {"name": "segment",     "label": "segment",     "dataType": "Text"},
        ]
    },
    # ... one entry per table in the data model
]

merged = {s["name"]: s for s in cleaned_existing}
for s in new_schemas:
    merged[s["name"]] = s

r = requests.put(f"{BASE_SF}/ssot/connections/{CONN_SF_ID}/schema",
                 headers=SF_HDRS, json={"schemas": list(merged.values())})
r.raise_for_status()
print(f"  ✅ Schema registered: {[s['name'] for s in new_schemas]}")
```

### 5c — Create one data stream per schema object

```python
DATASOURCE_SHORT = CONN_NAME   # short name (no UUID suffix) — e.g. "tableau_next_demo"

created_streams = {}  # obj_name → full stream name

for schema in new_schemas:
    obj_name    = schema["name"]
    stream_name = f"demo_{obj_name.lower()}"[:10]

    # Only PK field in dataLakeFieldInputRepresentations — platform auto-populates the rest
    pk_field = next(f for f in schema["fields"] if f.get("isPrimaryKey"))

    payload = {
        "name":           stream_name,
        "label":          stream_name.replace("_", " ").title(),
        "datasource":     DATASOURCE_SHORT,
        "datastreamType": "INGESTAPI",
        "connectorInfo": {
            "connectorType":    "IngestApi",
            "connectorDetails": {
                "name":   CONN_UUID,
                "events": [obj_name]
            }
        },
        "dataLakeObjectInfo": {
            "label":    stream_name.replace("_", " ").title(),
            "category": "Other",
            "dataspaceInfo": [{"name": "default"}],
            "dataLakeFieldInputRepresentations": [
                {"name": pk_field["name"], "label": pk_field["name"],
                 "dataType": pk_field["dataType"], "isPrimaryKey": True}
            ],
            "eventDateTimeFieldName": "",
            "recordModifiedFieldName": ""
        },
        "mappings": []
    }

    r = requests.post(f"{BASE_SF}/ssot/data-streams", headers=SF_HDRS, json=payload)
    if r.status_code in (200, 201):
        full_name = r.json().get("name", "unknown")
        created_streams[obj_name] = full_name
        print(f"  ✅ Stream created: {full_name}")
    elif "already in use" in r.text.lower():
        print(f"  ℹ️  Stream already exists for {obj_name} — discovering name")
        r2 = requests.get(f"{BASE_SF}/ssot/data-streams",
                          headers=SF_HDRS, params={"connectorId": CONN_SF_ID, "limit": 100})
        for ds in r2.json().get("dataStreams", []):
            if obj_name in ds.get("name", ""):
                created_streams[obj_name] = ds["name"]
                break
    else:
        print(f"  ⚠️  Stream creation failed for {obj_name}: {r.text[:200]}")
```

### 5d — DLO ACTIVE gate (always poll before ingesting)

```python
import time as _time

def _dlo_active(stream_name, sf_instance, sf_hdrs, timeout=300, interval=10):
    """Poll until the DLO linked to this stream reaches ACTIVE status. Returns DLO API name."""
    deadline = _time.time() + timeout
    start    = _time.time()
    while _time.time() < deadline:
        r = requests.get(f"{sf_instance}/services/data/v62.0/ssot/data-streams/{stream_name}",
                         headers=sf_hdrs)
        if r.ok:
            dlo_info = r.json().get("dataLakeObjectInfo", {})
            status   = dlo_info.get("status", "")
            dlo_name = dlo_info.get("name", "")
            if status.upper() == "ACTIVE" and dlo_name:
                elapsed = int(_time.time() - start)
                print(f"  ✅ DLO ACTIVE: {dlo_name}  ({elapsed}s)")
                return dlo_name
        elapsed = int(_time.time() - start)
        print(f"\r  ⏳ DLO ACTIVE: {stream_name}  ({elapsed}s)    ", end="", flush=True)
        _time.sleep(interval)
    print()
    raise RuntimeError(f"Timeout waiting for DLO ACTIVE: {stream_name}")

# Wait for each stream's DLO to be ACTIVE before ingesting
FACT_DLO = _dlo_active(created_streams[FACT_OBJ], sf_instance, SF_HDRS)
DIM_DLO  = _dlo_active(created_streams[DIM_OBJ],  sf_instance, SF_HDRS)
```

### 5e — Bulk ingest: submit all jobs first, then poll

```python
import io

def bulk_ingest_submit(df, obj_name, dc_domain, dc_token, conn_short_name):
    """Submit a bulk ingest job and return (job_id, row_count). Does NOT wait."""
    hdrs_dc  = {"Authorization": f"Bearer {dc_token}", "Content-Type": "application/json"}
    hdrs_csv = {"Authorization": f"Bearer {dc_token}", "Content-Type": "text/csv"}
    base_dc  = f"https://{dc_domain}"

    # Check for in-progress jobs
    r = requests.get(f"{base_dc}/api/v1/ingest/jobs", headers=hdrs_dc)
    if r.ok:
        for job in r.json().get("data", []):   # CONFIRMED key is "data", not "jobs"
            if job.get("object") == obj_name and job.get("state") in ("Open", "UploadComplete", "InProgress"):
                print(f"  ℹ️  Active job for {obj_name} ({job['state']}) — skipping submit")
                return job["id"], len(df)

    r = requests.post(f"{base_dc}/api/v1/ingest/jobs", headers=hdrs_dc,
                      json={"object": obj_name, "sourceName": conn_short_name, "operation": "upsert"})
    if not r.ok:
        print(f"  ⚠️  Job create failed for {obj_name}: {r.text[:200]}"); r.raise_for_status()
    job_id = r.json()["id"]

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    r = requests.put(f"{base_dc}/api/v1/ingest/jobs/{job_id}/batches",
                     headers=hdrs_csv, data=csv_buf.getvalue().encode("utf-8"))
    if not r.ok:
        print(f"  ⚠️  Batch upload failed for {obj_name}: {r.text[:200]}"); r.raise_for_status()

    r = requests.patch(f"{base_dc}/api/v1/ingest/jobs/{job_id}", headers=hdrs_dc,
                       json={"state": "UploadComplete"})
    if not r.ok:
        print(f"  ⚠️  Job close failed for {obj_name}: {r.text[:200]}"); r.raise_for_status()

    print(f"  ✅ Bulk job submitted: {obj_name}  ({len(df)} rows)  job_id={job_id}")
    return job_id, len(df)


def wait_for_bulk_job(job_id, obj_name, dc_domain, dc_token, timeout=600, interval=15):
    """Poll until job is JobComplete or Failed."""
    hdrs_dc = {"Authorization": f"Bearer {dc_token}", "Content-Type": "application/json"}
    base_dc = f"https://{dc_domain}"
    deadline = _time.time() + timeout
    start    = _time.time()
    dots     = 0
    while _time.time() < deadline:
        r = requests.get(f"{base_dc}/api/v1/ingest/jobs/{job_id}", headers=hdrs_dc)
        if r.ok:
            state = r.json().get("state", "")
            if state == "JobComplete":    # NOT "Complete"
                elapsed = int(_time.time() - start)
                print(f"\r  ✅ {obj_name} ingested  ({elapsed}s)                 ")
                return True
            if state in ("Failed", "Aborted"):
                print(f"\r  ❌ {obj_name} bulk job {state}: {r.text[:200]}")
                return False
        dots += 1
        if dots % 4 == 0:
            elapsed = int(_time.time() - start)
            print(f"\r  ⏳ Waiting for {obj_name}  ({elapsed}s elapsed)    ", end="", flush=True)
        else:
            print(".", end="", flush=True)
        _time.sleep(interval)
    elapsed = int(_time.time() - start)
    print(f"\n\n  ⚠️  Data Cloud is still processing {obj_name} after {elapsed}s.")
    print(f"  This is normal — DC async queue adds 5–10 min regardless of data size.")
    print(f"  Wait 10–15 minutes, then tell Claude 'continue' or 'try again'.")
    return False

# CONFIRMED PATTERN: submit ALL tables first, then poll. Saves 30–60s per extra table.
fact_job_id, _ = bulk_ingest_submit(df_fact, FACT_OBJ, dc_domain, dc_token, CONN_SHORT)
dim_job_id,  _ = bulk_ingest_submit(df_dim,  DIM_OBJ,  dc_domain, dc_token, CONN_SHORT)
print("  ✅ Both jobs submitted — Data Cloud processing both tables simultaneously")
wait_for_bulk_job(fact_job_id, FACT_OBJ, dc_domain, dc_token)
wait_for_bulk_job(dim_job_id,  DIM_OBJ,  dc_domain, dc_token)
```

---

## STEP 7 — FULL CODE: Semantic Data Model

### Step A — Delete existing model (idempotent)

```python
r = requests.get(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}", headers=SF_HDRS)
if r.status_code == 200:
    requests.delete(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}", headers=SF_HDRS).raise_for_status()
    print(f"  ✅ Deleted existing model: {MODEL_API_NAME}")
```

### Step B — Create model

```python
model_payload = {
    "apiName":     MODEL_API_NAME,
    "label":       f"{BANK_NAME} — {USE_CASE}",
    "description": f"Demo semantic model for {BANK_NAME} {USE_CASE}.",
    "app":         workspace_name,   # links SDM to workspace at creation time
    "categories":  [],
    "dataspace":   "default",
    "agentEnabled": True,            # REQUIRED for Concierge
    "semanticDataObjects": [
        {
            "label":          "Loan Originations",
            "description":    "Monthly loan origination activity. One row per loan officer per month.",
            "dataObjectName": FACT_DLO,
            "dataObjectType": "Dlo",
            "shouldIncludeAllFields": False,
            "semanticDimensions": [
                {
                    "dataObjectFieldName": "date__c",   # DLO fields always have __c suffix
                    "label":       "Date",
                    "description": "First day of the reporting month.",
                    "dataType":    "Date",
                    "geoRole":     None,
                    "sortOrder":   "Ascending",
                    "displayCategory": "Continuous",
                    "isVisible":   True,
                },
                # ... one per dimension/categorical field
            ],
            "semanticMeasurements": [
                {
                    "dataObjectFieldName": "loan_amount__c",
                    "label":       "Loan Amount",
                    "description": "Total dollar value of commercial loans originated in the given month.",
                    "dataType":    "Number",   # ALWAYS "Number" for IngestAPI DLOs — never "Currency" or "Percentage"
                    "decimalPlace": 2,
                    "aggregationType": "None",
                    "directionality": "Up",
                    "displayCategory": "Continuous",
                    "sortOrder":   "Ascending",
                    "isVisible":   True,
                    "shouldTreatNullsAsZeros": False,
                },
                # ... one per numeric/measure field
            ],
        },
        # ... one SDO per DLO table
    ],
    "semanticRelationships":          [],
    "semanticCalculatedMeasurements": [],
    "semanticCalculatedDimensions":   [],
    "semanticLogicalTables":          [],
    "semanticMetrics":                [],
}

resp = requests.post(f"{BASE_SEM}/ssot/semantic/models", headers=SF_HDRS, json=model_payload)
if not resp.ok:
    print(f"ERROR: {resp.text}"); sys.exit(1)
model_data     = resp.json()
model_api_name = model_data["apiName"]
model_id       = model_data["id"]
sdo_api_names  = {sdo["label"]: sdo["apiName"] for sdo in model_data["semanticDataObjects"]}
```

### Step C — GET model to discover auto-generated field apiNames (REQUIRED)

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
fact_sdo = sdo_api_names["Loan Originations"]

calc_measurements = [
    {
        "apiName":         "Total_Loan_Amount_clc",
        "label":           "Total Loan Amount",
        "description":     "Sum of commercial loan dollar value originated in a given period.",
        "expression":      f"[{fact_sdo}].[{fld(fact_sdo, 'loan_amount__c')}]",
        "aggregationType": "Sum",
        "dataType":        "Currency",   # ✅ Currency accepted for calc measurements
        "decimalPlace":    2,
        "directionality":  "Up",
        "displayCategory": "Continuous",
        "level":           "Row",
        "isVisible":       True,
        "shouldTreatNullsAsZeros": False,
        "sortOrder":       "Ascending",
        "sentiment":       "SentimentTypeUpIsGood",
    },
    # ... one per KPI
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
# For single fact table — reference fact date field:
date_sdo   = fact_sdo
date_field = fld(fact_sdo, 'date__c')

# For multiple fact tables with Dim_Date:
# date_sdo   = "Dim_Date"
# date_field = fld("Dim_Date", "date__c")

# Date-shift: always shifts data to be current relative to today
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
        "description":     (
            "Primary time dimension for all metrics. Dates are dynamically shifted so "
            "the most recent data always aligns with the current month — demo stays "
            "current without re-ingesting data."
        ),
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

**Tableau formula quick reference** (for expression strings):
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

dim_sdo         = sdo_api_names["Loan Officers"]
officer_name_ref = dim_ref(dim_sdo, "officer_name__c")

metric_dims = [
    dim_ref(fact_sdo, "region__c"),
    dim_ref(fact_sdo, "segment__c"),
    dim_ref(fact_sdo, "officer_id__c"),
    dim_ref(dim_sdo,  "officer_name__c"),   # MUST be here because it's in identifyingDimension
    dim_ref(dim_sdo,  "region__c"),
]

metrics = [
    {
        "apiName":     "total_loan_origination_volume_md",
        "label":       "Total Loan Origination Volume",
        "description": "...",
        "measurementReference":   {"calculatedFieldApiName": "Total_Loan_Amount_clc"},   # MUST use calc field
        "timeDimensionReference": {"calculatedFieldApiName": "Activity_Date_clc"},        # MUST use calc field
        "aggregationType": "Sum",
        "isCumulative":    False,
        "timeGrains":      ["Month", "Quarter", "Year"],
        "additionalDimensions": metric_dims,
        "insightsSettings": {
            "identifyingDimension": {"identifierDimensionReference": officer_name_ref},
            "insightTypes": all_insight_types(),
            "insightsDimensionsReferences": [
                officer_name_ref,
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
```

**Get metric IDs** (needed for dashboard metric widgets):
```python
# After creating metrics, fetch real metric IDs
r = requests.get(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/metrics", headers=SF_HDRS)
metric_ids = {m["label"]: m["id"] for m in r.json().get("metrics", [])}   # key is "metrics" not "semanticMetrics"
```

### Step G — POST relationship

```python
resp = requests.post(
    f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/relationships",
    headers=SF_HDRS,
    json={
        "leftSemanticDefinitionApiName":  fact_sdo,   # NOT DeveloperName
        "rightSemanticDefinitionApiName": dim_sdo,
        "joinType": "Auto",    # MUST be "Auto" at model level — explicit types only for logical views
        "criteria": [{
            "joinOperator":             "EqualsIgnoreCase",
            "leftFieldType":            "TableField",
            "leftSemanticFieldApiName":  fld(fact_sdo, "officer_id__c"),
            "rightFieldType":           "TableField",
            "rightSemanticFieldApiName": fld(dim_sdo, "officer_id__c"),
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

### Step — Link SDM to workspace (do this after model creation)

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

### Optional Steps (use when demo scenario calls for it)

**Step I — Parameters (dynamic variables):**
```python
parameters = [{"apiName": "Target_Origination_Amount_prm", "label": "Target Origination Amount",
               "description": "Threshold for flagging underperforming loan officers.",
               "dataType": "Number", "defaultValue": "500000"}]
for param in parameters:
    resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/parameters",
                         headers=SF_HDRS, json=param)
# Reference in expression: [Parameters].[Target_Origination_Amount_prm]
```

**Step J — Submetrics (pre-filtered parent metric breakdowns):**
```python
submetric = {"apiName": "commercial_loan_volume_sub", "label": "Commercial Loan Volume",
             "description": "...",
             "filters": [{"fieldReference": {"tableFieldReference": {"fieldApiName": fld(fact_sdo, "segment__c"), "tableApiName": fact_sdo}},
                          "operator": "Equals", "values": ["Commercial"]}]}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/metrics/{PARENT_METRIC_API_NAME}/submetrics",
                     headers=SF_HDRS, json=submetric)
```

**Step K — Logical Views (explicit join types / unions):**
```python
# Explicit LEFT JOIN:
lv_payload = {"apiName": "Client_Activity_lv", "label": "Client Activity View", "description": "...",
              "joins": [{"leftSemanticDefinitionApiName": fact_sdo, "rightSemanticDefinitionApiName": dim_sdo,
                         "joinType": "Left",
                         "criteria": [{"joinOperator": "EqualsIgnoreCase", "leftFieldType": "TableField",
                                       "leftSemanticFieldApiName": fld(fact_sdo, "officer_id__c"),
                                       "rightFieldType": "TableField",
                                       "rightSemanticFieldApiName": fld(dim_sdo, "officer_id__c")}]}]}
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
# Group:
group = {"apiName": "Client_Tier_Group_grp", "label": "Client Tier Group", "description": "...",
         "sourceFieldReference": {"tableFieldReference": {"fieldApiName": fld(fact_sdo, "tier_code__c"), "tableApiName": fact_sdo}},
         "groups": [{"label": "High Value", "values": ["PLAT", "GOLD"]}, {"label": "Mid Tier", "values": ["SILV"]}],
         "otherLabel": "Other"}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/groups", headers=SF_HDRS, json=group)

# Numeric bin:
bin_p = {"apiName": "Loan_Amount_Bin_bin", "label": "Loan Amount Bucket", "description": "...",
          "sourceFieldReference": {"tableFieldReference": {"fieldApiName": fld(fact_sdo, "loan_amount__c"), "tableApiName": fact_sdo}},
          "binCount": 5}
resp = requests.post(f"{BASE_SEM}/ssot/semantic/models/{model_api_name}/bins", headers=SF_HDRS, json=bin_p)
```

---

## STEP M — Visualizations (CONFIRMED WORKING — v66.0)

```python
BASE_CONNECT = f"{sf_instance}/services/data/v66.0"

# Field builder helpers
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

# Style constants
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

def build_viz_style(axis_dict, pane_dict, reverse_range=False, dim_row_keys=None):
    # reverse_range=True for horizontal bar (dim on rows, measure on columns)
    # dim_row_keys: list of field keys for dims on rows shelf — each needs allHeaders.fields entry
    fields_headers = {k: {"hiddenValues": [], "isVisible": True, "showMissingValues": False}
                      for k in (dim_row_keys or [])}
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
                          "size": {"isAutomatic": False, "type": "Pixel", "value": 4}}},
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
    resp = requests.post(f"{BASE_CONNECT}/tableau/visualizations", headers=SF_HDRS, json=payload)
    if resp.ok:
        result = resp.json()
        print(f"  ✅ Visualization: {label}  id={result.get('id')}")
        return result
    else:
        print(f"  ERROR '{label}': {resp.text[:400]}")
        return None

# Example visualizations:
vol_trend = create_visualization(
    label="Origination Volume — Monthly Trend", name=f"{model_api_name}_vol_trend",
    sdm_name=model_api_name, workspace_name=workspace_name,
    fields_dict={"F1": calc_measure("Total_Loan_Amount_clc", "Origination Volume ($)"),
                 "F2": calc_dim("Activity_Date_clc", "Month", is_date=True)},
    rows=["F1"], columns=["F2"], mark_type="Line",
    style=build_viz_style(axis_dict={**axis_number("F1", "Origination Volume"), **axis_date("F2")},
                          pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"), reverse_range=False),
)

vol_region = create_visualization(
    label="Origination Volume by Region", name=f"{model_api_name}_vol_by_region",
    sdm_name=model_api_name, workspace_name=workspace_name,
    fields_dict={"F1": calc_measure("Total_Loan_Amount_clc", "Origination Volume ($)"),
                 "F2": raw_dim(fld(fact_sdo, "region__c"), fact_sdo, "Region")},
    rows=["F2"], columns=["F1"], mark_type="Bar",   # dim on rows = horizontal bar
    style=build_viz_style(axis_dict=axis_number("F1", "Origination Volume"),
                          pane_dict=pane_format("F1", decimals=0, fmt_type="Currency"),
                          reverse_range=True, dim_row_keys=["F2"]),
)
```

**Confirmed working mark types**: `"Bar"`, `"Line"`, `"Area"`, `"Circle"` (scatter). `"Pie"` → rejected.
**Sorting**: `sortOrders` only works for `mode="Table"` — cannot sort bar/line charts via API.

---

## STEP N — Dashboard (CONFIRMED WORKING — always include)

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

def dash_date_filter(name, label, calc_date_dim_api, sdm_name, sdm_id, default_days=90):
    return {"actions": [], "name": name, "type": "filter", "label": label,
            "initialValues": {"details": {"fieldName": calc_date_dim_api, "operator": "LastNDays", "values": [float(default_days)]}},
            "parameters": {"filterOption": {"dataType": "Date", "fieldName": calc_date_dim_api, "selectionType": "multiple"},
                           "isLabelHidden": False,
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "viewType": "list", "widgetStyle": FILTER_STYLE},
            "source": {"id": sdm_id, "name": sdm_name}}

def dash_toggle_filter(name, label, field_api, sdo_api, sdm_name, sdm_id, single=False):
    # ⚠️  Only use for fields with ≤4 distinct values.
    # Fields with 5+ values (e.g. Region=5, Industry=many) overflow horizontally → use dash_list_filter instead.
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
    """Bordered background card. Position dash_text_inner + dash_viz_inner on top at the same grid coords."""
    return {"actions": [], "name": name, "type": "container",
            "parameters": {"widgetStyle": {"backgroundColor": _SLDS_SURFACE, "borderColor": _SLDS_BORDER,
                                           "borderEdges": ["all"], "borderRadius": _SLDS_RADIUS, "borderWidth": 1}}}

def dash_text_inner(name, text, description="", desc_color="#706E6B"):
    """Title + description for use INSIDE a dash_container card. White bg, no border."""
    content = [{"attributes": {"bold": True, "color": "#032D60", "size": "14px"}, "insert": text, "rules": []},
               {"insert": "\n", "rules": []}]
    if description:
        content += [{"attributes": {"color": desc_color, "size": "11px"}, "insert": description, "rules": []},
                    {"insert": "\n", "rules": []}]
    return {"actions": [], "name": name, "type": "text",
            "parameters": {"conditionalFormattingRules": [],
                           "content": content,
                           "widgetStyle": {"backgroundColor": _SLDS_SURFACE, "borderEdges": []},
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []}}}

def dash_viz_inner(name, viz_api_name, viz_id, legend_position="Bottom"):
    """Viz for use INSIDE a dash_container card. No border — container provides the border."""
    return {"actions": [], "name": name, "type": "visualization",
            "parameters": {"legendPosition": legend_position,
                           "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "widgetStyle": {"backgroundColor": _SLDS_SURFACE, "borderEdges": []}},
            "source": {"id": viz_id, "name": viz_api_name}}

def dash_pos(name, col, row, colspan, rowspan):
    return {"name": name, "column": col, "row": row, "colspan": colspan, "rowspan": rowspan}

# ── UNIFIED CARD PATTERN (title + description + viz as one card) ───────────────
# Use dash_container + dash_text_inner + dash_viz_inner at overlapping positions.
# Container spans ALL rows of the card. Text takes the top N rows. Viz takes the rest.
# Example (cols 2–46, rows 10–22, 13 rows total):
#
#   widgets["container_trend"] = dash_container("container_trend")
#   page_cells.append(dash_pos("container_trend", 2, 10, 45, 13))  # full card
#
#   widgets["label_trend"] = dash_text_inner("label_trend", "Balance Trend",
#       description="Aggregate deposit balance over time...")
#   page_cells.append(dash_pos("label_trend", 2, 10, 45, 3))       # top 3 rows
#
#   widgets["viz_1"] = dash_viz_inner("viz_1", viz_api, viz_id)
#   page_cells.append(dash_pos("viz_1", 2, 13, 45, 10))            # bottom 10 rows
#
# ── OUTER MARGIN RULE ──────────────────────────────────────────────────────────
# With columnCount=72: reserve col 1 and col 72 as empty gutters. Run all content
# through cols 2–71. A full-width widget at cols 1–72 renders edge-to-edge (no
# outer margin) while multi-widget rows get cellSpacing gaps — misaligned appearance.
# Recommended settings: columnCount=72, rowHeight=16, cellSpacingX=16, cellSpacingY=16


# Build dashboard
widgets_dict = {}
page_cells   = []

# Background container
widgets_dict["container_1"] = dash_container("container_1")
page_cells.append(dash_pos("container_1", 0, 0, 36, 41))

# Title
widgets_dict["text_1"] = dash_text("text_1", f"{BANK_NAME} — {USE_CASE}", bold=True, size="28px")
page_cells.append(dash_pos("text_1", 0, 0, 36, 2))

# Filters
widgets_dict["list_1"] = dash_date_filter("list_1", "Date", "Activity_Date_clc", model_api_name, model_id)
page_cells.append(dash_pos("list_1", 0, 2, 11, 2))
# widgets_dict["toggle_1"] = dash_toggle_filter("toggle_1", "Segment", seg_field_api, fact_sdo, model_api_name, model_id)
# page_cells.append(dash_pos("toggle_1", 12, 2, 12, 2))

# Section + metric tiles
widgets_dict["text_2"] = dash_text("text_2", "Key Metrics", bold=True, size="16px", color="#5c5c5c")
page_cells.append(dash_pos("text_2", 0, 5, 36, 1))
metrics_to_show = [
    ("metric_1", "metric_api_name_1", metric_ids["Metric Label 1"]),
    ("metric_2", "metric_api_name_2", metric_ids["Metric Label 2"]),
    ("metric_3", "metric_api_name_3", metric_ids["Metric Label 3"]),
    ("metric_4", "metric_api_name_4", metric_ids["Metric Label 4"]),
]
n = len(metrics_to_show)
metric_cols = 36 // n
for i, (mname, mapi, mid) in enumerate(metrics_to_show):
    widgets_dict[mname] = dash_metric(mname, mapi, mid, model_api_name, model_id)
    page_cells.append(dash_pos(mname, i * metric_cols, 6, metric_cols, 9))

# Section + visualizations (2×2 grid)
widgets_dict["text_3"] = dash_text("text_3", "Trends & Breakdowns", bold=True, size="16px", color="#5c5c5c")
page_cells.append(dash_pos("text_3", 0, 16, 36, 1))
viz_grid = [
    # NOTE: viz POST response uses "name" not "apiName" — use .get("apiName") or .get("name") to handle both
    ("viz_1", (vol_trend.get("apiName") or vol_trend.get("name"))   if vol_trend  else "", vol_trend["id"]  if vol_trend  else "",  0, 17, 18, 13),
    ("viz_2", (vol_region.get("apiName") or vol_region.get("name")) if vol_region else "", vol_region["id"] if vol_region else "", 18, 17, 18, 13),
]
for vname, vapi, vid, col, row, colspan, rowspan in viz_grid:
    if vid:
        widgets_dict[vname] = dash_viz(vname, vapi, vid)
        page_cells.append(dash_pos(vname, col, row, colspan, rowspan))

# POST dashboard
DASH_NAME = f"{WORKSPACE_NAME}_dashboard"
dash_payload = {
    "label": f"{BANK_NAME} — {USE_CASE} Overview",
    "name":  DASH_NAME,
    "description": f"Auto-generated dashboard for {BANK_NAME} {USE_CASE} demo.",
    "workspaceIdOrApiName": WORKSPACE_NAME,
    "style": {"widgetStyle": {"backgroundColor": _SLDS_PAGE_BG, "borderColor": _SLDS_BORDER,
                               "borderEdges": [], "borderRadius": 0, "borderWidth": 1}},
    "widgets": widgets_dict,   # MUST be dict, not list
    "layouts": [{
        "name": "default", "columnCount": 36, "rowHeight": 24, "maxWidth": 1440,
        "pages": [{"name": str(uuid.uuid4()), "label": "Overview", "widgets": page_cells}],  # UUID required
        "style": {"backgroundColor": _SLDS_PAGE_BG, "cellSpacingX": 8, "cellSpacingY": 8, "gutterColor": _SLDS_PAGE_BG},  # required — {} causes blank canvas
    }],
    # DO NOT include "customViews" — rejected with JSON_PARSER_ERROR
}

resp = requests.post(f"{BASE_CONNECT}/tableau/dashboards", headers=SF_HDRS, json=dash_payload)
if resp.ok:
    print(f"  ✅ Dashboard created: {DASH_NAME}  id={resp.json().get('id')}")
else:
    print(f"  ⚠️  Dashboard failed: {resp.status_code} {resp.text[:300]}")
```

---

## STEP 8 — FULL CODE: Demo Guide

```python
import textwrap

def build_demo_guide(bank_name, use_case, persona, story, signal_onset_months,
                     metrics, visualizations, concierge_questions,
                     workspace_name, sdm_name, script_name, bank_slug, use_case_slug):
    today_str   = date.today().strftime("%B %d, %Y")
    metrics_rows = "\n".join(
        f"| {m['name']} | {m['type']} | {m.get('concierge_note', '')} |" for m in metrics)
    metrics_table = "| Metric | Type | Concierge note |\n|---|---|---|\n" + metrics_rows
    viz_sections = []
    for i, v in enumerate(visualizations, 1):
        points = "\n".join(f"  - {p}" for p in v["talking_points"])
        viz_sections.append(f"**{i}. {v['label']}** ({v['type']})\n{points}")
    viz_walkthrough = "\n\n".join(viz_sections)
    q_lines = "\n".join(f'{i+1}. "{q}"' for i, q in enumerate(concierge_questions))

    guide = f"""# {bank_name} — {use_case} Demo Guide

**Persona:** {persona}
**Story:** {story}
**Signal onset:** {signal_onset_months} months ago, ramping to full effect today
**Built:** {today_str}

---

## Before You Demo

1. **Run the script** (if not already done): `python3 {script_name}`
2. **Enable Analytics Agent Readiness**: Data 360 → Semantic Model → **{sdm_name}** → Settings → Analytics Agent Readiness → toggle ON
3. **Business Preferences** are applied automatically by the script. To add custom preferences: Data 360 → Semantic Model → {sdm_name} → Business Preferences
4. **Seed Q&A Calibration**: Data 360 → Semantic Model → {sdm_name} → Q&A Calibration → add questions below as Verified Questions (see Q&A Calibration Guide at end of skill file)

---

## Metrics in This Demo

{metrics_table}

---

## Suggested Demo Walk-Through

Open the **{workspace_name}** workspace in Tableau Next.

{viz_walkthrough}

**Switch to Concierge:**
> "Now let me show you what happens when your {persona} just types a question..."

---

## Concierge Questions to Ask Live

{q_lines}

**Bonus — semantic learning question (most impressive moment):**
> Ask "Which officers are underperformers?"
> Concierge: "How do you define underperformer?"
> You define it in natural language → Concierge creates a calculated field on the fly.

---

## Q&A Calibration (show for data/IT audiences)

After the demo: Data 360 → {sdm_name} → Q&A Calibration → add these questions as Verified Questions, run a regression test.

---

## Teardown

```
python3 next_teardown.py
```

Workspace: {workspace_name}
"""
    Path(f"{bank_slug}_{use_case_slug}_demo_guide.md").write_text(guide)
    print(f"  ✅ Demo guide written: {bank_slug}_{use_case_slug}_demo_guide.md")
```

---

## ALL COMMON PITFALLS (57 items)

1. **Do not use the SF access token for Data Cloud API calls** — always complete the second token exchange at `/services/a360/token`.
2. **Do not leave field descriptions blank** — Concierge quality degrades sharply with undescribed fields.
3. **Do not use abbreviations in field descriptions** — Concierge reads them literally.
4. **Do not use a flat single-table model** — always use at least a fact + one dimension table.
5. **Do not use snake_case field labels** — must be business-readable: `Loan Amount`, not `loan_amount`.
6. **Always log `resp.text` on failures** — `raise_for_status()` alone hides the actual API error.
7. **Ingestion schema + stream is fully programmatic** — use `PUT /ssot/connections/{id}/schema` then `POST /ssot/data-streams`. No UI required.
8. **PUT schema is a FULL REPLACE** — always GET first, strip read-only fields, merge with new, then PUT.
9. **Semantics Layer API uses SF access token** — `/ssot/semantic/` endpoints live on SF instance, not DC instance.
10. **`directionality` values are `"Up"` and `"Down"`** — not `"INCREASING"` / `"DECREASING"`.
11. **`aggregationType` is `"None"` (string), not `null`**.
12. **Always set `agentEnabled: True`** — required for Concierge.
13. **PATCH on the main model URL is a FULL REPLACE** — never use PATCH to add sub-entities; use sub-resource POST endpoints.
14. **Semantic Metrics MUST use `calculatedFieldApiName`** — `tableFieldReference` in `measurementReference` / `timeDimensionReference` is silently ignored.
15. **All dims in `insightsSettings` must also be in `additionalDimensions`** — missing causes 400.
16. **`joinType` must be `"Auto"` for model-level relationships** — explicit types only for logical views.
17. **Use `leftSemanticDefinitionApiName` / `rightSemanticDefinitionApiName`** — NOT `DeveloperName`.
18. **`queryUnrelatedDataObjects`** — `"Exception"` is a confirmed valid value; omitting the field is also fine.
19. **Semantic API version is v65.0** — use a separate `BASE_SEM` variable.
20. **DLO field names have `__c` suffix** — always use `date__c`, `loan_amount__c`, etc.
21. **Always delete and recreate on re-run** — duplicate apiName returns an error.
22. **Logical views can use joins OR unions — never both** in the same logical view.
23. **Union schemas must align by position** — mismatched schemas cause silent data loss.
24. **Submetrics must reference an existing parent metric apiName** — create parent first.
25. **Parameters must be created before the calculated fields that reference them**.
26. **Groups and bins are dimensions, not measures** — do not assign `aggregationType` to them.
27. **`agentEnabled: True` alone is not enough for Concierge** — user must also enable Analytics Agent Readiness in UI.
28. **Snapped metrics must never be summed across time** — use `aggregationType: "Sum"` + LOD filter or submetric filtered to `CurrentMonth`.
29. **SDM hard limits**: 500 semantic definitions total, max 100 objects at creation, max 20 additional dims per metric, max 9 objects in a union.
30. **Visualizations API requires v66.0** — v64.0 and v65.0 return `DOWNGRADE_VERSION_ERROR`.
31. **`fields` is a dict, not array** — `{"F1": {...}, "F2": {...}}`.
32. **`style.headers` must be omitted, not `{}`** — empty dict causes `JSON_PARSER_ERROR`.
33. **`allHeaders.fields` is required for dimension fields on the rows shelf** — omitting causes `INVALID_VISUALIZATION_METADATA`.
34. **`mode` must be `"Visualization"` for charts** — not `"Normal"`, not `"Table"`.
35. **Sorting bar charts by measure is not supported via API** — `sortOrders` only works when `mode="Table"`.
36. **`"UserAgg"` causes `ROW_LEVEL_CALC_AGG_VALIDATION_ERROR`** for row-level calcs — use `"Sum"` or `"Avg"` to match SDM `aggregationType`.
37. **Dashboard `widgets` is a dict, not a list** — sending an array causes 500 error.
38. **Dashboard `style` uses `widgetStyle`** — not `"canvas"`.
39. **Dashboard `customViews` must be omitted** — `[]` causes JSON_PARSER_ERROR.
40. **Delete dashboards before visualizations in teardown**.
41. **Dashboard layout `style` must include cell spacing** — `{}` causes blank canvas.
42. **Dashboard page `name` must be a UUID** — plain strings cause blank canvas.
43. **Bulk ingest job list response key is `"data"`, not `"jobs"`**.
44. **Never construct the DLO name manually** — always read from `GET /ssot/data-streams/{name}` → `dataLakeObjectInfo.name`.
45. **Always poll for DLO ACTIVE before ingesting** — submitting before ACTIVE causes silent data loss.
46. **Parallel bulk job submission is faster** — submit all jobs before waiting for any.
47. **`GET /ssot/semantic/models/{name}/metrics` returns `"metrics"` key, not `"semanticMetrics"`**.
48. **Mac notifications via `osascript -e` fail with em dash (`—`)** — write AppleScript to a tempfile instead.
49. **SDO `semanticMeasurements` must use `dataType: "Number"` for IngestAPI DLOs** — `"Currency"` rejected; use `"Number"` for raw SDO fields, `"Currency"` only for calc measurements.
50. **Use SLDS 2.0 design tokens** — brand `#0176D3`, surface `#FFFFFF`, page bg `#F4F6F9`, border `#DDDBDA`, radius `4px`, cell spacing `8px`.
51. **`GET /ssot/data-lake-objects` does NOT return IngestAPI DLOs** — use `GET /ssot/data-streams/{name}` instead.
52. **Only PK field in `dataLakeFieldInputRepresentations` when creating a stream** — sending all fields causes "Illegal argument" error on the 2nd+ object.
53. **Schema PUT fields only accept `name`, `label`, `dataType`** — including `isPrimaryKey` or `isEventTime` causes `JSON_PARSER_ERROR`; declare PKs only in the stream's `dataLakeFieldInputRepresentations` (Step 5c), not in the schema PUT.
54. **`if r:` is always False for failed responses** — use `if r is not None:` in `die()` and any error guard; `requests.Response.__bool__` returns False for 4xx/5xx, silently swallowing error details.
55. **Visualization POST response key is `name`, not `apiName`** — use `viz_result.get("apiName") or viz_result.get("name")` when extracting the identifier from a viz creation response.
56. **Mark `size` and `isAutomaticSize` belong in `style.marks.ALL`, not in `visualSpecification.marks.ALL`** — undocumented but accepted at v66.0. Valid size types: `"Pixel"` (absolute) and `"Percentage"` (relative, 2–100% of cell, equivalent to UI "Relative" slider). Use `"Percentage"` / `75` for bars; use `"Pixel"` / `2` for lines. `isAutomaticSize` must be present alongside `size` or API returns INVALID_INPUT. `isAutomaticSize` in `visualSpecification.marks.ALL` is silently rejected.
57. **Newly registered ingest schema objects return 404 from the bulk jobs endpoint for ~15–30s after DLO ACTIVE** — existing schemas are immediately ready; brand new ones need propagation time. Add retry logic with 15s backoff (up to 3 retries) on 404 in `bulk_ingest_submit()`. Existing (re-run) streams are unaffected.

---

## Q&A CALIBRATION GUIDE

*(Referenced in demo guide "Before You Demo" step 4. Show for data/IT/analytics audiences — not executives.)*

Q&A Calibration is a self-serve tool that lets data experts test and improve Concierge answer accuracy.

**What it does:**
- **Questions Bank** — library of test questions with statuses: New, Inaccurate, Verified, Regression
- **Verified Questions** — confirmed as accurate; surfaced to the agent as ground truth context
- **Batch Regression Testing** — run all VQs after any SDM change to confirm nothing broke
- **AI Question Generation** — seed 10+ questions, generate 10/30/50 more
- **Calibration suggestions** — when a question fails, suggests SDM changes to fix it

**How to build demo-ready Questions Bank (after script runs):**
1. Open Data 360 → Semantic Model → [model] → Q&A Calibration
2. Add 10–15 questions manually (one per metric, filtered, comparison, trend)
3. Ask Concierge each question. For good answers → click **Verify**
4. Once 10+ Verified, use **Generate Questions** to expand
5. Create a **Regression Test suite** and run baseline

**Demo talking points:**

| Moment | Talking point |
|---|---|
| Open Questions Bank | "This is where we govern what Concierge knows — every verified question is ground truth the agent learns from." |
| Show Verified Question | "When I verified this, I confirmed the answer is correct. Concierge uses this as a reference for similar questions." |
| Run Regression Test | "After any model change, I run this batch test. Anything that fails is automatically quarantined until I fix it." |
| AI Question Generation | "I can generate 30 new test questions grounded in the semantic model in seconds." |

**When to show:**
- Executive / business user → brief mention only
- Data / analytics manager → lead with it
- IT / data engineering → show regression testing
- BI developer → show question generation

**Feedback-to-questions flow (strong closing for governance buyers):**
- Prospect gives feedback during demo → "I can add that as a calibration question right now" → Verify → instant improvement
