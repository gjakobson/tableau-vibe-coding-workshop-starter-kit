# Tableau Next REST API Reference

Complete Salesforce REST API documentation for discovering and creating Tableau Next assets.

## Base URL

All endpoints use the base URL:
```
https://{instance}.salesforce.com/services/data/v66.0
```

Where `{instance}` is your Salesforce instance (e.g., `myorg` for `myorg.salesforce.com`)

**Important:** 
- Major version: `v66.0`
- Minor version: Use query parameter `?minorVersion=8` for Tableau endpoints (visualizations, dashboards)
- SDM endpoints: No minor version parameter needed

## Authentication

All requests require Bearer token authentication:

```bash
-H "Authorization: Bearer {access_token}"
-H "Content-Type: application/json"
```

**Getting an Access Token (workshop standard):**
- Salesforce CLI login: `sf org login web --alias <org>`
- Token retrieval: `sf org auth show-access-token --target-org <org> --json`
- Instance URL: `sf org display --target-org <org> --json`

**Required Permissions:**
- View Tableau Next Assets
- Create Tableau Next Assets
- Manage Tableau Next Assets (for updates/deletes)

---

## Discovery Endpoints

### List Semantic Models

Get all semantic models available to the authenticated user.

**Endpoint:** `GET /ssot/semantic/models`

**Request:**
```bash
curl -X GET \
  "https://{instance}.salesforce.com/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer {access_token}"
```

**Response:**
```json
{
  "semantic_models": [
    {
      "id": "0FKxx0000000001",
      "apiName": "Sales_Analytics_Model",
      "label": "Sales Analytics",
      "description": "Sales performance metrics and trends",
      "dataspace": "default",
      "categories": ["Sales"],
      "createdDate": "2024-01-15T10:30:00Z",
      "lastModifiedDate": "2024-02-20T14:45:00Z"
    }
  ],
  "count": 1
}
```

**Query Parameters:**
- `limit` (integer): Maximum results to return
- `offset` (integer): Pagination offset
- `category` (string): Filter by category (Sales, Marketing, Service, etc.)
- `searchTerm` (string): Search in name/description

### Get Semantic Model Definition

Retrieve complete structure of a semantic model including objects, dimensions, and measures.

**Endpoint:** `GET /ssot/semantic/models/{sdmApiNameOrId}`

**Request:**
```bash
curl -X GET \
  "https://{instance}.salesforce.com/services/data/v66.0/ssot/semantic/models/Sales_Analytics_Model" \
  -H "Authorization: Bearer {access_token}"
```

**Response Structure:**
```json
{
  "id": "0FKxx0000000001",
  "apiName": "Sales_Analytics_Model",
  "label": "Sales Analytics",
  "dataspace": "default",
  "semanticDataObjects": [
    {
      "apiName": "Opportunity",
      "label": "Opportunities",
      "dataObjectName": "Opportunity__dlm",
      "semanticDimensions": [
        {
          "apiName": "Region",
          "label": "Region",
          "fieldName": "Region__c",
          "dataType": "Text",
          "displayCategory": "Discrete",
          "semanticDataType": "None"
        },
        {
          "apiName": "Close_Date",
          "label": "Close Date",
          "fieldName": "CloseDate",
          "dataType": "Date",
          "displayCategory": "Continuous"
        }
      ],
      "semanticMeasurements": [
        {
          "apiName": "Amount",
          "label": "Amount",
          "fieldName": "Amount",
          "dataType": "Number",
          "aggregationType": "Sum",
          "displayCategory": "Continuous",
          "decimalPlace": 2
        }
      ]
    }
  ],
  "semanticMetrics": [
    {
      "apiName": "Total_Revenue_mtc",
      "label": "Total Revenue",
      "description": "Sum of all opportunity amounts",
      "aggregationType": "Sum"
    }
  ]
}
```

**Key Fields to Extract:**
- `semanticDataObjects[].apiName` → Use as `objectName` in visualizations
- `semanticDimensions[].apiName` or `.fieldName` → Use as `fieldName` for dimensions
- `semanticMeasurements[].apiName` or `.fieldName` → Use as `fieldName` for measures
- `semanticMetrics[].apiName` → Use for metric widgets

---

## Creation Endpoints

### Create Visualization

Create a new visualization in Tableau Next.

**Endpoint:** `POST /tableau/visualizations?minorVersion=8`

**Request:**
```bash
curl -X POST \
  "https://{instance}.salesforce.com/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Revenue_by_Region",
    "label": "Revenue by Region",
    "dataSource": {
      "name": "Sales_Analytics_Model",
      "type": "SemanticModel"
    },
    "workspace": {
      "name": "Sales_Workspace"
    },
    "fields": { ... },
    "visualSpecification": { ... }
  }'
```

**Response:**
```json
{
  "id": "0FLxx0000000001",
  "name": "Revenue_by_Region",
  "label": "Revenue by Region",
  "url": "https://{instance}.salesforce.com/analytics/visualization/0FLxx0000000001",
  "createdDate": "2024-02-25T15:30:00Z"
}
```

**Status Codes:**
- `201 Created`: Visualization created successfully
- `400 Bad Request`: Invalid JSON structure or missing required fields
- `401 Unauthorized`: Invalid or expired token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: SDM or workspace not found
- `500 Internal Server Error`: Server-side error

### Create Dashboard

Create a dashboard with multiple widgets.

**Endpoint:** `POST /tableau/dashboards?minorVersion=8`

**Request:**
```bash
curl -X POST \
  "https://{instance}.salesforce.com/services/data/v66.0/tableau/dashboards?minorVersion=8" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

**Response:**
```json
{
  "id": "0FMxx0000000001",
  "name": "Sales_Dashboard",
  "label": "Sales Dashboard",
  "url": "https://{instance}.salesforce.com/analytics/dashboard/0FMxx0000000001"
}
```

### Create Workspace

Create a workspace to organize visualizations and dashboards.

**Endpoint:** `POST /tableau/workspaces`

**Request:**
```bash
curl -X POST \
  "https://{instance}.salesforce.com/services/data/v66.0/tableau/workspaces" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales_Workspace",
    "label": "Sales Analytics Workspace",
    "description": "Workspace for sales team dashboards"
  }'
```

**Response:**
```json
{
  "id": "0FNxx0000000001",
  "name": "Sales_Workspace",
  "label": "Sales Analytics Workspace"
}
```

---

## Retrieval Endpoints

### Get Visualization

Retrieve a visualization by ID or API name.

**Endpoint:** `GET /tableau/visualizations/{visualizationIdOrApiName}?minorVersion=8`

**Request:**
```bash
curl -X GET \
  "https://{instance}.salesforce.com/services/data/v66.0/tableau/visualizations/Revenue_by_Region?minorVersion=8" \
  -H "Authorization: Bearer {access_token}"
```

**Response:** Complete visualization JSON with all fields and specifications

### List Visualizations

Get all visualizations available to the user.

**Endpoint:** `GET /tableau/visualizations`

**Query Parameters:**
- `limit`: Maximum results
- `offset`: Pagination offset
- `workspaceId`: Filter by workspace

### Get Dashboard

Retrieve dashboard configuration.

**Endpoint:** `GET /tableau/dashboards/{dashboardIdOrApiName}`

### List Dashboards

**Endpoint:** `GET /tableau/dashboards`

### Get Workspace

**Endpoint:** `GET /tableau/workspaces/{workspaceIdOrApiName}`

### List Workspaces

**Endpoint:** `GET /tableau/workspaces`

---

## Update Endpoints

### Update Visualization

Modify an existing visualization.

**Endpoint:** `PATCH /tableau/visualizations/{visualizationIdOrApiName}?minorVersion=8`

**Request:**
```bash
curl -X PATCH \
  "https://{instance}.salesforce.com/services/data/v66.0/tableau/visualizations/Revenue_by_Region?minorVersion=8" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Updated Revenue by Region",
    "visualSpecification": { ... }
  }'
```

**Note:** Partial updates supported - only include fields to change

### Update Dashboard

**Endpoint:** `PATCH /tableau/dashboards/{dashboardIdOrApiName}`

---

## Delete Endpoints

### Delete Visualization

**Endpoint:** `DELETE /tableau/visualizations/{visualizationIdOrApiName}?minorVersion=8`

```bash
curl -X DELETE \
  "https://{instance}.salesforce.com/services/data/v66.0/tableau/visualizations/Revenue_by_Region?minorVersion=8" \
  -H "Authorization: Bearer {access_token}"
```

**Response:** `204 No Content` on success

### Delete Dashboard

**Endpoint:** `DELETE /tableau/dashboards/{dashboardIdOrApiName}`

---

## Error Responses

All endpoints return structured error responses:

```json
{
  "error": {
    "code": "INVALID_FIELD",
    "message": "Field 'Region' not found in semantic model 'Sales_Analytics_Model'",
    "details": {
      "fieldName": "Region",
      "objectName": "Opportunity",
      "availableFields": ["Account_Name", "Close_Date", "Amount"]
    }
  }
}
```

**Common Error Codes:**
- `INVALID_TOKEN`: Authentication token is invalid or expired
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `RESOURCE_NOT_FOUND`: SDM, workspace, or visualization not found
- `INVALID_FIELD`: Field reference doesn't exist in SDM
- `INVALID_JSON`: Malformed JSON structure
- `VALIDATION_ERROR`: JSON structure valid but business rules violated

---

## Rate Limits

Salesforce API rate limits apply:
- **Standard**: 15,000 API requests per 24 hours per org
- **Unlimited**: 25,000 API requests per 24 hours per org
- **Per User**: Additional limits may apply per user

**Best Practices:**
- Batch operations when possible
- Cache SDM definitions (they change infrequently)
- Use exponential backoff for retries

---

## Complete Request Example

**1. Discover SDM:**
```bash
curl -X GET \
  "https://myorg.salesforce.com/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer 00Dxx0000000001!..."
```

**2. Get SDM Definition:**
```bash
curl -X GET \
  "https://myorg.salesforce.com/services/data/v66.0/ssot/semantic/models/Sales_Analytics_Model" \
  -H "Authorization: Bearer 00Dxx0000000001!..."
```

**3. Create Visualization:**
```bash
curl -X POST \
  "https://myorg.salesforce.com/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer 00Dxx0000000001!..." \
  -H "Content-Type: application/json" \
  -d @revenue_by_region.json
```

**4. Verify Creation:**
```bash
curl -X GET \
  "https://myorg.salesforce.com/services/data/v66.0/tableau/visualizations/Revenue_by_Region?minorVersion=8" \
  -H "Authorization: Bearer 00Dxx0000000001!..."
```

---

## Additional Resources

- [Salesforce Tableau Next REST API Docs](https://developer.salesforce.com/docs/analytics/tableau-next-rest-api/guide/resources_overview.html)
- [Salesforce CLI Auth Commands](https://developer.salesforce.com/docs/atlas.en-us.sfdx_cli_reference.meta/sfdx_cli_reference/cli_reference_org_commands_unified.htm)
- [SKILL.md](SKILL.md) - Main authoring workflow
- [chart-catalog.md](chart-catalog.md) - Visualization templates
- [examples.md](examples.md) - Complete workflows
