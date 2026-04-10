# P29 Summary Library First Slice

This slice is the executable starting point for the summary-library rollout. It covers the first four work packages from the breakdown: `P1-WP1`, `P1-WP2`, `P2-WP1`, and `P2-WP2`. The goal is to get schema v2 and the protein/provenance spine ready before any new materializers land.

## P1-WP1: Extend Summary Record Schema

Likely touch points: [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py), [core/storage/planning_index_schema.py](/D:/documents/ProteoSphereV2/core/storage/planning_index_schema.py), [tests/unit/core/test_summary_record.py](/D:/documents/ProteoSphereV2/tests/unit/core/test_summary_record.py).

Dependencies: [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md), [docs/reports/source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md), [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json), [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json).

Verification: new record families must round-trip through `to_dict` and `from_dict`, mixed payloads must preserve record kinds, and context defaults must keep the materialize/index/lazy split explicit.

Test goal: unit coverage for structure, motif, pathway, and provenance serialization plus a mixed-library round-trip regression.

## P1-WP2: Teach The Builder About Schema V2

Likely touch points: [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py), [execution/indexing/protein_pair_crossref.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_pair_crossref.py), [tests/unit/execution/test_build_summary_library.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_build_summary_library.py).

Dependencies: [artifacts/status/p29_summary_library_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/p29_summary_library_plan.json), [artifacts/status/source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json), [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py).

Verification: schema v1 behavior must stay stable when no overrides are supplied, new record families must merge without collapsing summary ids, and unresolved pair evidence must remain visible.

Test goal: builder regression tests for mixed libraries, pair evidence preservation, and bare-accession routing.

## P2-WP1: Materialize Provenance Cards

Likely touch points: [execution/library/source_provenance_summary.py](/D:/documents/ProteoSphereV2/execution/library/source_provenance_summary.py), [execution/acquire/local_source_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py), [execution/acquire/unified_source_catalog.py](/D:/documents/ProteoSphereV2/execution/acquire/unified_source_catalog.py), [scripts/materialize_summary_library.py](/D:/documents/ProteoSphereV2/scripts/materialize_summary_library.py).

Dependencies: [data/raw/bootstrap_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs/LATEST.json), [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json).

Verification: provenance cards must expose `source_name`, `source_record_id`, `release_version`, `release_date`, `checksum`, and `join_status`, and every materialized row must keep at least one provenance pointer.

Test goal: provenance round-trip tests plus an integration check that proves materialized rows still point back to the raw snapshot boundary.

## P2-WP2: Keep Protein Cards Accession-First

Likely touch points: [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py), [execution/indexing/protein_index.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_index.py), [tests/unit/execution/test_protein_index.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_index.py).

Dependencies: [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), [data/raw/bootstrap_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs/LATEST.json), [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md).

Verification: protein cards must keep reviewed status, sequence metadata, aliases, and join status, and bare accessions must still resolve to `protein:` ids in the common case.

Test goal: routing regressions for accession-first lookup, ambiguous or duplicate accession handling, and lazy pointer preservation.

## Shared Checks

- No heavy payloads should be embedded directly in this slice.
- No motif or interaction-network source should be treated as present when the local registry still marks it missing.
- The operator surface should stay read-only for this slice.
- Existing protein, pair, and ligand records must still round-trip cleanly.

## Next Step

If this slice is approved, the implementation sequence is already clear: schema and builder work first, then provenance and protein cards, then the source-specific materializers and operator validation.
