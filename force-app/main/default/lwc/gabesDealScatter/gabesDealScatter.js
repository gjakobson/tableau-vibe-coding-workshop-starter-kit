import { LightningElement, api } from "lwc";
import { loadScript } from "lightning/platformResourceLoader";
import D3 from "@salesforce/resourceUrl/d3";

const SDK_EVENTS = { DATA_UPDATE: "dataUpdate", FILTER_CHANGE: "filterChange" };

export default class GabesDealScatter extends LightningElement {
    @api sdk;

    _sdoName = "Opportunity1";
    @api get sdoName() { return this._sdoName; }
    set sdoName(v) { if (v) this._sdoName = v; }

    _sdmName = "New_Semantic_Model_4eb";
    @api get sdmName() { return this._sdmName; }
    set sdmName(v) { if (v) this._sdmName = v; }

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
            console.error("[gabesDealScatter] sdk not available");
            return;
        }
        try {
            await loadScript(this, D3);
            this._d3Loaded = true;
        } catch (e) {
            console.error("[gabesDealScatter] D3 load failed:", e);
            return;
        }

        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.FILTER_CHANGE, () => this.sdk.fetchData())
        );
        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.DATA_UPDATE, (rows) => {
                this._renderChart(Array.isArray(rows) ? rows : []);
            })
        );

        this._registerQuery();
    }

    _registerQuery() {
        // Rows: [0]=Opportunity Stage, [1]=Total Amount, [2]=Probability
        const fields = [
            { model: `${this._sdoName}.Opportunity_Stage1`, rowGrouping: true },
            { model: `${this._sdoName}.Total_Amount1`,      aggregationType: "SUM" },
            { model: `${this._sdoName}.Probability1`,       aggregationType: "AVG" }
        ];
        console.log("[gabesDealScatter] registerFieldsForQuery:", JSON.stringify(fields));
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

        const margin = { top: 30, right: 30, bottom: 60, left: 80 };
        const innerW = W - margin.left - margin.right;
        const innerH = H - margin.top  - margin.bottom;

        const points = rows
            .map(row => ({
                stage:       (row[0] ?? "Unknown").toString(),
                amount:      parseFloat(row[1]) || 0,
                probability: parseFloat(row[2]) || 0
            }))
            .filter(d => d.amount > 0);

        if (!points.length) return;

        container.innerHTML = "";
        const d3 = window.d3;

        const palette = [
            "#0176D3","#1B96FF","#032D60","#014486",
            "#0B5CAB","#1C74C4","#5EB5FF","#9DC9FF"
        ];
        const color = d3.scaleOrdinal(palette).domain(points.map(d => d.stage));

        const xScale = d3.scaleLinear()
            .domain([0, 100])
            .range([0, innerW]);

        const yScale = d3.scaleLinear()
            .domain([0, d3.max(points, d => d.amount) * 1.1])
            .range([innerH, 0]);

        const svg = d3.select(container)
            .append("svg")
            .attr("width", W).attr("height", H)
            .style("font-family", "Salesforce Sans, Arial, sans-serif");

        const g = svg.append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        // Grid lines
        g.append("g")
            .attr("stroke", "#EEEEEE").attr("stroke-dasharray", "3,3")
            .call(d3.axisLeft(yScale).ticks(5).tickSize(-innerW).tickFormat(""));
        g.append("g")
            .attr("stroke", "#EEEEEE").attr("stroke-dasharray", "3,3")
            .attr("transform", `translate(0,${innerH})`)
            .call(d3.axisBottom(xScale).ticks(5).tickSize(-innerH).tickFormat(""));

        // Axes
        g.append("g")
            .attr("transform", `translate(0,${innerH})`)
            .call(d3.axisBottom(xScale).ticks(5).tickFormat(d => d + "%"))
            .selectAll("text").attr("fill", "#706E6B").attr("font-size", "11px");

        g.append("g")
            .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => {
                if (d >= 1e6) return "$" + (d / 1e6).toFixed(1) + "M";
                if (d >= 1e3) return "$" + (d / 1e3).toFixed(0) + "K";
                return "$" + d;
            }))
            .selectAll("text").attr("fill", "#706E6B").attr("font-size", "11px");

        // Axis labels
        g.append("text")
            .attr("x", innerW / 2).attr("y", innerH + 44)
            .attr("text-anchor", "middle").attr("fill", "#444").attr("font-size", "12px")
            .text("Avg Probability (%)");

        g.append("text")
            .attr("transform", "rotate(-90)")
            .attr("x", -innerH / 2).attr("y", -62)
            .attr("text-anchor", "middle").attr("fill", "#444").attr("font-size", "12px")
            .text("Total Amount");

        // Dots
        g.selectAll("circle")
            .data(points)
            .join("circle")
            .attr("cx", d => xScale(d.probability))
            .attr("cy", d => yScale(d.amount))
            .attr("r", 8)
            .attr("fill", d => color(d.stage))
            .attr("opacity", 0.85)
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5);

        // Labels on dots
        g.selectAll(".dot-label")
            .data(points)
            .join("text")
            .attr("class", "dot-label")
            .attr("x", d => xScale(d.probability) + 11)
            .attr("y", d => yScale(d.amount) + 4)
            .attr("fill", "#032D60")
            .attr("font-size", "11px")
            .text(d => d.stage);

        console.log("[gabesDealScatter] chart rendered, points:", points.length);
    }
}
