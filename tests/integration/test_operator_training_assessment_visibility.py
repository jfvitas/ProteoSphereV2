from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_operator_dashboard_exposes_training_and_assessment_blocks() -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "export_operator_dashboard.py")],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    dashboard = json.loads(
        (
            REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "operator_dashboard.json"
        ).read_text(encoding="utf-8")
    )

    training_block = dashboard["training_set_creation_and_assessment"]
    overnight_block = dashboard["overnight_parallel"]

    assert training_block["training_set_readiness_preview"]["status"] == "report_only"
    assert training_block["training_set_readiness_preview"]["release_ready"] is False
    assert training_block["external_dataset_intake_contract_preview"]["accepted_shape_ids"] == [
        "json_manifest",
        "folder_package_manifest",
    ]
    assert training_block["external_dataset_assessment_preview"]["overall_verdict"] in {
        "usable_with_caveats",
        "audit_only",
        "blocked_pending_mapping",
        "blocked_pending_cleanup",
    }
    assert training_block["external_dataset_flaw_taxonomy_preview"]["status"] == "report_only"
    assert training_block["external_dataset_flaw_taxonomy_preview"]["dataset_accession_count"] == 12
    assert training_block["external_dataset_risk_register_preview"]["status"] == "report_only"
    assert training_block["external_dataset_risk_register_preview"]["dataset_accession_count"] == 12
    assert training_block["external_dataset_conflict_register_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_conflict_register_preview"]["dataset_accession_count"]
        == 12
    )
    assert (
        training_block["training_set_candidate_package_manifest_preview"]["package_ready"] is False
    )
    assert (
        training_block["procurement_process_diagnostics_preview"]["authoritative_tail_file_count"]
        == 1
    )
    assert (
        training_block["procurement_process_diagnostics_preview"]["raw_process_table_active_count"]
        >= training_block["procurement_process_diagnostics_preview"][
            "authoritative_tail_file_count"
        ]
    )
    assert training_block["split_simulation_preview"]["status"] == "report_only"
    assert training_block["split_simulation_preview"]["label_count"] == 12
    assert training_block["split_simulation_preview"]["package_ready"] is False
    assert training_block["training_set_remediation_plan_preview"]["status"] == "report_only"
    assert training_block["training_set_remediation_plan_preview"]["row_count"] == 12
    assert training_block["cohort_inclusion_rationale_preview"]["status"] == "report_only"
    assert training_block["cohort_inclusion_rationale_preview"]["row_count"] == 12
    assert training_block["training_set_unblock_plan_preview"]["status"] == "report_only"
    assert training_block["training_set_unblock_plan_preview"]["impacted_accession_count"] == 12
    assert training_block["training_set_gating_evidence_preview"]["status"] == "report_only"
    assert training_block["training_set_gating_evidence_preview"]["row_count"] == 12
    assert training_block["training_set_action_queue_preview"]["status"] == "report_only"
    assert training_block["training_set_action_queue_preview"]["selected_accession_count"] == 12
    assert training_block["training_set_blocker_burndown_preview"]["status"] == "report_only"
    assert training_block["training_set_blocker_burndown_preview"]["selected_accession_count"] == 12
    assert training_block["training_set_modality_gap_register_preview"]["status"] == "report_only"
    assert (
        training_block["training_set_modality_gap_register_preview"]["selected_accession_count"]
        == 12
    )
    assert training_block["training_set_package_blocker_matrix_preview"]["status"] == "report_only"
    assert (
        training_block["training_set_package_blocker_matrix_preview"]["selected_accession_count"]
        == 12
    )
    assert training_block["training_set_gate_ladder_preview"]["status"] == "report_only"
    assert training_block["training_set_gate_ladder_preview"]["selected_accession_count"] == 12
    assert training_block["training_set_gate_ladder_preview"]["gate_ladder_status"] in {
        "blocked_pending_package_gate",
        "ready_for_package",
        "blocked_missing_inputs",
    }
    assert training_block["training_set_unlock_route_preview"]["status"] == "report_only"
    assert training_block["training_set_unlock_route_preview"]["selected_accession_count"] == 12
    assert training_block["training_set_unlock_route_preview"]["current_route_state"] in {
        "blocked_pending_unlock_route",
        "blocked_pending_acquisition",
        "blocked_pending_package_gate",
        "preview_visible_non_governing",
        "blocked_missing_inputs",
    }
    assert training_block["training_set_transition_contract_preview"]["status"] == "report_only"
    assert (
        training_block["training_set_transition_contract_preview"]["selected_accession_count"] == 12
    )
    assert training_block["training_set_transition_contract_preview"][
        "current_transition_state"
    ] in {"blocked_pending_transition_contract", "package_transition_ready"}
    assert training_block["training_set_source_fix_batch_preview"]["status"] == "report_only"
    assert training_block["training_set_source_fix_batch_preview"]["selected_accession_count"] == 12
    assert training_block["training_set_source_fix_batch_preview"]["current_batch_state"] in {
        "blocked_pending_source_fix_batch",
        "no_source_fix_batch_required",
    }
    assert (
        training_block["training_set_package_transition_batch_preview"]["status"] == "report_only"
    )
    assert (
        training_block["training_set_package_transition_batch_preview"]["selected_accession_count"]
        == 12
    )
    assert training_block["training_set_package_transition_batch_preview"][
        "current_batch_state"
    ] in {
        "blocked_pending_package_transition_batch",
        "no_package_transition_batch_required",
    }
    assert training_block["training_set_package_execution_preview"]["status"] == "report_only"
    assert (
        training_block["training_set_package_execution_preview"]["selected_accession_count"] == 12
    )
    assert training_block["training_set_package_execution_preview"]["current_execution_state"] in {
        "package_execution_follow_up_required",
        "no_package_execution_follow_up_required",
    }
    assert training_block["training_set_preview_hold_register_preview"]["status"] == "report_only"
    assert (
        training_block["training_set_preview_hold_register_preview"]["selected_accession_count"]
        == 12
    )
    assert training_block["training_set_preview_hold_register_preview"]["current_hold_state"] in {
        "preview_hold_register_active",
        "no_preview_hold_register_entries",
    }
    assert (
        training_block["training_set_preview_hold_exit_criteria_preview"]["status"] == "report_only"
    )
    assert (
        training_block["training_set_preview_hold_exit_criteria_preview"][
            "selected_accession_count"
        ]
        == 12
    )
    assert training_block["training_set_preview_hold_exit_criteria_preview"][
        "current_exit_state"
    ] in {
        "preview_hold_exit_criteria_active",
        "no_preview_hold_exit_criteria_rows",
    }
    assert (
        training_block["training_set_preview_hold_clearance_batch_preview"]["status"]
        == "report_only"
    )
    assert (
        training_block["training_set_preview_hold_clearance_batch_preview"][
            "selected_accession_count"
        ]
        == 12
    )
    assert training_block["training_set_preview_hold_clearance_batch_preview"][
        "current_batch_state"
    ] in {
        "preview_hold_clearance_batch_active",
        "no_preview_hold_clearance_batch_rows",
    }
    assert training_block["training_set_builder_runbook_preview"]["status"] == "report_only"
    assert training_block["training_set_builder_runbook_preview"]["selected_count"] == 12
    assert "compile-cohort" in training_block["training_set_builder_runbook_preview"]["step_ids"]
    assert training_block["sample_external_dataset_assessment_bundle_preview"][
        "assessment_overall_verdict"
    ] in {"usable_with_caveats", "audit_only", "blocked_pending_mapping"}
    assert (
        training_block["sample_external_dataset_assessment_bundle_preview"]["sample_manifest_count"]
        == 2
    )
    assert training_block["external_dataset_issue_matrix_preview"]["status"] == "report_only"
    assert training_block["external_dataset_issue_matrix_preview"]["dataset_accession_count"] == 12
    assert training_block["external_dataset_manifest_lint_preview"]["status"] == "report_only"
    assert training_block["external_dataset_manifest_lint_preview"]["accepted_shape_count"] == 2
    assert training_block["external_dataset_acceptance_gate_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_acceptance_gate_preview"]["dataset_accession_count"] == 12
    )
    assert training_block["external_dataset_admission_decision_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_admission_decision_preview"]["dataset_accession_count"]
        == 12
    )
    assert training_block["external_dataset_clearance_delta_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_clearance_delta_preview"]["dataset_accession_count"] == 12
    )
    assert training_block["external_dataset_clearance_delta_preview"][
        "current_clearance_state"
    ] in {"blocked", "advisory_only"}
    assert training_block["external_dataset_acceptance_path_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_acceptance_path_preview"]["dataset_accession_count"] == 12
    )
    assert training_block["external_dataset_acceptance_path_preview"]["current_path_state"] in {
        "blocked",
        "advisory_only",
    }
    assert (
        training_block["seed_plus_neighbors_structured_corpus_preview"]["status"] == "report_only"
    )
    assert training_block["seed_plus_neighbors_structured_corpus_preview"]["row_count"] >= 12
    assert (
        training_block["seed_plus_neighbors_structured_corpus_preview"]["seed_accession_count"]
        == 12
    )
    assert (
        training_block["seed_plus_neighbors_structured_corpus_preview"][
            "one_hop_neighbor_accession_count"
        ]
        >= 0
    )
    assert training_block["training_set_baseline_sidecar_preview"]["status"] == "report_only"
    assert training_block["training_set_baseline_sidecar_preview"]["example_count"] == 12
    assert (
        training_block["training_set_baseline_sidecar_preview"]["governing_ready_example_count"]
        >= 0
    )
    assert training_block["training_set_multimodal_sidecar_preview"]["status"] == "report_only"
    assert training_block["training_set_multimodal_sidecar_preview"]["example_count"] == 12
    assert training_block["training_set_multimodal_sidecar_preview"]["canonical_record_count"] >= 0
    assert training_block["training_packet_summary_preview"]["status"] == "report_only"
    assert training_block["training_packet_summary_preview"]["packet_count"] == 12
    assert (
        training_block["external_dataset_remediation_readiness_preview"]["status"] == "report_only"
    )
    assert (
        training_block["external_dataset_remediation_readiness_preview"]["dataset_accession_count"]
        == 12
    )
    assert training_block["external_dataset_remediation_readiness_preview"][
        "current_readiness_state"
    ] in {"blocked_pending_remediation", "ready_for_human_review"}
    assert training_block["external_dataset_caveat_execution_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_caveat_execution_preview"]["dataset_accession_count"] == 12
    )
    assert training_block["external_dataset_caveat_execution_preview"][
        "current_execution_state"
    ] in {"caveat_follow_up_ready", "no_caveat_execution_required"}
    assert (
        training_block["external_dataset_blocked_acquisition_batch_preview"]["status"]
        == "report_only"
    )
    assert (
        training_block["external_dataset_blocked_acquisition_batch_preview"][
            "dataset_accession_count"
        ]
        == 12
    )
    assert training_block["external_dataset_blocked_acquisition_batch_preview"][
        "current_batch_state"
    ] in {
        "blocked_pending_acquisition_batch",
        "no_blocked_acquisition_batch_required",
    }
    assert training_block["external_dataset_acquisition_unblock_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_acquisition_unblock_preview"]["dataset_accession_count"]
        == 12
    )
    assert training_block["external_dataset_acquisition_unblock_preview"][
        "current_unblock_state"
    ] in {
        "blocked_acquisition_follow_up_required",
        "no_blocked_acquisition_follow_up_required",
    }
    assert (
        training_block["external_dataset_advisory_followup_register_preview"]["status"]
        == "report_only"
    )
    assert (
        training_block["external_dataset_advisory_followup_register_preview"][
            "dataset_accession_count"
        ]
        == 12
    )
    assert training_block["external_dataset_advisory_followup_register_preview"][
        "current_followup_state"
    ] in {
        "advisory_follow_up_register_active",
        "no_advisory_follow_up_register_entries",
    }
    assert (
        training_block["external_dataset_caveat_exit_criteria_preview"]["status"] == "report_only"
    )
    assert (
        training_block["external_dataset_caveat_exit_criteria_preview"]["dataset_accession_count"]
        == 12
    )
    assert training_block["external_dataset_caveat_exit_criteria_preview"][
        "current_exit_state"
    ] in {
        "caveat_exit_criteria_active",
        "no_caveat_exit_criteria_rows",
    }
    assert training_block["external_dataset_caveat_review_batch_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_caveat_review_batch_preview"]["dataset_accession_count"]
        == 12
    )
    assert training_block["external_dataset_caveat_review_batch_preview"][
        "current_batch_state"
    ] in {
        "caveat_review_batch_active",
        "no_caveat_review_batch_rows",
    }
    assert training_block["external_dataset_resolution_preview"]["status"] == "report_only"
    assert training_block["external_dataset_resolution_preview"]["dataset_accession_count"] == 12
    assert training_block["external_dataset_remediation_queue_preview"]["status"] == "report_only"
    assert (
        training_block["external_dataset_remediation_queue_preview"]["dataset_accession_count"]
        == 12
    )
    assert training_block["binding_measurement_suspect_rows_preview"]["suspect_row_count"] >= 0
    assert (
        training_block["cross_source_duplicate_measurement_audit_preview"][
            "cross_source_duplicate_group_count"
        ]
        >= 0
    )
    assert overnight_block["scrape_gap_matrix_preview"]["remaining_gap_file_count"] == 2
    assert overnight_block["overnight_execution_contract_preview"]["poll_seconds"] == 60
    assert overnight_block["overnight_queue_repair_status"]["recovery_state"] in {
        "repaired_and_redispatched",
        "repaired_and_idle",
        "report_only",
    }
    assert (
        overnight_block["interaction_string_merge_impact_preview"]["merge_changes_split_or_leakage"]
        is False
    )
    assert overnight_block["scrape_execution_wave_preview"]["status"] == "report_only"
    assert overnight_block["scrape_execution_wave_preview"]["structured_job_count"] >= 1
    assert overnight_block["scrape_execution_wave_preview"]["active_download_count"] == 1
    assert overnight_block["procurement_source_completion_preview"]["status"] == "report_only"
    assert (
        overnight_block["procurement_source_completion_preview"]["string_completion_status"]
        == "complete"
    )
    assert (
        overnight_block["procurement_source_completion_preview"]["uniprot_completion_status"]
        in {"partial", "active"}
    )
    assert overnight_block["string_interaction_materialization_preview"]["status"] == "report_only"
    assert overnight_block["string_interaction_materialization_preview"][
        "materialization_state"
    ] in {
        "blocked_pending_string_completion_gate",
        "string_complete_materialized_non_governing",
    }
    assert overnight_block["scrape_backlog_remaining_preview"]["status"] == "report_only"
    assert (
        overnight_block["scrape_backlog_remaining_preview"]["implemented_and_harvestable_now_count"]
        >= 1
    )
    assert overnight_block["overnight_idle_status_preview"]["status"] == "report_only"
    assert overnight_block["overnight_idle_status_preview"]["idle_state"] in {
        "healthy_queue_drained",
        "healthy_active",
        "blocked_waiting",
        "stalled_or_attention_needed",
    }
    assert overnight_block["overnight_idle_status_preview"]["active_download_count"] in {1, 2}
    assert overnight_block["overnight_pending_reconciliation_preview"]["status"] == "report_only"
    assert overnight_block["overnight_pending_reconciliation_preview"]["reconciliation_state"] in {
        "reconciled_no_pending",
        "stale_idle_preview_drift_resolved",
        "queue_monitor_pending_drift_requires_review",
        "aligned_pending_work_present",
    }
    assert overnight_block["overnight_worker_launch_gap_preview"]["status"] == "report_only"
    assert overnight_block["overnight_worker_launch_gap_preview"]["launch_gap_state"] in {
        "launch_gap_present",
        "launch_gap_attention",
        "non_launchable_pending_only",
        "blocked_or_idle_no_launch_gap",
        "workers_active",
        "idle_no_launch_gap",
    }
    assert overnight_block["procurement_supervisor_freshness_preview"]["status"] == "report_only"
    assert overnight_block["procurement_supervisor_freshness_preview"]["freshness_state"] in {
        "legacy_stale_state_superseded",
        "fresh_supervisor_state_available",
        "stale_supervisor_state_attention",
        "supervisor_state_unavailable",
    }
    assert (
        overnight_block["procurement_tail_signal_reconciliation_preview"]["status"] == "report_only"
    )
    assert overnight_block["procurement_tail_signal_reconciliation_preview"][
        "reconciliation_state"
    ] in {
        "authoritative_tail_aligned_with_legacy_stale_signal",
        "authoritative_tail_aligned",
        "raw_process_excess_diagnostic_only",
        "tail_signal_drift_requires_review",
    }
    assert overnight_block["procurement_tail_growth_preview"]["status"] == "report_only"
    assert overnight_block["procurement_tail_growth_preview"]["growth_state"] in {
        "active_growth",
        "mixed_growth",
        "flat_or_stalled",
        "no_tail_files_sampled",
    }
    assert overnight_block["procurement_headroom_guard_preview"]["status"] == "report_only"
    assert overnight_block["procurement_headroom_guard_preview"]["guard_state"] in {
        "healthy_headroom",
        "caution_headroom",
        "critical_headroom",
    }
    assert overnight_block["procurement_tail_space_drift_preview"]["status"] == "report_only"
    assert overnight_block["procurement_tail_space_drift_preview"]["drift_state"] in {
        "aligned_with_tail_growth",
        "free_space_released_during_tail_growth",
        "additional_unattributed_pressure",
        "tail_reset_or_shrink_detected",
        "no_tail_files_sampled",
    }
    assert overnight_block["procurement_tail_source_pressure_preview"]["status"] == "report_only"
    assert overnight_block["procurement_tail_source_pressure_preview"]["pressure_state"] in {
        "source_dominant",
        "split_pressure",
        "no_tail_sources",
    }
    assert (
        overnight_block["procurement_tail_log_progress_registry_preview"]["status"] == "report_only"
    )
    assert overnight_block["procurement_tail_log_progress_registry_preview"]["registry_state"] in {
        "fully_parsed",
        "partially_parsed",
        "no_progress_match",
        "no_tail_rows",
    }
    assert overnight_block["procurement_tail_completion_margin_preview"]["status"] == "report_only"
    assert overnight_block["procurement_tail_completion_margin_preview"]["completion_state"] in {
        "sufficient_margin_for_tail_completion",
        "tight_margin_for_tail_completion",
        "insufficient_margin_for_tail_completion",
        "no_exact_total_available",
    }
    assert overnight_block["procurement_space_recovery_target_preview"]["status"] == "report_only"
    assert overnight_block["procurement_space_recovery_target_preview"]["target_state"] in {
        "no_recovery_required",
        "moderate_recovery_required",
        "substantial_recovery_required",
    }
    assert (
        overnight_block["procurement_space_recovery_candidates_preview"]["status"] == "report_only"
    )
    assert overnight_block["procurement_space_recovery_candidates_preview"]["recovery_state"] in {
        "no_candidates_detected",
        "duplicate_first_recovery_lane_available",
        "manual_review_recovery_lane_only",
    }
    assert (
        overnight_block["procurement_space_recovery_execution_batch_preview"]["status"]
        == "report_only"
    )
    assert overnight_block["procurement_space_recovery_execution_batch_preview"][
        "execution_state"
    ] in {
        "no_execution_batches_available",
        "buffered_recovery_batches_available",
        "ten_gib_buffer_batch_available",
        "zero_gap_batch_available_only",
        "insufficient_ranked_capacity",
    }
    assert (
        overnight_block["procurement_space_recovery_safety_register_preview"]["status"]
        == "report_only"
    )
    assert overnight_block["procurement_space_recovery_safety_register_preview"][
        "safety_state"
    ] in {
        "no_safety_rows_detected",
        "duplicate_first_safety_lane_available",
        "mixed_safety_lane_requires_manual_review",
        "review_required_lane_only",
    }
    assert overnight_block["procurement_tail_fill_risk_preview"]["status"] == "report_only"
    assert overnight_block["procurement_tail_fill_risk_preview"]["risk_state"] in {
        "insufficient_rate_data",
        "space_exhaustion_imminent",
        "zero_before_completion",
        "completion_before_zero",
    }
    assert overnight_block["procurement_space_recovery_trigger_preview"]["status"] == "report_only"
    assert overnight_block["procurement_space_recovery_trigger_preview"]["trigger_state"] in {
        "prepare_recovery_review",
        "recovery_trigger_immediate",
        "ranked_batch_insufficient_escalate",
    }
    assert (
        overnight_block["procurement_space_recovery_gap_drift_preview"]["status"] == "report_only"
    )
    assert overnight_block["procurement_space_recovery_gap_drift_preview"]["drift_state"] in {
        "no_zero_gap_shortfall",
        "first_shortfall_observation",
        "gap_widening",
        "gap_narrowing",
        "gap_flat",
    }
    assert overnight_block["procurement_space_recovery_coverage_preview"]["status"] == "report_only"
    assert overnight_block["procurement_space_recovery_coverage_preview"]["coverage_state"] in {
        "no_recovery_required",
        "zero_gap_covered",
        "ten_gib_buffer_covered_zero_gap_short",
        "ranked_lane_short_of_zero_gap",
    }
    assert (
        overnight_block["procurement_recovery_intervention_priority_preview"]["status"]
        == "report_only"
    )
    assert overnight_block["procurement_recovery_intervention_priority_preview"][
        "priority_state"
    ] in {
        "urgent_expand_duplicate_first_review",
        "urgent_duplicate_first_recovery_lane_ready",
        "monitor_only",
        "active_review_required",
    }
    assert (
        overnight_block["procurement_recovery_escalation_lane_preview"]["status"] == "report_only"
    )
    assert overnight_block["procurement_recovery_escalation_lane_preview"]["escalation_state"] in {
        "no_escalation_required",
        "extend_ranked_lane_before_manual_review",
        "manual_review_lane_available",
        "ranked_duplicate_lane_exhausted",
        "no_recovery_lane_available",
    }
    assert (
        overnight_block["procurement_space_recovery_concentration_preview"]["status"]
        == "report_only"
    )
    assert overnight_block["procurement_space_recovery_concentration_preview"][
        "concentration_state"
    ] in {
        "no_ranked_reclaim",
        "top1_dominant",
        "top3_concentrated",
        "distributed_lane",
    }
    assert (
        overnight_block["procurement_recovery_shortfall_bridge_preview"]["status"] == "report_only"
    )
    assert overnight_block["procurement_recovery_shortfall_bridge_preview"]["bridge_state"] in {
        "no_bridge_required",
        "ranked_bridge_available",
        "manual_review_bridge_possible",
        "no_bridge_inside_current_universe",
    }
    assert overnight_block["procurement_recovery_lane_fragility_preview"]["status"] == "report_only"
    assert overnight_block["procurement_recovery_lane_fragility_preview"]["fragility_state"] in {
        "no_ranked_lane",
        "distributed_without_lead_risk",
        "lead_candidate_covers_shortfall",
        "lane_breaks_without_lead",
        "lane_survives_without_lead",
    }
    assert overnight_block["procurement_broader_search_trigger_preview"]["status"] == "report_only"
    assert overnight_block["procurement_broader_search_trigger_preview"]["trigger_state"] in {
        "no_broader_search_required",
        "broader_search_immediate",
        "manual_review_before_broader_search",
        "prepare_broader_search",
    }
    assert overnight_block["overnight_wave_advance_preview"]["status"] == "ok"
    assert (
        "auto_task_generator"
        in overnight_block["overnight_wave_advance_preview"]["execution_order"]
    )
