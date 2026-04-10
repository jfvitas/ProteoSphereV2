# P50 Training-Set Creator Library Contract

- Artifact: `p50_training_set_creator_library_contract`
- Status: `report_only`
- Generated at: `2026-04-01T11:00:51.1748269-05:00`
- Scope: lightweight library only

This is the report-only contract for the first executable training-set creator library surface. It stays inside the current materialized artifacts and defines what the lightweight library must expose for unbiased cohort design, leakage-safe splits, external cohort audit, and packet blueprint generation.

## Current Ground Truth

- Selected cohort materialization is still held: 12 packets, 7 complete, 5 partial, 0 unresolved, `latest_promotion_state=held`, `release_grade_ready=false`.
- Release registry is still blocked: 12 entries, 12 blocked, 0 ready, `freeze_state=draft`.
- Packet-gap planning is still narrow and truthful: 7 ranked source refs, 2 quick local extractions, 2 local bulk assay extractions, 3 fresh-acquisition blockers.
- Delta state stays split: 11 regressed packets, 1 unchanged packet, 7 fresh-run not promotable, 5 latest-baseline blockers.
- Report-only freshest-run evidence remains separate from backlog: `ligand:Q9NZD4` is present in the freshest payloads and must not be counted as unresolved work.

Current evidence anchors:

- [selected_cohort_materialization.current.json](D:/documents/ProteoSphereV2/artifacts/status/selected_cohort_materialization.current.json)
- [release_cohort_registry.json](D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json)
- [packet_gap_execution_plan.json](D:/documents/ProteoSphereV2/artifacts/status/packet_gap_execution_plan.json)
- [p35_packet_gap_priority_ranking.json](D:/documents/ProteoSphereV2/artifacts/status/p35_packet_gap_priority_ranking.json)
- [packet_deficit_dashboard.json](D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [packet_state_delta_report.json](D:/documents/ProteoSphereV2/artifacts/status/packet_state_delta_report.json)
- [packet_state_delta_summary.json](D:/documents/ProteoSphereV2/artifacts/status/packet_state_delta_summary.json)
- [training_packet_audit.md](D:/documents/ProteoSphereV2/docs/reports/training_packet_audit.md)

## What The Lightweight Library Must Expose

The contract is intentionally small. The library must expose summary records, source-rollup views, split- and audit-ready recipe records, and packet blueprint views. It must not try to solve procurement or heavy hydration itself.

| Domain | Must expose | Must preserve |
|---|---|---|
| Unbiased cohort design | candidate universe, balance diagnostics, coverage profile, inclusion/exclusion reasons | held cohort state, provenance, trust tier, partial rows, report-only current-run evidence |
| Leakage-safe splits | leakage signature set, split simulation result, locked split result, rejected candidate report | deterministic splits, fail-closed overlap handling, reproducibility, rejected rows kept visible |
| External cohort audit | external cohort audit, row-level entity resolution, missing entity report, conflict and partial report | no mutation, row-level provenance, unresolved rows, explicit conflicts |
| Packet blueprint generation | packet blueprint set, hydration route map, modality gap table, report-only reference boundary | partial status, blocked lanes, current-run-present refs, truthful modality gaps |

## Contracted Record Types

The lightweight library must surface these record families or their direct equivalents:

- `SummarySourceClaim`
- `SummarySourceRollup`
- `SummarySourceConnection`
- `SummaryCrossSourceView`
- `SummaryRecordContext`
- `ProteinSummaryRecord`
- `ProteinProteinSummaryRecord`
- `ProteinLigandSummaryRecord`
- `SummaryLibrarySchema`
- `EntityCardEvidenceSummary`
- `ProteinEntityCard`
- `ProteinProteinEntityCard`
- `ProteinLigandEntityCard`
- `RecipeSelectionRule`
- `RecipeRuleGroup`
- `RecipeCompletenessPolicy`
- `RecipeLeakagePolicy`
- `RecipeEvaluationContext`
- `RecipeCandidateEvaluation`
- `TrainingRecipeSchema`
- `SplitSimulationCandidate`
- `SplitSimulationAssignment`
- `SplitSimulationRejected`
- `SplitSimulationResult`
- `LockedSplitRecord`
- `LockedSplitAssignment`
- `LockedSplitUnresolvedRecord`
- `LockedSplitResult`

The important part is not the exact class names. The important part is that the library can represent a candidate universe, a leakage-aware split, an external audit, and a packet blueprint without losing provenance or conflict state.

## Boundary Cases The Contract Must Keep Visible

- `P31749` is the proof that disagreement must stay explicit. The preserved baseline is complete, but the freshest run regressed. The library must keep that as a conflict, not flatten it into consensus.
- `P00387` is the proof that partial must stay partial. The preserved baseline still has a ligand gap, so the library must keep the blocker state visible.
- `Q9NZD4` is the proof that report-only evidence is not backlog. It is present in the freshest payloads and must stay separate from unresolved missing-source work.

These cases are not special pleading. They are the current state of the repo, and the contract should behave correctly on them before it tries to generalize.

## Practical Contract Rules

The first executable version should follow these rules:

1. Build the candidate universe from the current lightweight library plus the current selected cohort snapshot.
2. Compute balance and leakage diagnostics before any split is frozen.
3. Keep external audits read-only and row-level.
4. Generate packet blueprints from source-fusion evidence, not from guesses.
5. Keep current-run-present refs report-only and keep fresh-run regressions separate from preserved-baseline blockers.
6. Never infer release readiness from this contract alone.

## Validation Gates

The contract should be checked against the current repo surfaces that already exist:

- `tests/unit/datasets/test_recipe_schema.py`
- `tests/unit/datasets/test_split_simulator.py`
- `tests/unit/datasets/test_locked_split.py`
- `tests/unit/execution/test_cohort_uplift_selector.py`
- `tests/unit/execution/test_training_packet_audit.py`
- `tests/unit/test_export_packet_gap_execution_plan.py`
- `tests/unit/test_export_packet_deficit_dashboard.py`
- `tests/unit/test_export_packet_state_delta_report.py`
- `tests/unit/test_export_packet_state_delta_summary.py`
- `tests/integration/test_operator_state_contract.py`
- `tests/integration/test_packet_rebuild_determinism.py`
- `tests/integration/test_recipe_reproducibility.py`

## Non-Goals

- No code edits.
- No protected latest packet manifest edits.
- No procurement claims.
- No heavy hydration claims.
- No release promotion claims.

The right reading is simple: the lightweight library should become the truth-preserving planning layer for cohort design, split governance, audit, and packet blueprints, while the actual packet-building and release systems stay separate.
