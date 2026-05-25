# Tableau Next Demo Builder

Build complete, realistic Tableau Next demos end-to-end — no coding required.

You describe the prospect, the persona, and the story. Claude builds the workspace, semantic model, visualizations, dashboard, and AI-ready metrics automatically in your Salesforce org.

---

## What You Need

**On your Mac:**
- [ ] [Claude Code](https://claude.ai/code) installed (VS Code extension)
- [ ] Python 3.10+ — check by opening Terminal and typing `python3 --version`

**In Salesforce:**
- [ ] A Salesforce org with Data Cloud and Tableau Next provisioned
- [ ] Admin access (or someone who can create a Connected App for you)

---

## One-Time Setup

### 1 — Open this folder in Claude Code

1. Open VS Code
2. **File → Open Folder** → select this folder
3. Click the **Claude Code** icon in the bottom status bar

### 2 — Ask Claude to set you up

Type this in the Claude panel:

> "Walk me through setup"

Claude will guide you through everything interactively — creating a Connected App, configuring credentials, and verifying your connection. **You do not need to follow PEER_SETUP.md manually.** Claude handles it step by step and will ask for your input only when needed.

**You only run setup once per Salesforce org.**

> `next_orgs.json` contains your credentials — never share it or commit it. It's excluded from this repo by `.gitignore`.

---

## Build a Demo

Type:
```
/start-workshop
```

Claude will ask for:
- The prospect's name (e.g., "First Meridian Bank")
- The persona (e.g., "Commercial Banking Relationship Manager")
- The story (e.g., "Loan originations have been declining for the past 6 months")

It shows you a plan and waits for your approval before building anything. Once you say **go**, it handles everything automatically — generating data, loading it into Data Cloud, building the semantic model, and creating the visualizations and dashboard.

The build takes about 8–15 minutes. You'll get a Mac notification when it's done.

---

## What Gets Built

For each demo, Claude creates:

| Asset | Where to find it |
|---|---|
| Synthetic data loaded into Data Cloud | Data Cloud → Data Explorer |
| Workspace | Tableau Next → Workspaces |
| Semantic Data Model | Data 360 → Semantic Models |
| Visualizations + Dashboard | Tableau Next → Visualizations / Dashboards |
| Demo guide with Concierge questions | This folder → `{bank}_{use_case}_demo_guide.md` |

---

## After the Demo — Clean Up

To remove a demo from your org:

```bash
python3 next_teardown.py
```

It lists every demo you've built and walks you through the cleanup.

---

## Troubleshooting

If something goes wrong, paste the error into Claude and ask — it can diagnose and fix most issues on the fly.

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip3 install -r requirements.txt` and try again |
| `Authentication failed` | Check `client_id`, `client_secret`, and `refresh_token` in `next_orgs.json` |
| `connector_sf_id not found` | Make sure the connector is named exactly `tableau_next_demo` in Data Cloud Setup |
| `DLO ACTIVE timeout` | The org is slow — re-run the script; it picks up where it left off |
| Dashboard is blank | Make sure you said **go** and the script completed Phase 10 |
| Concierge panel not showing | Enable **Analytics Agent Readiness** in Data 360 → Semantic Model → Settings |
