from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("PowerShell is required for the operator recipe integration test")


def _copy_repo_subset(temp_root: Path) -> Path:
    scripts_dir = temp_root / "scripts"
    reports_dir = temp_root / "docs" / "reports"
    results_dir = temp_root / "runs" / "real_data_benchmark" / "full_results"
    status_dir = temp_root / "artifacts" / "status"
    tasks_dir = temp_root / "tasks"

    scripts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    for name in ("powershell_interface.ps1", "operator_recipes.ps1", "monitor.py", "tasklib.py"):
        shutil.copy2(REPO_ROOT / "scripts" / name, scripts_dir / name)

    report_names = (
        "p19_training_envelopes.md",
        "p20_acceptance_matrix.md",
        "p20_simulated_researcher_personas.md",
        "p20_user_sim_regression.md",
        "p21_onboarding_friction.md",
        "p22_weeklong_soak.md",
        "training_packet_audit.md",
        "operator_library_materialization_regression.md",
    )
    for name in report_names:
        shutil.copy2(REPO_ROOT / "docs" / "reports" / name, reports_dir / name)

    result_names = (
        "run_summary.json",
        "checkpoint_summary.json",
        "model_portfolio_benchmark.json",
        "training_packet_audit.json",
        "user_sim_regression.json",
        "summary.json",
    )
    for name in result_names:
        shutil.copy2(
            REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / name,
            results_dir / name,
        )

    status_names = (
        "orchestrator_state.json",
        "P6-T001.json",
        "P6-T003.json",
        "training_set_readiness_preview.json",
        "cohort_compiler_preview.json",
        "balance_diagnostics_preview.json",
        "cohort_inclusion_rationale_preview.json",
        "training_set_gating_evidence_preview.json",
        "training_set_action_queue_preview.json",
        "training_set_blocker_burndown_preview.json",
        "training_set_modality_gap_register_preview.json",
        "training_set_package_blocker_matrix_preview.json",
        "training_set_gate_ladder_preview.json",
        "training_set_unlock_route_preview.json",
        "training_set_transition_contract_preview.json",
        "training_set_source_fix_batch_preview.json",
        "training_set_package_transition_batch_preview.json",
        "training_set_package_execution_preview.json",
        "training_set_preview_hold_register_preview.json",
        "training_set_preview_hold_exit_criteria_preview.json",
        "training_set_preview_hold_clearance_batch_preview.json",
        "training_set_remediation_plan_preview.json",
        "training_set_unblock_plan_preview.json",
        "scrape_backlog_remaining_preview.json",
        "package_readiness_preview.json",
        "training_set_builder_session_preview.json",
        "training_set_builder_runbook_preview.json",
        "external_dataset_intake_contract_preview.json",
        "external_dataset_assessment_preview.json",
        "external_dataset_manifest_lint_preview.json",
        "external_dataset_flaw_taxonomy_preview.json",
        "external_dataset_risk_register_preview.json",
        "external_dataset_conflict_register_preview.json",
        "external_dataset_acceptance_gate_preview.json",
        "external_dataset_admission_decision_preview.json",
        "external_dataset_clearance_delta_preview.json",
        "external_dataset_resolution_preview.json",
        "external_dataset_acceptance_path_preview.json",
        "external_dataset_remediation_readiness_preview.json",
        "external_dataset_caveat_execution_preview.json",
        "external_dataset_blocked_acquisition_batch_preview.json",
        "external_dataset_acquisition_unblock_preview.json",
        "external_dataset_advisory_followup_register_preview.json",
        "external_dataset_caveat_exit_criteria_preview.json",
        "external_dataset_caveat_review_batch_preview.json",
        "external_dataset_remediation_queue_preview.json",
        "external_dataset_leakage_audit_preview.json",
        "external_dataset_modality_audit_preview.json",
        "external_dataset_binding_audit_preview.json",
        "external_dataset_structure_audit_preview.json",
        "external_dataset_provenance_audit_preview.json",
        "external_dataset_issue_matrix_preview.json",
        "sample_external_dataset_assessment_bundle_preview.json",
        "scrape_gap_matrix_preview.json",
        "overnight_queue_backlog_preview.json",
        "overnight_execution_contract_preview.json",
        "scrape_execution_wave_preview.json",
        "overnight_idle_status_preview.json",
        "overnight_pending_reconciliation_preview.json",
        "overnight_worker_launch_gap_preview.json",
        "procurement_supervisor_freshness_preview.json",
        "procurement_tail_signal_reconciliation_preview.json",
        "procurement_tail_growth_preview.json",
        "procurement_headroom_guard_preview.json",
        "procurement_tail_space_drift_preview.json",
        "procurement_tail_source_pressure_preview.json",
        "procurement_tail_log_progress_registry_preview.json",
        "procurement_tail_completion_margin_preview.json",
        "procurement_space_recovery_target_preview.json",
        "procurement_space_recovery_candidates_preview.json",
        "procurement_space_recovery_execution_batch_preview.json",
        "procurement_space_recovery_safety_register_preview.json",
        "procurement_tail_fill_risk_preview.json",
        "procurement_space_recovery_trigger_preview.json",
        "procurement_space_recovery_gap_drift_preview.json",
        "procurement_space_recovery_coverage_preview.json",
        "procurement_recovery_intervention_priority_preview.json",
        "procurement_recovery_escalation_lane_preview.json",
        "procurement_space_recovery_concentration_preview.json",
        "procurement_recovery_shortfall_bridge_preview.json",
        "procurement_recovery_lane_fragility_preview.json",
        "procurement_broader_search_trigger_preview.json",
        "overnight_wave_advance_preview.json",
    )
    for name in status_names:
        shutil.copy2(REPO_ROOT / "artifacts" / "status" / name, status_dir / name)

    shutil.copy2(REPO_ROOT / "tasks" / "task_queue.json", tasks_dir / "task_queue.json")
    return temp_root


def _run_recipe(repo_root: Path, recipe: str) -> dict[str, object]:
    command = [
        _powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "operator_recipes.ps1"),
        "-Recipe",
        recipe,
        "-AsJson",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def test_operator_recipes_dispatch_supported_acceptance_review(tmp_path: Path) -> None:
    repo_root = _copy_repo_subset(tmp_path / "repo")

    payload = _run_recipe(repo_root, "acceptance-review")

    assert payload["recipe_id"] == "acceptance-review"
    assert payload["status"] == "supported"
    assert "1 supported, 4 weak, and 1 blocked workflows" in payload["summary"]
    assert any("p20_acceptance_matrix.md" in item for item in payload["artifacts"])
    assert any("supported workflows=" in item for item in payload["diagnostics"])
    assert "weeklong soak remains unproven" in payload["truth_boundary"]


def test_operator_recipes_dispatch_weak_packet_triage(tmp_path: Path) -> None:
    repo_root = _copy_repo_subset(tmp_path / "repo")

    payload = _run_recipe(repo_root, "packet-triage")

    assert payload["recipe_id"] == "packet-triage"
    assert payload["status"] == "weak"
    assert "remain partial" in payload["summary"]
    assert any("packet count=" in item for item in payload["diagnostics"])
    assert any("partial packets=" in item for item in payload["diagnostics"])
    assert "partial packets remain partial" in payload["truth_boundary"]


def test_operator_recipes_dispatch_blocked_soak_readiness(tmp_path: Path) -> None:
    repo_root = _copy_repo_subset(tmp_path / "repo")

    payload = _run_recipe(repo_root, "soak-readiness")

    assert payload["recipe_id"] == "soak-readiness"
    assert payload["status"] == "blocked"
    assert "weeklong-soak proof" in payload["summary"]
    assert any("readiness-only" in item for item in payload["diagnostics"])
    assert "weeklong soak remains unproven" in payload["truth_boundary"]


def test_operator_recipes_dispatch_supported_training_set_builder(tmp_path: Path) -> None:
    repo_root = _copy_repo_subset(tmp_path / "repo")

    payload = _run_recipe(repo_root, "training-set-builder")

    assert payload["recipe_id"] == "training-set-builder"
    assert payload["status"] == "supported"
    assert any("training_set_builder_runbook_preview.json" in item for item in payload["artifacts"])
    assert any("cohort_inclusion_rationale_preview.json" in item for item in payload["artifacts"])
    assert any(
        "training_set_gating_evidence_preview.json" in item for item in payload["artifacts"]
    )
    assert any(
        "training_set_action_queue_preview.json" in item for item in payload["artifacts"]
    )
    assert any(
        "training_set_blocker_burndown_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_modality_gap_register_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_package_blocker_matrix_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("training_set_gate_ladder_preview.json" in item for item in payload["artifacts"])
    assert any("training_set_unlock_route_preview.json" in item for item in payload["artifacts"])
    assert any(
        "training_set_transition_contract_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("training_set_unblock_plan_preview.json" in item for item in payload["artifacts"])
    assert any("scrape_backlog_remaining_preview.json" in item for item in payload["artifacts"])
    assert any("runbook steps=" in item for item in payload["diagnostics"])
    assert any("rationale rows=" in item for item in payload["diagnostics"])
    assert any("gating evidence rows=" in item for item in payload["diagnostics"])
    assert any("action queue rows=" in item for item in payload["diagnostics"])
    assert any("action queue impacted accessions=" in item for item in payload["diagnostics"])
    assert any("blocker burndown blocked accessions=" in item for item in payload["diagnostics"])
    assert any("blocker burndown critical actions=" in item for item in payload["diagnostics"])
    assert any("modality gap blocked modalities=" in item for item in payload["diagnostics"])
    assert any("top modality gap=" in item for item in payload["diagnostics"])
    assert any("package blocker rows=" in item for item in payload["diagnostics"])
    assert any("package blocker fold export blocked=" in item for item in payload["diagnostics"])
    assert any("gate ladder next step=" in item for item in payload["diagnostics"])
    assert any("gate ladder alerts=" in item for item in payload["diagnostics"])
    assert any("unlock route next transition=" in item for item in payload["diagnostics"])
    assert any("unlock route blocked routes=" in item for item in payload["diagnostics"])
    assert any(
        "transition contract next step=" in item for item in payload["diagnostics"]
    )
    assert any(
        "transition contract source-fix pending=" in item
        for item in payload["diagnostics"]
    )
    assert any(
        "training_set_source_fix_batch_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_package_transition_batch_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_package_execution_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_preview_hold_register_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_preview_hold_exit_criteria_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "training_set_preview_hold_clearance_batch_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("source-fix batch rows=" in item for item in payload["diagnostics"])
    assert any("source-fix batch next ref=" in item for item in payload["diagnostics"])
    assert any(
        "package transition batch rows=" in item for item in payload["diagnostics"]
    )
    assert any(
        "package transition next batch=" in item for item in payload["diagnostics"]
    )
    assert any("package execution rows=" in item for item in payload["diagnostics"])
    assert any("package execution lane=" in item for item in payload["diagnostics"])
    assert any("preview hold rows=" in item for item in payload["diagnostics"])
    assert any("preview hold lane=" in item for item in payload["diagnostics"])
    assert any("preview hold exit rows=" in item for item in payload["diagnostics"])
    assert any("preview hold exit state=" in item for item in payload["diagnostics"])
    assert any("preview hold clearance rows=" in item for item in payload["diagnostics"])
    assert any("preview hold clearance batch=" in item for item in payload["diagnostics"])
    assert any("unblock impacted accessions=" in item for item in payload["diagnostics"])
    assert any("scrape backlog next jobs=" in item for item in payload["diagnostics"])
    assert any("scrape backlog missing lanes=" in item for item in payload["diagnostics"])
    assert any(
        "training_set_remediation_plan_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("remediation rows=" in item for item in payload["diagnostics"])


def test_operator_recipes_dispatch_supported_external_dataset_assessment(tmp_path: Path) -> None:
    repo_root = _copy_repo_subset(tmp_path / "repo")

    payload = _run_recipe(repo_root, "external-dataset-assessment")

    assert payload["recipe_id"] == "external-dataset-assessment"
    assert payload["status"] == "supported"
    assert any(
        "sample_external_dataset_assessment_bundle_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_manifest_lint_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_flaw_taxonomy_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_risk_register_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_conflict_register_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_acceptance_gate_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_admission_decision_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_clearance_delta_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_resolution_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_acceptance_path_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_remediation_readiness_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_caveat_execution_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_blocked_acquisition_batch_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_acquisition_unblock_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_advisory_followup_register_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_caveat_exit_criteria_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_caveat_review_batch_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_remediation_queue_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "external_dataset_issue_matrix_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("manifest lint verdict=" in item for item in payload["diagnostics"])
    assert any("flaw taxonomy verdict=" in item for item in payload["diagnostics"])
    assert any("flaw taxonomy blocking categories=" in item for item in payload["diagnostics"])
    assert any("risk register verdict=" in item for item in payload["diagnostics"])
    assert any("risk register top rows=" in item for item in payload["diagnostics"])
    assert any("conflict register verdict=" in item for item in payload["diagnostics"])
    assert any("conflict register top rows=" in item for item in payload["diagnostics"])
    assert any("acceptance gate overall verdict=" in item for item in payload["diagnostics"])
    assert any("admission decision=" in item for item in payload["diagnostics"])
    assert any("admission blocking gate count=" in item for item in payload["diagnostics"])
    assert any("clearance delta state=" in item for item in payload["diagnostics"])
    assert any("clearance delta required changes=" in item for item in payload["diagnostics"])
    assert any("resolution overall verdict=" in item for item in payload["diagnostics"])
    assert any("acceptance path next transition=" in item for item in payload["diagnostics"])
    assert any("acceptance path blocked transitions=" in item for item in payload["diagnostics"])
    assert any(
        "remediation readiness next batch=" in item
        for item in payload["diagnostics"]
    )
    assert any(
        "remediation readiness blocked acquisitions=" in item
        for item in payload["diagnostics"]
    )
    assert any("caveat execution rows=" in item for item in payload["diagnostics"])
    assert any("caveat execution next batch=" in item for item in payload["diagnostics"])
    assert any(
        "blocked acquisition batch rows=" in item for item in payload["diagnostics"]
    )
    assert any(
        "blocked acquisition next gate=" in item for item in payload["diagnostics"]
    )
    assert any(
        "acquisition unblock rows=" in item for item in payload["diagnostics"]
    )
    assert any(
        "acquisition unblock lane=" in item for item in payload["diagnostics"]
    )
    assert any(
        "advisory follow-up rows=" in item for item in payload["diagnostics"]
    )
    assert any(
        "advisory follow-up lane=" in item for item in payload["diagnostics"]
    )
    assert any("caveat exit rows=" in item for item in payload["diagnostics"])
    assert any("caveat exit state=" in item for item in payload["diagnostics"])
    assert any("caveat review rows=" in item for item in payload["diagnostics"])
    assert any("caveat review batch=" in item for item in payload["diagnostics"])
    assert any("remediation queue rows=" in item for item in payload["diagnostics"])
    assert any("remediation queue blocked accessions=" in item for item in payload["diagnostics"])
    assert any("sample bundle verdict=" in item for item in payload["diagnostics"])
    assert any("issue rows=" in item for item in payload["diagnostics"])


def test_operator_recipes_dispatch_supported_overnight_run_readiness(tmp_path: Path) -> None:
    repo_root = _copy_repo_subset(tmp_path / "repo")

    payload = _run_recipe(repo_root, "overnight-run-readiness")

    assert payload["recipe_id"] == "overnight-run-readiness"
    assert payload["status"] == "supported"
    assert any("scrape_backlog_remaining_preview.json" in item for item in payload["artifacts"])
    assert any("scrape_execution_wave_preview.json" in item for item in payload["artifacts"])
    assert any("scrape backlog rows=" in item for item in payload["diagnostics"])
    assert any("still missing lanes=" in item for item in payload["diagnostics"])
    assert any("structured scrape jobs=" in item for item in payload["diagnostics"])
    assert any("overnight_idle_status_preview.json" in item for item in payload["artifacts"])
    assert any("idle state=" in item for item in payload["diagnostics"])
    assert any(
        "overnight_pending_reconciliation_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "pending reconciliation state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "overnight_worker_launch_gap_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("worker launch gap state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_supervisor_freshness_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("procurement freshness state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_tail_signal_reconciliation_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("tail reconciliation state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_tail_growth_preview.json" in item for item in payload["artifacts"]
    )
    assert any("tail growth state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_headroom_guard_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("headroom guard state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_tail_space_drift_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("tail space drift state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_tail_source_pressure_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "tail source pressure state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_tail_log_progress_registry_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("tail log registry state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_tail_completion_margin_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "tail completion margin state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_target_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery target state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_candidates_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery ranked GiB=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_execution_batch_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery execution state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_safety_register_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery safety state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_tail_fill_risk_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any("tail fill risk state=" in item for item in payload["diagnostics"])
    assert any(
        "procurement_space_recovery_trigger_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery trigger state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_gap_drift_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery gap drift state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_coverage_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "space recovery coverage state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_recovery_intervention_priority_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "recovery intervention priority state=" in item
        for item in payload["diagnostics"]
    )
    assert any(
        "procurement_recovery_escalation_lane_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "recovery escalation lane state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_space_recovery_concentration_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "recovery concentration state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_recovery_shortfall_bridge_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "recovery shortfall bridge state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_recovery_lane_fragility_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "recovery lane fragility state=" in item for item in payload["diagnostics"]
    )
    assert any(
        "procurement_broader_search_trigger_preview.json" in item
        for item in payload["artifacts"]
    )
    assert any(
        "broader search trigger state=" in item for item in payload["diagnostics"]
    )
    assert any("wave added tasks=" in item for item in payload["diagnostics"])
