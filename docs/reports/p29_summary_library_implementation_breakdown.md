# P29 Summary Library Implementation Breakdown

This breakdown turns the P29 summary-library plan into phased work packages. It stays grounded in the current schema and artifacts: [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py) already covers the protein, pair, and ligand spine, [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py) already preserves unresolved evidence, and the refreshed local registry at [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json) makes the current truth boundary explicit.

## Phase 1

Schema and builder expansion come first. We need new record families before structure, motif, pathway, and provenance cards can be materialized safely.

Likely touch points: [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py), [core/storage/planning_index_schema.py](/D:/documents/ProteoSphereV2/core/storage/planning_index_schema.py), [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py), [execution/indexing/protein_pair_crossref.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_pair_crossref.py), [tests/unit/core/test_summary_record.py](/D:/documents/ProteoSphereV2/tests/unit/core/test_summary_record.py), [tests/unit/execution/test_build_summary_library.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_build_summary_library.py).

Data dependencies: [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md), [docs/reports/source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md), [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json), [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json).

Verification targets: new record families round-trip through `to_dict` and `from_dict`, mixed-library serialization does not collapse record kinds, and context defaults keep materialize/index/lazy splits explicit.

Test coverage goals: add unit tests for structure, motif, pathway, and provenance serialization; add mixed-library round-trip coverage; keep duplicate-summary-id rejection intact.

## Phase 2

Protein spine and provenance come next. Every later join depends on a durable provenance card for each materialized row.

Likely touch points: [execution/library/source_provenance_summary.py](/D:/documents/ProteoSphereV2/execution/library/source_provenance_summary.py), [execution/acquire/local_source_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py), [execution/acquire/unified_source_catalog.py](/D:/documents/ProteoSphereV2/execution/acquire/unified_source_catalog.py), [scripts/materialize_summary_library.py](/D:/documents/ProteoSphereV2/scripts/materialize_summary_library.py), [execution/indexing/protein_index.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_index.py), [tests/unit/execution/test_protein_index.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_protein_index.py).

Data dependencies: [data/raw/bootstrap_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs/LATEST.json), [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json).

Verification targets: provenance cards carry `source_name`, `source_record_id`, `release_version`, `release_date`, `checksum`, and `join_status`, and each materialized row keeps at least one provenance pointer.

Test coverage goals: add provenance round-trip tests, add an integration check for provenance pointers on materialized rows, and keep accession-first protein routing explicit.

## Phase 3

Structure, ligand, and pathway cards are the first user-visible payload slice. The refreshed local registry already says these source families are present enough to materialize.

Likely touch points: [execution/library/structure_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/structure_local_summary.py), [execution/library/ligand_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/ligand_local_summary.py), [execution/library/reactome_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/reactome_local_summary.py), [execution/indexing/interaction_index.py](/D:/documents/ProteoSphereV2/execution/indexing/interaction_index.py), [tests/unit/execution/test_structure_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_structure_local_summary.py), [tests/unit/execution/test_reactome_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_reactome_local_summary.py).

Data dependencies: `data/raw/rcsb`, `data/structures/rcsb`, `data/extracted/entry`, `data/extracted/chains`, `data/extracted/interfaces`, `data/extracted/provenance`, `data_sources/alphafold`, `data_sources/bindingdb`, `data_sources/chembl`, `data_sources/biolip`, `data_sources/pdbbind`, `data_sources/reactome`.

Verification targets: experimental and predicted structure records stay separate, ligand cards join on stable chemical identity rather than target names alone, and pathway refs preserve stable id, species, ancestry, and evidence code.

Test coverage goals: add structure key and round-trip tests, add ligand chemical-identifier and assay summary tests, and extend Reactome coverage with ancestry assertions.

## Phase 4

Curated interactions and cross-references need to stay conservative. This slice should reuse the existing IntAct path and keep native ids visible.

Likely touch points: [execution/library/intact_local_summary.py](/D:/documents/ProteoSphereV2/execution/library/intact_local_summary.py), [execution/library/weak_ppi_candidate_summary.py](/D:/documents/ProteoSphereV2/execution/library/weak_ppi_candidate_summary.py), [execution/indexing/protein_pair_crossref.py](/D:/documents/ProteoSphereV2/execution/indexing/protein_pair_crossref.py), [execution/indexing/interaction_index.py](/D:/documents/ProteoSphereV2/execution/indexing/interaction_index.py), [tests/unit/execution/test_intact_local_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_intact_local_summary.py), [tests/unit/execution/test_weak_ppi_candidate_summary.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_weak_ppi_candidate_summary.py).

Data dependencies: [data/raw/intact](/D:/documents/ProteoSphereV2/data/raw/intact), [artifacts/status/interaction_index_fix_2026_03_22.json](/D:/documents/ProteoSphereV2/artifacts/status/interaction_index_fix_2026_03_22.json), [artifacts/status/p27_weak_ppi_summary_decision_p09105_q2tac2.json](/D:/documents/ProteoSphereV2/artifacts/status/p27_weak_ppi_summary_decision_p09105_q2tac2.json).

Verification targets: native interaction ids and association ids survive materialization, weak or self-only rows stay explicit partials, and pair provenance remains attached even when the row is partial.

Test coverage goals: add evidence-preservation regressions, weak-PPI eligibility regressions, and native-id round-trip coverage. Keep bare-accession routing and chemical-only ligand refs explicit in the planning layer.

## Phase 5

Motif support should be plumbed without pretending the local motif sources are present. The refreshed registry still marks motif and broad interaction-network families as missing.

Likely touch points: [execution/library/motif_summary.py](/D:/documents/ProteoSphereV2/execution/library/motif_summary.py), [execution/acquire/local_source_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py), [execution/acquire/unified_source_catalog.py](/D:/documents/ProteoSphereV2/execution/acquire/unified_source_catalog.py), [tests/unit/core/test_summary_record.py](/D:/documents/ProteoSphereV2/tests/unit/core/test_summary_record.py).

Data dependencies: [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json), [docs/reports/source_coverage_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/source_coverage_matrix.md), [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md).

Verification targets: motif rows require stable spans when materialized, missing motif sources stay explicit placeholders, and portal payloads remain lazy.

Test coverage goals: add span-aware motif serialization tests, add deferred/index-only missing-source tests, and keep placeholder round-trips separate from protein records.

## Phase 6

Operator surfacing and release validation close the loop. The operator view should be able to cite the concrete summary-library artifact, and validation should fail closed if the artifact is malformed.

Likely touch points: [scripts/powershell_interface.ps1](/D:/documents/ProteoSphereV2/scripts/powershell_interface.ps1), [scripts/validate_operator_state.py](/D:/documents/ProteoSphereV2/scripts/validate_operator_state.py), [tests/integration/test_powershell_interface.py](/D:/documents/ProteoSphereV2/tests/integration/test_powershell_interface.py), [tests/integration/test_operator_state_contract.py](/D:/documents/ProteoSphereV2/tests/integration/test_operator_state_contract.py), [tests/integration/test_summary_library_real_corpus.py](/D:/documents/ProteoSphereV2/tests/integration/test_summary_library_real_corpus.py), [tests/integration/test_index_rebuild.py](/D:/documents/ProteoSphereV2/tests/integration/test_index_rebuild.py).

Data dependencies: [artifacts/status/p29_summary_library_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/p29_summary_library_plan.json), [artifacts/status/p29_summary_library_implementation_breakdown.json](/D:/documents/ProteoSphereV2/artifacts/status/p29_summary_library_implementation_breakdown.json), [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json), [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json).

Verification targets: operator state reports the concrete summary-library path, id, source-manifest id, record count, and record types; readiness stays separate from materialization; parse/file errors fail closed.

Test coverage goals: add artifact-field assertions to the PowerShell integration tests, add a malformed-artifact fail-closed regression, and keep `ready_for_materialization` semantics unchanged while expanding visibility.

## Recommended First Slice

Start with schema and builder work, then provenance and protein cards:

1. `P1-WP1`
2. `P1-WP2`
3. `P2-WP1`
4. `P2-WP2`

That sequence unblocks everything else while keeping the operator surface and truth boundary stable.
