# Tableau Next Demo Builder — Peer Setup Guide

This guide gets you from zero to running your first demo in about 30 minutes.

---

## What You Need Before Starting

- A Salesforce org with **Data Cloud / Tableau Next** provisioned
- A Connected App in that org (see Step 2)
- Python 3.10+ installed on your Mac (`/opt/homebrew/bin/python3.13` preferred)
- Claude Code installed and running

---

## Step 1 — Install Python Dependencies

```bash
/opt/homebrew/bin/python3.13 -m pip install requests pandas numpy
```

---

## Step 2 — Create a Connected App in Salesforce

You need a Connected App to authenticate via the API. If your org already has one set up for demo builders, skip to Step 3.

1. In Salesforce Setup, search for **App Manager** → New Connected App
2. Enable OAuth:
   - Callback URL: `https://login.salesforce.com/services/oauth2/success`
   - Selected OAuth Scopes:
     - `cdp_ingest_api` (Access and manage your Data Cloud Ingestion API data)
     - `cdp_query_api` (Access and manage your Data Cloud Query API data)
     - `api` (Access the Salesforce APIs)
     - `sfap_api` (Access Tableau Semantics Layer)
     - `refresh_token` (Perform requests at any time)
3. Enable **Client Credentials Flow** (under OAuth settings)
4. Save and wait ~2 min for Salesforce to provision it
5. Copy the **Consumer Key** (client_id) and **Consumer Secret** (client_secret)

---

## Step 3 — Get a Refresh Token

The scripts authenticate with a refresh token (long-lived, no browser re-login needed).

**Easiest method — Salesforce CLI:**

```bash
sf org login web --instance-url https://login.salesforce.com
sf org display --verbose
```

Look for `Sfdx Auth Url` in the output — it contains your refresh token after `refreshToken=`.

**Alternative — OAuth flow in browser:**

1. Construct this URL (replace CLIENT_ID with your Connected App's Consumer Key):
   ```
   https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id=CLIENT_ID&redirect_uri=https://login.salesforce.com/services/oauth2/success&scope=cdp_ingest_api+cdp_query_api+api+sfap_api+refresh_token
   ```
2. Open in browser, log in, authorize
3. The callback URL will contain `?code=...` — copy that code
4. Exchange it for tokens:
   ```bash
   curl -X POST https://login.salesforce.com/services/oauth2/token \
     -d "grant_type=authorization_code" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "redirect_uri=https://login.salesforce.com/services/oauth2/success" \
     -d "code=YOUR_CODE"
   ```
5. Copy `refresh_token` from the JSON response

---

## Step 4 — Create Your Data Cloud Ingestion Connector

The scripts need a connector in Data Cloud to ingest synthetic data.

1. In Data Cloud Setup → **Ingestion API** → New
2. Name it exactly: `tableau_next_demo`
3. Under Schemas: upload any placeholder YAML (the script will overwrite it programmatically)
4. Save — you'll see the connector appear with a UUID-suffixed name like `tableau_next_demo_885b38ac_...`

---

## Step 5 — Configure Your Credentials

1. Copy the template:
   ```bash
   cp next_config.template.json next_config.json
   ```
2. Edit `next_config.json` with your values:
   ```json
   {
     "sf_login_url": "https://login.salesforce.com",
     "client_id": "3MVG...",
     "client_secret": "ABC123...",
     "refresh_token": "5Aep...",
     "data_cloud_domain": "yourorg.c360a.salesforce.com",
     "ingestion_connector_name": "tableau_next_demo",
     "connector_sf_id": "",
     "connector_uuid_name": ""
   }
   ```
3. The `connector_sf_id` and `connector_uuid_name` fields start empty — the script fills them in automatically on the first run and saves them back to the file.

> **IMPORTANT:** Never share or commit `next_config.json`. It contains your credentials. The `.template.json` file is safe to share.

---

## Step 6 — Install Claude Code and Load the Skill

1. Install Claude Code: `npm install -g @anthropic-ai/claude-code` (or follow Anthropic's docs)
2. Open this project folder in Claude Code
3. The `/start-workshop` skill loads automatically — it's in `.claude/commands/start-workshop.md`

---

## Step 7 — Build Your First Demo

Open Claude Code in this project folder and type:

```
/start-workshop
```

Claude will ask you for:
- Bank / company name
- Target persona (e.g., Commercial Banking RM, Wealth Advisor)
- Story (what's declining, what's rising, what's the business problem)

Reply **go** when the plan looks right. The script runs automatically — total time is 8–15 minutes. You'll get a Mac notification when it's done.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Authentication failed` | Check `client_id`, `client_secret`, and `refresh_token` in `next_config.json` |
| `connector_sf_id not found` | Make sure the connector is named exactly `tableau_next_demo` in Data Cloud Setup |
| `DLO ACTIVE timeout` | The org may be slow — re-run the script; it's idempotent |
| `409 Conflict on bulk job` | A previous job is still running — wait 5 min and re-run |
| Script runs but dashboard is blank | Check that `cellSpacingX/Y` and UUID page name are set (Pitfalls 43–44) |
| Concierge panel not showing | Enable **Analytics Agent Readiness** in Data 360 → Semantic Model settings |

---

## What Gets Built

Each `/start-workshop` run creates:

| Asset | Location |
|---|---|
| Synthetic data in Data Cloud | Data Cloud → Data Explorer |
| Workspace | Tableau Next → Workspaces |
| Semantic Data Model | Data 360 → Semantic Models |
| 4 Visualizations | Tableau Next → Visualizations |
| Dashboard | Tableau Next → Dashboards |
| Demo guide (Markdown) | Project folder → `{bank}_{use_case}_demo_guide.md` |

To tear down a demo environment: `python3 next_teardown.py`

---

*Questions? Ask in the SE Demo Tools Slack channel.*
