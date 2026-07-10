# Reference: Opportunity Detail Card Extension (Workshop)

Use this when the user asks in plain English for a card like:
- "add an external viz card allowing me to select from a dropdown of opportunities and see all properties"
- "build an opportunity detail card with a selector"
- "add a card that shows full opportunity details"

The user does **not** need to mention LWC.

---

## Routing rule

For this request type:
1. Do **not** scaffold a bare/minimal new component from scratch.
2. Reuse/extend `force-app/main/default/lwc/opportunityProfileCard` as the production baseline.
3. Keep the dark card UX and existing robust wiring.
4. Ignore legacy ad-hoc artifacts (`*OppViewer*`, `*_deploy_opp_viewer.py`) even if present in workspace.
5. Treat creation of any new one-off viewer component for this intent (for example `*OppViewer*` or `*opportunitiesCard*`) as an implementation error.

If the request is for chart visuals (sunburst/treemap/radar/etc), use `ref-viz-extensions.md` instead.

---

## Critical: SDM dimensions are NOT the list of queryable fields

**Read this before doing any field preflight.** The single biggest failure in this flow is inspecting the SDM's semantic dimension list, seeing that fields like `Opportunity Name`, `Lead Source`, or `Next Step` are absent, and wrongly concluding they must be added as new SDM dimensions before the card works. **Do not do this.**

- SDM semantic dimensions are a **curated, AI-surfaced subset** of the underlying DLO's columns — what Concierge and the semantic layer choose to expose.
- `registerFieldsForQuery` (the SDK call the card uses) operates at the **DLO layer**, not the SDM layer. It can query **any column in the underlying data lake object**, including columns that have no corresponding SDM dimension.
- The `opportunityProfileCard` component's default field apiNames (`nameField="Name"`, `leadSourceField="Lead_Source"`, `nextStepField="Next_Step"`, etc.) are **raw DLO references already validated against the `ssot__` CRM DLO schema**. They work even though those fields are not in the SDM dimension list. **Trust them and deploy as-is.**
- Only inspect the SDM dimension list if the user explicitly asks for a **new custom field that was never part of the production component**.

**The only preflight that matters:** confirm the **Opportunity SDO exists** in the selected model. If it does, the standard CRM fields (`Name`, `Lead_Source`, `Next_Step`, …) are in the underlying DLO and the component will query them. Do not gate on whether each card field is a declared SDM dimension.

**What the fix almost always is:** (1) set `sdmName` default in `opportunityProfileCard.js` and `.js-meta.xml` to the selected model's apiName, (2) deploy the component unchanged, (3) patch the dashboard to add the extension widget. No SDM changes.

---

## Required behavior (acceptance criteria)

1. Dropdown is populated from filter-aware dashboard data (`registerFieldsForQuery` + `dataUpdate`).
2. Selecting a record updates the displayed opportunity fields immediately.
3. Card shows business-useful details (stage, amount, probability, owner, source, next step, dates, ID).
4. Card is usable in dashboard layout without tiny/placeholder rendering.
5. If actions are enabled, action launch behavior is tested in-dashboard.
6. Preflight validation is completed before deploy: confirm the **Opportunity SDO exists** in the selected model. Do NOT gate on whether each card field is a declared SDM dimension — see "Critical: SDM dimensions are NOT the list of queryable fields" above.
7. Completion is blocked if dropdown options are empty after deploy/patch; fix wiring/layout (or the `sdmName`/DLO field defaults) and re-verify before marking done — but note an empty dropdown is almost never caused by a missing SDM dimension.

Do not mark complete unless all pass.

---

## Implementation defaults

Use/keep these defaults unless user asks otherwise:
- `sdmName = <selected model apiName from discovery>` (do not hardcode `WorkshopModel`)
- `sdoName = Opportunity` (if not present, stop and ask user which SDO should back the card)
- `queryLimit = 500`
- `actionList = Global.LogACall,Global.NewTask,Global.NewEvent`
- `defaultAction = Global.LogACall`

Field mapping policy for every org:
1. Confirm the Opportunity SDO exists in the selected model (a single `includeModelContent=true` GET). That is the whole preflight.
2. **Keep the component's built-in DLO field defaults** (`Name`, `Lead_Source`, `Next_Step`, `Amount`, `Probability`, `StageName`, `CloseDate`, owner, `Id`, …). These are raw `ssot__` CRM DLO references already validated to query correctly — they do NOT need to appear in the SDM dimension list. Only set `sdmName` to the selected model's apiName.
3. **Do NOT** map each card field against the SDM dimension list, and **do NOT** block completion because a field (e.g. `Opportunity Name`, `Lead Source`, `Next Step`) is absent from that list — it is expected to be absent; `registerFieldsForQuery` reads the DLO, not the SDM. Adding SDM dimensions is not part of this flow.
4. Only build a custom field mapping (and inspect the SDM/DLO for it) if the user explicitly requests a **new** field the production component doesn't already carry.

---

## Dashboard placement requirement

After deploy, patch dashboard layout so the extension cell has enough height/rowspan.

If the card has an inner scrollbar and content is clipped:
1. Increase widget `rowspan` in dashboard layout.
2. Re-save dashboard via API PATCH.

---

## Suggested operator prompt (copy/paste)

Use this when you want consistent output quality:

> "Add an opportunity detail external card using the existing `force-app/main/default/lwc/opportunityProfileCard` production pattern.  
> Keep filter-aware dropdown selection and full property display.  
> Keep production styling.  
> Deploy and patch dashboard layout height so no cramped inner scroll."

---

## Add-ons (optional)

- Salesforce actions on the card → read `Reference Files/ref-lwc-salesforce-actions.md`
- LLM chat panel on the card → read `Reference Files/ref-lwc-llm-chat.md`
