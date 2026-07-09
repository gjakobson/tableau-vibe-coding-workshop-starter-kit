# Tableau Next Demo Builder — Peer Setup Guide

This guide gets you from zero to running your first demo in about 30 minutes.

---

## What You Need Before Starting

- A Salesforce org with **Data Cloud / Tableau Next** provisioned
- Python 3.10+ installed (`python` command preferred; use `python3` if your system uses that)
- Salesforce CLI installed (`sf`)
- Claude Code installed and running

---

## Step 1 — Install Python Dependencies

```bash
python -m pip install requests pandas numpy
```

If your machine uses `python3`, run `python3 -m pip install requests pandas numpy`.

---

## Step 2 — Authenticate with Salesforce CLI

The workshop now uses CLI auth only.

```bash
sf org login web --alias workshop
sf org display --target-org workshop
```

---

## Step 3 — Create Your Data Cloud Ingestion Connector

The scripts need a connector in Data Cloud to ingest synthetic data.

1. In Data Cloud Setup → **Ingestion API** → New
2. Name it exactly: `tableau_next_demo`
3. Under Schemas: upload any placeholder YAML (the script will overwrite it programmatically)
4. Save — you'll see the connector appear with a UUID-suffixed name like `tableau_next_demo_885b38ac_...`

---

## Step 4 — Configure `next_config.json`

1. Copy the template:
   ```bash
   cp next_config.template.json next_config.json
   ```
2. Edit `next_config.json` with your values:
   ```json
   {
     "target_org": "workshop",
     "data_cloud_domain": "yourorg.c360a.salesforce.com",
     "ingestion_connector_name": "tableau_next_demo",
     "connector_sf_id": "",
     "connector_uuid_name": ""
   }
   ```
3. The `connector_sf_id` and `connector_uuid_name` fields start empty — the script fills them in automatically on the first run and saves them back to the file.

> `next_config.json` should still stay local, but it no longer stores Connected App secrets or refresh tokens.

---

## Step 5 — Install Claude Code and Load the Skill

1. Install Claude Code: `npm install -g @anthropic-ai/claude-code` (or follow Anthropic's docs)
2. Open this project folder in Claude Code
3. The `/start-workshop` skill loads automatically — it's in `.claude/commands/start-workshop.md`

---

## Step 6 — Build Your First Demo

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
| `Authentication failed` | Re-run `sf org login web --alias workshop`, then retry |
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

To tear down a demo environment: `python next_teardown.py` (or `python3 next_teardown.py`).

---

*Questions? Ask in the SE Demo Tools Slack channel.*
