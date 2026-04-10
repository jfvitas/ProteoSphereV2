# P29 Summary Library Materializer Slice

This is the first executable slice for the integrated summary library. It keeps the protein card as the spine, then fuses provenance and lightweight source references from UniProt, Reactome, InterPro/Pfam/PROSITE, RCSB/SIFTS, and curated PPI lanes only when the refreshed local registry says those lanes are actually present.

## Slice Goal

The operator-facing output for this slice is a compact, accession-first protein card per selected protein plus a JSON artifact at [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json). The cards must stay rebuildable, provenance-rich, and honest about gaps.

## Source Fusion Rules

- UniProt is the spine source for `protein_ref`, name, organism, sequence fields, and base aliases.
- Reactome contributes pathway references and its own provenance pointer when the lane is present.
- InterPro, Pfam, and PROSITE contribute domain and motif references only when the registry marks those lanes present or partially present.
- RCSB and SIFTS contribute lightweight structure references, not coordinates or residue maps.
- Curated PPI sources contribute interaction ids and source evidence ids as cross references, not flattened pair payloads.
- Conflicts are kept in notes and provenance, not silently overwritten.

## Materialize, Index, Lazy

- Materialize: accession, protein name, organism, taxon id, sequence length, sequence version, sequence checksum when stable, gene names, aliases, provenance pointers, pathway references, domain references, motif references, and lightweight cross references.
- Index: secondary accessions, source record ids, structure ids, curated PPI ids, and feature spans.
- Lazy: full UniProt comments, full Reactome neighborhoods, full feature match tables, SIFTS residue maps, structure coordinates, and raw curated PPI rows.

## Work Packages

### SLICE-WP1: Protein Card Assembler and Provenance Contract

Code targets:
[execution/library/protein_summary_materializer.py](/D:/documents/ProteoSphereV2/execution/library/protein_summary_materializer.py), [scripts/materialize_protein_summary_library.py](/D:/documents/ProteoSphereV2/scripts/materialize_protein_summary_library.py)

Read-only dependencies:
[core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py), [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py), [execution/indexing/protein_index.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_index.py)

Inputs:
[data/canonical/LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json), [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json)

Outputs:
[artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)

Tests:
[tests/unit/execution/test_protein_summary_materializer.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_summary_materializer.py), [tests/unit/core/test_summary_record.py](/D:/documents/ProteoSphereV2/tests/unit/core/test_summary_record.py)

Verification targets:
every card should use `protein:{accession}` as both `summary_id` and `protein_ref`, every record should keep at least one provenance pointer, and `to_dict` / `from_dict` round-trips should preserve aliases, provenance, and notes.

### SLICE-WP2: UniProt Plus Reactome Fusion

Code targets:
[execution/library/protein_summary_materializer.py](/D:/documents/ProteoSphereV2/execution/library/protein_summary_materializer.py)

Read-only dependencies:
[execution/library/reactome_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/reactome_local_summary.py), [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json), [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md)

Inputs:
[execution/acquire/uniprot_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/uniprot_snapshot.py), [execution/library/reactome_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/reactome_local_summary.py)

Outputs:
`ProteinSummaryRecord.context.pathway_references`, `ProteinSummaryRecord.context.provenance_pointers`

Tests:
[tests/unit/execution/test_reactome_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_reactome_local_summary.py), [tests/unit/execution/test_build_summary_library.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_build_summary_library.py)

Verification targets:
Reactome hits should append pathway refs without replacing the UniProt spine, and Reactome-empty accessions should stay explicit partials instead of being promoted to joined coverage.

### SLICE-WP3: InterPro, Pfam, PROSITE, RCSB, and SIFTS Hooks

Code targets:
[execution/library/protein_summary_materializer.py](/D:/documents/ProteoSphereV2/execution/library/protein_summary_materializer.py)

Read-only dependencies:
[execution/acquire/interpro_motif_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/interpro_motif_snapshot.py), [execution/acquire/rcsb_pdbe_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/rcsb_pdbe_snapshot.py), [execution/library/family_motif_consensus.py](/D:/documents/ProteoSphereV2/execution/library/family_motif_consensus.py), [tests/unit/execution/test_acquire_interpro_motif_snapshot.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_acquire_interpro_motif_snapshot.py), [tests/unit/execution/test_acquire_rcsb_pdbe_snapshot.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_acquire_rcsb_pdbe_snapshot.py)

Inputs:
[data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), [execution/acquire/interpro_motif_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/interpro_motif_snapshot.py), [execution/acquire/rcsb_pdbe_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/rcsb_pdbe_snapshot.py)

Outputs:
`ProteinSummaryRecord.context.domain_references`, `ProteinSummaryRecord.context.motif_references`, `ProteinSummaryRecord.context.cross_references`

Tests:
[tests/unit/execution/test_protein_summary_materializer.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_summary_materializer.py), [tests/unit/execution/test_structure_packet_enricher.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_structure_packet_enricher.py)

Verification targets:
feature and structure references should appear only when the lane is present or partial in the local registry, and the first slice must keep coordinates, residue maps, and full feature tables lazy.

### SLICE-WP4: Curated PPI Fusion and Operator Driver

Code targets:
[execution/library/protein_summary_materializer.py](/D:/documents/ProteoSphereV2/execution/library/protein_summary_materializer.py), [scripts/materialize_protein_summary_library.py](/D:/documents/ProteoSphereV2/scripts/materialize_protein_summary_library.py)

Read-only dependencies:
[execution/library/intact_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/intact_local_summary.py), [execution/indexing/protein_pair_crossref.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_pair_crossref.py), [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json), [tests/unit/execution/test_protein_pair_crossref.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_pair_crossref.py)

Inputs:
[execution/library/intact_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/intact_local_summary.py), [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json)

Outputs:
[artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)

Tests:
[tests/integration/test_summary_library_real_corpus.py](/D:/documents/ProteoSphereV2/tests/integration/test_summary_library_real_corpus.py), [tests/unit/execution/test_intact_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_intact_local_summary.py)

Verification targets:
curated PPI ids should be attached as lightweight cross references, pair provenance should remain visible on the protein card, and the CLI should write the same payload it prints.

## Local Registry Guardrails

The refreshed registry still shows motif and broader interaction-network gaps, so those lanes must stay source-gated in this slice. That means the first executable artifact should be sparse but explicit, not aggressively filled.

## Acceptance

- One operator command should materialize an accession-scoped protein summary library artifact.
- Every emitted protein card should carry at least one provenance pointer.
- Source enrichments should appear only when the local registry says the lane exists.
- Missing lanes should remain partial and visible.
- The materialized JSON should round-trip through `SummaryLibrarySchema` without losing provenance or reference families.
