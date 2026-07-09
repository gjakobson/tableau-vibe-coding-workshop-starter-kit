#!/usr/bin/env python3
"""Shared Salesforce CLI authentication helpers for workshop scripts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import requests


def run_sf_json(args: list[str]) -> dict:
    """Run an sf CLI command and parse JSON output."""
    proc = subprocess.run(
        ["sf", *args, "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "sf command failed")
    return json.loads(proc.stdout)


def get_sf_cli_tokens(target_org: str | None = None) -> tuple[str, str, str]:
    """Return (alias, sf_access_token, instance_url) from Salesforce CLI auth."""
    alias = target_org
    if not alias:
        org = run_sf_json(["org", "display"])
        alias = org.get("result", {}).get("alias") or org.get("result", {}).get("username")
    if not alias:
        raise RuntimeError("No target org configured. Run `sf org login web --alias <alias>` first.")

    try:
        token = run_sf_json(["org", "auth", "show-access-token", "--target-org", alias])
    except Exception:
        # Fallback for CLI variants where this command is unavailable.
        token = run_sf_json(["force", "org", "display", "--target-org", alias, "--verbose"])
    details = run_sf_json(["org", "display", "--target-org", alias])

    sf_token = token.get("result", {}).get("accessToken")
    instance_url = details.get("result", {}).get("instanceUrl")
    if not sf_token or not instance_url:
        raise RuntimeError(f"Unable to read token or instance URL for org alias '{alias}'.")
    return alias, sf_token, instance_url


def exchange_dc_token(sf_instance: str, sf_token: str) -> tuple[str, str]:
    """Exchange Salesforce access token for Data Cloud token."""
    r = requests.post(
        f"{sf_instance}/services/a360/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:salesforce:grant-type:external:cdp",
            "subject_token": sf_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    return body["access_token"], body["instance_url"]


def load_next_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text())
