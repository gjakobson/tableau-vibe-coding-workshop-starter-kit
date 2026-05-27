import json, requests, warnings, zipfile, io, base64, textwrap
warnings.filterwarnings('ignore')
from pathlib import Path

cfg = json.loads(Path("next_config.json").read_text())
r = requests.post(cfg["sf_login_url"] + "/services/oauth2/token", data={
    "grant_type": "refresh_token", "client_id": cfg["client_id"],
    "client_secret": cfg["client_secret"], "refresh_token": cfg["refresh_token"],
})
r.raise_for_status()
sf_token    = r.json()["access_token"]
sf_instance = r.json()["instance_url"]
print("SF instance:", sf_instance)

# ── Build zip ──────────────────────────────────────────────────────────────────
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

    # Package manifest
    zf.writestr("package.xml", textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <Package xmlns="http://soap.sforce.com/2006/04/metadata">
            <types>
                <members>gabesDealScatter</members>
                <name>LightningComponentBundle</name>
            </types>
            <types>
                <members>d3</members>
                <name>StaticResource</name>
            </types>
            <version>66.0</version>
        </Package>
    """))

    # LWC files
    lwc_base = Path("force-app/main/default/lwc/gabesDealScatter")
    for f in lwc_base.iterdir():
        zf.write(f, f"lwc/gabesDealScatter/{f.name}")

    # Static resource — d3 (reuse existing)
    d3_js = Path("force-app/main/default/staticresources/d3.js")
    if not d3_js.exists():
        print("Downloading D3 v7.9.0 ...")
        resp = requests.get("https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js")
        resp.raise_for_status()
        d3_js.write_bytes(resp.content)
        print(f"  Downloaded {len(resp.content):,} bytes")

    zf.write(d3_js, "staticresources/d3.resource")
    zf.writestr("staticresources/d3.resource-meta.xml", textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <StaticResource xmlns="http://soap.sforce.com/2006/04/metadata">
            <cacheControl>Public</cacheControl>
            <contentType>application/javascript</contentType>
        </StaticResource>
    """))

zip_b64 = base64.b64encode(buf.getvalue()).decode()
print(f"Zip size: {len(buf.getvalue()):,} bytes")

# ── Deploy via Metadata SOAP API ───────────────────────────────────────────────
SOAP_ENDPOINT = f"{sf_instance}/services/Soap/m/62.0"
SOAP_DEPLOY = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:CallOptions><met:client>deploy-script</met:client></met:CallOptions>
    <met:SessionHeader><met:sessionId>{sf_token}</met:sessionId></met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:deploy>
      <met:ZipFile>{zip_b64}</met:ZipFile>
      <met:DeployOptions>
        <met:allowMissingFiles>false</met:allowMissingFiles>
        <met:autoUpdatePackage>false</met:autoUpdatePackage>
        <met:checkOnly>false</met:checkOnly>
        <met:ignoreWarnings>true</met:ignoreWarnings>
        <met:performRetrieve>false</met:performRetrieve>
        <met:purgeOnDelete>false</met:purgeOnDelete>
        <met:rollbackOnError>true</met:rollbackOnError>
        <met:runAllTests>false</met:runAllTests>
        <met:singlePackage>true</met:singlePackage>
      </met:DeployOptions>
    </met:deploy>
  </soapenv:Body>
</soapenv:Envelope>"""

resp = requests.post(SOAP_ENDPOINT,
    headers={"Content-Type": "text/xml", "SOAPAction": "deploy"},
    data=SOAP_DEPLOY.encode("utf-8"), verify=False)
resp.raise_for_status()

import re
job_id = re.search(r"<id>(.*?)</id>", resp.text)
if not job_id:
    print("ERROR: no job id in response:", resp.text[:500])
    exit(1)
job_id = job_id.group(1)
print(f"Deploy job: {job_id}")

# ── Poll ───────────────────────────────────────────────────────────────────────
import time
CHECK_TMPL = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:SessionHeader><met:sessionId>{token}</met:sessionId></met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:checkDeployStatus>
      <met:asyncProcessId>{job_id}</met:asyncProcessId>
      <met:includeDetails>true</met:includeDetails>
    </met:checkDeployStatus>
  </soapenv:Body>
</soapenv:Envelope>"""

for attempt in range(30):
    time.sleep(5)
    cr = requests.post(SOAP_ENDPOINT,
        headers={"Content-Type": "text/xml", "SOAPAction": "checkDeployStatus"},
        data=CHECK_TMPL.format(token=sf_token, job_id=job_id).encode(), verify=False)
    done  = re.search(r"<done>(.*?)</done>",   cr.text)
    state = re.search(r"<status>(.*?)</status>", cr.text)
    done_val  = done.group(1)  if done  else "?"
    state_val = state.group(1) if state else "?"
    print(f"  [{attempt+1}] done={done_val} status={state_val}")
    if done_val == "true":
        success = re.search(r"<success>(.*?)</success>", cr.text)
        if success and success.group(1) == "true":
            print("  ✅ Deploy succeeded!")
        else:
            errs = re.findall(r"<problem>(.*?)</problem>", cr.text)
            print("  ❌ Deploy failed:", errs[:5])
        break
