# P29 Normalization Rollout Wave

This is the first implementation wave for the identifier contract. The order is deliberate: stabilize the UniProt spine, then wire structure, ligand, and curated PPI joins, and leave motif work as a blocked readiness task until source coverage appears.

## Wave Order

1. Stabilize the UniProt accession spine in `core/canonical/protein.py`, `core/canonical/registry.py`, `execution/ingest/sequences.py`, and `execution/indexing/protein_index.py`.
2. Wire RCSB/PDBe structure joins through the current PDBe mapping path in `execution/acquire/rcsb_pdbe_snapshot.py`, then project them in `execution/ingest/structures.py` and `execution/materialization/structure_packet_enricher.py`.
3. Normalize ligand identity in `core/canonical/ligand.py`, `core/canonical/assay.py`, `execution/acquire/bindingdb_snapshot.py`, `execution/ingest/assays.py`, `execution/materialization/ligand_packet_enricher.py`, and `execution/materialization/local_bridge_ligand_backfill.py`.
4. Preserve curated PPI identifiers in `execution/acquire/biogrid_snapshot.py`, `execution/acquire/intact_snapshot.py`, `execution/acquire/biogrid_cohort_slice.py`, `execution/acquire/intact_cohort_slice.py`, `execution/indexing/interaction_index.py`, `execution/indexing/protein_pair_crossref.py`, `execution/library/intact_local_summary.py`, `execution/materialization/local_bridge_ppi_backfill.py`, and `execution/library/weak_ppi_candidate_summary.py`.
5. Hold motif span work as a blocked readiness task until the motif lane is actually available locally.

## Test Plan

The first wave should be backed by existing unit test surfaces rather than new broad integration scaffolding:

- Protein spine: `tests/unit/core/test_canonical_protein.py`, `tests/unit/core/test_canonical_registry.py`, `tests/unit/execution/test_ingest_sequences.py`, `tests/unit/execution/test_protein_index.py`.
- Structure joins: `tests/unit/execution/test_acquire_rcsb_pdbe_snapshot.py`, `tests/unit/execution/test_ingest_structures.py`, `tests/unit/execution/test_structure_packet_enricher.py`.
- Ligand identity: `tests/unit/core/test_canonical_ligand.py`, `tests/unit/core/test_canonical_assay.py`, `tests/unit/execution/test_acquire_bindingdb_snapshot.py`, `tests/unit/execution/test_ingest_assays.py`, `tests/unit/execution/test_ligand_packet_enricher.py`, `tests/unit/execution/test_local_bridge_ligand_backfill.py`.
- Curated PPI: `tests/unit/execution/test_acquire_biogrid_snapshot.py`, `tests/unit/execution/test_acquire_intact_snapshot.py`, `tests/unit/execution/test_biogrid_cohort_slice.py`, `tests/unit/execution/test_intact_cohort_slice.py`, `tests/unit/execution/test_interaction_index.py`, `tests/unit/execution/test_protein_pair_crossref.py`, `tests/unit/execution/test_intact_local_summary.py`, `tests/unit/execution/test_local_bridge_ppi_backfill.py`, `tests/unit/execution/test_weak_ppi_candidate_summary.py`.
- Motif readiness: `tests/unit/execution/test_acquire_interpro_motif_snapshot.py`, `tests/unit/execution/test_family_motif_consensus.py`, `tests/unit/core/test_summary_record.py`, `tests/unit/execution/test_build_summary_library.py`.

## Dependency Order

The wave should move in this order:

1. `task_accession_spine`
2. `task_structure_join`
3. `task_ligand_identity`
4. `task_curated_ppi`
5. `task_motif_span_readiness`

That order keeps every later join grounded in the accession spine and prevents the more complex bridges from inventing their own identity rules.

## Blocked Readiness

Motif span work is included only as readiness. The current local registry still marks motif sources as missing, so the rollout should prepare the code path and tests, but not claim completion until those sources are actually present.

## Exit Criteria

The first wave is complete when:

- Protein normalization passes and ambiguity stays explicit.
- At least one structure, one ligand, and one curated PPI bridge can run end-to-end without fake joins.
- The summary library can ingest the normalized records while preserving provenance and evidence class boundaries.
