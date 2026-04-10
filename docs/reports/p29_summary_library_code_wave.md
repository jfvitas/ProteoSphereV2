# P29 Summary Library Code Wave

This is the first code-wave checklist for the protein summary-card materializer. It turns the plan artifacts into an execution order: scaffold the materializer, emit UniProt-backed protein cards with provenance, add source-gated enrichment, then finish with curated PPI and the operator CLI.

## Wave Order

### 1. Scaffold the materializer and CLI

Create [execution/library/protein_summary_materializer.py](/D:/documents/ProteoSphereV2/execution/library/protein_summary_materializer.py) and [scripts/materialize_protein_summary_library.py](/D:/documents/ProteoSphereV2/scripts/materialize_protein_summary_library.py).

Use [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py), [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py), [execution/indexing/protein_index.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_index.py), [data/canonical/LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json), [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), and [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json) as the first dependencies.

Test first with [tests/unit/execution/test_protein_summary_materializer.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_summary_materializer.py). The first pass should only prove that the module loads, the CLI accepts accessions and output, and the top-level JSON shape is stable.

Sample output to expect:

- `library_id`
- `schema_version`
- `source_manifest_id`
- `record_count`

### 2. Emit UniProt-backed protein cards

Update [execution/library/protein_summary_materializer.py](/D:/documents/ProteoSphereV2/execution/library/protein_summary_materializer.py) so it can produce a stable `protein:{accession}` record with `protein_ref`, name, organism, sequence fields, aliases, and provenance.

The key follow-up tests are [tests/unit/execution/test_protein_summary_materializer.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_summary_materializer.py) and [tests/unit/core/test_summary_record.py](/D:/documents/ProteoSphereV2/tests/unit/core/test_summary_record.py). The round-trip check matters as much as the assembly itself.

Sample output to expect:

```json
{
  "summary_id": "protein:P69905",
  "protein_ref": "protein:P69905",
  "protein_name": "Hemoglobin subunit alpha",
  "organism_name": "Homo sapiens"
}
```

### 3. Add Reactome, feature, and structure enrichers

Extend the same materializer branch to append Reactome pathway references, then sparse InterPro/Pfam/PROSITE and RCSB/SIFTS references when the refreshed registry says those lanes are present.

Read the existing reference shapes from [execution/library/reactome_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/reactome_local_summary.py), [execution/acquire/interpro_motif_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/interpro_motif_snapshot.py), [execution/acquire/rcsb_pdbe_snapshot.py](/D:/documents/ProteoSphereV2/execution/acquire/rcsb_pdbe_snapshot.py), and [execution/library/family_motif_consensus.py](/D:/documents/ProteoSphereV2/execution/library/family_motif_consensus.py). Keep [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json) as the Reactome ground truth.

Use [tests/unit/execution/test_reactome_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_reactome_local_summary.py), [tests/unit/execution/test_acquire_interpro_motif_snapshot.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_acquire_interpro_motif_snapshot.py), [tests/unit/execution/test_acquire_rcsb_pdbe_snapshot.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_acquire_rcsb_pdbe_snapshot.py), and the materializer unit tests to verify that references append cleanly and heavy payloads stay lazy.

Sample output to expect:

- `context.pathway_references`
- `context.domain_references`
- `context.motif_references`
- `context.cross_references`

### 4. Attach curated PPI evidence and finish the driver

Finish the materializer with curated PPI cross references from [execution/library/intact_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/intact_local_summary.py) and [execution/indexing/protein_pair_crossref.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_pair_crossref.py), then make sure the CLI writes the final artifact to [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json).

The important regressions here are [tests/unit/execution/test_intact_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_intact_local_summary.py), [tests/unit/execution/test_protein_pair_crossref.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_pair_crossref.py), and [tests/integration/test_summary_library_real_corpus.py](/D:/documents/ProteoSphereV2/tests/integration/test_summary_library_real_corpus.py).

Sample output to expect:

- `context.cross_references` with IntAct or IMEx identifiers
- a final JSON artifact written and printed by the CLI
- one record per selected accession, round-trippable through `SummaryLibrarySchema`

## Suggested Validation Commands

```powershell
pytest tests/unit/core/test_summary_record.py tests/unit/execution/test_build_summary_library.py tests/unit/execution/test_protein_summary_materializer.py
pytest tests/unit/execution/test_reactome_local_summary.py tests/unit/execution/test_intact_local_summary.py tests/unit/execution/test_protein_pair_crossref.py
pytest tests/integration/test_summary_library_real_corpus.py -k summary_library
```

## Guardrails

- Keep the accession-first spine stable.
- Gate every non-UniProt lane through the refreshed local registry.
- Leave motif and broad interaction-network gaps explicit.
- Do not inline heavy payloads into the first wave.
