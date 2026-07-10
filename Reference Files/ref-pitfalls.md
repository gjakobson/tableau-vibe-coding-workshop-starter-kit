# Reference: All Common Pitfalls

Read this file at the start of every session — these are hard-won API constraints that apply across all steps.

---

## Authentication & Data Cloud

1. **Do not use the SF access token for Data Cloud API calls** — always complete the second token exchange at `/services/a360/token`.
9. **Semantics Layer API uses SF access token** — `/ssot/semantic/` endpoints live on SF instance, not DC instance.
19. **Semantic API version is v65.0** — use a separate `BASE_SEM` variable.
30. **Visualizations API requires v66.0** — v64.0 and v65.0 return `DOWNGRADE_VERSION_ERROR`.

## Semantic Data Model

2. **Do not leave field descriptions blank** — Concierge quality degrades sharply.
3. **Do not use abbreviations in field descriptions** — Concierge reads them literally.
4. **Do not use a flat single-table model** — always use at least a fact + one dimension table.
5. **Do not use snake_case field labels** — must be business-readable: `Deal Amount`, not `deal_amount`.
6. **Always log `resp.text` on failures** — `raise_for_status()` alone hides the actual API error.
10. **`directionality` values are `"Up"` and `"Down"`** — not `"INCREASING"` / `"DECREASING"`.
11. **`aggregationType` is `"None"` (string), not `null`**.
12. **Always set `agentEnabled: True`** — required for Concierge.
13. **PATCH on the main model URL is a FULL REPLACE** — never use PATCH to add sub-entities; use sub-resource POST endpoints.
14. **Semantic Metrics `measurementReference` can use either `calculatedFieldApiName` OR `tableFieldReference`** — `timeDimensionReference` should use the date-shift calc dimension for demo date-shifting.
15. **All dims in `insightsSettings` must also be in `additionalDimensions`** — missing causes 400.
16. **`joinType` must be `"Auto"` for model-level relationships** — explicit types only for logical views.
17. **Use `leftSemanticDefinitionApiName` / `rightSemanticDefinitionApiName`** — NOT `DeveloperName`.
18. **`queryUnrelatedDataObjects`** — `"Exception"` is a confirmed valid value; omitting is also fine.
20. **DLO field names have `__c` suffix** — always use `date__c`, `loan_amount__c`, etc.
21. **Always delete and recreate on re-run** — duplicate apiName returns an error.
22. **Logical views can use joins OR unions — never both** in the same logical view.
23. **Union schemas must align by position** — mismatched schemas cause silent data loss.
24. **Submetrics must reference an existing parent metric apiName** — create parent first.
25. **Parameters must be created before the calculated fields that reference them**.
26. **Groups and bins are dimensions, not measures** — do not assign `aggregationType` to them.
27. **`agentEnabled: True` alone is not enough** — user must also enable Analytics Agent Readiness in UI.
28. **Snapped metrics must never be summed across time** — use `aggregationType: "Sum"` + LOD filter or submetric filtered to `CurrentMonth`.
29. **SDM hard limits**: 500 semantic definitions total, max 100 objects at creation, max 20 additional dims per metric, max 9 objects in a union.
47. **`GET /ssot/semantic/models/{name}/metrics` returns `"metrics"` key, not `"semanticMetrics"`**.
49. **SDO `semanticMeasurements` must use `dataType: "Number"` for IngestAPI DLOs** — `"Currency"` rejected; use `"Currency"` only for calc measurements.
54. **`if r:` is always False for failed responses** — use `if r is not None:`.
58. **CRM date fields are stored as `DateTime`, not `Date`** — wrap with `DATE()` in date-shift calc dimension expression.

## Visualizations (STEP M)

31. **`fields` is a dict, not array** — `{"F1": {...}, "F2": {...}}`.
32. **`style.headers` must be omitted, not `{}`** — empty dict causes `JSON_PARSER_ERROR`.
33. **`allHeaders.fields` is required for dimension fields on the rows shelf** — omitting causes `INVALID_VISUALIZATION_METADATA`.
34. **`mode` must be `"Visualization"` for charts** — not `"Normal"`, not `"Table"`.
35. **Sorting bar charts by measure is not supported via API** — `sortOrders` only works when `mode="Table"`.
36. **`"UserAgg"` causes `ROW_LEVEL_CALC_AGG_VALIDATION_ERROR`** for row-level calcs — use `"Sum"` or `"Avg"`.
55. **Visualization POST response key is `name`, not `apiName`** — use `viz_result.get("apiName") or viz_result.get("name")`.
56. **Mark `size` and `isAutomaticSize` belong in `style.marks.ALL`, not in `visualSpecification.marks.ALL`** — Percentage range is 2–200 (minimum is 2, not 0 or 1). `isAutomaticSize` must be present alongside `size`.
62. **`sortOrders` in `visualSpecification` causes `JSON_PARSER_ERROR`** — belongs in `view.viewSpecification`.
72. **Cloned visualization payloads may include non-writable metadata (`permissions`, `sourceVersion`)** — strip these fields (and other unknown top-level keys) before POST.
73. **Use an allow-list for cloned visualization POST payloads** — keep only `name`, `label`, `description`, `dataSource`, `workspace`, `fields`, `interactions`, `view`, `visualSpecification`.

## Viz Actions (STEP M2)

63. **Viz click actions live in `interactions`, not `actions`** — the `actions` array always stays `[]`.
64. **Use `recordaction` for native SF actions; use `navigate` for URLs** — do not use `navigate` for Log a Call.
65. **`recordaction` requires an Action Table** — `mode: "Visualization"`, mark `"Text"`, `isAutomatic: true`, dims on `rows`, measures as `"Label"` encodings. Bar charts and `mode: "Table"` fail to resolve `recordId`.
66. **The record ID must appear TWICE in `fields`** — once on `rows` (clickable), once as `"Detail"` encoding.
67. **`Global.LogACall` is greyed out on User records** — works on Opportunity, Account, Contact only.
68. **All `fieldKey` / `field` / `destination.target` values are raw JSON strings on write** — GET returns them HTML-entity-encoded; do NOT use that format on write.
69. **Viz PATCH requires the full payload** — interactions-only PATCH is rejected. GET → swap interactions → strip read-only fields → PATCH with full payload.
70. **`{{fieldApiName}}` in a `navigate` URL substitutes the clicked mark's value at runtime** — use relative URLs (`/lightning/...`).
71. **In Action Table mode, `axis` must be `{}` and `marks.ALL.isAutomatic` must be `true`** — per-field axis config causes `INVALID_VISUALIZATION_METADATA`.

## Dashboard (STEP N)

37. **Dashboard `widgets` is a dict, not a list** — sending an array causes 500.
38. **Dashboard `style` uses `widgetStyle`** — not `"canvas"`.
39. **Dashboard `customViews` must be omitted** — `[]` causes `JSON_PARSER_ERROR`.
40. **Delete dashboards before visualizations in teardown**.
41. **Dashboard layout `style` must include cell spacing** — `{}` causes blank canvas.
42. **Dashboard page `name` must be a UUID** — plain strings cause blank canvas.
50. **Use SLDS 2.0 design tokens** — brand `#0176D3`, surface `#FFFFFF`, page bg `#F4F6F9`, border `#DDDBDA`, radius `4px`.
59. **Dashboard PATCH field-stripping rules** — strip `id`, `status`, `label` from widget top-level; strip `label` and `type` from each widget's `source`. Full payload required: `label`, `name`, `description`, `workspaceIdOrApiName`, `style`, `widgets`, `layouts`.
60. **Extension widget `source` field causes 403 on PATCH** — omit `source` entirely from extension widgets.
61. **Dashboard POST also rejects `source.type`** — strip `label` and `type` from every widget's `source` on POST too.
74. **KPI metric widgets must use metric `apiName` exactly** — do not derive `source.name` from label strings (e.g., `Total Sales` != `Total_Sales`).

## Data Ingestion

7. **Ingestion schema + stream is fully programmatic** — use `PUT /ssot/connections/{id}/schema` then `POST /ssot/data-streams`.
8. **PUT schema is a FULL REPLACE** — always GET first, strip read-only fields, merge, then PUT.
43. **Bulk ingest job list response key is `"data"`, not `"jobs"`**.
44. **Never construct the DLO name manually** — read from `GET /ssot/data-streams/{name}` → `dataLakeObjectInfo.name`.
45. **Always poll for DLO ACTIVE before ingesting** — submitting before ACTIVE causes silent data loss.
46. **Parallel bulk job submission is faster** — submit all jobs before waiting for any.
51. **`GET /ssot/data-lake-objects` does NOT return IngestAPI DLOs** — use `GET /ssot/data-streams/{name}`.
52. **Only PK field in `dataLakeFieldInputRepresentations`** — sending all fields causes "Illegal argument" on 2nd+ object.
53. **Schema PUT fields only accept `name`, `label`, `dataType`** — `isPrimaryKey` and `isEventTime` cause `JSON_PARSER_ERROR` here.
57. **Newly registered ingest schema objects return 404 for ~15–30s after DLO ACTIVE** — add retry logic with 15s backoff (up to 3 retries).

## Misc

48. **Mac notifications via `osascript -e` fail with em dash (`—`)** — write AppleScript to a tempfile instead.
