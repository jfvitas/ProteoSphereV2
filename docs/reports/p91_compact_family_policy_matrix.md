# P91 Compact Family Policy Matrix

This report-only note adds a coherent policy layer for the compact motif, interaction, and kinetics families across bundle and operator surfaces.

## Source Artifacts

- [artifacts/status/p89_motif_domain_compact_preview_family.json](/D:/documents/ProteoSphereV2/artifacts/status/p89_motif_domain_compact_preview_family.json)
- [artifacts/status/p90_motif_domain_compact_control_plane_boundary.json](/D:/documents/ProteoSphereV2/artifacts/status/p90_motif_domain_compact_control_plane_boundary.json)
- [artifacts/status/interaction_similarity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/interaction_similarity_signature_preview.json)
- [artifacts/status/interaction_similarity_operator_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/interaction_similarity_operator_handoff.json)
- [artifacts/status/sabio_rk_support_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/sabio_rk_support_preview.json)
- [artifacts/status/sabio_rk_support_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/sabio_rk_support_validation.json)
- [artifacts/status/kinetics_enzyme_support_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/kinetics_enzyme_support_preview.json)
- [artifacts/status/kinetics_enzyme_support_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/kinetics_enzyme_support_validation.json)
- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/training_set_eligibility_matrix_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/training_set_eligibility_matrix_preview.json)
- [artifacts/status/missing_data_policy_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/missing_data_policy_preview.json)

## Policy Labels

The policy layer uses three labels:

- `report_only_non_governing`
- `preview_bundle_safe_non_governing`
- `grounded_and_governing`

Current compact-family coverage is:

| Family | Bundle Label | Operator Label | Status |
|---|---|---|---|
| `motif_domain_compact_preview_family` | `preview_bundle_safe_non_governing` | `report_only_non_governing` | bundle-visible, non-governing |
| `interaction_similarity_compact_family` | `report_only_non_governing` | `report_only_non_governing` | operator-only, candidate-only |
| `kinetics_support_compact_family` | `report_only_non_governing` | `report_only_non_governing` | operator-only, consolidated SABIO/kinetics lane |

## Consolidation Rule

SABIO-RK support and kinetics/enzyme support should be presented as one operator family label:

- `kinetics_support_compact_family`

The separate artifacts remain useful as source surfaces, but they should be interpreted as aliases under that one policy family rather than as two ambiguous lanes.

## What Is Truthful Today

- The motif compact family is preview-bundle-safe but non-governing.
- The interaction compact family is report-only non-governing.
- The kinetics compact family is report-only non-governing.
- No compact family currently qualifies as `grounded_and_governing`.

## What Still Must Not Happen

- Do not let any of these compact families govern split or leakage by themselves.
- Do not claim live kinetic-law IDs or enzyme activity as verified.
- Do not promote the interaction similarity lane to bundle-safe until a real interaction family exists.

## Truth Boundary

- This is report-only.
- It consolidates SABIO-RK and kinetics/enzyme support for presentation only.
- It does not invent a grounded compact family where the repo does not yet show one.
- It does not authorize release-grade status for any compact family.

## Bottom Line

The compact policy layer is now coherent: one preview-bundle-safe motif family, two report-only non-governing operator families, and no compact family yet qualified as grounded_and_governing.
