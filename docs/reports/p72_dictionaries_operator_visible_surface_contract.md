# p72 Dictionaries Operator-Visible Surface Contract

This report-only contract proposes the smallest safe operator-visible surface for the new `dictionaries` preview family.

## Dashboard Review

The live operator dashboard is still release-blocked:

- `operator_go_no_go = no-go`
- `dashboard_status = blocked_on_release_grade_bar`
- `release_grade_status = blocked_on_release_grade_bar`
- `ready_for_release = false`
- `release_grade_blocked = true`

That means any dictionaries surface must stay report-only and must not weaken operator-state validation.

## `validate_operator_state` Expectations

The operator-state validator expects the current closed schema to remain intact:

- the top-level operator snapshot sections stay the same
- the dashboard section stays read-only and conservative
- the current blocked labels stay unchanged
- no new `dictionaries` field should be added to the operator state contract

The safest reading is that dictionaries visibility should be external to `operator_state`, not a schema expansion.

## Smallest Safe Surface

The smallest safe operator-visible surface is a single summary card:

- `family_name = dictionaries`
- `current_record_count = 0`
- `bundle_included = false`
- `manifest_status = preview_generated_verified_assets`
- `validation_status = reserved`

It can cite the current live namespace candidates from the summary-library inventory, but it should remain a single row and it must not claim any materialized dictionary payload.

## Why This Is the Right Size

- It keeps `validate_operator_state` unchanged and passing.
- It matches the current bundle manifest, which still records `dictionaries` as included=false and count=0.
- It gives operators a visible placeholder without inventing a new operator-state section or mutating the bundle.

## Expansion Gate

If dictionaries later become truly materialized, the next expansion can be the seven-row namespace lookup table from the p71 family proposal. That later step still should not require an operator-state schema change.

## Grounding

- [`artifacts/schemas/operator_state.schema.json`](D:/documents/ProteoSphereV2/artifacts/schemas/operator_state.schema.json)
- [`docs/reports/operator_state_contract.md`](D:/documents/ProteoSphereV2/docs/reports/operator_state_contract.md)
- [`docs/reports/operator_visibility_validation.md`](D:/documents/ProteoSphereV2/docs/reports/operator_visibility_validation.md)
- [`scripts/validate_operator_state.py`](D:/documents/ProteoSphereV2/scripts/validate_operator_state.py)
- [`runs/real_data_benchmark/full_results/operator_dashboard.json`](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [`artifacts/status/lightweight_bundle_manifest.json`](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [`artifacts/status/p71_dictionaries_family_proposal.json`](D:/documents/ProteoSphereV2/artifacts/status/p71_dictionaries_family_proposal.json)
- [`artifacts/status/p71_dictionaries_family_risk_review.json`](D:/documents/ProteoSphereV2/artifacts/status/p71_dictionaries_family_risk_review.json)
- [`artifacts/status/p71_namespace_inventory_preview_family.json`](D:/documents/ProteoSphereV2/artifacts/status/p71_namespace_inventory_preview_family.json)
- [`artifacts/status/p71_proteosphere_lite_dictionaries_family_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p71_proteosphere_lite_dictionaries_family_contract.json)
