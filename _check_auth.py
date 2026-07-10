import json
import subprocess
from pathlib import Path

import requests

cfg = json.loads(Path("next_config.json").read_text()) if Path("next_config.json").exists() else {}
target_org = cfg.get("target_org", "workshop")


def sf_json(args):
    """Run `sf ... --json` and return result dict, or None on failure."""
    p = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout).get("result")
    except Exception:
        return None


# `sf org display --json` returns BOTH accessToken and instanceUrl on modern CLI.
# Do NOT use `sf org auth show-access-token` — it does not exist on many CLI
# versions and returns a nonzero exit, which is easily mistaken for "not logged
# in" when the org is actually authenticated. Fall back to the legacy
# `force org display --verbose` surface only if the modern command fails.
res = sf_json(["org", "display", "--target-org", target_org]) \
    or sf_json(["force", "org", "display", "--target-org", target_org, "--verbose"])

if not res or not res.get("accessToken") or not res.get("instanceUrl"):
    # Genuine failure: the alias is not connected / has no live token.
    print(f"SF_AUTH_FAILED: org alias '{target_org}' is not logged in — run: sf org login web --alias {target_org}")
    raise SystemExit(0)

sf_token = res["accessToken"]
sf_instance = res["instanceUrl"]

r2 = requests.post(
    sf_instance + "/services/a360/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "grant_type": "urn:salesforce:grant-type:external:cdp",
        "subject_token": sf_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    },
)
if not r2.ok:
    print("AUTH_OK_NO_DC: " + sf_instance + " (Data Cloud scope unavailable)")
else:
    print("AUTH_OK: " + sf_instance)
