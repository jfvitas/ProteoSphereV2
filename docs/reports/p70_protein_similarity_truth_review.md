# P70 Protein Similarity Truth Review

This is a report-only review of [protein_similarity_signature_preview.json](D:/documents/ProteoSphereV2/artifacts/status/protein_similarity_signature_preview.json), [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), and [operator_dashboard.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json). It focuses on drift risk, what this family now unlocks, and what remains explicitly deferred.

## What This Family Truthfully Unlocks Now

The new protein similarity preview is real bundle/operator surface, not just a scratch artifact.

It now truthfully unlocks:

- an 11-row protein-family similarity preview
- one row per protein accession
- sequence-equivalence-based family labeling
- bundle inclusion for `protein_similarity_signatures`
- operator-dashboard wiring for the same preview surface

The live validation says the bundle manifest and the current preview are aligned. That matters because it means the bundle is not inventing a separate count or silently widening the family.

## Bundle And Operator Integration

The bundle manifest already includes `protein_similarity_signatures` with a record count of `11`, and the live validation surface says that count matches the current preview.

The operator dashboard also exposes the preview as complete, but the broader dashboard state is still:

- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`
- `ready_for_release = false`

So the family is integrated for preview-grade bundle and operator reporting, but it does not change the release gate.

## Drift Risks

The biggest drift risk is overreading the preview.

This surface is derived from protein spine and sequence-equivalence grouping, so it is truthful for operator grouping and planning, but it should not be mistaken for ligand similarity, interaction similarity, or a release-grade biological assertion.

Two smaller risks are worth keeping explicit:

- the preview must stay in lockstep with the manifest's `11` record count
- the presence of this family in the bundle must not be read as release readiness

The live validation and dashboard are aligned today, which is the right place for the preview to sit.

## What Remains Explicitly Deferred

The following are still out of scope:

- ligand similarity
- interaction similarity
- direct structure-backed variant joins
- release-grade promotion
- any claim that sequence-equivalence is a substitute for experimental validation

## Grounded Examples

- `P68871` and `P69905` show the globin portion of the preview is populated and visible in the bundle.
- `Q9NZD4` shows the preview is broader than globin and is not just a two-row special case.
- `P00387` shows the preview also contains singleton family labels from the same 11-protein slice.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim release-grade readiness that the dashboard explicitly denies.
