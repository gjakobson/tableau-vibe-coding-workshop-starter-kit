import { LightningElement, api, track } from "lwc";

const SDK_EVENTS = {
    FILTER_CHANGE: "filterChange",
    SELECTION_CHANGE: "selectionChange",
    PARAMETER_CHANGE: "parameterChange",
    DATA_UPDATE: "dataUpdate"
};

const LIFE_CYCLE_EVENTS = {
    LOADED: "loaded",
    ERROR: "error",
    NO_DATA: "nodata"
};

const QUERY_LIMIT_DEFAULT = 500;

export default class OpportunityProfileCard extends LightningElement {
    @api sdk;

    @api sdmName = "WorkshopModel";
    @api sdoName = "Opportunity";
    @api queryLimit = QUERY_LIMIT_DEFAULT;

    @api nameField = "Name";
    @api stageField = "Opportunity_Stage";
    @api amountField = "Total_Amount";
    @api expectedRevenueField = "Expected_Revenue_Amount";
    @api probabilityField = "Probability";
    @api ownerField = "OwnerUser";
    @api leadSourceField = "Lead_Source";
    @api closeDateField = "Close_Date";
    @api nextStepField = "Next_Step";
    @api idField = "Opportunity_Id";
    @api actionList = "Global.LogACall,Global.NewTask,Global.NewEvent";
    @api defaultAction = "Global.LogACall";

    @track _phase = "empty";
    @track errorMessage = "";

    @track opportunityName = "";
    @track stageName = "";
    @track ownerName = "";
    @track leadSource = "";
    @track nextStep = "";
    @track opportunityId = "";
    @track closeDate = "";
    @track totalAmount = 0;
    @track expectedRevenue = 0;
    @track probability = 0;
    @track opportunityOptions = [];
    @track selectedOpportunityKey = "";
    @track actionOptions = [];
    @track selectedActionApiName = "";

    _unsubscribes = [];
    _timeoutId = null;
    _fieldIndex = {};
    _opportunityRows = [];

    get isEmpty() { return this._phase === "empty"; }
    get isLoading() { return this._phase === "loading"; }
    get isReady() { return this._phase === "ready"; }
    get hasError() { return this._phase === "error"; }
    get hasOpportunityOptions() { return this.opportunityOptions.length > 0; }
    get hasActionOptions() { return this.actionOptions.length > 0; }
    get isRunActionDisabled() { return !this.opportunityId || !this.selectedActionApiName; }

    get opportunityInitials() {
        if (!this.opportunityName) return "?";
        const parts = this.opportunityName.trim().split(/\s+/);
        if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        return parts[0][0].toUpperCase();
    }

    get stageBadgeClass() {
        const stage = (this.stageName || "").toLowerCase();
        if (stage.includes("won")) return "status-badge status-won";
        if (stage.includes("lost")) return "status-badge status-lost";
        if (stage.includes("negotiation") || stage.includes("proposal")) return "status-badge status-late";
        return "status-badge status-open";
    }

    get stageDisplay() { return this.stageName || "Open"; }

    get activityStatusClass() {
        const days = this.daysToClose;
        if (days === null) return "activity-status activity-unknown";
        if (days <= 14) return "activity-status activity-urgent";
        if (days <= 45) return "activity-status activity-watch";
        return "activity-status activity-healthy";
    }

    get activityStatusLabel() {
        const days = this.daysToClose;
        if (days === null) return "No Close Date";
        if (days < 0) return "Close Date Passed";
        if (days <= 14) return "Closing Soon";
        if (days <= 45) return "Monitor Timeline";
        return "Healthy Timeline";
    }

    get totalAmountDisplay() { return this._fmtDollar(this.totalAmount); }
    get expectedRevenueDisplay() { return this._fmtDollar(this.expectedRevenue); }
    get probabilityDisplay() { return `${Math.round(this.probability)}%`; }

    get winProbBarStyle() {
        const pct = Math.min(100, Math.max(0, this.probability || 0));
        return `width: ${pct}%`;
    }

    get winProbBarClass() {
        if (this.probability >= 70) return "score-bar-fill score-high";
        if (this.probability >= 40) return "score-bar-fill score-med";
        return "score-bar-fill score-low";
    }

    get dealHealthScore() {
        const base = this.probability || 0;
        const days = this.daysToClose;
        if (days === null) return Math.round(base);
        const timelineAdjustment = days < 0 ? -25 : days <= 14 ? -10 : days <= 45 ? 0 : 10;
        return Math.max(0, Math.min(100, Math.round(base + timelineAdjustment)));
    }

    get dealHealthDisplay() { return `${this.dealHealthScore}%`; }
    get dealHealthBarStyle() { return `width: ${this.dealHealthScore}%`; }

    get dealHealthBarClass() {
        if (this.dealHealthScore >= 70) return "score-bar-fill score-high";
        if (this.dealHealthScore >= 40) return "score-bar-fill score-med";
        return "score-bar-fill score-low";
    }

    get closeDateDisplay() {
        if (!this.closeDate) return "—";
        const d = new Date(this.closeDate);
        if (Number.isNaN(d.getTime())) return this.closeDate;
        return d.toLocaleDateString();
    }

    get daysToClose() {
        if (!this.closeDate) return null;
        const close = new Date(this.closeDate);
        if (Number.isNaN(close.getTime())) return null;
        const now = new Date();
        const diffMs = close.setHours(0, 0, 0, 0) - now.setHours(0, 0, 0, 0);
        return Math.round(diffMs / (1000 * 60 * 60 * 24));
    }

    get daysToCloseDisplay() {
        const days = this.daysToClose;
        if (days === null) return "—";
        if (days < 0) return `${Math.abs(days)} days past`;
        return `${days} days`;
    }

    connectedCallback() { this._initialize(); }

    disconnectedCallback() {
        this._unsubscribes.forEach((fn) => typeof fn === "function" && fn());
        this._unsubscribes = [];
        if (this._timeoutId) {
            clearTimeout(this._timeoutId);
            this._timeoutId = null;
        }
    }

    _initialize() {
        if (!this.sdk) return;
        this._buildActionOptions();
        this._subscribeEvents();
        this._registerQuery();
    }

    _subscribeEvents() {
        if (!this.sdk?.on) return;
        this._unsubscribes.push(
            this.sdk.on(SDK_EVENTS.FILTER_CHANGE, () => {}),
            this.sdk.on(SDK_EVENTS.PARAMETER_CHANGE, () => {}),
            this.sdk.on(SDK_EVENTS.SELECTION_CHANGE, () => {}),
            this.sdk.on(SDK_EVENTS.DATA_UPDATE, (payload) => {
                if (this._timeoutId) {
                    clearTimeout(this._timeoutId);
                    this._timeoutId = null;
                }
                this._processSdkRows(payload);
            })
        );
    }

    _registerQuery() {
        try {
            const fields = [
                { model: `${this.sdoName}.${this.nameField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.stageField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.ownerField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.leadSourceField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.nextStepField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.closeDateField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.idField}`, rowGrouping: true },
                { model: `${this.sdoName}.${this.amountField}`, aggregationType: "SUM" },
                { model: `${this.sdoName}.${this.expectedRevenueField}`, aggregationType: "SUM" },
                { model: `${this.sdoName}.${this.probabilityField}`, aggregationType: "AVG" }
            ];

            this._fieldIndex = {
                name: 0, stage: 1, owner: 2, source: 3, nextStep: 4,
                closeDate: 5, oppId: 6, amount: 7, expectedRevenue: 8, probability: 9
            };

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
                this.opportunityOptions = [];
                this.selectedOpportunityKey = "";
                this._opportunityRows = [];
                this._phase = "empty";
                this.sdk?.actions?.notifyLifecycleChange?.(LIFE_CYCLE_EVENTS.NO_DATA);
                return;
            }

            const i = this._fieldIndex;
            const unique = [];
            const seen = new Set();
            for (const raw of rows) {
                const row = Array.isArray(raw) ? raw : Object.values(raw);
                const oppId = String(row[i.oppId] || "").trim();
                const name = String(row[i.name] || "").trim();
                const key = oppId || name;
                if (!key || seen.has(key)) continue;
                seen.add(key);
                unique.push(row);
            }

            this._opportunityRows = unique;
            this.opportunityOptions = unique.map((row) => {
                const oppId = String(row[i.oppId] || "").trim();
                const name = String(row[i.name] || "").trim();
                const key = oppId || name;
                return {
                    label: name || key,
                    value: key
                };
            });

            if (
                !this.selectedOpportunityKey ||
                !this.opportunityOptions.find((opt) => opt.value === this.selectedOpportunityKey)
            ) {
                this.selectedOpportunityKey = this.opportunityOptions[0]?.value || "";
            }

            const selectedRow =
                unique.find((row) => {
                    const oppId = String(row[i.oppId] || "").trim();
                    const name = String(row[i.name] || "").trim();
                    const key = oppId || name;
                    return key === this.selectedOpportunityKey;
                }) || unique[0];

            this._applySelectedRow(selectedRow);

            this._phase = "ready";
            this.sdk?.actions?.notifyLifecycleChange?.(LIFE_CYCLE_EVENTS.LOADED);
        } catch (err) {
            this.errorMessage = err.message || String(err);
            this._phase = "error";
            this.sdk?.actions?.notifyLifecycleChange?.(LIFE_CYCLE_EVENTS.ERROR);
        }
    }

    handleOpportunityChange(event) {
        this.selectedOpportunityKey = event.target.value;
        const i = this._fieldIndex;
        const selected =
            this._opportunityRows.find((row) => {
                const oppId = String(row[i.oppId] || "").trim();
                const name = String(row[i.name] || "").trim();
                const key = oppId || name;
                return key === this.selectedOpportunityKey;
            }) || this._opportunityRows[0];
        this._applySelectedRow(selected);
    }

    handleActionChange(event) {
        this.selectedActionApiName = event.target.value;
    }

    handleRunAction() {
        if (this.isRunActionDisabled) return;
        const quickActionUrl = `/lightning/action/quick/${this.selectedActionApiName}?recordId=${encodeURIComponent(this.opportunityId)}`;
        window.location.assign(quickActionUrl);
    }

    _applySelectedRow(row) {
        if (!row) return;
        const i = this._fieldIndex;
        this.opportunityName = String(row[i.name] || "");
        this.stageName = String(row[i.stage] || "");
        this.ownerName = String(row[i.owner] || "");
        this.leadSource = String(row[i.source] || "");
        this.nextStep = String(row[i.nextStep] || "");
        this.closeDate = String(row[i.closeDate] || "");
        this.opportunityId = String(row[i.oppId] || "");
        this.totalAmount = Number(row[i.amount]) || 0;
        this.expectedRevenue = Number(row[i.expectedRevenue]) || 0;
        this.probability = Number(row[i.probability]) || 0;
    }

    _fmtDollar(val) {
        if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
        if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
        if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
        return `$${Math.round(val).toLocaleString()}`;
    }

    _buildActionOptions() {
        const raw = (this.actionList || "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
        this.actionOptions = raw.map((apiName) => ({
            label: this._toActionLabel(apiName),
            value: apiName
        }));
        if (this.actionOptions.find((o) => o.value === this.defaultAction)) {
            this.selectedActionApiName = this.defaultAction;
        } else {
            this.selectedActionApiName = this.actionOptions[0]?.value || "";
        }
    }

    _toActionLabel(apiName) {
        const tail = apiName.includes(".") ? apiName.split(".").pop() : apiName;
        return tail
            .replace(/([A-Z])/g, " $1")
            .replace(/^./, (m) => m.toUpperCase())
            .trim();
    }
}
