# P55 Bundle Field Mapping

This report-only note maps the current live artifacts to the proposed bundle manifest exporter inputs for the lightweight library.

## Bundle Shape

The proposed default bundle layout remains `compressed_sqlite`, with:

- `proteosphere-lite.sqlite.zst`
- `proteosphere-lite.release_manifest.json`
- `proteosphere-lite.sha256`

Optional companion docs remain:

- `proteosphere-lite.contents.md`
- `proteosphere-lite.schema.md`

Source anchor:

- [artifacts/status/p50_lightweight_bundle_packaging_proposal.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_lightweight_bundle_packaging_proposal.json)
- [docs/reports/p50_lightweight_bundle_packaging_proposal.md](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md)

## Current Live Inputs

The exporter should draw from the current materialized and truth-bearing artifacts first:

- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [artifacts/status/source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
- [artifacts/status/broad_mirror_progress.json](/D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_progress.json)
- [artifacts/status/p46_motif_backbone_step1_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p46_motif_backbone_step1_contract.json)
- [artifacts/status/p47_motif_backbone_output_spec.json](/D:/documents/ProteoSphereV2/artifacts/status/p47_motif_backbone_output_spec.json)
- [artifacts/status/p48_motif_backbone_validation_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p48_motif_backbone_validation_contract.json)
- [artifacts/status/p50_motif_pathway_enrichment_tranche.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_motif_pathway_enrichment_tranche.json)
- [artifacts/status/p51_structure_motif_join_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p51_structure_motif_join_mapping.json)
- [artifacts/status/p53_structure_unit_operator_surface_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p53_structure_unit_operator_surface_contract.json)

## Exporter Input Map

| Exporter input | Current live artifact(s) | Mapping rule |
| --- | --- | --- |
| `bundle.layout_id` | `p50_lightweight_bundle_packaging_proposal.json` | Use the recommended default `compressed_sqlite` layout. |
| `bundle.release_assets` | `p50_lightweight_bundle_packaging_proposal.json` | Emit the three release assets first and keep the optional docs separate. |
| `bundle.optional_docs` | `p50_lightweight_bundle_packaging_proposal.json` | Keep `contents.md` and `schema.md` as report-only companions. |
| `bundle.source_manifest_id` | `protein_summary_library.json`, `structure_unit_summary_library.json` | Reuse the shared source-manifest root already present in both live library artifacts. |
| `bundle.record_counts` | `protein_summary_library.json`, `structure_unit_summary_library.json` | Carry current counts forward as truth-bearing bundle metadata, not completeness claims. |
| `bundle.table_families` | `p50_lightweight_bundle_packaging_proposal.json` | Declare the planned family set from the packaging proposal, but do not imply all families are populated yet. |
| `bundle.source_gates` | `source_coverage_matrix.json`, `broad_mirror_progress.json`, `p53_structure_unit_operator_surface_contract.json` | Use coverage and mirror truth to gate motif, pathway, and structure-class readiness. |
| `bundle.supporting_docs` | `p46`, `p47`, `p48`, `p50`, `p51`, `p53` | Attach the contract/report stack as exporter inputs for auditability. |

## Family Population

| Planned family | Current status from live artifacts | Bundle-manifest treatment |
| --- | --- | --- |
| `proteins` | populated | include now |
| `protein_variants` | not yet populated | declare, but keep empty until schema v2 materialization exists |
| `structures` | populated via structure-unit summary | include now |
| `motif_annotations` | partially populated, with ELM conditional | include now, but keep ELM as conditional and do not scrape first |
| `pathway_annotations` | partially populated | include now as truth-bearing context |
| `provenance_records` | populated | include now |
| `ligands`, `interactions`, similarity tables, `leakage_groups`, `dictionaries` | not yet populated in the current live bundle slice | declare as planned families only |

## Truth Boundaries

- Do not infer completeness from the current protein and structure-unit summaries.
- Do not add `mega_motif_base` or `motivated_proteins` as live bundle inputs; they remain missing in the current registry truth.
- Do not scrape InterPro, PROSITE, Reactome, CATH, or SCOP.
- Do not scrape ELM first; keep it conditional on the pinned TSV exports.
- Do not invent release checksums, record counts, or populated table families that are not already backed by the live artifacts.

## Bottom Line

The exporter can already be fed from the current protein and structure-unit libraries plus the coverage and join-contract reports. The bundle manifest itself should remain a report-only artifact until the missing motif lanes are procured or the planned schema v2 families are actually materialized.
