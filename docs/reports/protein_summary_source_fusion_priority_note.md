# Protein Summary Source Fusion Priority Note

- Library: `summary-library:protein-materialized:v1`
- Source manifest: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Selected accessions: P31749, P69905, P00387

This note is grounded in the current materialized protein summary artifacts only.
It shows when precedence yields a usable consensus, when a disagreement must remain explicit, and when a record stays partial.

- Coverage: 2 consensus example(s); 1 example(s) with preserved conflict; 1 example(s) held partial

## `protein:P31749` (consensus-with-preserved-conflict)
- Why: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Resolved fields: protein_name, organism_name, sequence_length, gene_names
- Partial fields: taxon_id, sequence_checksum, sequence_version
- Preserved conflicts: aliases (Reactome, IntAct disagree with UniProt)
- Cross-source view: 4 direct joins, 0 indirect bridges, 1 partial join

## `protein:P69905` (mixed-consensus)
- Why: precedence promotes organism_name, aliases, while protein_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names stay partial.
- Resolved fields: organism_name, aliases
- Partial fields: protein_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names
- Preserved conflicts: none
- Cross-source view: 4 direct joins, 4 indirect bridges, 1 partial join

## `protein:P00387` (partial-held-back)
- Why: the record still has only single-source support for its summary fields, so precedence cannot safely promote a consensus value yet.
- Resolved fields: none
- Partial fields: protein_name, organism_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names, aliases
- Preserved conflicts: none
- Cross-source view: 3 direct joins, 0 indirect bridges, 1 partial join

## Priority Rule
- promote a field only when the rollup is corroborated by the higher-precedence sources
- keep conflicts explicit rather than collapsing them into a false consensus
- leave single-source fields partial when the materialized sources do not fully agree
