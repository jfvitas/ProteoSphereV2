# Protein Summary Packet Gap Next Actions Note

- Library: `summary-library:protein-materialized:v1`
- Source manifest: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Selected accessions: P31749, P04637, P69905

This note is grounded in the protected packet dashboard, the packet delta summary, the packet-gap priority ranking, and the current protein summary artifacts only.
It keeps fresh-run regressions separate from the next data actions so operators do not confuse repair work with promotable improvement work.

- Protected dashboard: 7 complete, 5 partial, 5 deficits
- Delta summary: 11 regressed, 1 unchanged, 7 fresh-run not promotable, 5 latest-baseline blockers
- Priority ranking: 5 unresolved data actions after filtering current-run-present entries
- Current packet anchor: `P69905`. It is the only useful packet in the audit, but the freshest run still leaves it partial
- Already resolved in fresh-run payload surfaces and excluded from rank: ligand:Q9NZD4

## Regression Boundary
### `protein:P31749`
- Library class: consensus-with-preserved-conflict
- Library side: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Fresh-run status: partial (missing ppi, structure)
- Next operator action: hold the protected latest packet baseline and repair the freshest run before promotion

### `protein:P04637`
- Library class: consensus-with-preserved-conflict
- Library side: core fields (protein_name, organism_name, sequence_length, gene_names) are corroborated, but disagreement on aliases stays explicit because sources disagree.
- Fresh-run status: partial (missing ligand, structure)
- Next operator action: hold the protected latest packet baseline and repair the freshest run before promotion

### `protein:P69905`
- Library class: mixed-consensus
- Library side: precedence promotes organism_name, aliases, while protein_name, taxon_id, sequence_length, sequence_checksum, sequence_version, gene_names stay partial.
- Fresh-run status: partial (missing ppi, structure)
- Next operator action: keep as the current packet anchor and do not overwrite the protected baseline

## Next Data Actions
- rank 1: `ligand:P00387` (actionable_now_surface_reconciliation; can_promote_now=false)
  - Why: Local ChEMBL evidence already exists and the available-payload registry already includes ligand:P00387; the remaining gap is packet-surface propagation, not discovery.
  - Next step: Reconcile the existing ligand payload into the packet surfaces without touching latest-promotion logic.
- rank 2: `structure:Q9UCM0` (blocked_pending_fresh_acquisition; can_promote_now=false)
  - Why: Local registry, AlphaFold, RCSB, BioLiP, and PDBbind evidence do not provide a truthful accession-clean Q9UCM0 structure route.
  - Next step: Keep blocked until a fresh structure acquisition yields an accession-clean payload.
- rank 3: `ppi:Q9UCM0` (blocked_pending_fresh_acquisition; can_promote_now=false)
  - Why: The current IntAct mirror is alias-only for Q9UCM0, and BioGRID/STRING are not present in the local inventory; there is no credible local PPI rescue route yet.
  - Next step: Keep blocked until a guarded BioGRID or STRING acquisition yields a canonical Q9UCM0 pair.
- rank 4: `ligand:Q9UCM0` (blocked_pending_fresh_acquisition; can_promote_now=false)
  - Why: No accession-clean local BindingDB or ChEMBL route exists for Q9UCM0, and the structure lane is still missing, so the ligand lane cannot be truthfully materialized from current local sources.
  - Next step: Keep blocked until a fresh structure or accession-safe ligand source lands.
- rank 5: `ligand:P09105` (blocked_no_local_candidate; can_promote_now=false)
  - Why: Fresh local ChEMBL probing still returns structure_companion_only / no_local_candidate for P09105.
  - Next step: Hold for ligand acquisition; do not infer a payload from the structure companion alone.

## Boundary
- fresh-run regressions stay in the repair lane and are not counted as promotable improvements
- the ranked packet-gap actions are current data actions, not latest-promotion changes
- current-run-present entries are reported separately and are not treated as unresolved gap work
