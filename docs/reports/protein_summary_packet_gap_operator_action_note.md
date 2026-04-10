# Protein Summary Packet Gap Operator Action Note

- Library: `summary-library:protein-materialized:v1`
- Source manifest: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Selected accessions: P31749, P04637, P69905

This note is grounded in the protected packet dashboard, the packet delta report, and the current protein summary artifacts only.
It tells an operator which examples are library-strong but packet-regressed, why, and what to do next.

- Protected dashboard: 7 complete, 5 partial, 5 deficits
- Freshest delta: 11 regressed, 1 unchanged, 12 remaining gap packets
- Current packet anchor: `P69905`. It is the only useful packet in the audit, but the freshest run still leaves it partial

## `protein:P31749`
- Library class: consensus-with-preserved-conflict
- Library side: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Protected packet: complete (missing none)
- Freshest run: partial (fresh-run-regressed; missing ppi, structure)
- Next operator action: hold the protected latest packet baseline and repair the freshest run before promotion

## `protein:P04637`
- Library class: consensus-with-preserved-conflict
- Library side: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Protected packet: complete (missing none)
- Freshest run: partial (fresh-run-regressed; missing ligand, structure)
- Next operator action: hold the protected latest packet baseline and repair the freshest run before promotion

## `protein:P69905`
- Library class: mixed-consensus
- Library side: precedence promotes organism_name, aliases, while protein_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names stay partial.
- Protected packet: complete (missing none)
- Freshest run: partial (fresh-run-regressed; missing ppi, structure)
- Next operator action: keep as the current packet anchor and do not overwrite the protected baseline

## Actionable Source Refs
- ligand:P00387: ligand
- ligand:P09105: ligand
- ligand:Q2TAC2: ligand
- ligand:Q9NZD4: ligand
- ligand:Q9UCM0: ligand
- ppi:Q9UCM0: ppi
- structure:Q9UCM0: structure
## Operator Actions
- keep the protected latest packet baseline as the publication target
- repair the freshest-run regressions for P31749 and P04637 before promotion
- leave the source-fix candidate refs aimed at the true deficit rows, not the already-anchored library-strong examples
