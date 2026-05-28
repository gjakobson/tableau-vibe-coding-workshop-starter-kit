#!/usr/bin/env python3
"""
next_auth.py
Run once to authorize your Connected App and save credentials to next_orgs.json.
Usage: python3 next_auth.py
"""
import base64, hashlib, json, os, secrets, sys, webbrowser, urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: pip3 install requests")
    sys.exit(1)

_DIR         = os.path.dirname(os.path.abspath(__file__))
ORGS_FILE    = os.path.join(_DIR, "next_orgs.json")
CONFIG_FILE  = os.path.join(_DIR, "next_config.json")   # legacy fallback
CALLBACK_URL = "https://login.salesforce.com/services/oauth2/success"


def pkce_pair():
    verifier  = secrets.token_urlsafe(64)
    digest    = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def load_or_prompt_config():
    """Load existing config or prompt the user for the minimum fields needed."""
    # Try next_orgs.json first (current format)
    if os.path.exists(ORGS_FILE):
        orgs = json.loads(Path(ORGS_FILE).read_text()).get("orgs", {})
        if orgs:
            if len(orgs) == 1:
                org_name = next(iter(orgs))
                print(f"Found credentials for: {org_name}")
                return org_name, orgs[org_name], orgs
            # Multiple orgs — ask which one to re-auth
            names = list(orgs.keys())
            print("Multiple orgs found:")
            for i, n in enumerate(names, 1):
                print(f"  {i}. {n}")
            choice = input("Which org to re-authorize? (number or name, or press Enter for first): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(names):
                org_name = names[int(choice) - 1]
            elif choice in orgs:
                org_name = choice
            else:
                org_name = names[0]
            return org_name, orgs[org_name], orgs

    # Try legacy next_config.json
    if os.path.exists(CONFIG_FILE):
        cfg = json.loads(Path(CONFIG_FILE).read_text())
        return "default", cfg, None

    # No config at all — prompt for the essentials
    print("\nNo credentials file found. Let's set up your workshop org.\n")
    print("You'll need your Connected App credentials from Salesforce Setup → App Manager.\n")

    sf_login_url = input(
        "Salesforce login URL (My Domain URL, e.g. https://orgfarm-xxxxxxxxxx.my.salesforce.com): "
    ).strip().rstrip("/")
    if not sf_login_url:
        sf_login_url = "https://login.salesforce.com"

    client_id = input("Connected App Client ID (Consumer Key, ~100 chars): ").strip()
    if not client_id:
        print("Client ID is required. Exiting.")
        sys.exit(1)

    client_secret = input("Connected App Client Secret (64-char hex): ").strip()
    if not client_secret:
        print("Client Secret is required. Exiting.")
        sys.exit(1)

    org_name = input("Friendly name for this org (e.g. 'Workshop Org'): ").strip() or "Workshop Org"

    data_cloud_domain = input(
        "Data Cloud domain (e.g. m-xxxxxxxxxxxxxxxxxxxxxxxxxx.c360a.salesforce.com, no https://): "
    ).strip().lstrip("https://").lstrip("http://").rstrip("/")

    cfg = {
        "sf_login_url":      sf_login_url,
        "client_id":         client_id,
        "client_secret":     client_secret,
        "refresh_token":     "",
        "data_cloud_domain": data_cloud_domain,
    }
    return org_name, cfg, None


def main():
    org_name, cfg, existing_orgs = load_or_prompt_config()

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

    print("After you authorize, the browser redirects to a page that says 'Authorization Successful'.")
    print("Look at the URL — it contains '?code=...'")
    print("Copy everything after '?code=' and before any '&' character.\n")

    code = input("Paste the authorization code here: ").strip()
    if not code:
        print("No code entered. Exiting.")
        sys.exit(1)

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
        print("No refresh_token returned. Make sure your Connected App has 'refresh_token, offline_access' scope.")
        sys.exit(1)

    print(f"Connected to: {sf_instance}")

    # Test Data Cloud token exchange
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
    print("Data Cloud auth: OK")

    # Save updated credentials to next_orgs.json
    cfg["refresh_token"] = refresh_token

    if existing_orgs is not None:
        existing_orgs[org_name] = cfg
        orgs_data = {"orgs": existing_orgs}
    else:
        orgs_data = {"orgs": {org_name: cfg}}

    Path(ORGS_FILE).write_text(json.dumps(orgs_data, indent=2))
    print(f"\nCredentials saved to next_orgs.json  (org: {org_name})")
    print("You're ready — run /start-workshop in Claude Code to begin.")


if __name__ == "__main__":
    main()
