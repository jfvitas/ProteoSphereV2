# Broad Mirror Lane Plan

- Generated at: `2026-03-31T19:45:53.738450+00:00`
- Basis: `D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_remaining_transfer_status.json`
- Source policy: `D:/documents/ProteoSphereV2/protein_data_scope/source_policy.json`
- Remaining sources: `2`
- Not yet started files: `14`
- Recommended sidecar batches: `3`

## Launch Order

| Rank | Batch | Source | Role | Value class | Files |
| --- | --- | --- | --- | --- | --- |
| 1 | `uniprot-core-backbone` | `uniprot` | direct | direct-value | 3 |
| 2 | `uniprot-tail-representatives` | `uniprot` | direct | deferred-value | 3 |
| 3 | `string-guarded-network-pack` | `string` | guarded | deferred-value | 8 |

## Batch Details

### 1. `uniprot-core-backbone` (direct-value)

- Source: `uniprot` (direct)
- Files: `uniprot_sprot_varsplic.fasta.gz`, `uniref100.fasta.gz`, `uniref90.fasta.gz`
- Rationale: Highest immediate library value: the isoform-aware Swiss-Prot file and representative UniRef FASTA lanes are the smallest, most direct backbone.
- Expected impact: Restores the core sequence reference layer first, with the best direct-value payoff for library consumers.

### 2. `uniprot-tail-representatives` (deferred-value)

- Source: `uniprot` (direct)
- Files: `uniref90.xml.gz`, `uniref50.fasta.gz`, `uniref50.xml.gz`
- Rationale: Keep the lower-immediacy UniRef XML and compact representatives as a second UniProt sidecar so the core lane can finish independently.
- Expected impact: Completes the remaining UniProt coverage after the direct-value backbone has landed.

### 3. `string-guarded-network-pack` (deferred-value)

- Source: `string` (guarded)
- Files: `protein.physical.links.detailed.v12.0.txt.gz`, `protein.physical.links.full.v12.0.txt.gz`, `items_schema.v12.0.sql.gz`, `network_schema.v12.0.sql.gz`, `evidence_schema.v12.0.sql.gz`, `database.schema.v12.0.pdf`, `protein.network.embeddings.v12.0.h5`, `protein.sequence.embeddings.v12.0.h5`
- Rationale: STRING remains a guarded source, so keep the interaction tables, schema exports, PDFs, and embeddings together in one sidecar lane.
- Expected impact: Restores the remaining network reference payload without mixing guarded STRING transfers across multiple sidecars.

