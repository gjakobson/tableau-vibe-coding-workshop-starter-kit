#!/usr/bin/env python3
"""
next_teardown.py
Tears down a Tableau Next demo — removes all assets from Salesforce and Data Cloud.

Run: /opt/homebrew/bin/python3.13 next_teardown.py
"""

import json, os, re, io, sys, zipfile, base64, time, requests
from pathlib import Path

CONFIG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "next_config.json")
REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "next_demos.json")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def banner(title):
    width = 62
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else default


# ══════════════════════════════════════════════════════════════════════════════
# DEMO REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

def load_registry():
    """Load the list of demos created on this machine."""
    if not os.path.exists(REGISTRY_FILE):
        return []
    try:
        return json.loads(Path(REGISTRY_FILE).read_text())
    except Exception:
        return []


def remove_from_registry(workspace_name):
    """Remove a demo from the registry after successful teardown."""
    demos = load_registry()
    demos = [d for d in demos if d.get("workspace_name") != workspace_name]
    with open(REGISTRY_FILE, "w") as f:
        json.dump(demos, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# PICK DEMO TO TEAR DOWN
# ══════════════════════════════════════════════════════════════════════════════

banner("Tableau Next Demo Builder — Teardown")

print("""
  This script removes a demo from your Salesforce org.

  It will discover and delete — in safe order:
    1. Dashboards
    2. Visualizations
    3. Semantic Data Model
    4. Workspace
    5. Data Cloud streams and data (optional)

  Nothing is deleted until you confirm.
""")

# ── Load credentials ─────────────────────────────────────────────────────────
if not os.path.exists(CONFIG_FILE):
    print("  ❌ next_config.json not found.")
    print("     Run next_setup.py first to configure your credentials.")
    sys.exit(1)

cfg = json.loads(Path(CONFIG_FILE).read_text())
sf_login_url = cfg["sf_login_url"]

print("  Connecting to Salesforce...")
r = requests.post(f"{sf_login_url}/services/oauth2/token", data={
    "grant_type":    "refresh_token",
    "refresh_token": cfg["refresh_token"],
    "client_id":     cfg["client_id"],
    "client_secret": cfg["client_secret"],
})
if not r.ok:
    print(f"  ❌ Authentication failed: {r.status_code} {r.text[:200]}")
    sys.exit(1)

sf_token    = r.json()["access_token"]
sf_instance = r.json().get("instance_url", sf_login_url)
print(f"  ✅ Connected to: {sf_instance}")

HDR      = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
BASE_DC  = f"{sf_instance}/services/data/v62.0"
BASE_SEM = f"{sf_instance}/services/data/v65.0"
BASE_VIZ = f"{sf_instance}/services/data/v66.0"

# ── Choose demo ──────────────────────────────────────────────────────────────
registry = load_registry()

if registry:
    print(f"\n  Demos built on this machine:\n")
    for i, demo in enumerate(registry, 1):
        built = demo.get("built_on", "")
        label = demo.get("label", demo.get("workspace_name", ""))
        print(f"    {i}. {label}  (built {built})")
    print()
    choice = ask("Enter a number to select, or press Enter to type a name manually")
    if choice and choice.isdigit() and 1 <= int(choice) <= len(registry):
        selected = registry[int(choice) - 1]
        WORKSPACE_NAME = selected["workspace_name"]
        DC_PREFIX      = selected.get("dc_prefix", "")
        print(f"\n  Selected: {selected.get('label', WORKSPACE_NAME)}")
    else:
        WORKSPACE_NAME = ask("Workspace name (from the end of your demo script output)")
        DC_PREFIX      = ask("Data Cloud prefix to clean up (press Enter to skip)", default="")
else:
    print("\n  No demos found in registry. You can still enter names manually.")
    print("  Tip: the workspace name was printed at the end of your demo script run.")
    WORKSPACE_NAME = ask("Workspace name")
    DC_PREFIX      = ask("Data Cloud prefix to clean up (press Enter to skip)", default="")

SDM_NAME = WORKSPACE_NAME   # SDM name always matches workspace name

print(f"""
  ─────────────────────────────────────────────────────────
  Workspace  : {WORKSPACE_NAME}
  SDM        : {SDM_NAME}
  DC prefix  : {DC_PREFIX if DC_PREFIX else "(skipping Data Cloud cleanup)"}
  ─────────────────────────────────────────────────────────
""")

confirm_start = ask("Continue with discovery? (yes/no)", default="yes")
if confirm_start.lower() not in ("yes", "y"):
    print("\n  Cancelled.")
    sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n  Scanning your org for demo assets...")

assets = {
    "dashboard_ids":    [],
    "viz_ids":          [],
    "sdm_exists":       False,
    "workspace_exists": False,
    "dsd_dev_names":    [],
    "datasource_id":    None,
    "dlo_rest_ids":     [],
    "conn_full_name":   None,
}

# Dashboards (must be deleted before vizzes)
rd = requests.get(f"{BASE_VIZ}/tableau/dashboards", headers=HDR)
if rd.ok:
    for d in rd.json().get("dashboards", []):
        if d.get("workspaceIdOrApiName") == WORKSPACE_NAME:
            assets["dashboard_ids"].append((d["id"], d.get("label", d["id"])))
    count = len(assets["dashboard_ids"])
    print(f"  {'✅' if count else '—'} Dashboards: {count} found")
else:
    print(f"  ⚠️  Could not check dashboards: {rd.status_code}")

# Visualizations
rv = requests.get(f"{BASE_VIZ}/tableau/visualizations", headers=HDR)
if rv.ok:
    for v in rv.json().get("visualizations", []):
        ws = v.get("workspace", {})
        ws_name = ws.get("name", "") if isinstance(ws, dict) else ""
        if ws_name == WORKSPACE_NAME:
            assets["viz_ids"].append((v["id"], v.get("label", v["id"])))
    count = len(assets["viz_ids"])
    print(f"  {'✅' if count else '—'} Visualizations: {count} found")
else:
    print(f"  ⚠️  Could not check visualizations: {rv.status_code}")

# SDM
rs = requests.get(f"{BASE_SEM}/ssot/semantic/models/{SDM_NAME}", headers=HDR)
if rs.ok:
    assets["sdm_exists"] = True
    print(f"  ✅ Semantic Model: found ({rs.json().get('label', SDM_NAME)})")
elif rs.status_code == 404:
    print(f"  —  Semantic Model: not found (will skip)")
else:
    print(f"  ⚠️  Semantic Model: {rs.status_code}")

# Workspace
rw = requests.get(f"{BASE_SEM}/tableau/workspaces/{WORKSPACE_NAME}", headers=HDR)
if rw.ok:
    assets["workspace_exists"] = True
    print(f"  ✅ Workspace: found ({rw.json().get('label', WORKSPACE_NAME)})")
elif rw.status_code == 404:
    print(f"  —  Workspace: not found (will skip)")
else:
    print(f"  ⚠️  Workspace: {rw.status_code}")

# Data Cloud assets (optional)
if DC_PREFIX:
    # IngestAPI connection
    rc = requests.get(f"{BASE_DC}/ssot/connections?connectorType=IngestApi&limit=50", headers=HDR)
    if rc.ok:
        for conn in rc.json().get("connections", []):
            name = conn.get("name", "")
            if name == DC_PREFIX or name.startswith(DC_PREFIX + "_"):
                assets["conn_full_name"] = name
                break
    if not assets["conn_full_name"]:
        assets["conn_full_name"] = DC_PREFIX

    # DataStreamDefinitions
    q = f"SELECT Id,DeveloperName FROM DataStreamDefinition WHERE DeveloperName LIKE '{DC_PREFIX}%'"
    rd = requests.get(f"{BASE_DC}/tooling/query", headers=HDR, params={"q": q})
    if rd.ok:
        assets["dsd_dev_names"] = [rec["DeveloperName"] for rec in rd.json().get("records", [])]

    # DataSource
    q2 = f"SELECT Id FROM DataSource WHERE DeveloperName LIKE '{DC_PREFIX}%'"
    rd2 = requests.get(f"{BASE_DC}/tooling/query", headers=HDR, params={"q": q2})
    if rd2.ok:
        recs = rd2.json().get("records", [])
        if recs:
            assets["datasource_id"] = recs[0]["Id"]

    # DLOs
    rdl = requests.get(f"{BASE_DC}/ssot/data-lake-objects?limit=100", headers=HDR)
    if rdl.ok:
        for dlo in rdl.json().get("dataLakeObjects", []):
            name = dlo.get("name", "")
            if name.upper().startswith(DC_PREFIX.upper()):
                assets["dlo_rest_ids"].append(dlo["id"])

    dc_count = len(assets["dsd_dev_names"]) + len(assets["dlo_rest_ids"]) + int(bool(assets["datasource_id"]))
    print(f"  {'✅' if dc_count else '—'} Data Cloud objects: {dc_count} found")
    if assets["dsd_dev_names"]:
        for n in assets["dsd_dev_names"]:
            print(f"       Stream: {n}")
    if assets["dlo_rest_ids"]:
        print(f"       DLOs: {len(assets['dlo_rest_ids'])}")
else:
    print(f"  —  Data Cloud: skipped")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY + CONFIRM
# ══════════════════════════════════════════════════════════════════════════════

total = (len(assets["dashboard_ids"]) + len(assets["viz_ids"]) +
         int(assets["sdm_exists"]) + int(assets["workspace_exists"]) +
         len(assets["dsd_dev_names"]) + len(assets["dlo_rest_ids"]) +
         int(bool(assets["datasource_id"])))

if total == 0:
    print("\n  ✅ Nothing to delete — the org is already clean for this demo.")
    sys.exit(0)

print(f"""
  ─────────────────────────────────────────────────────────
  Ready to permanently delete {total} asset(s):
""")
if assets["dashboard_ids"]:
    print(f"    • {len(assets['dashboard_ids'])} dashboard(s)")
    for _, label in assets["dashboard_ids"]:
        print(f"        – {label}")
if assets["viz_ids"]:
    print(f"    • {len(assets['viz_ids'])} visualization(s)")
    for _, label in assets["viz_ids"]:
        print(f"        – {label}")
if assets["sdm_exists"]:
    print(f"    • Semantic Data Model: {SDM_NAME}")
if assets["workspace_exists"]:
    print(f"    • Workspace: {WORKSPACE_NAME}")
if DC_PREFIX and any([assets["dsd_dev_names"], assets["dlo_rest_ids"], assets["datasource_id"]]):
    print(f"    • Data Cloud streams and data (prefix: {DC_PREFIX})")
print(f"""
  This cannot be undone.
  ─────────────────────────────────────────────────────────
""")

answer = ask("Type YES to delete everything, or press Enter to cancel")
if answer != "YES":
    print("\n  Cancelled. Nothing was deleted.")
    sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# DELETE
# ══════════════════════════════════════════════════════════════════════════════

print()
errors = []

# ── Step 1: Dashboards ────────────────────────────────────────────────────────
if assets["dashboard_ids"]:
    print(f"  [1/5] Deleting {len(assets['dashboard_ids'])} dashboard(s)...")
    for did, dlabel in assets["dashboard_ids"]:
        rd = requests.delete(f"{BASE_VIZ}/tableau/dashboards/{did}", headers=HDR)
        if rd.status_code in (200, 204):
            print(f"    ✅ {dlabel}")
        else:
            print(f"    ❌ {dlabel}: {rd.status_code}")
            errors.append(f"Dashboard {dlabel}: {rd.status_code}")
else:
    print("  [1/5] No dashboards — skipping")

# ── Step 2: Visualizations ────────────────────────────────────────────────────
if assets["viz_ids"]:
    print(f"  [2/5] Deleting {len(assets['viz_ids'])} visualization(s)...")
    for vid, vlabel in assets["viz_ids"]:
        rd = requests.delete(f"{BASE_VIZ}/tableau/visualizations/{vid}", headers=HDR)
        if rd.status_code in (200, 204):
            print(f"    ✅ {vlabel}")
        else:
            print(f"    ❌ {vlabel}: {rd.status_code}")
            errors.append(f"Visualization {vlabel}: {rd.status_code}")
else:
    print("  [2/5] No visualizations — skipping")

# ── Step 3: SDM ───────────────────────────────────────────────────────────────
if assets["sdm_exists"]:
    print(f"  [3/5] Deleting Semantic Data Model '{SDM_NAME}'...")
    rd = requests.delete(f"{BASE_SEM}/ssot/semantic/models/{SDM_NAME}", headers=HDR)
    if rd.status_code in (200, 204):
        print(f"    ✅ Semantic Model deleted")
    else:
        print(f"    ❌ {rd.status_code}: {rd.text[:200]}")
        errors.append(f"SDM: {rd.status_code}")
else:
    print("  [3/5] No Semantic Model — skipping")

# ── Step 4: Workspace ─────────────────────────────────────────────────────────
if assets["workspace_exists"]:
    print(f"  [4/5] Deleting workspace '{WORKSPACE_NAME}'...")
    rd = requests.delete(f"{BASE_SEM}/tableau/workspaces/{WORKSPACE_NAME}", headers=HDR)
    if rd.status_code in (200, 204):
        print(f"    ✅ Workspace deleted")
    else:
        print(f"    ❌ {rd.status_code}: {rd.text[:200]}")
        errors.append(f"Workspace: {rd.status_code}")
else:
    print("  [4/5] No workspace — skipping")

# ── Step 5: DC assets ─────────────────────────────────────────────────────────
if DC_PREFIX and any([assets["dsd_dev_names"], assets["datasource_id"], assets["dlo_rest_ids"]]):
    print(f"  [5/5] Removing Data Cloud objects...")

    # 4a — SOAP Metadata destructive deploy (removes streams + connector metadata)
    def soap_destructive_deploy(conn_full_name, short_name, dsd_dev_names):
        dsd_members  = "\n".join(f"        <members>{n}</members>" for n in dsd_dev_names) if dsd_dev_names else ""
        mdto_members = dsd_members
        types_xml = ""
        if dsd_members:
            types_xml += f"""    <types>\n{dsd_members}\n        <name>DataStreamDefinition</name>\n    </types>\n"""
            types_xml += f"""    <types>\n{mdto_members}\n        <name>MktDataTranObject</name>\n    </types>\n"""
        types_xml += f"""    <types>\n        <members>{conn_full_name}</members>\n        <name>ExternalDataConnector</name>\n    </types>\n"""
        types_xml += f"""    <types>\n        <members>{short_name}</members>\n        <name>DataConnectorIngestApi</name>\n    </types>\n"""

        destructive_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n{types_xml}</Package>"""
        empty_package = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>62.0</version>
</Package>"""

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("destructiveChanges.xml", destructive_xml)
            zf.writestr("package.xml", empty_package)
        zip_b64 = base64.b64encode(buf.getvalue()).decode()

        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:CallOptions/>
    <met:SessionHeader><met:sessionId>{sf_token}</met:sessionId></met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:deploy>
      <met:ZipFile>{zip_b64}</met:ZipFile>
      <met:DeployOptions>
        <met:singlePackage>true</met:singlePackage>
        <met:rollbackOnError>true</met:rollbackOnError>
      </met:DeployOptions>
    </met:deploy>
  </soapenv:Body>
</soapenv:Envelope>"""

        r = requests.post(f"{sf_instance}/services/Soap/m/62.0",
            headers={"Content-Type": "text/xml", "SOAPAction": "deploy"}, data=soap_body)
        match = re.search(r'<id>([^<]+)</id>', r.text)
        if not match:
            return False
        job_id = match.group(1)
        print(f"    Removing streams (this takes up to 3 minutes)...", end="", flush=True)
        for _ in range(36):
            time.sleep(5)
            rs = requests.get(f"{BASE_DC}/metadata/deployRequest/{job_id}?includeDetails=true", headers=HDR)
            result = rs.json().get("deployResult", {})
            state  = result.get("status", "Unknown")
            print(".", end="", flush=True)
            if state in ("Succeeded", "Failed", "Canceled"):
                print()
                if state != "Succeeded":
                    for fail in (result.get("details", {}).get("componentFailures") or []):
                        if isinstance(fail, dict):
                            print(f"    ⚠️  [{fail.get('componentType')}] {fail.get('fullName')}: {fail.get('problem')}")
                return state == "Succeeded"
        print()
        return False

    ok = soap_destructive_deploy(assets["conn_full_name"], DC_PREFIX, assets["dsd_dev_names"])
    print(f"    {'✅ Streams and connector metadata removed' if ok else '⚠️  Stream removal had errors — continuing'}")

    # 4b — DataSource
    if assets["datasource_id"]:
        rd = requests.delete(f"{BASE_DC}/tooling/sobjects/DataSource/{assets['datasource_id']}", headers=HDR)
        print(f"    {'✅ DataSource removed' if rd.status_code == 204 else '⚠️  DataSource: ' + str(rd.status_code)}")

    # 4c — DLOs
    if assets["dlo_rest_ids"]:
        dlo_ok = 0
        for rid in assets["dlo_rest_ids"]:
            rd = requests.delete(f"{BASE_DC}/ssot/data-lake-objects/{rid}", headers=HDR)
            if rd.status_code in (200, 204):
                dlo_ok += 1
        print(f"    {'✅' if dlo_ok == len(assets['dlo_rest_ids']) else '⚠️ '} DLOs removed: {dlo_ok}/{len(assets['dlo_rest_ids'])}")
else:
    print("  [5/5] No Data Cloud assets to remove — skipping")


# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════

# Remove from registry
remove_from_registry(WORKSPACE_NAME)

banner("Teardown Complete")
if errors:
    print(f"\n  ⚠️  Completed with {len(errors)} error(s):")
    for e in errors:
        print(f"     • {e}")
    print("\n  You may need to remove those items manually in the Salesforce UI.")
else:
    print(f"\n  ✅ All demo assets deleted successfully.")

print(f"""
  Workspace '{WORKSPACE_NAME}' has been removed from your org.

  To build a new demo, open Claude Code and type:

      /start-workshop
""")
