"""Inspect one semantic model (SDOs, calc fields, metrics). Auth via Salesforce CLI.

Usage: python3 _inspect_model.py <model_api_name>
Get the apiName from _list_models.py. No default model is hardcoded on purpose —
the model must come from discovery (never assume WorkshopModel).
"""
import json
import subprocess
import sys
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


res = sf_json(["org", "display", "--target-org", target_org]) \
    or sf_json(["force", "org", "display", "--target-org", target_org, "--verbose"])
if not res or not res.get("accessToken"):
    raise SystemExit(f"SF_AUTH_FAILED: org alias '{target_org}' not logged in — run: sf org login web --alias {target_org}")

sf_hdrs = {"Authorization": "Bearer " + res["accessToken"], "Content-Type": "application/json"}
base_sem = res["instanceUrl"] + "/services/data/v65.0"

if len(sys.argv) < 2 or not sys.argv[1].strip():
    raise SystemExit("USAGE: python3 _inspect_model.py <model_api_name>   (get it from _list_models.py)")
model_api_name = sys.argv[1].strip()
print("INSPECTING_MODEL:", model_api_name)

r = requests.get(base_sem + "/ssot/semantic/models/" + model_api_name, headers=sf_hdrs, params={"includeModelContent": True})
r.raise_for_status()
m = r.json()

print("=== DATA OBJECTS ===")
for sdo in m.get("semanticDataObjects", []):
    print("  " + sdo.get("label", "") + " (" + sdo.get("apiName", "") + ")")
    print("    Dimensions:  " + str([f.get("label", "") for f in sdo.get("semanticDimensions", [])]))
    print("    Measures:    " + str([f.get("label", "") for f in sdo.get("semanticMeasurements", [])]))

print("\n=== CALCULATED FIELDS ===")
for c in m.get("semanticCalculatedMeasurements", []):
    print("  [Measure] " + c.get("label", "") + " — " + (c.get("description", "") or "")[:80])
for c in m.get("semanticCalculatedDimensions", []):
    print("  [Dimension] " + c.get("label", "") + " — " + (c.get("description", "") or "")[:80])

print("\n=== METRICS ===")
r2 = requests.get(base_sem + "/ssot/semantic/models/" + model_api_name + "/metrics", headers=sf_hdrs)
r2.raise_for_status()
for met in r2.json().get("metrics", []):
    print("  " + met.get("label", "") + " (" + met.get("apiName", "") + ")  type=" + str(met.get("aggregationType", "")))
