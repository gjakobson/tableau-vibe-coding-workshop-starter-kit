import { LightningElement, api, track } from "lwc";

const SDK_EVENTS = {
    FILTER_CHANGE: "filterChange",
    SELECTION_CHANGE: "selectionChange",
    PARAMETER_CHANGE: "parameterChange",
    DATA_UPDATE: "dataUpdate"
};

const LIFE_CYCLE_EVENTS = { LOADED: "loaded", ERROR: "error", NO_DATA: "nodata" };

const PAGE_SIZE = 20;
const QUERY_LIMIT_DEFAULT = 500;

const STAGE_COLORS = {
    won: { bar: "seg-won", dot: "dot-won" },
    lost: { bar: "seg-lost", dot: "dot-lost" },
    negotiation: { bar: "seg-late", dot: "dot-late" },
    proposal: { bar: "seg-late", dot: "dot-late" },
    default: { bar: "seg-open", dot: "dot-open" }
};

function stageColorKey(stage) {
    const s = (stage || "").toLowerCase();
    if (s.includes("won")) return "won";
    if (s.includes("lost")) return "lost";
    if (s.includes("negotiation") || s.includes("proposal")) return "negotiation";
    return "default";
}

export default class OpportunitiesCard extends LightningElement {
    @api sdk;

    @api sdmName = "WorkshopModel";
    @api sdoName = "Opportunity";
    @api queryLimit = QUERY_LIMIT_DEFAULT;

    @api nameField = "Name";
    @api stageField = "Opportunity_Stage";
    @api amountField = "Total_Amount";
    @api probabilityField = "Probability";
    @api ownerField = "OwnerUser";
    @api closeDateField = "Close_Date";
    @api idField = "Opportunity_Id";
    @api debugMode = false;

    @track _phase = "empty";
    @track errorMessage = "";
    @track selectedStage = "all";
    @track sortField = "amount";
    @track sortAsc = false;
    @track visibleCount = PAGE_SIZE;

    _rows = [];
    _unsubscribes = [];
    _timeoutId = null;
    _fieldIndex = {};

    get isEmpty() { return this._phase === "empty"; }
    get isLoading() { return this._phase === "loading"; }
    get isReady() { return this._phase === "ready"; }
    get hasError() { return this._phase === "error"; }
    get isSortAsc() { return this.sortAsc; }

    get stageOptions() {
        const stages = [...new Set(this._rows.map(r => r.stage).filter(Boolean))].sort();
        return [{ label: "All Stages", value: "all" }, ...stages.map(s => ({ label: s, value: s }))];
    }

    get filteredRows() {
        let rows = this._rows;
        if (this.selectedStage !== "all") {
            rows = rows.filter(r => r.stage === this.selectedStage);
        }
        const field = this.sortField;
        const dir = this.sortAsc ? 1 : -1;
        return [...rows].sort((a, b) => {
            let av = a[field], bv = b[field];
            if (field === "closeDate") {
                av = av ? new Date(av).getTime() : 0;
                bv = bv ? new Date(bv).getTime() : 0;
            } else if (field === "name") {
                av = (av || "").toLowerCase();
                bv = (bv || "").toLowerCase();
            } else {
                av = Number(av) || 0;
                bv = Number(bv) || 0;
            }
            if (av < bv) return -1 * dir;
            if (av > bv) return 1 * dir;
            return 0;
        });
    }

    get totalCount() { return this.filteredRows.length; }

    get visibleRows() {
        return this.filteredRows.slice(0, this.visibleCount).map(r => this._decorateRow(r));
    }

    get hasMore() { return this.filteredRows.length > this.visibleCount; }
    get remainingCount() { return this.filteredRows.length - this.visibleCount; }

    get totalPipeline() {
        return this.filteredRows.reduce((s, r) => s + (Number(r.amount) || 0), 0);
    }
    get totalPipelineDisplay() { return this._fmtDollar(this.totalPipeline); }

    get weightedPipeline() {
        return this.filteredRows.reduce((s, r) => {
            const prob = Number(r.probability) || 0;
            const amt = Number(r.amount) || 0;
            return s + amt * (prob / 100);
        }, 0);
    }
    get weightedPipelineDisplay() { return this._fmtDollar(this.weightedPipeline); }

    get avgProbability() {
        const rows = this.filteredRows.filter(r => r.probability != null);
        if (!rows.length) return 0;
        return rows.reduce((s, r) => s + (Number(r.probability) || 0), 0) / rows.length;
    }
    get avgProbabilityDisplay() { return `${Math.round(this.avgProbability)}%`; }

    get closingSoonCount() {
        const now = new Date();
        const cutoff = new Date(now);
        cutoff.setDate(cutoff.getDate() + 30);
        return this.filteredRows.filter(r => {
            if (!r.closeDate) return false;
            const d = new Date(r.closeDate);
            return !Number.isNaN(d.getTime()) && d >= now && d <= cutoff;
        }).length;
    }

    get stageDistribution() {
        const totAmt = this.totalPipeline || 1;
        const groups = {};
        for (const r of this.filteredRows) {
            const s = r.stage || "Unknown";
            if (!groups[s]) groups[s] = 0;
            groups[s] += Number(r.amount) || 0;
        }
        return Object.entries(groups)
            .sort((a, b) => b[1] - a[1])
            .map(([stage, amt]) => {
                const pct = Math.round((amt / totAmt) * 100);
                const colorKey = stageColorKey(stage);
                const colors = STAGE_COLORS[colorKey] || STAGE_COLORS.default;
                return {
                    stage,
                    pct,
                    barClass: `stage-seg ${colors.bar}`,
                    barStyle: `width: ${pct}%`,
                    dotClass: `legend-dot ${colors.dot}`,
                    tooltip: `${stage}: ${this._fmtDollar(amt)} (${pct}%)`
                };
            });
    }

    connectedCallback() { this._initialize(); }

    disconnectedCallback() {
        this._unsubscribes.forEach(fn => typeof fn === "function" && fn());
        this._unsubscribes = [];
        if (this._timeoutId) { clearTimeout(this._timeoutId); this._timeoutId = null; }
    }

    _initialize() {
        if (!this.sdk) return;
        this._subscribeEvents();
        this._registerQuery();
    }

    _subscribeEvents() {
        if (!this.sdk?.on) return;
        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.FILTER_CHANGE, () => {}),
            this.sdk.on(SDK_EVENTS.PARAMETER_CHANGE, () => {}),
            this.sdk.on(SDK_EVENTS.SELECTION_CHANGE, () => {}),
            this.sdk.on(SDK_EVENTS.DATA_UPDATE, payload => {
                if (this._timeoutId) { clearTimeout(this._timeoutId); this._timeoutId = null; }
                this._processSdkRows(payload);
            })
        );
    }

    _registerQuery() {
        try {
            const fields = [
                { model: `${this.sdoName}.${this.nameField}`,        rowGrouping: true },
                { model: `${this.sdoName}.${this.stageField}`,       rowGrouping: true },
                { model: `${this.sdoName}.${this.ownerField}`,       rowGrouping: true },
                { model: `${this.sdoName}.${this.closeDateField}`,   rowGrouping: true },
                { model: `${this.sdoName}.${this.idField}`,          rowGrouping: true },
                { model: `${this.sdoName}.${this.amountField}`,      aggregationType: "SUM" },
                { model: `${this.sdoName}.${this.probabilityField}`, aggregationType: "AVG" }
            ];
            this._fieldIndex = { name: 0, stage: 1, owner: 2, closeDate: 3, oppId: 4, amount: 5, probability: 6 };
            this.sdk.registerFieldsForQuery(fields, this.sdmName, {
                limit: parseInt(this.queryLimit, 10) || QUERY_LIMIT_DEFAULT
            });
            this._phase = "loading";
            this._timeoutId = setTimeout(() => {
                if (this._phase === "loading") this._phase = "empty";
            }, 8000);
        } catch (err) {
            this.errorMessage = err.message || String(err);
            this._phase = "error";
        }
    }

    _processSdkRows(payload) {
        try {
            const rows = payload?.rows || payload?.data || payload;
            if (!Array.isArray(rows) || rows.length === 0) {
                this._rows = [];
                this._phase = "empty";
                this.sdk?.actions?.notifyLifecycleChange?.(LIFE_CYCLE_EVENTS.NO_DATA);
                return;
            }
            const i = this._fieldIndex;
            const seen = new Set();
            const parsed = [];
            for (const raw of rows) {
                const row = Array.isArray(raw) ? raw : Object.values(raw);
                const oppId = String(row[i.oppId] || "").trim();
                const name = String(row[i.name] || "").trim();
                const key = oppId || name;
                if (!key || seen.has(key)) continue;
                seen.add(key);
                parsed.push({
                    key,
                    name,
                    stage: String(row[i.stage] || ""),
                    owner: String(row[i.owner] || ""),
                    closeDate: String(row[i.closeDate] || ""),
                    oppId,
                    amount: Number(row[i.amount]) || 0,
                    probability: Number(row[i.probability]) || 0
                });
            }
            this._rows = parsed;
            this.visibleCount = PAGE_SIZE;
            this._phase = "ready";
            this.sdk?.actions?.notifyLifecycleChange?.(LIFE_CYCLE_EVENTS.LOADED);
        } catch (err) {
            this.errorMessage = err.message || String(err);
            this._phase = "error";
            this.sdk?.actions?.notifyLifecycleChange?.(LIFE_CYCLE_EVENTS.ERROR);
        }
    }

    _decorateRow(r) {
        const prob = Number(r.probability) || 0;
        const probBarClass = prob >= 70
            ? "prob-bar-fill bar-high"
            : prob >= 40 ? "prob-bar-fill bar-med" : "prob-bar-fill bar-low";

        const colorKey = stageColorKey(r.stage);
        const badgeSuffix = colorKey === "won" ? "badge-won"
            : colorKey === "lost" ? "badge-lost"
            : colorKey === "negotiation" ? "badge-late" : "badge-open";

        let closeDateDisplay = "—";
        let closeDateClass = "cell-date";
        if (r.closeDate) {
            const d = new Date(r.closeDate);
            if (!Number.isNaN(d.getTime())) {
                closeDateDisplay = d.toLocaleDateString();
                const diffDays = Math.round((d - new Date()) / 86400000);
                if (diffDays < 0) closeDateClass = "cell-date date-past";
                else if (diffDays <= 14) closeDateClass = "cell-date date-urgent";
                else if (diffDays <= 30) closeDateClass = "cell-date date-soon";
            }
        }

        return {
            ...r,
            amountDisplay: this._fmtDollar(r.amount),
            probabilityDisplay: `${Math.round(prob)}%`,
            probBarClass,
            probBarStyle: `width: ${Math.min(100, prob)}%`,
            stageBadgeClass: `stage-badge ${badgeSuffix}`,
            closeDateDisplay,
            closeDateClass,
            rowClass: colorKey === "lost" ? "opp-row row-lost" : "opp-row"
        };
    }

    handleStageFilter(event) {
        this.selectedStage = event.target.value;
        this.visibleCount = PAGE_SIZE;
    }

    handleSortChange(event) {
        this.sortField = event.target.value;
    }

    handleSortDirToggle() {
        this.sortAsc = !this.sortAsc;
    }

    handleShowMore() {
        this.visibleCount = Math.min(this.visibleCount + PAGE_SIZE, this.filteredRows.length);
    }

    _fmtDollar(val) {
        if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
        if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
        if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
        return `$${Math.round(val).toLocaleString()}`;
    }
}
