# Reference: LWC LLM Chat Add-On (Workshop Step)

Use this as a separate step after the base card is already working.

---

## When to use

When the user says:

- "add chat to the card"
- "add an LLM copilot panel"
- "let me ask questions about the selected opportunity"

---

## Workshop sequence

1. Build and validate the base card first.
2. Add this chat add-on as a distinct step.
3. Confirm chat scaffold works in dashboard.
4. Optionally wire real Models API in Apex.

---

## Included scaffolding in this repo

- LWC chat panel:
  - `force-app/main/default/lwc/opportunityCardChat/opportunityCardChat.js`
  - `force-app/main/default/lwc/opportunityCardChat/opportunityCardChat.html`
  - `force-app/main/default/lwc/opportunityCardChat/opportunityCardChat.css`
  - `force-app/main/default/lwc/opportunityCardChat/opportunityCardChat.js-meta.xml`
- Apex controller scaffold:
  - `force-app/main/default/classes/OpportunityCardChatController.cls`
  - `force-app/main/default/classes/OpportunityCardChatController.cls-meta.xml`

This scaffold compiles and runs without Einstein enabled. It returns a context-aware placeholder answer.

---

## To enable real LLM answers

Replace the placeholder section in:

- `OpportunityCardChatController.chatOpportunity()`

with your org's approved Apex LLM invocation pattern (for example, `aiplatform.ModelsAPI` if available in the target org).

---

## Prompting guidance for future runs

Use this exact intent:

> "Add the LLM chat add-on to the opportunity card using ref-lwc-llm-chat.md as a separate workshop step."

