# Reference: LWC Salesforce Actions (Workshop Add-On)

Use this when the user already has an LWC card/table extension and wants to add a Salesforce action picker later as a separate step.

---

## Goal

Add a control that lets users:

1. pick a Salesforce quick action
2. run it for the currently selected/displayed record

---

## Recommended pattern

- Use a direct Lightning quick-action URL (same pattern used in working table/action flows):
  - `/lightning/action/quick/<ActionApiName>?recordId=<recordId>`
- Keep actions configurable from widget properties:
  - `actionList` (comma-separated quick action API names)
  - `defaultAction`

```javascript
const quickActionUrl = `/lightning/action/quick/${selectedActionApiName}?recordId=${encodeURIComponent(currentRecordId)}`;
window.location.assign(quickActionUrl);
```

---

## Default action list for Opportunity cards

- `Global.LogACall`
- `Global.NewTask`
- `Global.NewEvent`

These can be overridden in dashboard widget properties.

---

## UX guidance

- Put action controls in the card header near the record selector.
- Keep a dedicated `Run` button.
- Disable button when:
  - no current record id
  - no selected action

---

## Workshop sequencing guidance

Use this as a separate stage:

1. Build base card extension first (display-only / selector)
2. Validate data display
3. Add Salesforce action picker using this reference
4. Validate each action against current displayed record

