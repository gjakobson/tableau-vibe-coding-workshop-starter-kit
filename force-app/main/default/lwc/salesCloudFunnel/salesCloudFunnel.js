import { LightningElement, api } from "lwc";
import { loadScript } from "lightning/platformResourceLoader";
import D3 from "@salesforce/resourceUrl/d3";

export default class SalesCloudFunnel extends LightningElement {
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

    // Stage order — funnel flows top-to-bottom by typical sales progression
    _stageOrder = [
        "Prospecting", "Qualification", "Needs Analysis", "Value Proposition",
        "Id. Decision Makers", "Perception Analysis", "Proposal/Price Quote",
        "Negotiation/Review", "Closed Won", "Closed Lost"
    ];

    connectedCallback() {
        if (this._sdk) this._initialize();
    }

    disconnectedCallback() {
        this._unsubscribes.forEach(fn => typeof fn === "function" && fn());
        this._unsubscribes = [];
    }

    async _initialize() {
        if (!this._sdk) return;
        if (this._initialized) return;
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
        const W = container.clientWidth  || 480;
        const H = container.clientHeight || 360;
        if (W <= 0 || H <= 0) { setTimeout(() => this.renderChart(), 100); return; }

        const d3 = window.d3;

        // Parse rows: row[0] = stage name, row[1] = total amount
        let data = this._data
            .map(row => ({ stage: String(row[0] || ""), value: parseFloat(row[1]) || 0 }))
            .filter(d => d.stage && d.value > 0);

        // Sort by known stage order, then alphabetically for unknowns
        data.sort((a, b) => {
            const ai = this._stageOrder.indexOf(a.stage);
            const bi = this._stageOrder.indexOf(b.stage);
            if (ai !== -1 && bi !== -1) return ai - bi;
            if (ai !== -1) return -1;
            if (bi !== -1) return 1;
            return a.stage.localeCompare(b.stage);
        });

        if (!data.length) return;

        const margin = { top: 20, right: 120, bottom: 20, left: 10 };
        const innerW  = W - margin.left - margin.right;
        const innerH  = H - margin.top  - margin.bottom;
        const bandH   = Math.max(24, innerH / data.length);
        const maxVal  = d3.max(data, d => d.value);

        // Funnel: each bar width scales to value / maxVal * innerW, centered
        const barW = d => (d.value / maxVal) * innerW;

        // Color scale — blues darkening toward top (larger stages)
        const color = d3.scaleSequential()
            .domain([data.length - 1, 0])
            .interpolator(d3.interpolate("#90c8f8", "#0176D3"));

        // Clear previous render
        d3.select(container).select("svg").remove();

        const svg = d3.select(container).append("svg")
            .attr("width", W).attr("height", H)
            .style("font-family", "Salesforce Sans, Arial, sans-serif");

        const g = svg.append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const fmt = d3.format("$,.0f");

        data.forEach((d, i) => {
            const bw   = barW(d);
            const x    = (innerW - bw) / 2;
            const y    = i * bandH;
            const fill = color(i);

            // Trapezoid path for funnel effect
            const nextBw = i < data.length - 1 ? barW(data[i + 1]) : bw * 0.8;
            const nextX  = (innerW - nextBw) / 2;
            const trap   = `M${x},${y} L${x + bw},${y} L${nextX + nextBw},${y + bandH - 2} L${nextX},${y + bandH - 2} Z`;

            g.append("path")
                .attr("d", trap)
                .attr("fill", fill)
                .attr("opacity", 0.92);

            // Stage label (centered, white if dark enough)
            const brightness = d3.hsl(fill).l;
            g.append("text")
                .attr("x", innerW / 2)
                .attr("y", y + bandH / 2 + 1)
                .attr("dy", "0.35em")
                .attr("text-anchor", "middle")
                .attr("fill", brightness < 0.55 ? "#fff" : "#032D60")
                .attr("font-size", Math.min(12, bandH * 0.42) + "px")
                .attr("font-weight", "600")
                .text(d.stage);

            // Value label — right side
            g.append("text")
                .attr("x", innerW + 8)
                .attr("y", y + bandH / 2 + 1)
                .attr("dy", "0.35em")
                .attr("text-anchor", "start")
                .attr("fill", "#2E2E2E")
                .attr("font-size", Math.min(11, bandH * 0.38) + "px")
                .text(fmt(d.value));
        });

        // Chart title
        svg.append("text")
            .attr("x", W / 2).attr("y", 13)
            .attr("text-anchor", "middle")
            .attr("fill", "#032D60")
            .attr("font-size", "12px")
            .attr("font-weight", "700")
            .text("Pipeline by Stage");
    }
}
