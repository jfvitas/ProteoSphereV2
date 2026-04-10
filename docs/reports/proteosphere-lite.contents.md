# ProteoSphere Lite Bundle Contents

## Bundle Identity

- Bundle ID: `proteosphere-lite`
- Bundle kind: `debug_bundle`
- Bundle version: `0.1.0-preview`
- Release ID: `2026.04.01-lightweight-preview.1`
- Packaging layout: `compressed_sqlite`
- Manifest status: `preview_generated_verified_assets`
- Validation status: `passed`

## Release Assets

- `proteosphere-lite.sqlite.zst` (core_bundle, size `278836` bytes, required `True`)
- `proteosphere-lite.release_manifest.json` (manifest, size `1284` bytes, required `True`)
- `proteosphere-lite.sha256` (checksum_root, size `96` bytes, required `True`)
- `proteosphere-lite.contents.md` (human_contents, size `3323` bytes, required `False`)
- `proteosphere-lite.schema.md` (human_schema, size `5210` bytes, required `False`)

## Included Surfaces

- `proteins`: `11` records
- `protein_variants`: `1874` records
- `structures`: `4` records
- `ligands`: `24` records
- `motif_annotations`: `98` records
- `pathway_annotations`: `254` records
- `provenance_records`: `1915` records
- `protein_similarity_signatures`: `11` records
- `structure_similarity_signatures`: `4` records
- `ligand_similarity_signatures`: `24` records
- `leakage_groups`: `11` records
- `dictionaries`: `275` records
- `structure_followup_payloads`: `2` records
- `ligand_support_readiness`: `4` records
- `ligand_identity_pilot`: `4` records
- `ligand_stage1_validation_panel`: `2` records
- `ligand_identity_core_materialization_preview`: `4` records
- `ligand_row_materialization_preview`: `24` records
- `q9nzd4_bridge_validation_preview`: `1` records
- `motif_domain_compact_preview_family`: `55` records
- `kinetics_support_preview`: `11` records
- Record counts are current live counts, not completeness claims.

## Declared Empty Surfaces

- `interactions`: declared in schema, currently `0` materialized records
- `interaction_similarity_signatures`: declared in schema, currently `0` materialized records

## Source Truth And Gating

- Source count: `53`
- Present sources: `48`
- Partial sources: `2`
- Missing sources: `3`
- Procurement priorities: `mega_motif_base, motivated_proteins, string, elm, sabio_rk`
- ELM remains conditional and is not scrape-first.
- `mega_motif_base` and `motivated_proteins` remain outside the live bundle.

## Excluded Payload Families

- `raw_mmcif_pdb_bcif_pae_msa_assets`
- `raw_assay_tables_and_long_text`
- `full_mitab_or_psi_mi_payloads`
- `pathway_diagrams_biopax_sbml`
- `full_motif_instance_tables_and_logos`
- `cryo_em_maps_and_validation_payloads`
- `heavy_packet_outputs`

## Truth Boundaries

- This document is generated from the live bundle manifest, not hand-maintained.
- Structures currently come from the structure-unit feature-cache slice, not coordinate-heavy payloads.
- Variant, structure, motif, pathway, and provenance counts reflect current emitted slices only.
- Dictionaries are compact lookup rows derived from live reference entries; they are not a new biological content family.
- record counts are current counts, not completeness claims
- ELM is conditional and not scrape-first
- mega_motif_base and motivated_proteins remain outside the live bundle
- structures currently come from the structure-unit feature-cache slice, not coordinate-heavy payloads
