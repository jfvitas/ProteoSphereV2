from __future__ import annotations

import time
from pathlib import Path

from api.model_studio.contracts import (
    compile_execution_graph,
    pipeline_spec_from_dict,
    validate_pipeline_spec,
)
from api.model_studio.runtime import MISSING_STRUCTURE_SENTINEL, _load_rows_from_csv
from api.model_studio.service import (
    build_hardware_profile_payload,
    build_program_status,
    build_training_set_payload,
    build_workspace_payload,
    compare_pipeline_runs,
    launch_pipeline_run,
    load_pipeline_run,
    preview_training_set_payload,
    record_session_event,
    submit_feedback,
)


def _default_pipeline_payload() -> dict:
    return build_workspace_payload()["pipeline_spec"]


def _ligand_pilot_payload(
    *,
    model_family: str = "graphsage",
    label_type: str = "delta_G",
) -> dict:
    payload = _default_pipeline_payload()
    payload["data_strategy"]["task_type"] = "protein-ligand"
    payload["data_strategy"]["label_type"] = label_type
    payload["data_strategy"]["split_strategy"] = "protein_ligand_component_grouped"
    payload["data_strategy"]["dataset_refs"] = ["governed_pl_bridge_pilot_subset_v1"]
    payload["training_set_request"]["task_type"] = "protein-ligand"
    payload["training_set_request"]["label_type"] = label_type
    payload["training_set_request"]["source_families"] = ["governed_pl_bridge_pilot"]
    payload["training_set_request"]["dataset_refs"] = ["governed_pl_bridge_pilot_subset_v1"]
    payload["training_set_request"]["target_size"] = 48
    payload["graph_recipes"][0]["graph_kind"] = "whole_complex_graph"
    payload["graph_recipes"][0]["region_policy"] = "whole_molecule"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"
    payload["preprocess_plan"]["modules"] = [
        "PDB acquisition",
        "chain extraction and canonical mapping",
        "ligand descriptors",
    ]
    payload["split_plan"]["objective"] = "protein_ligand_component_grouped"
    payload["split_plan"]["grouping_policy"] = "protein_ligand_component_grouped"
    if model_family == "graphsage":
        payload["training_plan"]["model_family"] = "graphsage"
        payload["training_plan"]["architecture"] = "graphsage_interface_encoder"
    else:
        payload["training_plan"]["model_family"] = "multimodal_fusion"
        payload["training_plan"]["architecture"] = "graph_global_fusion"
    return payload


def _external_beta_ppi_payload() -> dict:
    payload = _default_pipeline_payload()
    payload["data_strategy"]["dataset_refs"] = ["governed_ppi_external_beta_candidate_v1"]
    payload["training_set_request"]["dataset_refs"] = ["governed_ppi_external_beta_candidate_v1"]
    payload["training_set_request"]["target_size"] = 8
    payload["training_plan"]["model_family"] = "multimodal_fusion"
    payload["training_plan"]["architecture"] = "graph_global_fusion"
    return payload


def _wait_for_completed_run(run_id: str, *, timeout_s: float = 120.0) -> dict:
    deadline = time.time() + timeout_s
    latest = load_pipeline_run(run_id)
    while time.time() < deadline:
        latest = load_pipeline_run(run_id)
        status = latest.get("run_manifest", {}).get("status")
        if status in {"completed", "failed", "blocked", "cancelled"}:
            return latest
        time.sleep(0.2)
    return latest


def test_workspace_payload_exposes_beta_ui_contract() -> None:
    workspace = build_workspace_payload()

    assert "field_help_registry" in workspace["catalog"]
    assert "ui_option_registry" in workspace["catalog"]
    assert "stepper" in workspace
    assert "latest_artifact" in workspace["status_rail"]
    assert "hardware_mode" in workspace["status_rail"]
    assert "ui_contract" in workspace
    assert workspace["ui_contract"]["stepper_state"]
    assert workspace["ui_contract"]["primary_actions"]
    assert workspace["ui_contract"]["inactive_explanations"]
    assert workspace["ui_contract"]["dataset_pools"]
    assert workspace["ui_contract"]["dataset_pool_views"]
    assert workspace["ui_contract"]["launchable_dataset_pools"]
    assert workspace["ui_contract"]["candidate_pool_summary"]["promoted_pool_ids"]
    assert workspace["ui_contract"]["candidate_database_summary"]["total_governed_rows"] >= 1
    assert workspace["ui_contract"]["candidate_database_summary_v2"]["promotion_ready_subset_count"] >= 1
    assert workspace["ui_contract"]["candidate_database_summary_v3"]["promoted_subset_count"] >= 1
    assert (
        workspace["ui_contract"]["candidate_database_summary_canonical"]
        == workspace["ui_contract"]["candidate_database_summary_v3"]
    )
    assert workspace["ui_contract"]["governed_bridge_manifests"]
    assert workspace["ui_contract"]["governed_subset_manifests"]
    assert workspace["ui_contract"]["governed_subset_manifests_v2"]
    assert workspace["ui_contract"]["promotion_queue"]
    assert workspace["ui_contract"]["promotion_queue_v2"]
    assert workspace["ui_contract"]["promotion_queue_canonical"] == workspace["ui_contract"]["promotion_queue_v2"]
    assert workspace["ui_contract"]["stage2_scientific_tracks"]
    assert workspace["ui_contract"]["beta_readiness_dashboard"]
    assert workspace["ui_contract"]["beta_test_agents"]
    assert workspace["ui_contract"]["beta_test_agent_runs"]
    assert workspace["ui_contract"]["beta_test_agent_findings"]["open_findings"]
    assert workspace["ui_contract"]["beta_test_agent_matrix"]["coverage"]
    assert workspace["ui_contract"]["beta_test_agent_status"]["required_viewport"] == {
        "width": 1920,
        "height": 1080,
    }
    assert workspace["ui_contract"]["beta_test_agent_status"]["minimum_viewport"] == {
        "width": 1280,
        "height": 720,
    }
    assert workspace["ui_contract"]["reference_library_status"]["bundle_kind"] == "compressed_sqlite"
    assert workspace["ui_contract"]["reference_library_manifest"]["bundle_id"] == "proteosphere-lite"
    assert workspace["ui_contract"]["reference_library_chunk_catalog"]
    assert workspace["ui_contract"]["reference_library_install_status"]["suite_decoder_ready"] is True
    assert workspace["ui_contract"]["reference_library_query"]["mode"] == "bundle_first"
    assert workspace["ui_contract"]["reference_library_hydration_requirements"]
    assert "assay_mix" in workspace["ui_contract"]["candidate_pool_summary"]
    assert "label_bin_mix" in workspace["ui_contract"]["candidate_pool_summary"]
    assert "leakage_risk_summary" in workspace["ui_contract"]["candidate_pool_summary"]
    assert workspace["ui_contract"]["pool_promotion_reports"]
    assert workspace["ui_contract"]["activation_ledger"]
    assert workspace["ui_contract"]["activation_readiness_reports"]
    assert workspace["ui_contract"]["feature_gate_views"]
    assert workspace["ui_contract"]["model_activation_matrix"]["entries"]
    assert workspace["ui_contract"]["beta_support"]["scope"] == "controlled_external_beta"
    assert workspace["ui_contract"]["beta_support"]["state_vocabulary"] == [
        "Launchable now",
        "Review pending",
        "Inactive",
    ]
    assert workspace["ui_contract"]["beta_support"]["safe_to_use_now"]
    assert workspace["ui_contract"]["beta_support"]["review_pending"]
    assert workspace["ui_contract"]["beta_support"]["known_limitations"]
    assert workspace["ui_contract"]["beta_support"]["support_response_expectation"]
    assert workspace["ui_contract"]["beta_support"]["escalation_path"]
    assert workspace["ui_contract"]["beta_support"]["issue_intake_categories"]
    assert workspace["ui_contract"]["beta_support"]["beta_docs"]
    assert workspace["ui_contract"]["beta_support"]["how_to_report"]
    for doc in workspace["ui_contract"]["beta_support"]["beta_docs"]:
        assert Path(doc["path"]).exists()
    gate_ids = {item["feature_id"] for item in workspace["ui_contract"]["activation_ledger"]}

    source_families = {
        item["value"]: item["status"]
        for item in workspace["catalog"]["ui_option_registry"]["source_families"]
    }
    task_types = {
        item["value"]: item["status"]
        for item in workspace["catalog"]["capability_registry"]["task_types"]
    }
    dataset_refs = {
        item["value"]: item["status"]
        for item in workspace["catalog"]["ui_option_registry"]["dataset_refs"]
    }
    model_families = {
        item["value"]: item["status"]
        for item in workspace["catalog"]["capability_registry"]["model_families"]
    }
    node_granularities = {
        item["value"]: item["status"]
        for item in workspace["catalog"]["ui_option_registry"]["node_granularities"]
    }
    graph_kinds = {
        item["value"]: item["status"]
        for item in workspace["catalog"]["capability_registry"]["graph_kinds"]
    }
    assert source_families["balanced_ppi_beta_pool"] == "beta"
    assert source_families["governed_ppi_promoted_subsets"] == "beta"
    assert source_families["governed_pl_bridge_pilot"] == "beta"
    assert task_types["protein-ligand"] == "beta"
    assert dataset_refs["governed_pl_bridge_pilot_subset_v1"] == "beta"
    approved_local_reason = next(
        item["reason"]
        for item in workspace["catalog"]["ui_option_registry"]["source_families"]
        if item["value"] == "approved_local_ppi"
    )
    assert "without the broader expanded pool" in approved_local_reason
    assert model_families["gin"] == "beta"
    assert model_families["gcn"] == "beta"
    assert model_families["gat"] == "beta"
    assert node_granularities["atom"] == "beta"
    assert graph_kinds["atom_graph"] == "beta"
    assert "graph:atom_graph" in gate_ids
    assert "node:atom" in gate_ids
    assert "ros:pyrosetta" in gate_ids
    assert "preprocess:free_state_comparison" in gate_ids
    assert "resolved_execution_device" in workspace["status_rail"]


def test_dataset_pool_views_expose_authoritative_launchability() -> None:
    workspace = build_workspace_payload()
    pool_views = {
        item["pool_id"]: item for item in workspace["ui_contract"]["dataset_pool_views"]
    }

    assert pool_views["pool:release_pp_alpha_benchmark_v1"]["is_launchable"] is True
    assert pool_views["pool:release_pp_alpha_benchmark_v1"]["audience_state"] == "launchable_now"
    assert pool_views["pool:governed_ppi_blended_subset_v1"]["is_launchable"] is False
    assert pool_views["pool:governed_ppi_blended_subset_v1"]["audience_state"] == "review_pending"
    assert pool_views["pool:governed_ppi_blended_subset_v2"]["is_launchable"] is True
    assert pool_views["pool:governed_ppi_blended_subset_v2"]["audience_state"] == "launchable_now"
    assert pool_views["pool:governed_ppi_stage2_candidate_v1"]["is_launchable"] is False
    assert pool_views["pool:governed_ppi_stage2_candidate_v1"]["audience_state"] == "review_pending"
    assert pool_views["pool:governed_ppi_external_beta_candidate_v1"]["is_launchable"] is True
    assert pool_views["pool:governed_ppi_external_beta_candidate_v1"]["audience_state"] == "launchable_now"
    assert pool_views["pool:governed_ppi_external_beta_candidate_v1"]["audience_label"] == "Launchable now"
    assert "Kepler" in pool_views["pool:governed_ppi_external_beta_candidate_v1"]["required_reviewers"]
    assert "external_beta_rehearsal" in pool_views["pool:governed_ppi_external_beta_candidate_v1"]["required_matrix_tests"]
    assert pool_views["pool:governed_pl_bridge_pilot_subset_v1"]["is_launchable"] is True
    assert pool_views["pool:governed_pl_bridge_pilot_subset_v1"]["audience_state"] == "launchable_now"
    assert "ligand_pilot_matrix" in pool_views["pool:governed_pl_bridge_pilot_subset_v1"]["required_matrix_tests"]
    assert pool_views["pool:expanded_ppi_procurement_bridge"]["is_launchable"] is False
    assert pool_views["pool:expanded_ppi_procurement_bridge"]["audience_state"] == "review_pending"
    assert "launchable yet" in pool_views["pool:expanded_ppi_procurement_bridge"]["use_now_summary"]


def test_feedback_and_session_event_are_persisted() -> None:
    feedback = submit_feedback(
        {
            "study_title": "beta study",
            "pipeline_id": "pipeline:test",
            "category": "confusion",
            "message": "Tooltip was unclear.",
        }
    )
    session_event = record_session_event(
        {
            "session_id": "beta-session-test",
            "event_type": "workspace_loaded",
            "detail": "Loaded successfully",
            "pipeline_id": "pipeline:test",
        }
    )

    assert feedback["feedback_id"].startswith("feedback-")
    assert feedback["record"]["message"] == "Tooltip was unclear."
    assert session_event["event_id"].startswith("event-")
    assert session_event["record"]["event_type"] == "workspace_loaded"


def test_preview_payload_returns_full_rows_and_chart_payloads() -> None:
    preview = preview_training_set_payload(_default_pipeline_payload())

    assert preview["status"] == "ready"
    assert preview["candidate_preview"]["rows"]
    assert len(preview["candidate_preview"]["rows"]) == preview["diagnostics"]["row_count"]
    assert preview["candidate_preview"]["total_candidate_count"] >= preview["candidate_preview"]["filtered_candidate_count"]
    assert (
        preview["candidate_preview"]["eligible_quality_ceiling"]
        >= preview["candidate_preview"]["final_selected_count"]
    )
    assert preview["candidate_preview"]["resolved_target_cap"] == preview["candidate_preview"]["final_selected_count"]
    assert "pagination" in preview["candidate_preview"]
    assert preview["charts"]["label_distribution"]
    assert preview["charts"]["split_distribution"]


def test_build_payload_keeps_selected_rows_and_chart_payloads() -> None:
    build_payload = build_training_set_payload(_default_pipeline_payload())
    manifest = build_payload["build_manifest"]

    assert build_payload["status"] == "ready"
    assert manifest["status"] == "ready"
    assert manifest["selected_rows"]
    assert len(manifest["selected_rows"]) == manifest["row_count"]
    assert manifest["total_candidate_count"] >= manifest["filtered_candidate_count"]
    assert manifest["eligible_quality_ceiling"] >= manifest["final_selected_count"]
    assert manifest["resolved_target_cap"] == manifest["final_selected_count"]
    assert "excluded_rows" in manifest
    assert manifest["charts"]["label_distribution"]
    assert manifest["charts"]["split_distribution"]


def test_preview_and_build_expose_target_cap_when_request_exceeds_ceiling() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["target_size"] = 5000
    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)

    assert preview["status"] == "ready"
    assert preview["candidate_preview"]["requested_target_size"] == 5000
    assert preview["candidate_preview"]["eligible_quality_ceiling"] < 5000
    assert preview["candidate_preview"]["resolved_target_cap"] == preview["candidate_preview"]["eligible_quality_ceiling"]
    assert "eligible quality-controlled ceiling" in (preview["candidate_preview"]["target_size_warning"] or "")

    manifest = build["build_manifest"]
    assert manifest["requested_target_size"] == 5000
    assert manifest["resolved_target_cap"] == manifest["eligible_quality_ceiling"]
    assert manifest["final_selected_count"] == manifest["row_count"]
    assert "eligible quality-controlled ceiling" in (manifest["target_size_warning"] or "")


def test_csv_loader_treats_dot_structure_path_as_missing(tmp_path) -> None:
    csv_path = tmp_path / "dot-structure.csv"
    csv_path.write_text(
        "\n".join(
            [
                "PDB,exp_dG,Source Data Set,Complex Type,Mapped Protein Accessions,Ligand Chains,Receptor Chains,Structure File,Resolution (A),Release Year,Label Temperature (K)",
                "5IIA,-11.9,governed_ppi_blended_subset_v2,protein_protein,P04552;Q8WR62,,,.,1.7,2017,298.15",
            ]
        ),
        encoding="utf-8",
    )

    rows = _load_rows_from_csv(csv_path, "test")

    assert len(rows) == 1
    assert rows[0].structure_file == MISSING_STRUCTURE_SENTINEL


def test_hardware_profile_includes_cpu_gpu_and_runtime_keys() -> None:
    profile = build_hardware_profile_payload()

    assert "cpu_model" in profile
    assert "cpu_count" in profile
    assert "total_ram_gb" in profile
    assert "cuda_available" in profile
    assert "gpu_name" in profile
    assert "detected_gpus" in profile
    assert "recommended_preset" in profile


def test_beta_activation_configuration_validates_and_builds() -> None:
    payload = _default_pipeline_payload()
    payload["data_strategy"]["split_strategy"] = "accession_grouped"
    payload["training_set_request"]["source_families"] = ["balanced_ppi_beta_pool"]
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["encoding_policy"] = "one_hot"
    payload["feature_recipes"][0]["node_feature_policy"] = "one_hot"
    payload["feature_recipes"][0]["edge_feature_policy"] = "one_hot"
    payload["training_plan"]["model_family"] = "gin"
    payload["training_plan"]["architecture"] = "gin_encoder"
    payload["split_plan"]["objective"] = "accession_grouped"
    payload["split_plan"]["grouping_policy"] = "accession_grouped"

    spec = pipeline_spec_from_dict(payload)
    report = validate_pipeline_spec(spec)
    graph = compile_execution_graph(spec)

    assert all(item.level != "blocker" for item in report.items)
    assert not graph.blockers

    build_payload = build_training_set_payload(payload)
    assert build_payload["build_manifest"]["row_count"] > 0


def test_gcn_whole_complex_beta_configuration_validates() -> None:
    payload = _default_pipeline_payload()
    payload["data_strategy"]["split_strategy"] = "graph_component_grouped"
    payload["training_set_request"]["source_families"] = ["balanced_ppi_beta_pool"]
    payload["graph_recipes"][0]["graph_kind"] = "whole_complex_graph"
    payload["graph_recipes"][0]["region_policy"] = "whole_molecule"
    payload["graph_recipes"][0]["encoding_policy"] = "ordinal_ranked"
    payload["feature_recipes"][0]["node_feature_policy"] = "ordinal_ranked"
    payload["feature_recipes"][0]["edge_feature_policy"] = "ordinal_ranked"
    payload["training_plan"]["model_family"] = "gcn"
    payload["training_plan"]["architecture"] = "gcn_encoder"
    payload["split_plan"]["objective"] = "graph_component_grouped"
    payload["split_plan"]["grouping_policy"] = "graph_component_grouped"

    spec = pipeline_spec_from_dict(payload)
    report = validate_pipeline_spec(spec)
    graph = compile_execution_graph(spec)

    assert all(item.level != "blocker" for item in report.items)
    assert not graph.blockers


def test_gat_shell_graph_beta_configuration_validates() -> None:
    payload = _default_pipeline_payload()
    payload["data_strategy"]["split_strategy"] = "accession_grouped"
    payload["training_set_request"]["source_families"] = ["balanced_ppi_beta_pool"]
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"
    payload["graph_recipes"][0]["encoding_policy"] = "one_hot"
    payload["feature_recipes"][0]["node_feature_policy"] = "one_hot"
    payload["feature_recipes"][0]["edge_feature_policy"] = "one_hot"
    payload["training_plan"]["model_family"] = "gat"
    payload["training_plan"]["architecture"] = "gat_encoder"
    payload["training_plan"]["optimizer"] = "lion"
    payload["training_plan"]["scheduler"] = "warmup_cosine"
    payload["training_plan"]["batch_policy"] = "adaptive_gradient_accumulation"
    payload["split_plan"]["objective"] = "accession_grouped"
    payload["split_plan"]["grouping_policy"] = "accession_grouped"

    spec = pipeline_spec_from_dict(payload)
    report = validate_pipeline_spec(spec)
    graph = compile_execution_graph(spec)

    assert all(item.level != "blocker" for item in report.items)
    assert not graph.blockers


def test_beta_soon_payloads_are_blocked_by_backend_validation() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["dataset_refs"] = ["final_structured_candidates_v1"]
    payload["data_strategy"]["dataset_refs"] = ["final_structured_candidates_v1"]
    payload["training_plan"]["model_family"] = "mlp"
    payload["training_plan"]["optimizer"] = "lion"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("active beta dataset catalog" in message for message in messages)
    assert any("graph-backed model families" in message for message in messages)


def test_data_strategy_dataset_refs_are_also_beta_catalog_validated() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["dataset_refs"] = []
    payload["data_strategy"]["dataset_refs"] = ["final_structured_candidates_v1"]

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("active beta dataset catalog" in message for message in messages)


def test_governed_subset_requires_whole_complex_symmetric_scope() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["dataset_refs"] = ["governed_ppi_blended_subset_v1"]
    payload["data_strategy"]["dataset_refs"] = ["governed_ppi_blended_subset_v1"]
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("whole_complex_graph" in message for message in messages)
    assert any("whole_molecule" in message for message in messages)
    assert any("symmetric partner awareness" in message for message in messages)


def test_governed_subset_source_family_also_enforces_scope() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["source_families"] = ["governed_ppi_promoted_subsets"]
    payload["training_set_request"]["dataset_refs"] = []
    payload["data_strategy"]["dataset_refs"] = []
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("whole_complex_graph" in message for message in messages)
    assert any("whole_molecule" in message for message in messages)
    assert any("symmetric partner awareness" in message for message in messages)


def test_atom_graph_payload_is_native_beta_and_validates() -> None:
    payload = _default_pipeline_payload()
    payload["graph_recipes"][0]["graph_kind"] = "atom_graph"
    payload["graph_recipes"][0]["node_granularity"] = "atom"
    payload["graph_recipes"][0]["region_policy"] = "whole_molecule"
    payload["training_plan"]["model_family"] = "gin"
    payload["training_plan"]["architecture"] = "gin_encoder"
    payload["training_plan"]["optimizer"] = "lion"
    payload["training_plan"]["scheduler"] = "warmup_cosine"
    payload["training_plan"]["batch_policy"] = "adaptive_gradient_accumulation"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert not [item.message for item in report.items if item.level == "blocker"]

    build_payload = build_training_set_payload(payload)
    assert build_payload["build_manifest"]["row_count"] > 0


def test_program_status_reports_deduped_beta_pool_summary() -> None:
    status = build_program_status()
    active_pools = [
        pool
        for pool in status["dataset_pools"]
        if pool["pool_id"] in set(status["candidate_pool_summary"]["promoted_pool_ids"])
    ]
    raw_total = sum(pool["row_count"] for pool in active_pools)

    assert status["program_preview"]["mode"] == "controlled_external_beta_rehearsal"
    assert status["program_preview"]["summary"]["status"] == "controlled_external_beta_hardening"
    assert status["release_catalog_mode"] == "active_beta_lane"
    assert status["candidate_database_summary_canonical"] == status["candidate_database_summary_v3"]
    assert status["promotion_queue_canonical"] == status["promotion_queue_v2"]
    assert status["dataset_pool_views"]
    assert status["launchable_dataset_pools"]
    assert status["beta_support"]["beta_docs"]
    assert status["beta_readiness_dashboard"]
    assert len(status["beta_test_agents"]) == 6
    assert status["beta_test_agent_status"]["required_viewport"] == {"width": 1920, "height": 1080}
    assert status["beta_test_agent_status"]["minimum_viewport"] == {"width": 1280, "height": 720}
    assert status["beta_test_agent_findings"]["open_p1_count"] == 0
    assert status["reference_library_status"]["build_state"] == "ready"
    assert status["reference_library_manifest"]["bundle_id"] == "proteosphere-lite"
    assert status["reference_library_chunk_catalog"]
    assert status["reference_library_install_status"]["core_bundle_local"] is True
    assert status["candidate_pool_summary"]["total_row_count"] <= raw_total
    assert set(status["candidate_pool_summary"]["promoted_pool_ids"]) == {
        "pool:release_pp_alpha_benchmark_v1",
        "pool:robust_pp_benchmark_v1",
        "pool:expanded_pp_benchmark_v1",
        "pool:governed_ppi_blended_subset_v2",
        "pool:governed_ppi_external_beta_candidate_v1",
        "pool:governed_pl_bridge_pilot_subset_v1",
    }


def test_fresh_workspace_stepper_starts_at_training_request() -> None:
    workspace = build_workspace_payload()
    stepper = {item["id"]: item for item in workspace["stepper"]}

    assert stepper["training-request"]["status"] == "current"
    assert stepper["dataset-preview"]["status"] == "next"
    assert stepper["build-split"]["status"] == "next"
    assert stepper["run-monitor"]["status"] == "next"
    assert stepper["analysis-compare"]["status"] == "next"
    assert stepper["export-review"]["status"] == "next"


def test_beta_readiness_dashboard_exposes_gate_and_lane_truth() -> None:
    workspace = build_workspace_payload()
    dashboard = workspace["ui_contract"]["beta_readiness_dashboard"]
    gates = {item["gate_id"]: item for item in dashboard["gates"]}
    lanes = {item["lane_id"]: item for item in dashboard["program_lanes"]}
    evidence = {item["artifact_id"]: item for item in dashboard["evidence_checklist"]}

    assert dashboard["overall_status"] == "beta_ready"
    assert dashboard["current_focus"] == "final_external_rehearsal"
    assert dashboard["completion_percent"] == 100
    assert gates["ppi_freeze_gate"]["status"] == "ready"
    assert "Two governed PPI subsets are launchable." in gates["ppi_freeze_gate"]["detail"]
    assert gates["stage2_implementation_gate"]["status"] == "review_pending"
    assert gates["stage2_implementation_gate"]["blocks_beta_launch"] is False
    assert gates["protein_ligand_pilot_gate"]["status"] == "ready"
    assert gates["ops_launch_gate"]["status"] == "ready"
    assert gates["final_external_rehearsal_gate"]["status"] == "ready"
    assert dashboard["remaining_blockers"] == []
    assert dashboard["parallel_risks"]
    assert lanes["ppi_primary"]["state"] == "launchable_now"
    assert "governed_ppi_blended_subset_v2" in " ".join(lanes["ppi_primary"]["launchable_pool_ids"])
    assert "governed_ppi_external_beta_candidate_v1" in " ".join(lanes["ppi_primary"]["launchable_pool_ids"])
    assert lanes["protein_ligand_pilot"]["state"] == "launchable_now"
    assert "governed_pl_bridge_pilot_subset_v1" in " ".join(lanes["protein_ligand_pilot"]["launchable_pool_ids"])
    assert evidence["reviewer_signoff_ledger"]["status"] == "ready"
    assert evidence["browser_traces"]["status"] == "ready"
    assert evidence["desktop_screenshots"]["status"] == "ready"
    assert evidence["narrow_screenshots"]["status"] == "ready"
    assert evidence["ligand_pilot_evidence"]["status"] == "ready"
    assert evidence["failure_state_screenshots"]["status"] == "ready"
    assert dashboard["beta_agent_status"]["required_viewport"] == {"width": 1920, "height": 1080}
    assert dashboard["beta_agent_status"]["minimum_viewport"] == {"width": 1280, "height": 720}
    assert dashboard["beta_agent_status"]["open_p1_findings"] == 0


def test_beta_test_agent_matrix_and_reference_library_surfaces_are_exposed() -> None:
    status = build_program_status()
    matrix = status["beta_test_agent_matrix"]
    flows = {item["flow_id"]: item for item in matrix["coverage"]}
    agent_ids = {item["agent_id"] for item in status["beta_test_agents"]}
    library_manifest = status["reference_library_manifest"]

    assert {
        "visual-cleanliness-agent",
        "usability-agent",
        "content-relevance-agent",
        "scientific-output-agent",
        "failure-recovery-agent",
        "release-governance-agent",
    }.issubset(agent_ids)
    assert set(flows) == {
        "ppi_benchmark_launchable_flow",
        "governed_ppi_subset_flow",
        "protein_ligand_pilot_flow",
        "blocked_pyrosetta_flow",
        "blocked_free_state_flow",
    }
    assert flows["ppi_benchmark_launchable_flow"]["status"] == "ready"
    assert flows["protein_ligand_pilot_flow"]["status"] == "ready"
    assert flows["governed_ppi_subset_flow"]["status"] == "ready"
    assert library_manifest["packaging_layout"] == "core_bundle_plus_family_chunks"
    assert library_manifest["bundle_kind"] == "compressed_sqlite"
    assert library_manifest["decoder_version"] == "proteosphere-lite-decoder-v1"
    assert library_manifest["family_counts"]["proteins"] >= 1


def test_beta_test_agent_runs_expose_interaction_verification_fields() -> None:
    status = build_program_status()
    first_run = status["beta_test_agent_runs"][0]
    first_agent = status["beta_test_agents"][0]

    assert first_agent["interaction_contract"]
    assert first_run["interaction_steps"]
    assert "expected_effect" in first_run["interaction_steps"][0]
    assert "observed_effect" in first_run["interaction_steps"][0]
    assert "pass_fail" in first_run["interaction_steps"][0]
    assert first_run["ui_diff_summary"]
    assert first_run["backend_diff_summary"]


def test_pool_promotion_reports_include_governed_bridge_metadata() -> None:
    workspace = build_workspace_payload()
    reports = {
        item["pool_id"]: item for item in workspace["ui_contract"]["pool_promotion_reports"]
    }
    pools = {item["pool_id"]: item for item in workspace["ui_contract"]["dataset_pools"]}
    bridge_manifests = {
        item["bridge_id"]: item for item in workspace["ui_contract"]["governed_bridge_manifests"]
    }

    assert reports["pool:release_pp_alpha_benchmark_v1"]["promotion_bar"] == "release_matrix_plus_review"
    assert reports["pool:robust_pp_benchmark_v1"]["status"] == "beta"
    assert not reports["pool:robust_pp_benchmark_v1"]["blockers"]
    assert reports["pool:governed_ppi_blended_subset_v1"]["status"] == "beta_soon"
    assert reports["pool:governed_ppi_blended_subset_v1"]["review_signoff_state"] == "wave_1_pending_reviews"
    assert reports["pool:governed_ppi_blended_subset_v1"]["promotion_readiness"] == "review_pending_candidate"
    assert reports["pool:governed_ppi_blended_subset_v1"]["blockers"]
    assert reports["pool:governed_ppi_blended_subset_v2"]["status"] == "beta"
    assert reports["pool:governed_ppi_blended_subset_v2"]["review_signoff_state"] == "wave_4_ready_for_freeze"
    assert reports["pool:governed_ppi_blended_subset_v2"]["promotion_readiness"] == "launchable_now"
    assert not reports["pool:governed_ppi_blended_subset_v2"]["blockers"]
    assert reports["pool:governed_ppi_stage2_candidate_v1"]["status"] == "beta_soon"
    assert reports["pool:governed_ppi_stage2_candidate_v1"]["review_signoff_state"] == "wave_1_pending_reviews"
    assert reports["pool:governed_ppi_stage2_candidate_v1"]["promotion_readiness"] == "review_pending_candidate"
    assert reports["pool:governed_ppi_stage2_candidate_v1"]["blockers"]
    assert reports["pool:governed_ppi_external_beta_candidate_v1"]["status"] == "beta"
    assert reports["pool:governed_ppi_external_beta_candidate_v1"]["review_signoff_state"] == "controlled_external_beta_ready"
    assert reports["pool:governed_ppi_external_beta_candidate_v1"]["promotion_readiness"] == "launchable_now"
    assert "Kepler" in reports["pool:governed_ppi_external_beta_candidate_v1"]["required_reviewers"]
    assert "external_beta_rehearsal" in reports["pool:governed_ppi_external_beta_candidate_v1"]["required_matrix_tests"]
    assert not reports["pool:governed_ppi_external_beta_candidate_v1"]["blockers"]
    assert reports["pool:governed_pl_bridge_pilot_subset_v1"]["status"] == "beta"
    assert reports["pool:governed_pl_bridge_pilot_subset_v1"]["review_signoff_state"] == "wave_6_ready_for_beta"
    assert reports["pool:governed_pl_bridge_pilot_subset_v1"]["promotion_readiness"] == "launchable_now"
    assert "ligand_pilot_matrix" in reports["pool:governed_pl_bridge_pilot_subset_v1"]["required_matrix_tests"]
    assert not reports["pool:governed_pl_bridge_pilot_subset_v1"]["blockers"]
    assert reports["pool:expanded_ppi_procurement_bridge"]["status"] == "beta_soon"
    assert reports["pool:expanded_ppi_procurement_bridge"]["promotion_readiness"] in {
        "candidate_promotion_ready_for_review",
        "row_governed_but_still_gated",
    }
    assert reports["pool:expanded_ppi_procurement_bridge"]["launchability_reason"]
    assert reports["pool:expanded_ppi_procurement_bridge"]["last_review_wave"] == "wave-1"
    assert pools["pool:expanded_ppi_procurement_bridge"]["truth_boundary"]["row_level_provenance_state"] == (
        "row_level_compiled"
    )
    assert pools["pool:expanded_ppi_procurement_bridge"]["balancing_metadata"]["procurement_dataset_count"] >= 1
    assert pools["pool:expanded_ppi_procurement_bridge"]["balancing_metadata"]["quality_verdict"] == (
        "row_governed_but_still_gated"
    )
    assert bridge_manifests["bridge:expanded_ppi_procurement_bridge"]["row_count"] >= 1
    assert bridge_manifests["bridge:expanded_ppi_procurement_bridge"]["provenance_completeness"] == (
        "row_level_compiled"
    )
    assert bridge_manifests["bridge:expanded_ppi_procurement_bridge"]["admissibility_completeness"] == (
        "row_level_compiled"
    )
    assert "gated in the beta lane" in reports["pool:expanded_ppi_procurement_bridge"]["launchability_reason"]


def test_candidate_database_summary_exposes_governed_staged_balance() -> None:
    workspace = build_workspace_payload()
    summary = workspace["ui_contract"]["candidate_database_summary"]
    summary_v2 = workspace["ui_contract"]["candidate_database_summary_v2"]

    assert summary["total_governed_rows"] > 615
    assert "expanded_ppi_procurement_bridge" in summary["source_family_mix"]
    assert summary["label_bin_mix"]
    assert isinstance(summary["bias_diagnostics"], list)
    assert summary_v2["promotion_ready_subset_count"] >= 1
    assert summary_v2["governance_state_mix"]
    assert workspace["ui_contract"]["candidate_database_summary_v3"]["promoted_subset_count"] >= 1


def test_governed_bridge_and_pool_truth_are_consistent() -> None:
    workspace = build_workspace_payload()
    pools = {item["pool_id"]: item for item in workspace["ui_contract"]["dataset_pools"]}
    reports = {item["pool_id"]: item for item in workspace["ui_contract"]["pool_promotion_reports"]}
    manifests = {
        item["bridge_id"]: item for item in workspace["ui_contract"]["governed_bridge_manifests"]
    }

    procurement_pool = pools["pool:expanded_ppi_procurement_bridge"]
    procurement_manifest = manifests["bridge:expanded_ppi_procurement_bridge"]
    procurement_report = reports["pool:expanded_ppi_procurement_bridge"]

    assert procurement_pool["truth_boundary"]["row_level_provenance_state"] == procurement_manifest["provenance_completeness"]
    assert procurement_pool["truth_boundary"]["measurement_normalization_state"] == procurement_manifest["normalization_completeness"]
    assert procurement_pool["truth_boundary"]["admissibility_flag_state"] == procurement_manifest["admissibility_completeness"]
    assert procurement_report["blockers"]
    assert "gated" in procurement_report["launchability_reason"]


def test_launchable_pool_view_only_exposes_clean_promoted_pools() -> None:
    workspace = build_workspace_payload()
    launchable_ids = {
        item["pool_id"] for item in workspace["ui_contract"]["launchable_dataset_pools"]
    }
    report_lookup = {
        item["pool_id"]: item for item in workspace["ui_contract"]["pool_promotion_reports"]
    }

    assert launchable_ids == {
        "pool:release_pp_alpha_benchmark_v1",
        "pool:robust_pp_benchmark_v1",
        "pool:expanded_pp_benchmark_v1",
        "pool:governed_ppi_blended_subset_v2",
        "pool:governed_ppi_external_beta_candidate_v1",
        "pool:governed_pl_bridge_pilot_subset_v1",
    }
    assert all(not report_lookup[pool_id]["blockers"] for pool_id in launchable_ids)


def test_governed_subset_manifest_meets_promotion_targets() -> None:
    workspace = build_workspace_payload()
    subset = next(
        item
        for item in workspace["ui_contract"]["governed_subset_manifests_v2"]
        if item["promoted_dataset_ref"] == "governed_ppi_blended_subset_v2"
    )
    source_mix = subset["source_family_mix"]
    assay_mix = subset["assay_family_mix"]
    row_count = subset["row_count"]

    assert subset["promoted_dataset_ref"] == "governed_ppi_blended_subset_v2"
    assert row_count >= 1500
    assert max(source_mix.values()) / row_count <= 0.45
    assert max(assay_mix.values()) / row_count <= 0.60
    assert subset["promotion_readiness"] == "launchable_now"
    assert subset["review_signoff_state"] == "wave_4_ready_for_freeze"
    assert not subset["blockers"]
    assert subset["notes"]


def test_external_beta_candidate_manifest_meets_review_targets() -> None:
    workspace = build_workspace_payload()
    subset = next(
        item
        for item in workspace["ui_contract"]["governed_subset_manifests_v2"]
        if item["promoted_dataset_ref"] == "governed_ppi_external_beta_candidate_v1"
    )
    source_mix = subset["source_family_mix"]
    assay_mix = subset["assay_family_mix"]
    row_count = subset["row_count"]

    assert row_count >= 1500
    assert max(source_mix.values()) / row_count <= 0.45
    assert max(assay_mix.values()) / row_count <= 0.60
    assert subset["promotion_readiness"] == "launchable_now"
    assert subset["status"] == "launchable_now"
    assert subset["review_signoff_state"] == "controlled_external_beta_ready"
    assert not subset["blockers"]
    assert "external_beta_rehearsal" in subset["required_matrix_tests"]


def test_promotion_queue_includes_governed_subset_and_reviewers() -> None:
    workspace = build_workspace_payload()
    queue = {item["queue_id"]: item for item in workspace["ui_contract"]["promotion_queue_v2"]}
    subset_item = queue["subset:governed_ppi_blended_subset_v2"]
    stage2_item = queue["subset:governed_ppi_stage2_candidate_v1"]
    external_beta_item = queue["subset:governed_ppi_external_beta_candidate_v1"]

    assert subset_item["kind"] == "governed_subset"
    assert subset_item["promotion_readiness"] == "launchable_now"
    assert subset_item["review_signoff_state"] == "wave_4_ready_for_freeze"
    assert "Kepler" in subset_item["required_reviewers"]
    assert "McClintock" in subset_item["required_reviewers"]
    assert "run_matrix" in subset_item["required_matrix_tests"]
    assert (
        sum(
            1
            for item in workspace["ui_contract"]["promotion_queue_v2"]
            if item.get("promoted_dataset_ref") == "governed_ppi_blended_subset_v2"
        )
        == 1
    )
    assert stage2_item["promotion_readiness"] == "review_pending_candidate"
    assert "Kepler" in stage2_item["required_reviewers"]
    assert external_beta_item["promotion_readiness"] == "launchable_now"
    assert external_beta_item["review_signoff_state"] == "controlled_external_beta_ready"
    assert "external_beta_rehearsal" in external_beta_item["required_matrix_tests"]


def test_preview_and_build_payloads_return_blocked_state_for_invalid_specs() -> None:
    payload = _default_pipeline_payload()
    payload["data_strategy"]["dataset_refs"] = ["final_structured_candidates_v1"]
    payload["training_set_request"]["dataset_refs"] = []

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)

    assert preview["status"] == "blocked"
    assert preview["blockers"]
    assert preview["candidate_preview"]["rows"] == []
    assert build["status"] == "blocked"
    assert build["build_manifest"]["status"] == "blocked"
    assert build["blockers"]
    assert build["build_manifest"]["split_preview"]["grouping_policy"] == payload["split_plan"]["grouping_policy"]


def test_governed_subset_scope_is_blocked_at_service_layer() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["dataset_refs"] = ["governed_ppi_blended_subset_v1"]
    payload["data_strategy"]["dataset_refs"] = ["governed_ppi_blended_subset_v1"]
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)

    assert preview["status"] == "blocked"
    assert any("whole_complex_graph" in item["message"] for item in preview["blockers"])
    assert build["status"] == "blocked"
    assert any("whole_complex_graph" in item["message"] for item in build["blockers"])


def test_activation_matrix_discloses_governed_subset_constraints_and_generic_graph_adapter_family() -> None:
    workspace = build_workspace_payload()
    entries = workspace["ui_contract"]["model_activation_matrix"]["entries"]
    gcn_entry = next(
        item
        for item in entries
        if item["model_family"] == "gcn" and item["graph_kind"] == "whole_complex_graph"
    )
    blocked_entry = next(
        item
        for item in entries
        if item["model_family"] == "gcn" and item["graph_kind"] == "shell_graph"
    )

    assert gcn_entry["resolved_backend_family"] == "adapter:graphsage-lite-family"
    assert (
        gcn_entry["dataset_scope_constraints"]["governed_ppi_blended_subset_v2"]["partner_awareness"]
        == ["symmetric"]
    )
    assert blocked_entry["dataset_scope_constraints"]["governed_ppi_blended_subset_v2"]["status"] == "blocked"


def test_governed_subset_source_family_is_blocked_at_service_layer() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["source_families"] = ["governed_ppi_promoted_subsets"]
    payload["training_set_request"]["dataset_refs"] = []
    payload["data_strategy"]["dataset_refs"] = []
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)

    assert preview["status"] == "blocked"
    assert build["status"] == "blocked"
    assert any(
        "active beta source-family catalog" in item["message"] or "whole_complex_graph" in item["message"]
        for item in preview["blockers"]
    )


def test_feature_gate_views_expose_atom_and_sequence_embedding_requirements() -> None:
    workspace = build_workspace_payload()
    views = {item["feature_id"]: item for item in workspace["ui_contract"]["feature_gate_views"]}

    assert views["graph:atom_graph"]["status"] == "beta"
    assert "atom_graph_materialization" in views["graph:atom_graph"]["required_matrix_tests"]
    assert views["distributed:sequence_embeddings"]["status"] == "beta"
    assert "sequence_leakage_audit" in views["distributed:sequence_embeddings"]["required_matrix_tests"]
    assert views["ros:pyrosetta"]["status"] == "beta_soon"
    assert views["ros:pyrosetta"]["prototype_artifact"]
    assert views["preprocess:free_state_comparison"]["status"] == "beta_soon"
    assert views["preprocess:free_state_comparison"]["prototype_artifact"]


def test_stage2_scientific_tracks_are_exposed_in_ui_contract() -> None:
    workspace = build_workspace_payload()
    tracks = {item["track_id"]: item for item in workspace["ui_contract"]["stage2_scientific_tracks"]}

    assert tracks["ros:pyrosetta"]["status"] == "review_pending"
    assert tracks["ros:pyrosetta"]["artifact_path"]
    assert Path("D:/documents/ProteoSphereV2", tracks["ros:pyrosetta"]["artifact_path"]).exists()
    assert tracks["preprocess:free_state_comparison"]["status"] == "review_pending"
    assert tracks["preprocess:free_state_comparison"]["artifact_path"]
    assert Path("D:/documents/ProteoSphereV2", tracks["preprocess:free_state_comparison"]["artifact_path"]).exists()


def test_stage2_review_pending_dataset_and_preprocess_modules_return_specific_blockers() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["dataset_refs"] = ["governed_ppi_stage2_candidate_v1"]
    payload["data_strategy"]["dataset_refs"] = ["governed_ppi_stage2_candidate_v1"]
    payload["preprocess_plan"]["modules"] = [
        *payload["preprocess_plan"]["modules"],
        "PyRosetta",
        "Free-state comparison",
    ]

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("review-pending, not launchable now" in message for message in blocker_messages)
    assert any("PyRosetta" in message and "review-pending" in message for message in blocker_messages)
    assert any("Free-state comparison" in message and "governed bound/free structure pairs" in message for message in blocker_messages)

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)
    preview_messages = [item["message"] for item in preview.get("blockers", [])]
    build_messages = [item["message"] for item in build.get("blockers", [])]

    assert any("review-pending, not launchable now" in message for message in preview_messages)
    assert any("PyRosetta" in message and "review-pending" in message for message in build_messages)


def test_external_beta_candidate_returns_specific_review_pending_blocker() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["dataset_refs"] = ["governed_ppi_external_beta_candidate_v1"]
    payload["data_strategy"]["dataset_refs"] = ["governed_ppi_external_beta_candidate_v1"]

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]
    assert not blocker_messages

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)
    preview_messages = [item["message"] for item in preview.get("blockers", [])]
    build_messages = [item["message"] for item in build.get("blockers", [])]

    assert preview["status"] == "ready"
    assert build["status"] == "ready"
    assert not preview_messages
    assert not build_messages


def test_ligand_pilot_graphsage_validates_and_builds() -> None:
    payload = _ligand_pilot_payload(model_family="graphsage")

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert not [item.message for item in report.items if item.level == "blocker"]

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)

    assert preview["status"] == "ready"
    assert build["status"] == "ready"
    assert preview["candidate_preview"]["row_count"] > 0
    assert build["build_manifest"]["row_count"] > 0
    assert build["build_manifest"]["split_strategy"] == "protein_ligand_component_grouped"


def test_ligand_pilot_multimodal_fusion_validates_and_builds() -> None:
    payload = _ligand_pilot_payload(model_family="multimodal_fusion")

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert not [item.message for item in report.items if item.level == "blocker"]

    build = build_training_set_payload(payload)
    assert build["status"] == "ready"
    assert build["build_manifest"]["row_count"] > 0


def test_external_beta_candidate_launches_successfully() -> None:
    payload = _external_beta_ppi_payload()

    launched = launch_pipeline_run(payload)
    run_id = launched["run_manifest"]["run_id"]
    run = _wait_for_completed_run(run_id)

    assert launched["run_manifest"]["status"] in {"running", "completed"}
    assert run["run_manifest"]["status"] == "completed"
    assert run["run_manifest"]["dataset_ref"].startswith("study_build:")
    assert run["run_manifest"]["resolved_training_backend"] == "sklearn-mlp-fusion-adapter"


def test_ligand_pilot_launches_successfully_for_both_launchable_models() -> None:
    for model_family, backend in (
        ("graphsage", "torch-graphsage-lite"),
        ("multimodal_fusion", "sklearn-mlp-fusion-adapter"),
    ):
        launched = launch_pipeline_run(_ligand_pilot_payload(model_family=model_family))
        run_id = launched["run_manifest"]["run_id"]
        run = _wait_for_completed_run(run_id)

        assert launched["run_manifest"]["status"] in {"running", "completed"}
        assert run["run_manifest"]["status"] == "completed"
        assert run["run_manifest"]["resolved_training_backend"] == backend


def test_ligand_pilot_blocks_wrong_model_and_missing_ligand_module() -> None:
    payload = _ligand_pilot_payload(model_family="graphsage")
    payload["training_plan"]["model_family"] = "gin"
    payload["training_plan"]["architecture"] = "gin_encoder"
    payload["preprocess_plan"]["modules"] = [
        item for item in payload["preprocess_plan"]["modules"] if item != "ligand descriptors"
    ]

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("supports only `graphsage` and `multimodal_fusion`" in message for message in blocker_messages)
    assert any("requires the `ligand descriptors` preprocessing module" in message for message in blocker_messages)


def test_ligand_pilot_blocks_wrong_split_and_scope() -> None:
    payload = _ligand_pilot_payload(model_family="graphsage")
    payload["data_strategy"]["split_strategy"] = "graph_component_grouped"
    payload["split_plan"]["grouping_policy"] = "graph_component_grouped"
    payload["graph_recipes"][0]["graph_kind"] = "shell_graph"
    payload["graph_recipes"][0]["region_policy"] = "interface_plus_shell"
    payload["graph_recipes"][0]["partner_awareness"] = "symmetric"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("protein_ligand_component_grouped" in message for message in blocker_messages)
    assert any("requires `whole_complex_graph`" in message for message in blocker_messages)
    assert any("requires the `whole_molecule` region policy" in message for message in blocker_messages)
    assert any("requires `role_conditioned` partner awareness" in message for message in blocker_messages)


def test_sequence_embeddings_require_preprocess_module_and_validate_when_enabled() -> None:
    payload = _default_pipeline_payload()
    payload["feature_recipes"][0]["distributed_feature_sets"] = [
        *payload["feature_recipes"][0]["distributed_feature_sets"],
        "sequence_embeddings",
    ]
    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]
    assert any("Sequence-embedding distributed features require" in message for message in blocker_messages)

    payload["preprocess_plan"]["modules"] = [
        *payload["preprocess_plan"]["modules"],
        "sequence embeddings",
    ]
    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert not [item.message for item in report.items if item.level == "blocker"]


def test_catalog_exposes_high_value_activation_wave() -> None:
    workspace = build_workspace_payload()
    capability_registry = workspace["catalog"]["capability_registry"]
    ui_registry = workspace["catalog"]["ui_option_registry"]

    label_types = {item["value"]: item["status"] for item in capability_registry["label_types"]}
    split_strategies = {
        item["value"]: item["status"] for item in capability_registry["split_strategies"]
    }
    source_families = {item["value"]: item["status"] for item in ui_registry["source_families"]}
    fidelity_levels = {
        item["value"]: item["status"] for item in ui_registry["acceptable_fidelity_levels"]
    }
    uncertainty_heads = {
        item["value"]: item["status"] for item in ui_registry["uncertainty_heads"]
    }
    hardware_presets = {
        item["value"]: item["status"] for item in ui_registry["hardware_runtime_presets"]
    }

    assert label_types["Kd"] == "beta"
    assert label_types["Ki"] == "beta"
    assert label_types["IC50"] == "beta"
    assert split_strategies["uniref_grouped"] == "beta"
    assert split_strategies["paper_faithful_external"] == "beta"
    assert fidelity_levels["publication_candidate"] == "beta"
    assert uncertainty_heads["ensemble_dropout"] == "beta"
    assert hardware_presets["custom"] == "beta"
    assert source_families["expanded_ppi_procurement"] == "beta"


def test_preview_exposes_drop_breakdowns_and_label_fields() -> None:
    preview = preview_training_set_payload(_default_pipeline_payload())
    row = preview["candidate_preview"]["rows"][0]

    assert "drop_reason_breakdown" in preview["candidate_preview"]
    assert "drop_source_breakdown" in preview["candidate_preview"]
    assert "missing_structure_rate" in preview["candidate_preview"]
    assert "resolution_filter_rate" in preview["candidate_preview"]
    assert "drop_reason_breakdown" in preview["diagnostics"]
    assert "drop_source_breakdown" in preview["diagnostics"]
    assert "label_type" in row
    assert "label_origin" in row
    assert "label_provenance" in row


def test_ligand_pilot_supports_kd_and_ki_direct_label_builds() -> None:
    for label_type in ("Kd", "Ki"):
        payload = _ligand_pilot_payload(model_family="graphsage", label_type=label_type)

        report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
        assert not [item.message for item in report.items if item.level == "blocker"]

        preview = preview_training_set_payload(payload)
        build = build_training_set_payload(payload)

        assert preview["status"] == "ready"
        assert build["status"] == "ready"
        assert preview["candidate_preview"]["row_count"] > 0
        assert build["build_manifest"]["label_type"] == label_type
        assert build["build_manifest"]["charts"]["label_distribution"]


def test_ic50_proxy_label_validation_stays_truthful() -> None:
    payload = _ligand_pilot_payload(model_family="graphsage", label_type="IC50")
    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    warning_messages = [item.message for item in report.items if item.level == "warning"]

    assert any("proxy assay label" in message for message in warning_messages)

    preview = preview_training_set_payload(payload)
    if preview["status"] == "ready":
        first_row = preview["candidate_preview"]["rows"][0]
        assert first_row["label_type"] == "IC50"
        assert first_row["label_origin"] == "proxy_assay_measurement"
        assert first_row["label_provenance"]
        assert first_row["assay_family"]
    else:
        assert preview["diagnostics"]["status"] == "blocked"
        assert preview["diagnostics"]["blockers"]


def test_uniref_and_paper_faithful_splits_compile_with_diagnostics() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["source_families"] = ["balanced_ppi_beta_pool"]
    payload["training_set_request"]["dataset_refs"] = []
    payload["data_strategy"]["dataset_refs"] = ["governed_ppi_external_beta_candidate_v1"]

    payload["data_strategy"]["split_strategy"] = "uniref_grouped"
    payload["split_plan"]["grouping_policy"] = "uniref_grouped"
    preview = preview_training_set_payload(payload)
    assert preview["status"] == "ready"
    assert "uniref_grouping_diagnostics" in preview["split_preview"]

    payload["data_strategy"]["split_strategy"] = "paper_faithful_external"
    payload["split_plan"]["grouping_policy"] = "paper_faithful_external"
    preview = preview_training_set_payload(payload)
    assert preview["status"] == "ready"
    assert "paper_faithful_external_diagnostics" in preview["split_preview"]


def test_publication_candidate_and_procurement_source_family_build_truthfully() -> None:
    payload = _default_pipeline_payload()
    payload["training_set_request"]["acceptable_fidelity"] = "publication_candidate"
    payload["training_set_request"]["source_families"] = ["expanded_ppi_procurement"]
    payload["training_set_request"]["dataset_refs"] = []

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert not [item.message for item in report.items if item.level == "blocker"]
    assert any(
        item.category == "fidelity" for item in report.items
    )

    preview = preview_training_set_payload(payload)
    build = build_training_set_payload(payload)

    assert preview["status"] == "ready"
    assert build["status"] == "ready"
    assert build["build_manifest"]["diagnostics"]["drop_reason_breakdown"] is not None


def test_custom_runtime_and_ensemble_dropout_surface_truthfully_in_runs_and_compare() -> None:
    payload = _ligand_pilot_payload(model_family="multimodal_fusion")
    payload["preprocess_plan"]["options"]["hardware_runtime_preset"] = "custom"
    payload["training_plan"]["uncertainty_head"] = "ensemble_dropout"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert not [item.message for item in report.items if item.level == "blocker"]

    launched = launch_pipeline_run(payload)
    run_id = launched["run_manifest"]["run_id"]
    run = _wait_for_completed_run(run_id)

    assert run["run_manifest"]["status"] == "completed"
    assert run["metrics"]["quality_verdict"] in {"healthy", "quality_warning", "quality_blocked"}
    assert "quality_blockers" in run["metrics"]
    assert "quality_warnings" in run["metrics"]
    assert "label_scale_expected" in run["metrics"]
    assert "prediction_scale_observed" in run["metrics"]
    assert "outlier_mass_summary" in run["metrics"]
    assert run["metrics"]["requested_hardware_preset"] == "custom"
    assert run["metrics"]["uncertainty_summary"]["enabled"] is True
    assert run["metrics"]["uncertainty_summary"]["resolved_uncertainty_head"] == (
        "adapter:ensemble_dropout_proxy"
    )
    assert run["recommendations"]["quality_verdict"] == run["metrics"]["quality_verdict"]

    comparison = compare_pipeline_runs([run_id])
    item = comparison["items"][0]
    assert item["requested_hardware_preset"] == "custom"
    assert item["requested_uncertainty_head"] == "ensemble_dropout"
    assert item["quality_verdict"] == run["metrics"]["quality_verdict"]
    assert item["uncertainty_summary"]["enabled"] is True
