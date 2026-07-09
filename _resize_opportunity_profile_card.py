from pathlib import Path

import requests
from auth_cli import get_sf_cli_tokens, load_next_config


DASHBOARD_NAME = "gabe_sales_pipeline_dashboard"
WIDGET_NAME = "ext_opportunity_profile_card"
TARGET_ROWSPAN = 34


def clean_widget(widget):
    cleaned = {k: v for k, v in widget.items() if k not in ("id", "status", "label")}
    if cleaned.get("type") == "extension":
        cleaned.pop("source", None)
    elif "source" in cleaned:
        cleaned["source"] = {
            k: v for k, v in cleaned["source"].items() if k not in ("label", "type")
        }
    return cleaned


cfg = load_next_config(Path("next_config.json"))
_, sf_token, sf_instance = get_sf_cli_tokens(cfg.get("target_org"))

sf_headers = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
base_viz = f"{sf_instance}/services/data/v66.0"

r = requests.get(f"{base_viz}/tableau/dashboards/{DASHBOARD_NAME}", headers=sf_headers)
r.raise_for_status()
dash = r.json()

widgets = {k: clean_widget(dict(v)) for k, v in dash["widgets"].items()}
cells = [{k: v for k, v in cell.items() if k != "id"} for cell in dash["layouts"][0]["pages"][0]["widgets"]]

found = False
for cell in cells:
    if cell.get("name") == WIDGET_NAME:
        old = cell.get("rowspan", 0)
        cell["rowspan"] = max(old, TARGET_ROWSPAN)
        found = True
        print(f"ROWSPAN_UPDATED: {old} -> {cell['rowspan']}")
        break

if not found:
    raise SystemExit(f"WIDGET_NOT_FOUND: {WIDGET_NAME}")

patch_payload = {
    "label": dash["label"],
    "name": dash["name"],
    "description": dash.get("description", ""),
    "workspaceIdOrApiName": dash["workspaceIdOrApiName"],
    "style": dash["style"],
    "widgets": widgets,
    "layouts": [
        {
            "name": dash["layouts"][0]["name"],
            "columnCount": dash["layouts"][0]["columnCount"],
            "rowHeight": dash["layouts"][0]["rowHeight"],
            "maxWidth": dash["layouts"][0]["maxWidth"],
            "pages": [
                {
                    "name": dash["layouts"][0]["pages"][0]["name"],
                    "label": dash["layouts"][0]["pages"][0]["label"],
                    "widgets": cells,
                }
            ],
            "style": dash["layouts"][0]["style"],
        }
    ],
}

patch_resp = requests.patch(
    f"{base_viz}/tableau/dashboards/{DASHBOARD_NAME}",
    headers=sf_headers,
    json=patch_payload,
)
patch_resp.raise_for_status()
print(f"PATCH_OK: {DASHBOARD_NAME}")
