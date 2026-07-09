#!/usr/bin/env python3
"""Authenticate workshop org via Salesforce CLI."""

import json
import subprocess
import sys
from pathlib import Path

from auth_cli import exchange_dc_token, get_sf_cli_tokens


CONFIG_FILE = Path(__file__).with_name("next_config.json")


def main():
    target_org = input("Salesforce CLI org alias (press Enter for default): ").strip() or None

    if not target_org:
        print("\nLogging in with Salesforce CLI...")
        subprocess.run(["sf", "org", "login", "web", "--alias", "workshop"], check=True)
        target_org = "workshop"

    alias, sf_token, sf_instance = get_sf_cli_tokens(target_org)
    dc_domain = ""
    try:
        _, dc_domain = exchange_dc_token(sf_instance, sf_token)
    except Exception as exc:
        print(f"Data Cloud auth not available (non-blocking): {exc}")
        print("Continuing with Salesforce-only setup.")

    cfg = {}
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
    cfg["target_org"] = alias
    if dc_domain:
        cfg["data_cloud_domain"] = dc_domain
    cfg.setdefault("ingestion_connector_name", "tableau_next_demo")
    cfg.setdefault("connector_sf_id", "")
    cfg.setdefault("connector_uuid_name", "")
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

    print(f"\nConnected to org alias: {alias}")
    print(f"Salesforce instance: {sf_instance}")
    if dc_domain:
        print(f"Data Cloud domain: {dc_domain}")
    else:
        print("Data Cloud domain: not configured")
    print(f"Saved: {CONFIG_FILE.name}")
    print("You're ready — run /start-workshop in Claude Code to begin.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"\nSalesforce CLI command failed: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nAuthentication failed: {exc}")
        sys.exit(1)
