# P67 Leakage Group Bundle Acceptance

This report-only note answers a narrow question: do `leakage_groups` now meet the intended iteration-two bar?

## Baseline

The lightweight bundle is still the verified preview baseline:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes

## Grounding

This acceptance is grounded in:

- [artifacts/status/leakage_group_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_group_preview.json)
- [artifacts/status/p64_bundle_iteration_two_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_bundle_iteration_two_contract.json)
- [artifacts/status/p66_structure_signature_bundle_integration_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p66_structure_signature_bundle_integration_contract.json)
- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)

## Intended Iteration-Two Bar

The intended bar for iteration two is:

- `leakage_groups` as the target family
- 11 rows total
- explicit `test`, `train`, and `val` coverage
- risk classes covering `candidate_overlap`, `structure_followup`, and `protein_only`

## Observed Preview

The current `leakage_group_preview.json` shows:

- 11 rows
- split group counts: 9 `test`, 1 `train`, 1 `val`
- risk class counts: 2 `candidate_overlap`, 2 `structure_followup`, 7 `protein_only`
- `ready_for_bundle_preview: true`

Observed accession groups:

- candidate overlap: `P68871`, `P69905`
- structure follow-up: `P04637`, `P31749`
- protein-only: `P00387`, `P02042`, `P02100`, `P09105`, `P69892`, `Q2TAC2`, `Q9NZD4`

## Acceptance Result

`leakage_groups` now meet the intended iteration-two bar.

That is true because the preview has the right row count, the split coverage is explicit, the intended risk classes are present, and the preview is explicitly marked ready for bundle preview.

## What This Does Not Mean

This acceptance does not promote the bundle manifest yet. It also does not claim release-grade completeness, and it does not imply that ligand or interaction families are ready.

## Bottom Line

The leakage-group preview is good enough for the intended iteration-two bar, but the bundle manifest still needs a separate promotion step before `leakage_groups` are materialized in the preview bundle itself.
