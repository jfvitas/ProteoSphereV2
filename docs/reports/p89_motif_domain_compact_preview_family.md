# P89 Motif/Domain Compact Preview Family

This report-only note defines the first compact motif/domain preview family as the narrow slice of the live dictionary preview that keeps only InterPro, Pfam, and PROSITE.

- Policy family: `motif_domain_compact_family`
- Bundle policy label: `preview_bundle_safe_non_governing`
- Operator policy label: `report_only_non_governing`

## Source Artifacts

- [artifacts/status/dictionary_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/dictionary_preview.json)
- [docs/reports/dictionary_preview.md](/D:/documents/ProteoSphereV2/docs/reports/dictionary_preview.md)
- [artifacts/status/p71_namespace_inventory_preview_family.json](/D:/documents/ProteoSphereV2/artifacts/status/p71_namespace_inventory_preview_family.json)
- [docs/reports/p71_namespace_inventory_preview_family.md](/D:/documents/ProteoSphereV2/docs/reports/p71_namespace_inventory_preview_family.md)
- [artifacts/status/p72_dictionary_preview_review.json](/D:/documents/ProteoSphereV2/artifacts/status/p72_dictionary_preview_review.json)
- [docs/reports/p72_dictionary_preview_review.md](/D:/documents/ProteoSphereV2/docs/reports/p72_dictionary_preview_review.md)
- [artifacts/status/p46_motif_backbone_step1_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p46_motif_backbone_step1_contract.json)
- [artifacts/status/p47_motif_backbone_output_spec.json](/D:/documents/ProteoSphereV2/artifacts/status/p47_motif_backbone_output_spec.json)
- [artifacts/status/p48_motif_backbone_validation_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p48_motif_backbone_validation_contract.json)
- [artifacts/status/source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
- [artifacts/status/broad_mirror_progress.json](/D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_progress.json)
- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

## What The Compact Family Contains

The compact family is the motif/domain subset of the current preview surface:

| Namespace | Reference Kind | Rows | Supporting Records | Preview Role |
|---|---|---:|---:|---|
| InterPro | domain | 36 | 11 | canonical domain/family spine |
| Pfam | domain | 11 | 10 | supporting domain family under InterPro |
| PROSITE | motif | 8 | 9 | canonical motif lane |

Totals:

- Namespace count: `3`
- Row count: `55`
- Supporting-record count: `30`
- Reference-kind counts: `domain=47`, `motif=8`

## Why This Is The First Compact Family

- It is the narrowest useful motif/domain slice already present in the live dictionary preview.
- It keeps the canonical domain spine, the supporting domain family, and the canonical motif lane together.
- It excludes structure and cross-reference namespaces, which belong to other preview families.

## What Stays Out

- ELM stays candidate-only for now because it is still partial in the local registry and does not yet appear as a live namespace-bearing row in the dictionary preview.
- Reactome stays out because it is a pathway family.
- CATH and SCOPe stay out because they are structure families.
- IntAct stays out because it is a cross-reference family.

## Truth Boundary

- This is a report-only artifact.
- It describes a compact preview family, not a new acquisition family.
- It is the motif/domain slice of the current dictionary preview, not a claim of full motif breadth.
- It does not infer ELM rows that are absent from the live namespace-bearing inventory.
- It does not promote the preview to release-grade readiness.

## Bottom Line

The first compact motif/domain preview family is ready as a report-only preview boundary: InterPro plus Pfam plus PROSITE, with ELM explicitly held out until it becomes namespace-bearing in the live summary artifacts.
