# P29 Normalization Implementation Queue

This queue turns the bridge-priority order into concrete module-level work. The goal is to improve packet completion and summary-library fusion in the safest order: UniProt spine first, then RCSB/PDBe + SIFTS, Reactome, ligand identity, and curated PPI joins.

## Shared Targets

Three modules show up across the whole slice:

- `core/canonical/registry.py` for conservative alias resolution and explicit ambiguity.
- `core/library/summary_record.py` for the shared summary and provenance shape.
- `execution/library/build_summary_library.py` for the operator-facing summary assembly step.

## Implementation Order

| Rank | Bridge | Module targets | Why now |
|---|---|---|---|
| 1 | UniProt spine | `core/canonical/protein.py`, `execution/ingest/sequences.py`, `execution/indexing/protein_index.py`, `core/canonical/registry.py` | This is the root identity normalization step for every other bridge. |
| 2 | RCSB/PDBe + SIFTS | `execution/acquire/rcsb_pdbe_snapshot.py`, `execution/ingest/structures.py`, `execution/materialization/structure_packet_enricher.py` | This is the safest and highest-value route from coordinates back to accession. |
| 3 | Reactome | `execution/acquire/reactome_snapshot.py`, `execution/library/reactome_local_summary.py`, `core/library/summary_record.py` | Reactome gives stable pathway joins and immediate summary value. |
| 4 | Ligand identity | `core/canonical/ligand.py`, `core/canonical/assay.py`, `execution/acquire/bindingdb_snapshot.py`, `execution/ingest/assays.py`, `execution/materialization/ligand_packet_enricher.py`, `execution/materialization/local_bridge_ligand_backfill.py` | This closes the remaining ligand-only gaps without collapsing assay and chemistry. |
| 5 | Curated PPI joins | `execution/acquire/biogrid_snapshot.py`, `execution/acquire/intact_snapshot.py`, `execution/acquire/biogrid_cohort_slice.py`, `execution/acquire/intact_cohort_slice.py`, `execution/library/intact_local_summary.py`, `execution/indexing/interaction_index.py`, `execution/indexing/protein_pair_crossref.py`, `execution/materialization/local_bridge_ppi_backfill.py`, `execution/library/weak_ppi_candidate_summary.py` | This restores the missing curated interaction breadth and unlocks packet rescues. |

## Module-Level Notes

The structure bridge currently uses `execution/acquire/rcsb_pdbe_snapshot.py` as the place where PDBe `uniprot_mapping` and `chains` resources are hydrated. There is no dedicated local SIFTS module in the repo tree, so the queue treats SIFTS as a bridge input inside the existing RCSB/PDBe acquisition path rather than inventing a new module.

The ligand lane should stay split between identity and assay work. `core/canonical/ligand.py` and `core/canonical/assay.py` own the canonical shapes, while BindingDB acquisition and ligand packet enrichment own the source-side normalization and packet-state projection.

The curated PPI lane should keep interaction IDs, IMEx IDs, participant accessions, and projection lineage intact. `execution/indexing/interaction_index.py` and `execution/indexing/protein_pair_crossref.py` are the right places to keep the join keys and unresolved participants visible.

## Guardrails

This queue keeps the same no-fake-joins posture as the bridge map:

- Secondary accessions stay aliases, not alternate primaries.
- Experimental and predicted structure truth stay separate.
- Native interaction complexes are not flattened into binary truth without lineage.
- Ligand identity is not collapsed into assay measurements.
- Alias-only or construct-only joins stay unresolved.

## Bottom Line

If we implement the top five module groups in this order, we get the fastest increase in packet completeness and the largest reuse gain in the summary library without overclaiming joins.
