# Training Set Creator Execution Backlog

- Artifact: `training_set_creator_execution_backlog`
- Generated at: `2026-04-01T10:16:50.9662238-05:00`
- Status: `planning_only`
- Scope: cohort compiler, bias analyzer, split governance, packet blueprinting, heavy hydration

## Current State
- Selected cohort: 12 packets; 7 complete, 5 partial, 0 unresolved; held; release-grade ready = false
- Release registry: 12 entries; 12 blocked; 0 ready
- Packet-gap plan: 7 ranked refs; 2 quick local extractions; 2 local bulk assay extractions; 3 fresh-acquisition blockers
- Delta boundary: 11 regressed, 1 unchanged, 7 fresh-run not promotable, 5 latest-baseline blockers

## Parallel Groups
- G0: cohort_compiler, split_governance, bias_analyzer
  - run these together after shared contracts; they consume the current cohort and delta state but do not need packet blueprints to start.
- G1: packet_blueprinting
  - turn the ranked packet-gap evidence into explicit blueprints and keep current-run-present refs report-only.
- G2: heavy_hydration
  - split hydration by modality lane once blueprints are frozen; keep writes scoped to run-scoped outputs.

## Backlog
### 1. cohort_compiler
- Action: Refresh the candidate universe and keep the held cohort frozen.
- Parallel group: `G0`

### 2. split_governance
- Action: Keep the locked split deterministic and leakage-safe.
- Parallel group: `G0`

### 3. bias_analyzer
- Action: Separate fresh-run regressions from latest-baseline blockers.
- Parallel group: `G0`

### 4. packet_blueprinting
- Action: Blueprint the packet gap queue and keep current-run-present refs report-only.
- Parallel group: `G1`

### 5. heavy_hydration
- Action: Hydrate modality lanes and rebuild only run-scoped outputs.
- Parallel group: `G2`

## cohort_compiler
- Plan alignment: `training_set_creator_and_cohort_governance`
- Status: `ready_to_run`
- Depends on: W5, W6
- Parallelizable with: split_governance, bias_analyzer
- Purpose: Assemble the candidate universe and keep the training cohort frozen until the split and bias diagnostics are stable.
- Current state: selected_cohort: packet_count=12, complete_count=7, partial_count=5, unresolved_count=0, latest_promotion_state=held, release_grade_ready=False; release_registry: entry_count=12, blocked_count=12, release_ready_count=0
- Next actions:
  - 1. Refresh the candidate universe from selected_cohort_materialization.current.json and release_cohort_registry.json without changing the protected latest manifests.
    - Why: The current cohort is held at 7 complete / 5 partial / 0 unresolved, and the release registry still has 12 blocked entries.
    - Outputs: candidate_universe_snapshot, cohort_reasons, blocked_accession_list
    - Validation gates: tests/unit/execution/test_cohort_uplift_selector.py, tests/integration/test_training_package_materialization.py
  - 2. Emit cohort-compiler diagnostics that stay fail-closed on any move that would touch protected latest manifests.
    - Why: The release registry has 0 ready rows, so the compiler should describe the hold state rather than imply release readiness.
    - Outputs: compiler_guardrails, release_hold_note
    - Validation gates: scripts/validate_operator_state.py, tests/integration/test_operator_state_contract.py
- Evidence paths: artifacts/status/selected_cohort_materialization.current.json, artifacts/status/release_cohort_registry.json, execution/analysis/cohort_uplift_selector.py, datasets/recipes/balanced_cohort_scorer.py

## bias_analyzer
- Plan alignment: `qa_benchmarking_and_release_use`
- Status: `ready_to_run`
- Depends on: W5, W6, W7, W8
- Parallelizable with: cohort_compiler, split_governance
- Purpose: Separate fresh-run regressions from latest-baseline blockers and keep the current-run-present payloads out of unresolved backlog counts.
- Current state: packet_delta_report: packet_level_regressed_count=11, packet_level_unchanged_count=1, remaining_gap_packet_count=12; packet_delta_summary: fresh_run_not_promotable_count=7, latest_baseline_blocker_count=5, fresh_run_not_promotable_accessions=['P02042', 'P02100', 'P04637', 'P31749', 'P68871', 'P69892', 'P69905'], latest_baseline_blocker_accessions=['Q9UCM0', 'P00387', 'P09105', 'Q2TAC2', 'Q9NZD4']
- Next actions:
  - 1. Build a bias/leakage scoreboard from the packet delta report, packet delta summary, and training packet audit.
    - Why: The current run has 11 regressed packet rows and 1 unchanged row; the analyzer should keep that evidence separate from promotable improvements.
    - Outputs: bias_scoreboard, leakage_notes, regression_vs_blocker_split
    - Validation gates: tests/unit/execution/test_training_packet_audit.py, tests/unit/evaluation/test_post_tier1_packet_regression.py, tests/unit/evaluation/test_release_corpus_completeness.py
  - 2. Treat ligand:Q9NZD4 as current-run-present report-only evidence, not as unresolved gap work.
    - Why: The priority ranking explicitly excludes Q9NZD4 from unresolved ranking because fresh-run payload surfaces already contain it.
    - Outputs: current_run_present_exclusion_note, bias_boundary_note
    - Validation gates: scripts/export_packet_state_delta_report.py, tests/unit/test_export_packet_state_delta_summary.py
- Evidence paths: artifacts/status/packet_state_delta_report.json, artifacts/status/packet_state_delta_summary.json, docs/reports/training_packet_audit.md, docs/reports/p19_training_envelopes.md

## split_governance
- Plan alignment: `training_set_creator_and_cohort_governance`
- Status: `ready_to_run`
- Depends on: W5, W6
- Parallelizable with: cohort_compiler, bias_analyzer
- Purpose: Keep the locked split deterministic and leakage-safe before any new cohort expansion or packet expansion.
- Current state: locked_split_envelope: frozen_cohort_split=8 train / 2 val / 2 test, resume_stability=stable, checkpoint_identity=stable, loss_mean_direction=improved_on_resume; governance_note: split governance exists and should stay fail-closed on leakage or cross-split drift.
- Next actions:
  - 1. Validate the locked split recipe and cohort selection rules against the current candidate universe.
    - Why: The frozen benchmark envelope is reproducible, but the training-set creator must keep the split contract deterministic as the cohort changes.
    - Outputs: locked_split_validation, reproducibility_note
    - Validation gates: tests/unit/datasets/test_recipe_schema.py, tests/unit/datasets/test_split_simulator.py, tests/unit/datasets/test_locked_split.py, tests/integration/test_recipe_reproducibility.py
  - 2. Keep split governance aligned with the current held cohort and do not widen the split until leakage checks remain clean.
    - Why: The current packet materialization is still held and partial at the cohort level, so split governance should support, not outrun, the cohort state.
    - Outputs: split_guardrail_note, leakage_hold_flag
    - Validation gates: tests/integration/test_operator_workflow_parity.py, tests/integration/test_packet_rebuild_determinism.py
- Evidence paths: datasets/recipes/schema.py, datasets/recipes/split_simulator.py, datasets/splits/locked_split.py, docs/reports/p19_training_envelopes.md, docs/reports/p26_data_training_gap_assessment.md

## packet_blueprinting
- Plan alignment: `packet_blueprinting_and_heavy_hydration`
- Status: `ready_to_run`
- Depends on: W5, W7
- Purpose: Translate the packet-gap execution plan into explicit blueprints and keep report-only references separate from unresolved gap work.
- Report-only refs: ligand:Q9NZD4
- Current state: packet_gap_execution_plan: ranked_source_ref_count=7, quick_local_extraction_count=2, local_bulk_assay_extraction_count=2, fresh_acquisition_blocker_count=3; packet_gap_priority_ranking: actionable_now_source_ref=ligand:P00387, current_run_present_report_only=['ligand:Q9NZD4'], blocked_source_refs=['structure:Q9UCM0', 'ppi:Q9UCM0', 'ligand:Q9UCM0', 'ligand:P09105', 'ligand:Q2TAC2']
- Next actions:
  - 1. Build packet blueprints for ligand:P00387 first and carry the local ChEMBL rescue forward into packet surfaces.
    - Why: It is the top actionable-now surface reconciliation in the ranking, and the remaining gap is packet propagation rather than discovery.
    - Outputs: p00387_packet_blueprint, surface_reconciliation_note
    - Validation gates: tests/unit/test_export_packet_gap_execution_plan.py, tests/unit/test_export_packet_deficit_dashboard.py
  - 2. Keep ligand:Q9NZD4 out of unresolved backlog counts because it is already present in fresh-run payload surfaces.
    - Why: This protects the backlog from mixing report-only current-run evidence with true missing-source work.
    - Outputs: report_only_current_run_present_note
    - Validation gates: tests/unit/test_export_packet_state_delta_summary.py, tests/unit/test_export_packet_state_delta_report.py
  - 3. Leave structure:Q9UCM0, ppi:Q9UCM0, ligand:Q9UCM0, ligand:P09105, and ligand:Q2TAC2 in blocked acquisition lanes.
    - Why: The packet-gap ranking shows these as fresh-acquisition blockers or no-local-candidate lanes, not as promotable improvements.
    - Outputs: blocked_lane_blueprints, fresh_acquisition_boundary_note
    - Validation gates: tests/unit/test_export_packet_gap_execution_plan.py, tests/unit/test_export_packet_operator_blocker_surface.py
- Evidence paths: artifacts/status/packet_gap_execution_plan.json, artifacts/status/p35_packet_gap_priority_ranking.json, artifacts/status/packet_deficit_dashboard.json, artifacts/status/packet_state_delta_report.json, docs/reports/packet_gap_execution_plan.md, docs/reports/p35_packet_gap_priority_ranking.md

## heavy_hydration
- Plan alignment: `packet_blueprinting_and_heavy_hydration`
- Status: `ready_in_lanes`
- Depends on: W5, W7, W8
- Parallelizable with: ligand_lane, structure_lane, ppi_lane
- Purpose: Hydrate packet lanes from blueprints while preserving the held latest baseline and keeping outputs run-scoped.
- Current state: selected_cohort_materialization: packet_count=12, complete_count=7, partial_count=5, unresolved_count=0, status_mismatch_count=7, latest_promotion_state=held, release_grade_ready=False; output_root: data\packages\selected-cohort-refresh\selected-cohort-refresh-20260323T1822Z
- Lanes:
  - ligand_lane: hydrate ligand packets without altering the protected latest manifests
    - Modules: execution/materialization/ligand_packet_enricher.py, execution/materialization/local_bridge_ligand_backfill.py, execution/acquire/local_chembl_rescue.py
  - structure_lane: hydrate structure packets only when the accession-clean payload exists
    - Modules: execution/materialization/structure_packet_enricher.py, execution/acquire/alphafold_snapshot.py, execution/acquire/rcsb_pdbe_snapshot.py
  - ppi_lane: hydrate curated PPI packets while treating alias-only evidence as non-rescue
    - Modules: execution/materialization/local_bridge_ppi_backfill.py, execution/acquire/biogrid_snapshot.py, execution/acquire/intact_snapshot.py
  - package_build_lane: rebuild the selected cohort package outputs from the lane results
    - Modules: execution/materialization/training_packet_materializer.py, execution/materialization/selective_materializer.py, execution/materialization/package_builder.py, scripts/materialize_selected_packet_cohort.py
- Next actions:
  - 1. Hydrate the modality lanes in parallel once the blueprints are frozen.
    - Why: The current selected cohort is held at 7 complete / 5 partial, so lane hydration should improve the run-scoped outputs without implying release readiness.
    - Outputs: hydrated_ligand_lane, hydrated_structure_lane, hydrated_ppi_lane
    - Validation gates: tests/integration/test_materialize_selected_packet_cohort.py, tests/integration/test_packet_rehydration.py, tests/integration/test_packet_rebuild_determinism.py
  - 2. Keep writes scoped to run artifacts and do not modify protected latest packet manifests.
    - Why: The held latest promotion state and the release registry both remain blocked, so heavy hydration must stay on the run-scoped side of the boundary.
    - Outputs: run_scoped_package_root, hydration_guardrail_note
    - Validation gates: tests/unit/execution/test_training_packet_materializer.py, tests/unit/execution/test_ligand_packet_enricher.py, tests/unit/execution/test_structure_packet_enricher.py
  - 3. Re-run release-wave and operator validation only after hydration changes settle.
    - Why: Release readiness is still false, so the last step is verifying the operator surface rather than claiming success early.
    - Outputs: release_wave_recheck, operator_surface_refresh
    - Validation gates: tests/unit/execution/test_release_ligand_wave.py, tests/unit/execution/test_release_ppi_wave.py, scripts/validate_operator_state.py
- Evidence paths: execution/materialization/training_packet_materializer.py, execution/materialization/selective_materializer.py, execution/materialization/package_builder.py, scripts/materialize_selected_packet_cohort.py, artifacts/status/selected_cohort_materialization.current.json, data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z

## Guardrails
- Do not modify protected latest packet manifests.
- Treat current-run-present references like ligand:Q9NZD4 as report-only, not unresolved backlog.
- Keep fresh-run regressions separate from promotable improvements.
- Keep release readiness false until hydration, split governance, and operator validation all agree.
