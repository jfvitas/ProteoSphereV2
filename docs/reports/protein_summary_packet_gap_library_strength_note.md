# Protein Summary Packet Gap and Library Strength Note

- Library: `summary-library:protein-materialized:v1`
- Source manifest: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Selected accessions: P31749, P04637, P00387

This note is grounded in the current materialized protein summary artifacts and the current training packet audit only.
It shows why the reference library can already be consensus-ready while the training packets for the same accessions remain partial.

- Packet audit: 12 packets; 12 partial; 1 useful; missing structure 11, ligand 11, ppi 10, sequence 2
- Current packet anchor: `P69905`. P69905 is the only useful packet in the current audit, but it still stays partial because ligand and ppi are missing.

## `protein:P31749`
- Library side: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Library resolved fields: protein_name, organism_name, sequence_length, gene_names
- Library preserved conflicts: aliases (Reactome, IntAct disagree with UniProt)
- Packet side: packet weak at lane depth 1; source lanes BindingDB; missing sequence, structure, ppi
- Packet missing modalities: sequence, structure, ppi
- Packet source lanes: BindingDB
- Coverage notes: single-lane coverage

## `protein:P04637`
- Library side: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Library resolved fields: protein_name, organism_name, sequence_length, gene_names
- Library preserved conflicts: aliases (Reactome, IntAct disagree with UniProt)
- Packet side: packet weak at lane depth 1; source lanes IntAct; missing sequence, structure, ligand
- Packet missing modalities: sequence, structure, ligand
- Packet source lanes: IntAct
- Coverage notes: single-lane coverage

## `protein:P00387`
- Library side: the record still has only single-source support for its summary fields, so precedence cannot safely promote a consensus value yet.
- Library resolved fields: none
- Library preserved conflicts: none
- Packet side: packet weak at lane depth 1; source lanes UniProt; missing structure, ligand, ppi
- Packet missing modalities: structure, ligand, ppi
- Packet source lanes: UniProt
- Coverage notes: single-lane coverage; backed by in-tree live-derived snapshot

## Boundary
- reference-library consensus can be stronger than the packet side because it merges corroborating sources
- packet partiality is still driven by missing modality lanes, even when the library can resolve core fields
- single-lane packet rows stay weak until the missing modalities land in the current audit
