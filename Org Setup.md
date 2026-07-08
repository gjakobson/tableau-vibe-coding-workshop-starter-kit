# Org Setup

This document is the exact Salesforce org setup needed so new training orgs work with this workshop immediately.

Use this for:
- Manual org prep by admins
- Automated org patching/provisioning pipelines

---

## 1) What this workflow depends on

The workshop flow in this repo depends on:
1. Custom Lightning Web Components (LWC) for dashboard extensions
2. Apex classes used by LWC (including Models API chat callout)
3. Tableau Next dashboard assets that include the custom extension
4. Salesforce Quick Actions (for example, `Global.LogACall`)
5. Models API access (Einstein/Agentforce side) for real AI answers

If any of the above is missing, parts of the workshop still load, but features can degrade (for example, fallback chat text instead of real model output).

---

## 2) Org feature prerequisites

Configure these in each new org:

1. **Lightning + LWC support**
   - Must allow deploying and running LWC components.

2. **Apex execution enabled**
   - Needed for server-side chat controller.

3. **Models API / Einstein availability**
   - Org must have access to `aiplatform.ModelsAPI`.
   - A usable default model must be available (current code uses `sfdc_ai__DefaultOpenAIGPT4OmniMini`).

4. **Tableau Next / Dashboard extension compatibility**
   - Org must support Tableau dashboard extension widgets for custom components.

5. **Quick Action availability**
   - Ensure `Global.LogACall` exists and is enabled for users.

---

## 3) Metadata that must be deployed

Deploy the following metadata from this repo to each new org:

### Apex
- `force-app/main/default/classes/OpportunityCardChatController.cls`
- `force-app/main/default/classes/OpportunityCardChatController.cls-meta.xml`

### LWC bundle (primary)
- `force-app/main/default/lwc/opportunityProfileCard/opportunityProfileCard.js`
- `force-app/main/default/lwc/opportunityProfileCard/opportunityProfileCard.html`
- `force-app/main/default/lwc/opportunityProfileCard/opportunityProfileCard.css`
- `force-app/main/default/lwc/opportunityProfileCard/opportunityProfileCard.js-meta.xml`

### Optional LWC scaffold (separate chat add-on pattern)
- `force-app/main/default/lwc/opportunityCardChat/*`

---

## 4) Dashboard patching required

After metadata deploy, each org's training dashboard must include the extension widget.

Current dashboard API name used in this repo:
- `gabe_sales_pipeline_dashboard`

Current extension widget name:
- `ext_opportunity_profile_card`

Current LWC fully-qualified component name:
- `c:opportunityProfileCard`

The widget is patched into dashboard layout via API scripts in this repo. The layout height/rowspan also needs to be large enough to avoid inner scrolling.

Scripts currently used:
- `_add_opportunity_profile_card_to_dashboard.py`
- `_resize_opportunity_profile_card.py`

If your automation framework does not run these scripts directly, replicate their PATCH behavior:
1. Insert/update extension widget pointing to `c:opportunityProfileCard`
2. Ensure widget layout cell exists on the page
3. Set a sufficiently large `rowspan` (current target used: `34`)

---

## 5) Required extension properties

When provisioning the extension widget, set these properties (defaults shown):

- `sdmName`: `WorkshopModel`
- `sdoName`: `Opportunity`
- `queryLimit`: `500`
- `nameField`: `Name`
- `stageField`: `Opportunity_Stage`
- `amountField`: `Total_Amount`
- `expectedRevenueField`: `Expected_Revenue_Amount`
- `probabilityField`: `Probability`
- `ownerField`: `OwnerUser`
- `leadSourceField`: `Lead_Source`
- `closeDateField`: `Close_Date`
- `nextStepField`: `Next_Step`
- `idField`: `Opportunity_Id`
- `actionList`: `Global.LogACall,Global.NewTask,Global.NewEvent`
- `defaultAction`: `Global.LogACall`
- `debugMode`: `true` (recommended during setup), can be `false` for production-like runs

---

## 6) Permissions checklist (user profile/permset)

Training users should have:
1. Access to the deployed Apex class `OpportunityCardChatController`
2. Access to LWC dashboard extension execution
3. Permission to use the target dashboard/workspace
4. Permission to run Quick Actions (`Global.LogACall`)
5. Permission/license to use Models API features in the org

---

## 7) Post-provision validation (must pass)

Run this smoke test in every newly provisioned org:

1. Open the target dashboard and confirm the opportunity card renders.
2. Confirm no inner scroll bar in the card area (or acceptable size if layout is constrained by design).
3. Ask a chat question and verify:
   - A structured answer returns (Top Risks / Confidence Read / Next Best Actions)
   - Follow-up call-to-action appears below the answer
4. Click `Set up call now` and verify Salesforce opens `Log a Call`.
5. Use the action dropdown and click `Run`; verify the quick action opens successfully.

---

## 8) Automation order of operations (recommended)

For each new org:
1. Enable org features/licenses required above.
2. Deploy metadata (Apex + LWC).
3. Patch dashboard widgets/layout.
4. Assign permission sets/profiles.
5. Run smoke test and mark org as training-ready.

---

## 9) Notes for AWS-streamed Windows training environment

This document is org-side setup only. In addition, the streamed image should include:
- Salesforce CLI (`sf`)
- Python 3.x + `pip`
- Repo checkout + dependencies

Those image prerequisites are not optional if workshop operators need to run local deployment or dashboard patch scripts.
