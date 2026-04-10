# ProteoSphere Lite Bundle Schema

## Bundle Overview

- Bundle ID: `proteosphere-lite`
- Bundle kind: `debug_bundle`
- Schema version: `1`
- Packaging layout: `compressed_sqlite`
- Content scope: `planning_governance_only`
- Build state: `preview_generated_verified_assets`

## Included Assets

- `proteosphere-lite.sqlite.zst`: role `core_bundle`, required `True`
- `proteosphere-lite.release_manifest.json`: role `manifest`, required `True`
- `proteosphere-lite.sha256`: role `checksum_root`, required `True`
- `proteosphere-lite.contents.md`: role `human_contents`, required `False`
- `proteosphere-lite.schema.md`: role `human_schema`, required `False`

## Schema Conventions

- IDs are namespace-scoped, compact string keys such as `protein:P04637`.
- Nested reference arrays carry lineage and source context instead of flattening all joins into separate tables in this preview.
- Null or zero-count reserved families are declared explicitly rather than omitted.
- Provenance pointers and source snapshot IDs remain first-class schema elements.

## Current Live Table Families

- `proteins`: `included`, `11` records
- `protein_variants`: `included`, `1874` records
- `structures`: `included`, `4` records
- `ligands`: `included`, `24` records
- `interactions`: `reserved`, `0` records
- `motif_annotations`: `included`, `98` records
- `pathway_annotations`: `included`, `254` records
- `provenance_records`: `included`, `1915` records
- `protein_similarity_signatures`: `included`, `11` records
- `structure_similarity_signatures`: `included`, `4` records
- `ligand_similarity_signatures`: `included`, `24` records
- `interaction_similarity_signatures`: `reserved`, `0` records
- `leakage_groups`: `included`, `11` records
- `dictionaries`: `included`, `275` records
- `structure_followup_payloads`: `included`, `2` records
- `ligand_support_readiness`: `included`, `4` records
- `ligand_identity_pilot`: `included`, `4` records
- `ligand_stage1_validation_panel`: `included`, `2` records
- `ligand_identity_core_materialization_preview`: `included`, `4` records
- `ligand_row_materialization_preview`: `included`, `24` records
- `q9nzd4_bridge_validation_preview`: `included`, `1` records
- `motif_domain_compact_preview_family`: `included`, `55` records
- `kinetics_support_preview`: `included`, `11` records

## Family Notes

### Proteins Family

- Primary keys: `summary_id`, `protein_ref`
- Carries identity, sequence, classification, pathway, provenance, and source-rollup context.
- Example anchor: `protein:P00387`.

### Protein Variants Family

- Primary keys: `summary_id`, `protein_ref`, `variant_signature`
- Current slice uses compact mutation/isoform signatures and keeps construct lineage deferred when unsupported.
- Included now only where materialized by the live variant summary library.

### Structures Family

- Current representation is structure-unit oriented, not full coordinate payloads.
- Keys include `protein_ref`, `structure_id`, and `chain_id`.
- Intended for leakage/similarity planning rather than heavy structure hydration.

### Motif, Pathway, And Provenance Families

- These are still compact preview families derived from current live library surfaces.
- Motif/domain annotations remain logically distinct but are budgeted together in the current bundle manifest.
- Provenance records preserve source lineage and should not be treated as completeness claims.

### Dictionaries Family

- This family is a compact lookup layer built from unique live reference entries across motif, domain, pathway, and cross-reference rows.
- It is packaging-oriented and helps future consumers resolve stable namespace/identifier labels without shipping heavy source payloads.
- It should not be treated as a new biological acquisition family.

## Reserved Families

- `interactions`
- `interaction_similarity_signatures`

## Source Lineage And Trust Notes

- `UniProt` -> `2026-03-23:api:2a2e3af898cc6772`
- `bio-agent-lab/reactome` -> `2026-03-16`
- `IntAct` -> `20260323T002625Z:download:6a49b82dc9ec053d`
- `bio-agent-lab-import-manifest` -> `v1`
- `IntActMutation` -> `20260323T002625Z`
- `VariantSupport` -> `p54`

## Exclusions

- `raw_mmcif_pdb_bcif_pae_msa_assets`
- `raw_assay_tables_and_long_text`
- `full_mitab_or_psi_mi_payloads`
- `pathway_diagrams_biopax_sbml`
- `full_motif_instance_tables_and_logos`
- `cryo_em_maps_and_validation_payloads`
- `heavy_packet_outputs`

## Schema Evolution Notes

- This schema doc is generated from the live bundle manifest and should evolve with emitted families.
- Reserved families stay reserved until they have real materialized surfaces.
- The current default layout remains `compressed_sqlite`; future partitioning is a growth path, not current truth.

## Basis

- `budget_contract`: `docs/reports/p51_bundle_manifest_budget_contract.md`
- `manifest_example`: `docs/reports/p53_bundle_manifest_example.md`
- `export_contract`: `docs/reports/p54_bundle_manifest_export_contract.md`
- `current_library_artifact`: `artifacts/status/protein_summary_library.json`
- `current_canonical_status`: `data/canonical/LATEST.json`
