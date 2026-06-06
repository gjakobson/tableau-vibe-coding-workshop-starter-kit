# Reference: Custom Viz Extensions (STEP VIZ-EXT — LWC + D3)

Read this file when the user wants a chart type not available natively in Tableau Next (sunburst, beeswarm, radar, funnel, gauge, treemap, hexbin map, bullet chart).

---

## VIZ-EXT-a — Ask what chart type and what data

> "What kind of chart would you like?
>
> - **Sunburst** — hierarchical part-of-whole (e.g. pipeline by stage → product)
> - **Beeswarm** — distribution of individual deals/accounts along a measure
> - **Radar / Spider** — compare multiple metrics across categories
> - **Funnel** — conversion rates across stages
> - **Gauge** — single KPI vs. target
> - **Treemap** — relative size of categories
> - **Bullet chart** — KPI vs. target vs. range
>
> Or describe what you want and I'll pick the right type.
> Which fields from the semantic model should it use?"

Wait for the user's reply before proceeding.

---

## VIZ-EXT-b — Generate the LWC files

Component name convention: `{userSlug}{ChartType}` (e.g. `gabeTreemap`, `firstMeridianSunburst`).

Use **Option A** (filter-aware) by default. Use **Option B** only for standalone snapshots.

```javascript
// Option A — registerFieldsForQuery (filter-aware, recommended)
// CRITICAL: use sdk.on(), NOT sdk.addEventListener() — addEventListener doesn't exist on SDK
// CRITICAL: dataUpdate callback receives rows as a plain array, NOT an event object
async _initialize() {
    if (!this.sdk) return;
    await loadScript(this, D3);
    this.sdk.on("filterChange", () => { this.sdk.fetchData(); });
    this.sdk.on("dataUpdate", (rows) => {          // rows = plain array
        this._data = Array.isArray(rows) ? rows : [];
        this.renderChart();
    });
    // Fields MUST be "SdoApiName.rawFieldApiName" — calc measurements cannot be used
    // Dimensions: rowGrouping: true | Measures: aggregationType: "SUM"
    // rowGrouping: false on a measure returns no value (silent empty data)
    const fields = [
        { model: `${this._sdoName}.${this._dimField}`,     rowGrouping: true },
        { model: `${this._sdoName}.${this._measureField}`, aggregationType: "SUM" }
    ];
    this.sdk.registerFieldsForQuery(fields, this._sdmName, { limit: this._queryLimit });
    this.sdk.fetchData();
}

// Option B — fetchDataUsingQueryAndSource (one-shot, no filter wiring)
async loadData() {
    const rows = await this.sdk.fetchDataUsingQueryAndSource(
        { queryFields: [{ name: this._dimField, dataType: "string" },
                        { name: this._measureField, dataType: "real" }] },
        this._sdmName
    );
    this._data = rows;
    this.renderChart();
}
```

**File 1 — `{componentName}.js`:**
```javascript
import { LightningElement, api } from "lwc";
import { loadScript } from "lightning/platformResourceLoader";
import D3 from "@salesforce/resourceUrl/d3";

export default class {ComponentName} extends LightningElement {
    @api sdk;

    _sdmName = "{model_api_name}";
    @api get sdmName() { return this._sdmName; }
    set sdmName(v) { if (v) { this._sdmName = v; } }

    _sdoName = "{sdo_api_name}";
    @api get sdoName() { return this._sdoName; }
    set sdoName(v) { if (v) { this._sdoName = v; } }

    _dimField = "{dim_field_api_name}";
    @api get dimField() { return this._dimField; }
    set dimField(v) { if (v) { this._dimField = v; } }

    _measureField = "{measure_field_api_name}";
    @api get measureField() { return this._measureField; }
    set measureField(v) { if (v) { this._measureField = v; } }

    _queryLimit = 500;
    @api get queryLimit() { return this._queryLimit; }
    set queryLimit(v) { if (v) { this._queryLimit = parseInt(v, 10); } }

    _d3Loaded = false;
    _data = [];
    _unsubscribes = [];

    connectedCallback() { this._initialize(); }

    disconnectedCallback() {
        this._unsubscribes.forEach(fn => typeof fn === "function" && fn());
        this._unsubscribes = [];
    }

    async _initialize() {
        if (!this.sdk) { console.error("[{componentName}] sdk not available"); return; }
        await loadScript(this, D3);
        this._d3Loaded = true;
        this._unsubscribes.push(this.sdk.on("filterChange", () => { this.sdk.fetchData(); }));
        this._unsubscribes.push(this.sdk.on("dataUpdate", (rows) => {
            this._data = Array.isArray(rows) ? rows : [];
            this.renderChart();
        }));
        const fields = [
            { model: `${this._sdoName}.${this._dimField}`,     rowGrouping: true },
            { model: `${this._sdoName}.${this._measureField}`, aggregationType: "SUM" }
        ];
        this.sdk.registerFieldsForQuery(fields, this._sdmName, { limit: this._queryLimit });
        this.sdk.fetchData();
    }

    renderChart() {
        const container = this.template.querySelector(".chart-container");
        if (!container || !this._d3Loaded || !this._data.length) return;
        const W = container.clientWidth  || 400;
        const H = container.clientHeight || 300;
        if (W <= 0 || H <= 0) { setTimeout(() => this.renderChart(), 100); return; }
        const d3 = window.d3;  // loadScript puts D3 on window
        // Rows are positional: row[0] = dim, row[1] = measure
        // D3 chart code here
    }
}
```

**File 2 — `{componentName}.html`:**
```html
<template>
    <div class="chart-container" style="width:100%;height:100%;"></div>
</template>
```

**File 3 — `{componentName}.css`:**
```css
.chart-container { width: 100%; height: 100%; overflow: hidden; }
```

**File 4 — `{componentName}.js-meta.xml`:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>{Human Readable Label}</masterLabel>
    <targets><target>analytics__Dashboard</target></targets>
    <targetConfigs>
        <targetConfig targets="analytics__Dashboard">
            <property name="sdmName"      type="String"  label="Semantic Model Name" default="{model_api_name}" />
            <property name="dimField"     type="String"  label="Dimension Field"     default="{dim_field_api_name}" />
            <property name="measureField" type="String"  label="Measure Field"       default="{measure_field_api_name}" />
            <property name="queryLimit"   type="Integer" label="Query Limit"         default="500" />
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

Write files to: `force-app/main/default/lwc/{componentName}/` (or `lwc/{componentName}/` if that directory doesn't exist).

---

## VIZ-EXT-c — Deploy via Metadata REST API (no sf CLI needed)

```python
# _deploy_lwc.py
import base64, io, json, re, requests, time, zipfile
from pathlib import Path

cfg = json.loads(Path("next_orgs.json").read_text())
# ... auth (standard pattern) ...

COMPONENT_NAME = "{componentName}"
LWC_DIR        = Path("lwc") / COMPONENT_NAME

D3_URL  = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
D3_META = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<StaticResource xmlns="http://soap.sforce.com/2006/04/metadata">\n'
           '    <cacheControl>Public</cacheControl>\n'
           '    <contentType>application/javascript</contentType>\n'
           '</StaticResource>')

d3_js = requests.get(D3_URL).text

lwc_files = {
    COMPONENT_NAME + ".js":          (LWC_DIR / (COMPONENT_NAME + ".js")).read_text(),
    COMPONENT_NAME + ".html":        (LWC_DIR / (COMPONENT_NAME + ".html")).read_text(),
    COMPONENT_NAME + ".css":         (LWC_DIR / (COMPONENT_NAME + ".css")).read_text(),
    COMPONENT_NAME + ".js-meta.xml": (LWC_DIR / (COMPONENT_NAME + ".js-meta.xml")).read_text(),
}

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
    for fname, content in lwc_files.items():
        zf.writestr("lwc/" + COMPONENT_NAME + "/" + fname, content)
    zf.writestr("staticresources/d3.resource", d3_js)           # .resource extension required
    zf.writestr("staticresources/d3.resource-meta.xml", D3_META)
    zf.writestr("package.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        '  <types><members>' + COMPONENT_NAME + '</members><name>LightningComponentBundle</name></types>\n'
        '  <types><members>d3</members><name>StaticResource</name></types>\n'
        '  <version>66.0</version>\n</Package>')
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

r = requests.post(sf_instance + "/services/Soap/m/66.0",   # try /62.0 if 404
    headers={"Content-Type": "text/xml", "SOAPAction": "deploy"}, data=soap_body)
job_id = re.search(r'<id>([^<]+)</id>', r.text).group(1)

for _ in range(60):
    time.sleep(5)
    status = requests.get(sf_instance + "/services/data/v66.0/metadata/deployRequest/" + job_id +
                          "?includeDetails=true", headers=SF_HDRS).json().get("deployResult", {})
    state = status.get("status", "")
    print(f"  {state} ({status.get('numberComponentsDeployed',0)}/{status.get('numberComponentsTotal',0)})", end="\r")
    if state in ("Succeeded", "Failed", "Canceled"):
        print(); break

if state != "Succeeded":
    for f in (status.get("details", {}).get("componentFailures") or []):
        print(f"  FAILURE: {f.get('fileName')} — {f.get('problem')}")
```

After deployment succeeds, present the dashboard list and ask where to add the component.

---

## VIZ-EXT-d — Add to dashboard

```python
def dash_lwc_extension(name, component_name, namespace="c", properties=None):
    """
    namespace: "c" for unmanaged. Use org namespace prefix if the org has one.
    Do NOT include a "source" field — causes 403 ACCESS_DENIED on PATCH.
    """
    return {
        "actions": [],
        "componentType": "Custom",
        "name": name,
        "parameters": {
            "fullyQualifiedName": f"{namespace}:{component_name}",
            "properties": properties or {}
        },
        "type": "extension"
    }

# Add to existing dashboard:
widgets["ext_1"] = dash_lwc_extension("ext_1", "{componentName}",
    properties={"sdmName": model_api_name, "dimField": dim_field, "measureField": measure_field})
cells.append({"name": "ext_1", "column": 2, "row": next_row, "colspan": 70, "rowspan": 20})
```

**Blank tile troubleshooting** (shows `ext_{name}.png` instead of chart):
1. D3 not loaded — `renderChart()` must be called inside `dataUpdate` handler, never from `renderedCallback()`
2. Container zero dimensions — add `|| 400` / `|| 300` fallback or `setTimeout(() => this.renderChart(), 100)`
3. `sdk` undefined at `connectedCallback` — add null check before registering listeners
4. Stale deployment — hard-refresh (Cmd+Shift+R)
5. Namespace mismatch — check org namespace in Setup → Company Settings → Company Information
