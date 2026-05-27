import { LightningElement, api } from "lwc";
import { loadScript } from "lightning/platformResourceLoader";
import D3 from "@salesforce/resourceUrl/d3";

const SDK_EVENTS = { DATA_UPDATE: "dataUpdate", FILTER_CHANGE: "filterChange" };

export default class GabesSalesTreemap extends LightningElement {
    @api sdk;

    _sdmName = "Gabe_Sales_Data_Sample";
    @api get sdmName() { return this._sdmName; }
    set sdmName(v) { if (v) this._sdmName = v; }

    _dimField = "Opportunity_Stage";
    @api get dimField() { return this._dimField; }
    set dimField(v) { if (v) this._dimField = v; }

    _measureField = "Deal_Size_clc";
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
            console.error("[gabesSalesTreemap] sdk not available");
            return;
        }

        try {
            await loadScript(this, D3);
            this._d3Loaded = true;
        } catch (e) {
            console.error("[gabesSalesTreemap] D3 load failed:", e);
            return;
        }

        // Subscribe to filter changes — re-fetch when dashboard filters update
        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.FILTER_CHANGE, () => {
                this.sdk.fetchData();
            })
        );

        // DATA_UPDATE: rows arrive as a plain array, not an event object
        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.DATA_UPDATE, (rows) => {
                this._renderChart(Array.isArray(rows) ? rows : []);
            })
        );

        this._registerQuery();
    }

    _registerQuery() {
        const fields = [
            { name: this._dimField,     dataType: "string" },
            { name: this._measureField, dataType: "real"   }
        ];
        this.sdk.registerFieldsForQuery(fields, this._sdmName, { limit: this._queryLimit });
        this.sdk.fetchData();
    }

    _renderChart(rows) {
        const container = this.template.querySelector(".chart-container");
        if (!container || !this._d3Loaded || !rows.length) return;

        const rect = container.getBoundingClientRect();
        const W = rect.width  > 0 ? rect.width  : (container.clientWidth  || 600);
        const H = rect.height > 0 ? rect.height : (container.clientHeight || 400);

        if (W <= 0 || H <= 0) {
            setTimeout(() => this._renderChart(rows), 100);
            return;
        }

        container.innerHTML = "";

        // Aggregate rows by dimension field
        const d3 = window.d3;
        const rollup = {};
        for (const row of rows) {
            const dim = row[this._dimField] ?? "Unknown";
            const val = parseFloat(row[this._measureField]) || 0;
            rollup[dim] = (rollup[dim] || 0) + val;
        }

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
            .attr("width", W)
            .attr("height", H)
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
    }
}
