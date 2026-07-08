# Org Setup - Automation Spec

Use this as the machine-oriented checklist for org auto-provisioning.

---

## Provisioning Inputs

```yaml
dashboard_api_name: gabe_sales_pipeline_dashboard
extension_widget_name: ext_opportunity_profile_card
extension_component_fqn: c:opportunityProfileCard
extension_target_rowspan: 34
models_api_default_model: sfdc_ai__DefaultOpenAIGPT4OmniMini
```

---

## Required Org Capabilities

```yaml
org_features:
  - lightning_web_components_enabled
  - apex_runtime_enabled
  - tableau_dashboard_extensions_enabled
  - models_api_available_in_aiplatform_namespace
  - quick_action_global_log_a_call_available
```

---

## Required Metadata Deploy Set

```yaml
deploy_paths:
  - force-app/main/default/classes/OpportunityCardChatController.cls
  - force-app/main/default/classes/OpportunityCardChatController.cls-meta.xml
  - force-app/main/default/lwc/opportunityProfileCard/**
  - force-app/main/default/lwc/opportunityCardChat/**
```

---

## Dashboard Extension Patch Contract

```yaml
extension_widget:
  name: ext_opportunity_profile_card
  type: extension
  componentType: Custom
  parameters:
    fullyQualifiedName: c:opportunityProfileCard
    properties:
      sdmName: WorkshopModel
      sdoName: Opportunity
      queryLimit: 500
      nameField: Name
      stageField: Opportunity_Stage
      amountField: Total_Amount
      expectedRevenueField: Expected_Revenue_Amount
      probabilityField: Probability
      ownerField: OwnerUser
      leadSourceField: Lead_Source
      closeDateField: Close_Date
      nextStepField: Next_Step
      idField: Opportunity_Id
      actionList: Global.LogACall,Global.NewTask,Global.NewEvent
      defaultAction: Global.LogACall
      debugMode: true
```

```yaml
layout_patch_rules:
  - ensure_widget_cell_exists: true
  - widget_cell_name: ext_opportunity_profile_card
  - widget_cell_rowspan_min: 34
  - preserve_existing_layout_structure: true
```

---

## Security / Access Requirements

```yaml
permissions_required:
  - apex_class_access:
      - OpportunityCardChatController
  - dashboard_access:
      - gabe_sales_pipeline_dashboard
  - quick_action_access:
      - Global.LogACall
  - models_api_access: true
```

---

## Post-Provision Smoke Tests

```yaml
smoke_tests:
  - open_dashboard: gabe_sales_pipeline_dashboard
  - verify_extension_renders: ext_opportunity_profile_card
  - verify_no_inner_scrollbar_or_acceptable_height: true
  - ask_chat_question_and_verify_structured_answer: true
  - click_inline_set_up_call_and_verify_log_a_call_opens: true
  - run_action_dropdown_and_verify_action_launch: true
```

---

## Recommended Automation Sequence

```yaml
run_order:
  - enable_org_features
  - deploy_metadata
  - patch_dashboard_widget_and_layout
  - assign_permissions
  - execute_smoke_tests
```

---

## Non-Org (Image) Prereqs for Workshop Operators

```yaml
training_image_requirements:
  - sf_cli_installed
  - python3_installed
  - pip_installed
  - repo_cloned
  - python_requirements_installed
```
