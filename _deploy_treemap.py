import base64, io, json, re, requests, time, zipfile, warnings
warnings.filterwarnings('ignore')
from pathlib import Path

orgs = json.loads(Path("next_orgs.json").read_text())["orgs"]
cfg  = next(iter(orgs.values()))

r = requests.post(cfg["sf_login_url"] + "/services/oauth2/token", data={
    "grant_type": "refresh_token", "client_id": cfg["client_id"],
    "client_secret": cfg["client_secret"], "refresh_token": cfg["refresh_token"],
})
r.raise_for_status()
sf_token    = r.json()["access_token"]
sf_instance = r.json()["instance_url"]
SF_HDRS  = {"Authorization": f"Bearer {sf_token}", "Content-Type": "application/json"}
META_REST = sf_instance + "/services/data/v66.0"

COMPONENT_NAME = "salesCloudTreemap"
LWC_DIR        = Path("lwc") / COMPONENT_NAME
DASH_NAME      = "may_27_test_run"

# ── Deploy LWC + D3 ───────────────────────────────────────────────────────────
D3_URL  = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
D3_META = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<StaticResource xmlns="http://soap.sforce.com/2006/04/metadata">\n'
           '    <cacheControl>Public</cacheControl>\n'
           '    <contentType>application/javascript</contentType>\n'
           '</StaticResource>')

print("Fetching D3 from CDN...")
d3_js = requests.get(D3_URL).text
print(f"  D3 fetched ({len(d3_js) // 1024} KB)")

lwc_files = {
    f"{COMPONENT_NAME}.js":          (LWC_DIR / f"{COMPONENT_NAME}.js").read_text(),
    f"{COMPONENT_NAME}.html":        (LWC_DIR / f"{COMPONENT_NAME}.html").read_text(),
    f"{COMPONENT_NAME}.css":         (LWC_DIR / f"{COMPONENT_NAME}.css").read_text(),
    f"{COMPONENT_NAME}.js-meta.xml": (LWC_DIR / f"{COMPONENT_NAME}.js-meta.xml").read_text(),
}

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
    for fname, content in lwc_files.items():
        zf.writestr(f"lwc/{COMPONENT_NAME}/{fname}", content)
    zf.writestr("staticresources/d3.resource", d3_js)
    zf.writestr("staticresources/d3.resource-meta.xml", D3_META)
    zf.writestr("package.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        f'  <types><members>{COMPONENT_NAME}</members>'
        '<name>LightningComponentBundle</name></types>\n'
        '  <types><members>d3</members>'
        '<name>StaticResource</name></types>\n'
        '  <version>66.0</version>\n'
        '</Package>')
zip_b64 = base64.b64encode(buf.getvalue()).decode()

soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:CallOptions/>
    <met:SessionHeader><met:sessionId>{sf_token}</met:sessionId></met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:deploy>
      <met:ZipFile>{zip_b64}</met:ZipFile>
      <met:DeployOptions>
        <met:singlePackage>true</met:singlePackage>
        <met:rollbackOnError>true</met:rollbackOnError>
        <met:ignoreWarnings>true</met:ignoreWarnings>
      </met:DeployOptions>
    </met:deploy>
  </soapenv:Body>
</soapenv:Envelope>"""

r = requests.post(sf_instance + "/services/Soap/m/66.0",
    headers={"Content-Type": "text/xml", "SOAPAction": "deploy"}, data=soap_body)
match = re.search(r'<id>([^<]+)</id>', r.text)
if not match:
    print("Deploy failed to start:", r.text[:400])
    raise SystemExit(1)
job_id = match.group(1)
print(f"Deploy started: {job_id}")

state = ""
for _ in range(60):
    time.sleep(5)
    status_r = requests.get(f"{META_REST}/metadata/deployRequest/{job_id}?includeDetails=true", headers=SF_HDRS)
    status = status_r.json().get("deployResult", {})
    state  = status.get("status", "")
    done   = status.get("numberComponentsDeployed", 0)
    total  = status.get("numberComponentsTotal", 0)
    print(f"  {state} ({done}/{total})", end="\r")
    if state in ("Succeeded", "Failed", "Canceled"):
        print()
        break

if state != "Succeeded":
    for f in (status.get("details", {}).get("componentFailures") or []):
        print(f"  FAILURE: {f.get('fileName')} — {f.get('problem')}")
    raise SystemExit(1)
print(f"Deployed: {COMPONENT_NAME}")

# ── PATCH dashboard — add treemap below existing widgets ──────────────────────
resp = requests.get(f"{META_REST}/tableau/dashboards/{DASH_NAME}", headers=SF_HDRS)
resp.raise_for_status()
dash = resp.json()

# Find the bottom-most row currently occupied
existing_cells = dash["layouts"][0]["pages"][0]["widgets"]
max_row = max((c.get("row", 0) + c.get("rowspan", 0)) for c in existing_cells)
next_row = max_row + 1
print(f"  Existing dashboard bottom row: {max_row} — placing treemap at row {next_row}")

def clean_widget(w):
    w = {k: v for k, v in w.items() if k not in ("id", "status", "label")}
    if "source" in w:
        w["source"] = {k: v for k, v in w["source"].items() if k not in ("label", "type")}
    return w

widgets = {k: clean_widget(dict(w)) for k, w in dash["widgets"].items()}
cells   = [{k: v for k, v in c.items() if k != "id"} for c in existing_cells]

# Treemap extension widget — NO "source" field (pitfall #60)
widgets["treemap_ext"] = {
    "actions": [],
    "componentType": "Custom",
    "name": "treemap_ext",
    "parameters": {
        "fullyQualifiedName": "c:salesCloudTreemap",
        "properties": {
            "sdmName":      "New_Semantic_Model_818",
            "sdoName":      "Opportunity1",
            "dimField":     "Opportunity_Stage1",
            "measureField": "Total_Amount",
            "queryLimit":   500,
        }
    },
    "type": "extension"
}
cells.append({"name": "treemap_ext", "column": 1, "row": next_row, "colspan": 70, "rowspan": 24})

layout = dash["layouts"][0]
resp = requests.patch(f"{META_REST}/tableau/dashboards/{DASH_NAME}", headers=SF_HDRS, json={
    "label":                dash["label"],
    "name":                 dash["name"],
    "description":          dash.get("description", ""),
    "workspaceIdOrApiName": dash["workspaceIdOrApiName"],
    "style":                dash["style"],
    "widgets":              widgets,
    "layouts": [{
        "name":        layout["name"],
        "columnCount": layout["columnCount"],
        "rowHeight":   layout["rowHeight"],
        "maxWidth":    layout["maxWidth"],
        "pages": [{
            "name":    layout["pages"][0]["name"],
            "label":   layout["pages"][0]["label"],
            "widgets": cells,
        }],
        "style": layout["style"],
    }],
})

if resp.ok:
    print("  ✅ Treemap added to dashboard")
else:
    print(f"  ❌ PATCH failed: {resp.status_code} {resp.text[:400]}")
