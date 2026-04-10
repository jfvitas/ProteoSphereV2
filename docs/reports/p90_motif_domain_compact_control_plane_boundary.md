# P90 Motif/Domain Compact Control-Plane Boundary

This report-only note answers the control-plane question for the compact motif/domain preview family: it should not feed eligibility, it should not feed split, and it should not feed leakage governance yet.

- Policy family: `motif_domain_compact_family`
- Bundle policy label: `report_only_non_governing`
- Operator policy label: `report_only_non_governing`

## Source Artifacts

- [artifacts/status/p89_motif_domain_compact_preview_family.json](/D:/documents/ProteoSphereV2/artifacts/status/p89_motif_domain_compact_preview_family.json)
- [artifacts/status/dictionary_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/dictionary_preview.json)
- [artifacts/status/p72_dictionary_preview_review.json](/D:/documents/ProteoSphereV2/artifacts/status/p72_dictionary_preview_review.json)
- [artifacts/status/p71_namespace_inventory_preview_family.json](/D:/documents/ProteoSphereV2/artifacts/status/p71_namespace_inventory_preview_family.json)
- [artifacts/status/p46_motif_backbone_step1_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p46_motif_backbone_step1_contract.json)
- [artifacts/status/p47_motif_backbone_output_spec.json](/D:/documents/ProteoSphereV2/artifacts/status/p47_motif_backbone_output_spec.json)
- [artifacts/status/p48_motif_backbone_validation_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p48_motif_backbone_validation_contract.json)
- [artifacts/status/training_set_eligibility_matrix_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/training_set_eligibility_matrix_preview.json)
- [artifacts/status/entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [artifacts/status/missing_data_policy_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/missing_data_policy_preview.json)

## Decision

The compact family stays out of eligibility and split governance.

- `should_feed_eligibility`: `false`
- `should_feed_split`: `false`
- `should_feed_leakage_governance`: `false`
- `should_feed_operator_go_no_go`: `false`

The current truthful status for this family is `library_only`, with `audit_only` as the safest operator-facing framing.

## Why Not

- The family is a report-only dictionary preview slice, not a new biological acquisition family.
- It describes already-visible motif/domain namespaces instead of introducing new governed rows.
- The current eligibility and split surfaces are governed by protein, variant, structure, and ligand evidence, not by dictionary membership.
- ELM remains candidate-only and does not yet appear as a live namespace-bearing row in the dictionary preview.

## Current Boundary

The family is:

- `motif_domain_compact_preview_family`
- `compact_dictionary_preview_family`
- a dictionary lookup and packaging aid

It is not:

- a split input
- a leakage input
- an eligibility-driving task surface
- a release-grade acquisition family

## Next Unlock Condition

The first truthful governance unlock requires the compact family to become a governed motif/domain annotation slice with explicit accession, span, source-native id, and provenance pointers in the materialized summary library.

That means:

1. Rows must exist as materialized motif/domain annotation surfaces, not only as dictionary lookup rows.
1. Rows must keep source-native accession and explicit span joins.
1. A downstream task-facing surface must explicitly opt in before the family can govern eligibility.
1. A split or eligibility preview must say so directly instead of inferring governance from dictionary membership.

The first truthful governance effect after that is `library_only`, and `eligible_for_task` only becomes valid after a task-specific preview explicitly grants it.

## Policy Alignment

- `missing_data_policy_preview`: keep the family at `library_only` or `audit_only` until a task surface exists.
- `entity_split_candidate_preview`: do not change split behavior from this family alone.
- `training_set_eligibility_matrix_preview`: no new motif/domain governing rule is justified today.

## Truth Boundary

- This is a report-only artifact.
- It does not authorize the compact family to govern split, leakage, or task eligibility.
- It does not infer any new motif or domain rows.
- It does not override existing protein, variant, structure, or ligand governance surfaces.
- It does not claim release-grade or bundle-governed status.

## Bottom Line

The compact motif/domain family is useful for lookup and packaging, but it should remain non-governing until a future governed annotation slice and a task-specific preview explicitly promote it.
