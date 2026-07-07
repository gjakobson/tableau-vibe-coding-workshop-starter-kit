#!/usr/bin/env python3
"""
next_setup.py
First-time setup for the Tableau Next Demo Builder.

Run this once per Salesforce org. It will:
  1. Walk you through creating a Connected App (UI steps)
  2. Run the OAuth flow to capture a refresh token (browser-based, automatic)
  3. Walk you through creating the IngestAPI connector (UI steps)
  4. Discover your connector IDs automatically
  5. Write next_config.json

Run: python3 next_setup.py
"""

import json
import os
import sys
import time
import threading
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

try:
    import requests
except ImportError:
    print("\n  ❌ Missing required package: requests")
    print("     Install it by running:\n")
    print("       pip3 install requests\n")
    print("     Then run this script again.")
    sys.exit(1)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "next_config.json")
CALLBACK_PORT = 8080
CALLBACK_URL  = f"http://localhost:{CALLBACK_PORT}/callback"


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def banner(title):
    width = 62
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")


def step(n, total, text):
    print(f"\n[Step {n}/{total}] {text}")
    print("─" * 50)


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else default


def pause(msg="Press Enter when done..."):
    input(f"\n  ▶  {msg}")


def test_sf_token(sf_instance, sf_token):
    r = requests.get(f"{sf_instance}/services/data/v62.0/",
                     headers={"Authorization": f"Bearer {sf_token}"})
    return r.ok


def get_dc_token(sf_instance, sf_token):
    r = requests.post(
        f"{sf_instance}/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":         "urn:salesforce:grant-type:external:cdp",
            "subject_token":      sf_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }
    )
    if r.ok:
        return r.json().get("access_token"), r.json().get("instance_url")
    return None, None


# ══════════════════════════════════════════════════════════════════════════════
# OAUTH — local callback server captures the authorization code automatically
# ══════════════════════════════════════════════════════════════════════════════

class _CallbackHandler(BaseHTTPRequestHandler):
    captured_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.captured_code = params["code"][0]
            body = b"<html><body><h2>Authorization successful!</h2><p>You can close this tab and return to the terminal.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        else:
            body = b"<html><body><h2>Authorization failed.</h2><p>No code received. Return to terminal.</p></body></html>"
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress server log noise


def run_oauth_flow(sf_login_url, client_id, client_secret):
    """Open browser for OAuth authorization, capture code via local server, exchange for tokens."""

    # Build auth URL
    auth_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  CALLBACK_URL,
        "prompt":        "login consent",
        "scope":         "cdp_ingest_api cdp_query_api api sfap_api refresh_token",
    })
    auth_url = f"{sf_login_url}/services/oauth2/authorize?{auth_params}"

    # Start local callback server in background thread
    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("\n  Opening your browser for Salesforce login...")
    print(f"  If the browser doesn't open, visit this URL:\n")
    print(f"  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait up to 120 seconds for the callback
    print("  Waiting for authorization (up to 2 minutes)...")
    for _ in range(120):
        time.sleep(1)
        if _CallbackHandler.captured_code:
            break
    server.server_close()

    if not _CallbackHandler.captured_code:
        print("\n  ❌ Timed out waiting for authorization. Run the script again.")
        sys.exit(1)

    code = _CallbackHandler.captured_code
    print("  ✅ Authorization code received.")

    # Exchange code for tokens
    r = requests.post(
        f"{sf_login_url}/services/oauth2/token",
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  CALLBACK_URL,
        }
    )
    if not r.ok:
        print(f"\n  ❌ Token exchange failed: {r.status_code} {r.text[:300]}")
        sys.exit(1)

    data          = r.json()
    sf_token      = data["access_token"]
    refresh_token = data.get("refresh_token")
    sf_instance   = data["instance_url"]

    if not refresh_token:
        print("\n  ❌ No refresh_token returned. Make sure your Connected App has")
        print("     'Perform requests at any time (refresh_token, offline_access)' scope enabled.")
        sys.exit(1)

    print("  ✅ Refresh token captured — this is stored permanently in next_config.json.")
    return sf_token, refresh_token, sf_instance


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTOR DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════

def discover_connector(sf_instance, sf_token, short_name):
    """Find connector SF ID and UUID name from the short connector name."""
    SF_HDRS = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
    BASE_SF = f"{sf_instance}/services/data/v62.0"

    r = requests.get(f"{BASE_SF}/ssot/connections",
                     headers=SF_HDRS, params={"connectorType": "IngestApi", "limit": 50})
    if not r.ok:
        return None, None

    for conn in r.json().get("connections", []):
        if conn.get("name", "").lower().startswith(short_name.lower()):
            return conn["id"], conn["name"]

    # Show available connectors to help the user
    all_conns = [c.get("name", "") for c in r.json().get("connections", [])
                 if "ingest" in c.get("connectorType", "").lower()]
    if all_conns:
        print(f"\n  Available IngestAPI connectors in your org:")
        for c in all_conns:
            print(f"    • {c}")

    return None, None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SETUP FLOW
# ══════════════════════════════════════════════════════════════════════════════

def main():
    banner("Tableau Next Demo Builder — First-Time Setup")
    print("""
  This script configures your Salesforce credentials so you can
  build Tableau Next demos end-to-end from the command line.

  You'll need:
    • Access to your Salesforce org as an administrator (or someone who can create Connected Apps)
    • Data Cloud enabled in your org
    • About 10–15 minutes

  Everything is saved to next_config.json in this folder.
  Run this script once — demo scripts will use it automatically.
""")

    # ── Check if already configured ─────────────────────────────────────────
    if os.path.exists(CONFIG_FILE):
        print("  ⚠️  next_config.json already exists.")
        choice = ask("Re-run setup and overwrite it? (yes/no)", default="no")
        if choice.lower() not in ("yes", "y"):
            print("\n  Setup cancelled. Your existing config is unchanged.")
            sys.exit(0)
        print()

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1 — Connected App
    # ═══════════════════════════════════════════════════════════════════════
    step(1, 4, "Create a Connected App in Salesforce Setup")

    print("""
  A Connected App gives this tool permission to call Salesforce
  and Data Cloud APIs on your behalf. You only create this once per org.

  ┌─────────────────────────────────────────────────────────┐
  │  IN YOUR SALESFORCE ORG — do the following:            │
  │                                                         │
  │  1. Go to Setup → search "App Manager" → click it      │
  │  2. Click "New Connected App" (top right)              │
  │  3. Fill in:                                            │
  │       Connected App Name: Tableau Next Demo Builder     │
  │       API Name:           Tableau_Next_Demo_Builder     │
  │       Contact Email:      your email address            │
  │                                                         │
  │  4. Under "API (Enable OAuth Settings)":               │
  │       ☑ Enable OAuth Settings                          │
  │       Callback URL: http://localhost:8080/callback      │
  │                                                         │
  │  5. Add these OAuth Scopes (click each → Add):         │
  │       • Access and manage your data (api)               │
  │       • Access Analytics REST API resources (sfap_api)  │
  │       • Manage user data via APIs (api)                 │
  │       • Perform requests at any time                    │
  │           (refresh_token, offline_access)               │
  │       • cdp_ingest_api                                  │
  │       • cdp_query_api                                   │
  │                                                         │
  │  6. Click Save → then Continue                         │
  │                                                         │
  │  7. Wait 2–10 minutes for the app to propagate         │
  │                                                         │
  │  8. Click "Manage Consumer Details" to reveal your     │
  │     Consumer Key and Consumer Secret                    │
  └─────────────────────────────────────────────────────────┘
""")

    pause("Press Enter once you have your Consumer Key and Consumer Secret ready...")

    sf_login_url = ask("Salesforce login URL", default="https://login.salesforce.com")
    client_id    = ask("Consumer Key (Client ID)")
    client_secret = ask("Consumer Secret (Client Secret)")

    if not client_id or not client_secret:
        print("\n  ❌ Client ID and Client Secret are required. Run the script again.")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2 — OAuth flow
    # ═══════════════════════════════════════════════════════════════════════
    step(2, 4, "Authorize the Connected App (browser will open automatically)")

    print("""
  Your browser will open to the Salesforce login page.
  Log in with your org credentials and click Allow when prompted.
  The browser will redirect to localhost and this script will
  capture your tokens automatically — nothing to copy or paste.
""")

    pause("Press Enter to open the browser...")
    sf_token, refresh_token, sf_instance = run_oauth_flow(sf_login_url, client_id, client_secret)

    print(f"\n  ✅ Connected to: {sf_instance}")

    # Test Data Cloud token exchange
    print("  Testing Data Cloud token exchange...")
    dc_token, dc_domain = get_dc_token(sf_instance, sf_token)
    if not dc_token:
        print("\n  ❌ Data Cloud token exchange failed.")
        print("     Make sure Data Cloud is enabled in your org and the Connected App")
        print("     has the cdp_ingest_api and cdp_query_api scopes.")
        sys.exit(1)
    print(f"  ✅ Data Cloud domain: {dc_domain}")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3 — IngestAPI connector
    # ═══════════════════════════════════════════════════════════════════════
    step(3, 4, "Create the IngestAPI Connector in Data Cloud Setup")

    print("""
  The IngestAPI connector is a one-time Data Cloud configuration.
  It's what lets this tool push synthetic data into Data Cloud.

  ┌─────────────────────────────────────────────────────────┐
  │  IN YOUR SALESFORCE ORG — do the following:            │
  │                                                         │
  │  1. Go to the App Launcher → open "Data Cloud"         │
  │                                                         │
  │  2. Click the gear icon (Setup) in the top right       │
  │                                                         │
  │  3. Under "Integrations", click "Ingest API"           │
  │                                                         │
  │  4. Click "New" to create a connector                  │
  │                                                         │
  │  5. Connector Name: tableau_next_demo                  │
  │     (use this exact name — lowercase, underscores)     │
  │                                                         │
  │  6. Click Save                                         │
  │                                                         │
  │  7. The connector will show as Active within           │
  │     a few seconds                                       │
  └─────────────────────────────────────────────────────────┘

  Note: If you already have an IngestAPI connector you want to
  reuse, you can enter its name below instead.
""")

    pause("Press Enter once the connector is created and Active...")

    connector_name = ask("Connector name", default="tableau_next_demo")

    # Auto-discover connector IDs
    print(f"\n  Discovering connector '{connector_name}' in your org...")
    SF_HDRS = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
    conn_sf_id, conn_uuid = discover_connector(sf_instance, sf_token, connector_name)

    if conn_sf_id:
        print(f"  ✅ Connector found:")
        print(f"     SF ID   : {conn_sf_id}")
        print(f"     UUID    : {conn_uuid}")
    else:
        print(f"\n  ⚠️  Connector '{connector_name}' not found yet.")
        print("     This can happen if the connector was just created — it may take a minute.")
        print("     The connector IDs will be auto-filled the first time you run a demo script.")
        conn_sf_id = ""
        conn_uuid  = ""

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 4 — Write config
    # ═══════════════════════════════════════════════════════════════════════
    step(4, 4, "Saving next_config.json")

    config = {
        "sf_login_url":            sf_login_url,
        "client_id":               client_id,
        "client_secret":           client_secret,
        "refresh_token":           refresh_token,
        "data_cloud_domain":       dc_domain,
        "ingestion_connector_name": connector_name,
        "connector_sf_id":         conn_sf_id,
        "connector_uuid_name":     conn_uuid,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n  ✅ Saved to: {CONFIG_FILE}")

    # ── Summary ─────────────────────────────────────────────────────────────
    banner("Setup Complete")
    print(f"""
  Your environment is ready. Here's what was configured:

    Salesforce org    : {sf_instance}
    Data Cloud domain : {dc_domain}
    Connector name    : {connector_name}
    Config file       : next_config.json

  ─────────────────────────────────────────────────────────

  To clean up a demo after use:

      /opt/homebrew/bin/python3.13 next_teardown.py

  ─────────────────────────────────────────────────────────

  IMPORTANT — keep next_config.json private.
  It contains your refresh token. Do not share it or commit
  it to a git repository.
""")


if __name__ == "__main__":
    main()
