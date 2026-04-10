# Broad Mirror Sidecar Procurement Status

- Generated at: `2026-03-31T20:03:24.455723+00:00`
- Basis: `artifacts/status/broad_mirror_remaining_transfer_status.json`
- Source policy: `protein_data_scope/source_policy.json`
- Runtime dir: `artifacts/runtime`
- Remaining files: `21`
- Active sidecar files: `14`
- Active bulk files: `8`
- Still uncovered: `0`
- Active/not-yet-started overlap: `11`

## Active Sidecars

| Rank | Batch | Source | Role | Value class | Files |
| --- | --- | --- | --- | --- | --- |
| 1 | `uniprot-core` | `uniprot` | direct | direct-value | 3 |
| 2 | `uniprot-tail` | `uniprot` | direct | deferred-value | 3 |
| 3 | `string-schema` | `string` | guarded | deferred-value | 4 |
| 4 | `string-physical-tail` | `string` | guarded | deferred-value | 4 |

## Active Bulk

- `string`: `protein.links.full.v12.0.txt.gz` (missing)
- `string`: `protein.links.v12.0.txt.gz` (partial)
- `string`: `protein.links.detailed.v12.0.txt.gz` (partial)
- `string`: `protein.physical.links.v12.0.txt.gz` (partial)
- `uniprot`: `uniref100.xml.gz` (missing)
- `uniprot`: `uniprot_trembl.dat.gz` (partial)
- `uniprot`: `uniprot_trembl.xml.gz` (partial)
- `uniprot`: `idmapping_selected.tab.gz` (partial)

## Still-Uncovered Backlog

- none

## Evidence

- `uniprot-core`: logs=artifacts/runtime/uniprot_core_backbone_stdout.log, artifacts/runtime/uniprot_core_backbone_stderr.log; partials=data/raw/protein_data_scope_seed/uniprot/uniref100.fasta.gz.part, data/raw/protein_data_scope_seed/uniprot/uniref90.fasta.gz.part
- `uniprot-tail`: logs=artifacts/runtime/uniprot_tail_sidecar_stdout.log, artifacts/runtime/uniprot_tail_sidecar_stderr.log; partials=data/raw/protein_data_scope_seed/uniprot/uniref50.fasta.gz.part, data/raw/protein_data_scope_seed/uniprot/uniref50.xml.gz.part, data/raw/protein_data_scope_seed/uniprot/uniref90.xml.gz.part
- `string-schema`: logs=artifacts/runtime/string_schema_sidecar_stdout.log, artifacts/runtime/string_schema_sidecar_stderr.log; partials=data/raw/protein_data_scope_seed/string/items_schema.v12.0.sql.gz.part, data/raw/protein_data_scope_seed/string/network_schema.v12.0.sql.gz.part
- `string-physical-tail`: logs=artifacts/runtime/string_physical_tail_sidecar_stdout.log, artifacts/runtime/string_physical_tail_sidecar_stderr.log; partials=data/raw/protein_data_scope_seed/string/protein.network.embeddings.v12.0.h5.part, data/raw/protein_data_scope_seed/string/protein.physical.links.detailed.v12.0.txt.gz.part, data/raw/protein_data_scope_seed/string/protein.physical.links.full.v12.0.txt.gz.part, data/raw/protein_data_scope_seed/string/protein.sequence.embeddings.v12.0.h5.part

## Overlap

- `items_schema.v12.0.sql.gz`, `network_schema.v12.0.sql.gz`, `protein.network.embeddings.v12.0.h5`, `protein.physical.links.detailed.v12.0.txt.gz`, `protein.physical.links.full.v12.0.txt.gz`, `protein.sequence.embeddings.v12.0.h5`, `uniref100.fasta.gz`, `uniref50.fasta.gz`, `uniref50.xml.gz`, `uniref90.fasta.gz`, `uniref90.xml.gz`
