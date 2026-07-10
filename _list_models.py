"""List semantic models in the target org. Auth via Salesforce CLI (no secrets on disk)."""
import json
import subprocess
import warnings
from pathlib import Path

import requests

warnings.filterwarnings("ignore")

cfg = json.loads(Path("next_config.json").read_text()) if Path("next_config.json").exists() else {}
target_org = cfg.get("target_org", "workshop")


def sf_json(args):
    p = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout).get("result")
    except Exception:
        return None


# `sf org display --json` returns accessToken + instanceUrl (see _check_auth.py note).
res = sf_json(["org", "display", "--target-org", target_org]) \
    or sf_json(["force", "org", "display", "--target-org", target_org, "--verbose"])
if not res or not res.get("accessToken"):
    raise SystemExit(f"SF_AUTH_FAILED: org alias '{target_org}' not logged in — run: sf org login web --alias {target_org}")

sf_hdrs = {"Authorization": "Bearer " + res["accessToken"], "Content-Type": "application/json"}
base_sem = res["instanceUrl"] + "/services/data/v65.0"

r = requests.get(base_sem + "/ssot/semantic/models", headers=sf_hdrs, params={"limit": 50})
r.raise_for_status()
data = r.json()
models = data.get("items", data.get("semanticModels", data.get("records", [])))
if not models:
    print("NO_MODELS")
else:
    for i, m in enumerate(models, 1):
        label = m.get("label", "")
        api = m.get("apiName", "")
        desc = (m.get("description", "") or "")[:80]
        print(f"{i}. {label}  [{api}]  — {desc}")
