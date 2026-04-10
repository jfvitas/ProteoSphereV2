# Protein Summary Disagreement and Priority Note

- Library: `summary-library:protein-materialized:v1`
- Source manifest: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Selected accessions: P00387, P31749, Q9NZD4

This note is grounded in the current materialized protein summary artifacts only.
It makes the precedence rule readable: corroborated fields can become consensus, conflicts stay explicit, and single-source values stay partial.

- Coverage: 1 consensus example(s) with preserved conflict; 2 example(s) held partial

## `protein:P00387` (partial-held-back)
- precedence UniProt > Reactome > IntAct; join trace 3 direct / 0 indirect / 1 partial; no resolved fields to promote; keep partial protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Resolved fields: none
- Partial fields: protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Preserved conflicts: none
- Cross-source view: 3 direct joins, 0 indirect bridges, 1 partial join

## `protein:P31749` (consensus-with-preserved-conflict)
- precedence UniProt > Reactome > IntAct; join trace 4 direct / 0 indirect / 1 partial; use consensus on protein_name, organism_name, sequence_length, gene_names; preserve disagreement on aliases; keep partial taxon_id, sequence_checksum, sequence_version
- Resolved fields: protein_name, organism_name, sequence_length, gene_names
- Partial fields: taxon_id, sequence_checksum, sequence_version
- Preserved conflicts: aliases (Reactome, IntAct disagree with UniProt)
- Cross-source view: 4 direct joins, 0 indirect bridges, 1 partial join

## `protein:Q9NZD4` (partial-held-back)
- precedence UniProt > Reactome > IntAct; join trace 2 direct / 0 indirect / 1 partial; no resolved fields to promote; keep partial protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Resolved fields: none
- Partial fields: protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Preserved conflicts: none
- Cross-source view: 2 direct joins, 0 indirect bridges, 1 partial join

## Priority Rule
- use the highest-precedence source only when the field is corroborated in the rollup
- preserve disagreements explicitly instead of collapsing them into a single winner
- keep single-source fields partial when the materialized sources do not fully agree
