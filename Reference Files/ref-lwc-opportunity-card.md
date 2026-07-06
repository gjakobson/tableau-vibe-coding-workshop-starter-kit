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
2. Reuse/extend `lwc/opportunityProfileCard` as the production baseline.
3. Keep the dark card UX and existing robust wiring.
4. Ignore legacy ad-hoc artifacts (`*OppViewer*`, `*_deploy_opp_viewer.py`) even if present in workspace.

If the request is for chart visuals (sunburst/treemap/radar/etc), use `ref-viz-extensions.md` instead.

---

## Required behavior (acceptance criteria)

1. Dropdown is populated from filter-aware dashboard data (`registerFieldsForQuery` + `dataUpdate`).
2. Selecting a record updates the displayed opportunity fields immediately.
3. Card shows business-useful details (stage, amount, probability, owner, source, next step, dates, ID).
4. Card is usable in dashboard layout without tiny/placeholder rendering.
5. If actions are enabled, action launch behavior is tested in-dashboard.

Do not mark complete unless all pass.

---

## Implementation defaults

Use/keep these defaults unless user asks otherwise:
- `sdmName = WorkshopModel`
- `sdoName = Opportunity`
- `queryLimit = 500`
- `actionList = Global.LogACall,Global.NewTask,Global.NewEvent`
- `defaultAction = Global.LogACall`

---

## Dashboard placement requirement

After deploy, patch dashboard layout so the extension cell has enough height/rowspan.

If the card has an inner scrollbar and content is clipped:
1. Increase widget `rowspan` in dashboard layout.
2. Re-save dashboard via API PATCH.

---

## Suggested operator prompt (copy/paste)

Use this when you want consistent output quality:

> "Add an opportunity detail external card using the existing `lwc/opportunityProfileCard` production pattern.  
> Keep filter-aware dropdown selection and full property display.  
> Keep production styling.  
> Deploy and patch dashboard layout height so no cramped inner scroll."

---

## Add-ons (optional)

- Salesforce actions on the card → read `Reference Files/ref-lwc-salesforce-actions.md`
- LLM chat panel on the card → read `Reference Files/ref-lwc-llm-chat.md`
