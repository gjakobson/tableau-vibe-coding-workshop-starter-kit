#!/usr/bin/env python3
"""
next_auth.py
Re-authorize your Connected App and update next_config.json with a fresh refresh token.
Run once from a terminal: python3 next_auth.py
"""
import base64, hashlib, json, os, secrets, sys, webbrowser, urllib.parse

try:
    import requests
except ImportError:
    print("Missing: pip3 install requests")
    sys.exit(1)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "next_config.json")
CALLBACK_URL = "https://login.salesforce.com/services/oauth2/success"


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def main():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)

    sf_login_url  = cfg["sf_login_url"]
    client_id     = cfg["client_id"]
    client_secret = cfg["client_secret"]

    code_verifier, code_challenge = pkce_pair()

    auth_url = (
        f"{sf_login_url}/services/oauth2/authorize?"
        + urllib.parse.urlencode({
            "response_type":         "code",
            "client_id":             client_id,
            "redirect_uri":          CALLBACK_URL,
            "prompt":                "login consent",
            "scope":                 "cdp_ingest_api cdp_query_api full sfap_api refresh_token",
            "code_challenge":        code_challenge,
            "code_challenge_method": "S256",
        })
    )

    print("\nOpening browser for Salesforce login...")
    print("If the browser doesn't open, visit:\n")
    print(f"  {auth_url}\n")
    webbrowser.open(auth_url)

    print("After you log in and authorize, the browser will redirect to a page that says")
    print("'Authorization Successful'. Look at the URL bar — it will contain '?code=...'")
    print("Copy everything after '?code=' and before any '&' character.\n")

    code = input("Paste the code here: ").strip()
    if not code:
        print("No code entered. Exiting.")
        sys.exit(1)

    # URL-decode the code in case the user copied it encoded
    code = urllib.parse.unquote(code)

    print("\nExchanging code for tokens...")
    r = requests.post(f"{sf_login_url}/services/oauth2/token", data={
        "grant_type":    "authorization_code",
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  CALLBACK_URL,
        "code_verifier": code_verifier,
    })
    if not r.ok:
        print(f"Token exchange failed: {r.status_code} {r.text[:300]}")
        sys.exit(1)

    data          = r.json()
    refresh_token = data.get("refresh_token")
    sf_token      = data["access_token"]
    sf_instance   = data["instance_url"]

    if not refresh_token:
        print("No refresh_token returned. Make sure your Connected App has 'refresh_token' scope.")
        sys.exit(1)

    print(f"Connected to: {sf_instance}")

    # Test Data Cloud
    r2 = requests.post(f"{sf_instance}/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":         "urn:salesforce:grant-type:external:cdp",
            "subject_token":      sf_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }
    )
    if not r2.ok:
        print(f"Data Cloud token exchange failed: {r2.status_code} {r2.text[:300]}")
        sys.exit(1)
    print("Data Cloud auth OK")

    # Discover connector
    hdrs = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
    r3 = requests.get(f"{sf_instance}/services/data/v62.0/ssot/connections",
        headers=hdrs, params={"connectorType": "IngestApi", "limit": 50})
    conn_sf_id, conn_uuid = "", ""
    if r3.ok:
        for conn in r3.json().get("connections", []):
            if conn.get("name", "").lower().startswith(cfg["ingestion_connector_name"].lower()):
                conn_sf_id = conn["id"]
                conn_uuid  = conn["name"]
                print(f"Connector found: {conn_uuid}")
                break
        if not conn_sf_id:
            names = [c.get("name") for c in r3.json().get("connections", [])]
            print(f"Connector '{cfg['ingestion_connector_name']}' not found. Available: {names}")

    # Update config
    cfg["refresh_token"]       = refresh_token
    cfg["connector_sf_id"]     = conn_sf_id
    cfg["connector_uuid_name"] = conn_uuid
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

    print("\nSetup complete. next_config.json updated.")
    if not conn_sf_id:
        print("\nNext: create the IngestAPI connector in Data Cloud Setup (name it 'tableau_next_demo'), then re-run this script.")
    else:
        print("You're ready to run /start-workshop")


if __name__ == "__main__":
    main()
