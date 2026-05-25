import { LightningElement, api } from "lwc";
import { loadScript } from "lightning/platformResourceLoader";
import D3 from "@salesforce/resourceUrl/d3";

const SDK_EVENTS = { DATA_UPDATE: "dataUpdate", FILTER_CHANGE: "filterChange" };

export default class GabesSalesTreemap extends LightningElement {
    @api sdk;

    // SDO name (table) — needed to qualify field references for registerFieldsForQuery
    _sdoName = "Opportunity";
    @api get sdoName() { return this._sdoName; }
    set sdoName(v) { if (v) this._sdoName = v; }

    _sdmName = "Gabe_Sales_Data_Sample";
    @api get sdmName() { return this._sdmName; }
    set sdmName(v) { if (v) this._sdmName = v; }

    // Field API names (unqualified — SDO prefix added at query time)
    _dimField = "Opportunity_Stage";
    @api get dimField() { return this._dimField; }
    set dimField(v) { if (v) this._dimField = v; }

    // Must be a raw SDO field — calc measurements (e.g. Deal_Size_clc) are model-level
    // and cannot be referenced as SdoName.fieldName in registerFieldsForQuery
    _measureField = "Total_Amount";
    @api get measureField() { return this._measureField; }
    set measureField(v) { if (v) this._measureField = v; }

    _queryLimit = 500;
    @api get queryLimit() { return this._queryLimit; }
    set queryLimit(v) { if (v) this._queryLimit = parseInt(v, 10); }

    _d3Loaded = false;
    _unsubscribes = [];

    connectedCallback() {
        this._initialize();
    }

    disconnectedCallback() {
        this._unsubscribes.forEach(fn => typeof fn === "function" && fn());
        this._unsubscribes = [];
    }

    async _initialize() {
        if (!this.sdk) {
            console.error("[gabesSalesTreemap] sdk not available at connectedCallback");
            return;
        }
        try {
            await loadScript(this, D3);
            this._d3Loaded = true;
            console.log("[gabesSalesTreemap] D3 loaded");
        } catch (e) {
            console.error("[gabesSalesTreemap] D3 load failed:", e);
            return;
        }

        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.FILTER_CHANGE, () => {
                console.log("[gabesSalesTreemap] filterChange — re-fetching");
                this.sdk.fetchData();
            })
        );
        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.DATA_UPDATE, (rows) => {
                console.log("[gabesSalesTreemap] dataUpdate rows:", Array.isArray(rows) ? rows.length : rows);
                this._renderChart(Array.isArray(rows) ? rows : []);
            })
        );

        this._registerQuery();
    }

    _registerQuery() {
        // Fields must use SDO-qualified format: "SdoApiName.fieldApiName"
        // Dimension uses rowGrouping:true; measure uses aggregationType (inherited from SDM)
        const dimQualified = `${this._sdoName}.${this._dimField}`;
        const measureQualified = `${this._sdoName}.${this._measureField}`;

        const fields = [
            { model: dimQualified,     rowGrouping: true },
            { model: measureQualified, rowGrouping: false }
        ];
        console.log("[gabesSalesTreemap] registerFieldsForQuery:", JSON.stringify(fields));
        this.sdk.registerFieldsForQuery(fields, this._sdmName, { limit: this._queryLimit });
        this.sdk.fetchData();
    }

    _renderChart(rows) {
        console.log("[gabesSalesTreemap] _renderChart rows:", rows.length, rows[0]);
        const container = this.template.querySelector(".chart-container");
        if (!container || !this._d3Loaded || !rows.length) {
            console.warn("[gabesSalesTreemap] render skipped — container:", !!container, "d3:", this._d3Loaded, "rows:", rows.length);
            return;
        }

        const rect = container.getBoundingClientRect();
        const W = rect.width  > 0 ? rect.width  : (container.clientWidth  || 600);
        const H = rect.height > 0 ? rect.height : (container.clientHeight || 400);

        if (W <= 0 || H <= 0) {
            console.warn("[gabesSalesTreemap] zero dimensions, retrying in 100ms");
            setTimeout(() => this._renderChart(rows), 100);
            return;
        }

        container.innerHTML = "";
        const d3 = window.d3;

        // Rows are positional arrays when using model/rowGrouping format:
        // index 0 = dim field, index 1 = measure field
        const rollup = {};
        for (const row of rows) {
            const dim = (Array.isArray(row) ? row[0] : row[this._dimField]) ?? "Unknown";
            const val = parseFloat(Array.isArray(row) ? row[1] : row[this._measureField]) || 0;
            rollup[dim] = (rollup[dim] || 0) + val;
        }
        console.log("[gabesSalesTreemap] rollup:", rollup);

        const leaves = Object.entries(rollup).map(([name, value]) => ({ name, value }));
        if (!leaves.length) return;

        const root = d3.hierarchy({ name: "root", children: leaves })
            .sum(d => d.value)
            .sort((a, b) => b.value - a.value);

        d3.treemap()
            .size([W, H])
            .paddingOuter(4)
            .paddingInner(3)
            .round(true)(root);

        const palette = [
            "#0176D3", "#1B96FF", "#032D60", "#014486",
            "#0B5CAB", "#1C74C4", "#5EB5FF", "#9DC9FF"
        ];
        const color = d3.scaleOrdinal(palette);

        const svg = d3.select(container)
            .append("svg")
            .attr("width", W).attr("height", H)
            .style("font-family", "Salesforce Sans, Arial, sans-serif");

        const cell = svg.selectAll("g")
            .data(root.leaves())
            .join("g")
            .attr("transform", d => `translate(${d.x0},${d.y0})`);

        cell.append("rect")
            .attr("width",  d => Math.max(0, d.x1 - d.x0))
            .attr("height", d => Math.max(0, d.y1 - d.y0))
            .attr("fill",   d => color(d.data.name))
            .attr("rx", 4).attr("ry", 4);

        cell.filter(d => (d.x1 - d.x0) > 60 && (d.y1 - d.y0) > 30)
            .append("text")
            .attr("x", 8).attr("y", 18)
            .attr("fill", "#FFFFFF")
            .attr("font-size", "12px").attr("font-weight", "bold")
            .text(d => d.data.name);

        cell.filter(d => (d.x1 - d.x0) > 60 && (d.y1 - d.y0) > 48)
            .append("text")
            .attr("x", 8).attr("y", 34)
            .attr("fill", "rgba(255,255,255,0.85)")
            .attr("font-size", "11px")
            .text(d => {
                const v = d.data.value;
                if (v >= 1e6) return "$" + (v / 1e6).toFixed(1) + "M";
                if (v >= 1e3) return "$" + (v / 1e3).toFixed(0) + "K";
                return "$" + v.toFixed(0);
            });

        console.log("[gabesSalesTreemap] chart rendered successfully");
    }
}
