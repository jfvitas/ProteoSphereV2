# P32 Summary Fusion Execution

This is the concrete plan for fusing downloaded and already-materialized sources into the summary library without weakening the join rules.

## What We Are Building

The summary library should stay accession-first and class-aware. Protein, ligand, and curated interaction records are the core materialized spine. Structure, pathway, and motif evidence are attached as accessioned references and provenance-backed context, not as free text.

The current local registry is enough to materialize the strong lanes now: UniProt, RCSB/PDBe, AlphaFold DB, BindingDB, ChEMBL, ChEBI, Reactome, InterPro, Pfam, BioLiP, and PDBBind. The missing or partial lanes still need procurement or refresh: IntAct, BioGRID, STRING, PROSITE, ELM, SABIO-RK, UniProt TrEMBL, and the broader motif sources.

## Canonical Join Order

1. Normalize protein accessions first through UniProt.
2. Crosswalk experimental structure through RCSB/PDBe and PDBe mapping resources.
3. Keep AlphaFold as the predicted companion lane, never as a substitute for experimental truth.
4. Resolve ligand identity through stable chemical identifiers before touching assays.
5. Materialize curated PPI only when a native interaction ID and accession-resolved participants are present.
6. Attach Reactome pathway and InterPro/Pfam motif context as accessioned references with release-stamped provenance.

## Source Precedence

- UniProt is the identity spine for proteins.
- RCSB/PDBe is the experimental structure authority.
- ChEBI is the chemical identity authority.
- BindingDB and ChEMBL are the assay-backed ligand authorities.
- IntAct and BioGRID are the curated PPI authorities.
- Reactome is the pathway and reaction authority.
- InterPro and Pfam are the motif and domain authorities.
- STRING, PDBBind, BioLiP, and local extracted assets stay in support or projection roles unless a source-native authority is missing.

## Conflict Handling

The rule is to normalize first and only then decide whether there is a winner.

- If values normalize to the same canonical identity, collapse them and keep all provenance pointers.
- If one value is a strict parent of another, keep the more specific value canonical and retain the broader one as supporting context.
- If experimental and predicted structure would be merged, stop.
- If a ligand identity changes because of salt, tautomer, or stereochemistry, keep the alternates instead of forcing one answer.
- If curated PPI is only supported through a complex projection, keep the projection lineage visible.
- If pathway species, motif span, or residue numbering changes the meaning, keep the records separate.
- If nothing better can be proven, mark the row ambiguous or conflict and do not coerce a winner.

## Fields That Should Stay Multi-Valued

The multi-valued contract is what keeps the library honest.

- Protein records should keep `aliases`, `gene_names`, cross references, motif references, domain references, pathway references, provenance pointers, and notes as lists.
- Protein-ligand records should keep `interaction_refs`, `assay_refs`, provenance pointers, and notes as lists.
- Protein-protein records should keep `interaction_refs`, `evidence_refs`, provenance pointers, and notes as lists.
- Alternates should stay visible for accessions, isoforms, ligand standard forms, interaction types, pathway ancestry, motif spans, and evidence references.
- Scalar fields should only be scalar when they are truly normalized and class-specific, such as accession, stable chemical identifier, Reactome ID, interaction ID, span boundaries, or measurement values that are already equivalent.

## Execution Phases

### Phase 1

Lock the accession spine with `core/canonical/protein.py`, `execution/ingest/sequences.py`, `execution/indexing/protein_index.py`, and `execution/library/build_summary_library.py`. This phase turns UniProt into the stable key for everything protein-bearing.

### Phase 2

Fuse structure and ligand lanes with `execution/acquire/rcsb_pdbe_snapshot.py`, `execution/ingest/structures.py`, `execution/materialization/structure_packet_enricher.py`, `core/canonical/ligand.py`, `execution/acquire/bindingdb_snapshot.py`, `execution/ingest/assays.py`, `execution/materialization/ligand_packet_enricher.py`, and `execution/materialization/local_bridge_ligand_backfill.py`.

### Phase 3

Fuse curated interaction evidence with `execution/acquire/intact_snapshot.py`, `execution/acquire/biogrid_snapshot.py`, `execution/acquire/intact_cohort_slice.py`, `execution/acquire/biogrid_cohort_slice.py`, `execution/indexing/interaction_index.py`, `execution/indexing/protein_pair_crossref.py`, `execution/library/intact_local_summary.py`, `execution/materialization/local_bridge_ppi_backfill.py`, and `execution/library/weak_ppi_candidate_summary.py`.

### Phase 4

Attach pathway and motif context with `execution/acquire/reactome_snapshot.py`, `execution/library/reactome_local_summary.py`, `execution/acquire/interpro_motif_snapshot.py`, `execution/library/family_motif_consensus.py`, and `execution/library/build_summary_library.py`.

### Phase 5

Bring in the download queue without relaxing the rules. That means BioGRID, IntAct, STRING, PROSITE, ELM, SABIO-RK, and UniProt TrEMBL should be added only when the same accession-first, fail-closed contract can be applied to them.

## Tests To Expect

The implementation should be covered by the existing unit surface and any small extensions needed around the fusion path:

- `tests/unit/core/test_canonical_protein.py`
- `tests/unit/execution/test_ingest_sequences.py`
- `tests/unit/execution/test_protein_index.py`
- `tests/unit/execution/test_acquire_rcsb_pdbe_snapshot.py`
- `tests/unit/execution/test_ingest_structures.py`
- `tests/unit/execution/test_structure_packet_enricher.py`
- `tests/unit/core/test_canonical_ligand.py`
- `tests/unit/execution/test_acquire_bindingdb_snapshot.py`
- `tests/unit/execution/test_ingest_assays.py`
- `tests/unit/execution/test_ligand_packet_enricher.py`
- `tests/unit/execution/test_acquire_intact_snapshot.py`
- `tests/unit/execution/test_acquire_biogrid_snapshot.py`
- `tests/unit/execution/test_interaction_index.py`
- `tests/unit/execution/test_acquire_interpro_motif_snapshot.py`
- `tests/unit/execution/test_family_motif_consensus.py`
- `tests/unit/core/test_summary_record.py`
- `tests/unit/execution/test_build_summary_library.py`

## Acceptance Rules

- Every fused record must be accession-first and provenance-backed.
- No source class may win by absence alone.
- Structure, ligand, interaction, pathway, and motif semantics must stay distinct.
- Ambiguity must be visible in the library instead of being smoothed away.
- The library should be rebuildable from release-stamped source manifests and local snapshots.

