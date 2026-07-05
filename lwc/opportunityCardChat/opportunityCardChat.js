import { LightningElement, api, track } from "lwc";
import chatOpportunity from "@salesforce/apex/OpportunityCardChatController.chatOpportunity";

const QUERY_LIMIT_DEFAULT = 200;

export default class OpportunityCardChat extends LightningElement {
    @api sdk;
    @api sdmName = "WorkshopModel";
    @api sdoName = "Opportunity";
    @api queryLimit = QUERY_LIMIT_DEFAULT;

    @api nameField = "Name";
    @api stageField = "Opportunity_Stage";
    @api amountField = "Total_Amount";
    @api probabilityField = "Probability";
    @api leadSourceField = "Lead_Source";
    @api nextStepField = "Next_Step";
    @api idField = "Opportunity_Id";

    @track opportunityOptions = [];
    @track selectedOpportunityKey = "";
    @track question = "";
    @track answer = "";
    @track isBusy = false;
    @track errorMessage = "";

    _rows = [];
    _fieldIndex = {};
    _unsubscribes = [];

    get hasRows() {
        return this.opportunityOptions.length > 0;
    }

    get isAskDisabled() {
        return !this.selectedOpportunityKey || !this.question.trim() || this.isBusy;
    }

    connectedCallback() {
        if (!this.sdk) return;
        this._subscribeEvents();
        this._registerQuery();
    }

    disconnectedCallback() {
        this._unsubscribes.forEach((fn) => typeof fn === "function" && fn());
        this._unsubscribes = [];
    }

    _subscribeEvents() {
        if (!this.sdk?.on) return;
        this._unsubscribes.push(
            this.sdk.on("filterChange", () => {}),
            this.sdk.on("parameterChange", () => {}),
            this.sdk.on("selectionChange", () => {}),
            this.sdk.on("dataUpdate", (payload) => this._processRows(payload))
        );
    }

    _registerQuery() {
        const fields = [
            { model: `${this.sdoName}.${this.nameField}`, rowGrouping: true },
            { model: `${this.sdoName}.${this.stageField}`, rowGrouping: true },
            { model: `${this.sdoName}.${this.leadSourceField}`, rowGrouping: true },
            { model: `${this.sdoName}.${this.nextStepField}`, rowGrouping: true },
            { model: `${this.sdoName}.${this.idField}`, rowGrouping: true },
            { model: `${this.sdoName}.${this.amountField}`, aggregationType: "SUM" },
            { model: `${this.sdoName}.${this.probabilityField}`, aggregationType: "AVG" }
        ];
        this._fieldIndex = {
            name: 0,
            stage: 1,
            leadSource: 2,
            nextStep: 3,
            oppId: 4,
            amount: 5,
            probability: 6
        };
        this.sdk.registerFieldsForQuery(fields, this.sdmName, {
            limit: parseInt(this.queryLimit, 10) || QUERY_LIMIT_DEFAULT
        });
    }

    _processRows(payload) {
        const rows = payload?.rows || payload?.data || payload;
        if (!Array.isArray(rows) || rows.length === 0) {
            this._rows = [];
            this.opportunityOptions = [];
            this.selectedOpportunityKey = "";
            return;
        }

        const i = this._fieldIndex;
        const unique = [];
        const seen = new Set();
        for (const raw of rows) {
            const row = Array.isArray(raw) ? raw : Object.values(raw);
            const key = String(row[i.oppId] || row[i.name] || "").trim();
            if (!key || seen.has(key)) continue;
            seen.add(key);
            unique.push(row);
        }
        this._rows = unique;
        this.opportunityOptions = unique.map((row) => {
            const key = String(row[i.oppId] || row[i.name] || "").trim();
            return { label: String(row[i.name] || key), value: key };
        });
        if (!this.selectedOpportunityKey || !this.opportunityOptions.find((o) => o.value === this.selectedOpportunityKey)) {
            this.selectedOpportunityKey = this.opportunityOptions[0]?.value || "";
        }
    }

    handleOpportunityChange(event) {
        this.selectedOpportunityKey = event.target.value;
    }

    handleQuestionChange(event) {
        this.question = event.target.value || "";
    }

    async handleAsk() {
        this.errorMessage = "";
        this.isBusy = true;
        try {
            const row = this._selectedRow();
            const i = this._fieldIndex;
            const result = await chatOpportunity({
                request: {
                    opportunityId: String(row[i.oppId] || ""),
                    opportunityName: String(row[i.name] || ""),
                    stage: String(row[i.stage] || ""),
                    amount: Number(row[i.amount]) || 0,
                    probability: Number(row[i.probability]) || 0,
                    leadSource: String(row[i.leadSource] || ""),
                    nextStep: String(row[i.nextStep] || ""),
                    userQuestion: this.question.trim()
                }
            });
            this.answer = result?.answer || "No response returned.";
        } catch (err) {
            this.errorMessage = err?.body?.message || err?.message || "Unable to run chat.";
        } finally {
            this.isBusy = false;
        }
    }

    _selectedRow() {
        const i = this._fieldIndex;
        return (
            this._rows.find((row) => {
                const key = String(row[i.oppId] || row[i.name] || "").trim();
                return key === this.selectedOpportunityKey;
            }) || this._rows[0] || []
        );
    }
}
