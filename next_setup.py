#!/usr/bin/env python3
"""Workshop setup using Salesforce CLI authentication."""

import json
import sys
from pathlib import Path

import requests

from auth_cli import exchange_dc_token, get_sf_cli_tokens, load_next_config


CONFIG_FILE = Path(__file__).with_name("next_config.json")


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else default


def discover_connector(sf_instance, sf_token, short_name):
    hdr = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
    base = f"{sf_instance}/services/data/v62.0"
    r = requests.get(f"{base}/ssot/connections", headers=hdr, params={"connectorType": "IngestApi", "limit": 50}, timeout=30)
    r.raise_for_status()
    for conn in r.json().get("connections", []):
        if conn.get("name", "").lower().startswith(short_name.lower()):
            return conn["id"], conn["name"]
    return "", ""


def main():
    print("\nTableau Next Demo Builder — CLI Setup\n")
    print("1) Log in with Salesforce CLI")
    print("2) Verify Data Cloud token exchange")
    print("3) Save workshop config to next_config.json\n")

    alias = ask("Salesforce CLI org alias to use", default="workshop")
    print(f"\nIf not already logged in, run: sf org login web --alias {alias}\n")
    input("Press Enter after login is complete...")

    alias, sf_token, sf_instance = get_sf_cli_tokens(alias)
    _, dc_domain = exchange_dc_token(sf_instance, sf_token)

    connector_name = ask("Ingest API connector name", default="tableau_next_demo")
    conn_sf_id, conn_uuid = discover_connector(sf_instance, sf_token, connector_name)

    cfg = load_next_config(CONFIG_FILE)
    cfg["target_org"] = alias
    cfg["data_cloud_domain"] = dc_domain
    cfg["ingestion_connector_name"] = connector_name
    cfg["connector_sf_id"] = conn_sf_id
    cfg["connector_uuid_name"] = conn_uuid
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

    print("\nSetup complete.")
    print(f"- Org alias: {alias}")
    print(f"- Salesforce instance: {sf_instance}")
    print(f"- Data Cloud domain: {dc_domain}")
    print(f"- Connector SF ID: {conn_sf_id or '(not found yet)'}")
    print(f"- Saved: {CONFIG_FILE.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nSetup failed: {exc}")
        sys.exit(1)
