# Protein Summary Consensus Examples Note

- Library: `summary-library:protein-materialized:v1`
- Source manifest: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Selected accessions: P00387, P31749, Q9NZD4

This note is grounded in the current materialized protein summary artifacts only.
It shows where the library already behaves like a consensus reference and where it must stay partial.

- Coverage: 1 example(s) with resolved agreement; 3 example(s) still carrying partial fields

## `protein:P00387` (partial-reference-shell)
- precedence UniProt > Reactome > IntAct; join trace 3 direct / 0 indirect / 1 partial; no resolved consensus fields yet; keep partial protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Consensus-ready fields: none
- Stay partial fields: protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Conflicts kept explicit: none
- Cross-source view: 3 direct joins, 0 indirect bridges, 1 partial join

## `protein:P31749` (strong-agreement-with-preserved-disagreement)
- precedence UniProt > Reactome > IntAct; join trace 4 direct / 0 indirect / 1 partial; agreement on protein_name, organism_name, sequence_length, gene_names; keep partial taxon_id, sequence_checksum, sequence_version; preserve disagreement on aliases
- Consensus-ready fields: protein_name, organism_name, sequence_length, gene_names
- Stay partial fields: taxon_id, sequence_checksum, sequence_version
- Conflicts kept explicit: aliases (Reactome, IntAct disagree with UniProt)
- Cross-source view: 4 direct joins, 0 indirect bridges, 1 partial join

## `protein:Q9NZD4` (partial-reference-shell)
- precedence UniProt > Reactome > IntAct; join trace 2 direct / 0 indirect / 1 partial; no resolved consensus fields yet; keep partial protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Consensus-ready fields: none
- Stay partial fields: protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Conflicts kept explicit: none
- Cross-source view: 2 direct joins, 0 indirect bridges, 1 partial join

## Boundary
- source agreement is strong when the current rollups are resolved and corroborated
- partial fields stay visible when the materialized sources do not fully agree
- conflicts stay explicit instead of being collapsed into a false consensus
