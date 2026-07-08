import { LightningElement, api } from "lwc";
import { loadScript } from "lightning/platformResourceLoader";
import D3 from "@salesforce/resourceUrl/d3";

export default class SalesCloudTreemap extends LightningElement {
    _sdk = null;
    @api get sdk() { return this._sdk; }
    set sdk(v) {
        this._sdk = v;
        if (v) this._initialize();
    }

    _sdmName = "New_Semantic_Model_818";
    @api get sdmName() { return this._sdmName; }
    set sdmName(v) { if (v) this._sdmName = v; }

    _sdoName = "Opportunity1";
    @api get sdoName() { return this._sdoName; }
    set sdoName(v) { if (v) this._sdoName = v; }

    _dimField = "Opportunity_Stage1";
    @api get dimField() { return this._dimField; }
    set dimField(v) { if (v) this._dimField = v; }

    _measureField = "Total_Amount";
    @api get measureField() { return this._measureField; }
    set measureField(v) { if (v) this._measureField = v; }

    _queryLimit = 500;
    @api get queryLimit() { return this._queryLimit; }
    set queryLimit(v) { if (v) this._queryLimit = parseInt(v, 10); }

    _d3Loaded = false;
    _data = [];
    _unsubscribes = [];

    connectedCallback() {
        if (this._sdk) this._initialize();
    }

    disconnectedCallback() {
        this._unsubscribes.forEach(fn => typeof fn === "function" && fn());
        this._unsubscribes = [];
    }

    async _initialize() {
        if (!this._sdk) return;
        if (this._initialized) return;  // guard against double-init
        this._initialized = true;

        await loadScript(this, D3);
        this._d3Loaded = true;

        this._unsubscribes.push(
            this._sdk.on("filterChange", () => { this._sdk.fetchData(); })
        );
        this._unsubscribes.push(
            this._sdk.on("dataUpdate", (rows) => {
                this._data = Array.isArray(rows) ? rows : [];
                this.renderChart();
            })
        );

        const fields = [
            { model: `${this._sdoName}.${this._dimField}`,     rowGrouping: true },
            { model: `${this._sdoName}.${this._measureField}`, aggregationType: "SUM" }
        ];
        this._sdk.registerFieldsForQuery(fields, this._sdmName, { limit: this._queryLimit });
        this._sdk.fetchData();
    }

    renderChart() {
        const container = this.template.querySelector(".chart-container");
        if (!container || !this._d3Loaded || !this._data.length) return;
        const W = container.clientWidth  || 600;
        const H = container.clientHeight || 320;
        if (W <= 0 || H <= 0) { setTimeout(() => this.renderChart(), 100); return; }

        const d3 = window.d3;

        const data = this._data
            .map(row => ({ name: String(row[0] || ""), value: parseFloat(row[1]) || 0 }))
            .filter(d => d.name && d.value > 0)
            .sort((a, b) => b.value - a.value);

        if (!data.length) return;

        // SLDS blue palette — darkest for largest tiles
        const color = d3.scaleOrdinal()
            .domain(data.map(d => d.name))
            .range([
                "#0176D3", "#1B96FF", "#032D60", "#0B5CAB",
                "#57A3FD", "#014486", "#7DC0FF", "#00396B",
                "#ADD8FF", "#1A4971",
            ]);

        const fmt = d3.format("$,.0f");

        const hierarchy = d3.hierarchy({ children: data })
            .sum(d => d.value)
            .sort((a, b) => b.value - a.value);

        d3.treemap()
            .size([W, H])
            .paddingOuter(4)
            .paddingInner(3)
            .round(true)(hierarchy);

        d3.select(container).select("svg").remove();

        const svg = d3.select(container).append("svg")
            .attr("width", W).attr("height", H)
            .style("font-family", "Salesforce Sans, Arial, sans-serif");

        const leaf = svg.selectAll("g")
            .data(hierarchy.leaves())
            .join("g")
            .attr("transform", d => `translate(${d.x0},${d.y0})`);

        leaf.append("rect")
            .attr("width",  d => Math.max(0, d.x1 - d.x0))
            .attr("height", d => Math.max(0, d.y1 - d.y0))
            .attr("fill",   d => color(d.data.name))
            .attr("rx", 3)
            .attr("ry", 3);

        // Only label tiles wide/tall enough to fit text
        leaf.each(function(d) {
            const tileW = d.x1 - d.x0;
            const tileH = d.y1 - d.y0;
            if (tileW < 40 || tileH < 28) return;

            const g        = d3.select(this);
            const fill     = color(d.data.name);
            const textColor = d3.hsl(fill).l < 0.5 ? "#fff" : "#032D60";
            const fontSize  = Math.min(13, tileW / 8, tileH / 3.5);
            const valSize   = Math.min(11, fontSize * 0.85);
            const cx        = tileW / 2;

            // Stage name
            g.append("text")
                .attr("x", cx).attr("y", tileH / 2 - valSize * 0.6)
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "middle")
                .attr("fill", textColor)
                .attr("font-size", fontSize + "px")
                .attr("font-weight", "700")
                .text(d.data.name.length > 16 ? d.data.name.slice(0, 14) + "…" : d.data.name);

            // Value
            if (tileH >= 44) {
                g.append("text")
                    .attr("x", cx).attr("y", tileH / 2 + valSize * 1.2)
                    .attr("text-anchor", "middle")
                    .attr("dominant-baseline", "middle")
                    .attr("fill", textColor)
                    .attr("font-size", valSize + "px")
                    .attr("opacity", 0.88)
                    .text(fmt(d.data.value));
            }
        });
    }
}
