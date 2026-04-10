# Source Verification Queue

- Generated at: `2026-03-30T22:15:27Z`
- Basis: [`artifacts/status/p29_scope_completeness_audit.json`](/D:/documents/ProteoSphereV2/artifacts/status/p29_scope_completeness_audit.json), [`artifacts/status/p28_chembl_rnacentral_resolver.json`](/D:/documents/ProteoSphereV2/artifacts/status/p28_chembl_rnacentral_resolver.json), [`artifacts/status/p28_interpro_complexportal_resolver.json`](/D:/documents/ProteoSphereV2/artifacts/status/p28_interpro_complexportal_resolver.json), [`protein_data_scope/sources_manifest.json`](/D:/documents/ProteoSphereV2/protein_data_scope/sources_manifest.json)

## What Was Patched

- `Complex Portal` now points at verified current-release files instead of a landing page placeholder.
- `InterPro` now points at verified current-release files instead of a landing page placeholder.
- `RNAcentral` keeps the current bulk spine and adds a verified residual queue for the next useful directory-driven files.

## Verified Next Downloads

- `Complex Portal`
  - `released_complexes.txt`
  - `complextab/9606.tsv`
  - `complextab/9606_predicted.tsv`
- `InterPro`
  - `ParentChildTreeFile.txt`
  - `entry.list`
  - `interpro.dtd`
  - `interpro.xml.gz`
  - `interpro2go`
  - `match_complete.dtd`
  - `names.dat`
  - `release_notes.txt`
  - `short_names.dat`
- `RNAcentral`
  - `id_mapping/database_mappings/ensembl.tsv`
  - `id_mapping/database_mappings/hgnc.tsv`
  - `id_mapping/database_mappings/intact.tsv`
  - `genome_coordinates/bed/homo_sapiens.GRCh38.bed.gz`

## Remaining Blockers

- `SABIO-RK` is still query-scoped. The REST vocabulary is verified, but the accession-specific query export still needs a runtime-confirmed encoded query before it should be promoted as a queue item.
- `ELM` is partial. `elms_index.tsv` is live, but `interactions/as_tsv` timed out during direct verification.
- `PROSITE` is already verified locally and does not need a manifest change.

## Truth Boundary

The queue does not invent new filenames or release paths. Anything not directly verified is left as a blocker, not collapsed into the download plan.
