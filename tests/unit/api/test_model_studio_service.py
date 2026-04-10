from __future__ import annotations

from api.model_studio import service
from api.model_studio.catalog import default_pipeline_spec


def test_service_can_save_and_list_pipeline_specs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "DRAFT_DIR", tmp_path / "drafts")
    monkeypatch.setattr(service, "RUN_DIR", tmp_path / "runs")
    monkeypatch.setattr(service, "MASTER_AGENT_STATE", tmp_path / "master.json")
    monkeypatch.setattr(service, "ORCHESTRATOR_STATE", tmp_path / "orchestrator.json")
    monkeypatch.setattr(service, "PROGRAM_PREVIEW", tmp_path / "preview.json")
    monkeypatch.setattr(service, "list_runs", lambda: [])
    monkeypatch.setattr(service, "list_known_datasets", lambda: [])
    monkeypatch.setattr(
        service,
        "preview_training_set_request",
        lambda *args, **kwargs: {
            "training_set_request": {},
            "resolved_dataset_refs": [],
            "candidate_preview": {"row_count": 0, "sample_pdb_ids": [], "dropped_rows": []},
            "split_preview": {},
            "diagnostics": {"status": "blocked", "row_count": 0, "blockers": ["missing dataset"]},
        },
    )
    monkeypatch.setattr(service, "list_training_set_builds", lambda: [])

    spec = default_pipeline_spec().to_dict()
    spec["pipeline_id"] = "pipeline:test-service"
    spec["study_title"] = "Test Service Draft"
    saved = service.save_pipeline_spec(spec)
    assert saved["pipeline_spec"]["pipeline_id"] == "pipeline:test-service"

    items = service.list_pipeline_specs()
    assert any(item["pipeline_id"] == "pipeline:test-service" for item in items)


def test_service_compile_payload_reports_quality_gates(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "DRAFT_DIR", tmp_path / "drafts")
    monkeypatch.setattr(service, "RUN_DIR", tmp_path / "runs")
    monkeypatch.setattr(service, "MASTER_AGENT_STATE", tmp_path / "master.json")
    monkeypatch.setattr(service, "ORCHESTRATOR_STATE", tmp_path / "orchestrator.json")
    monkeypatch.setattr(service, "PROGRAM_PREVIEW", tmp_path / "preview.json")
    monkeypatch.setattr(service, "list_runs", lambda: [])
    monkeypatch.setattr(service, "list_known_datasets", lambda: [])
    monkeypatch.setattr(service, "list_training_set_builds", lambda: [])

    payload = default_pipeline_spec().to_dict()
    result = service.compile_pipeline_payload(payload)
    assert result["execution_graph"]["graph_id"] == f"graph:{payload['pipeline_id']}"
    assert result["quality_gates"]["status"] in {"ready", "ready_with_warnings"}


def test_workspace_payload_includes_program_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "DRAFT_DIR", tmp_path / "drafts")
    monkeypatch.setattr(service, "RUN_DIR", tmp_path / "runs")
    monkeypatch.setattr(service, "MASTER_AGENT_STATE", tmp_path / "master.json")
    monkeypatch.setattr(service, "ORCHESTRATOR_STATE", tmp_path / "orchestrator.json")
    monkeypatch.setattr(service, "PROGRAM_PREVIEW", tmp_path / "preview.json")
    monkeypatch.setattr(service, "list_runs", lambda: [])
    monkeypatch.setattr(
        service,
        "list_known_datasets",
        lambda: [
            {"dataset_ref": "release_pp_alpha_benchmark_v1", "catalog_status": "release"},
            {"dataset_ref": "expanded_pp_benchmark_v1", "catalog_status": "lab"},
        ],
    )
    monkeypatch.setattr(
        service,
        "preview_training_set_request",
        lambda *args, **kwargs: {
            "training_set_request": {},
            "resolved_dataset_refs": ["release_pp_alpha_benchmark_v1"],
            "candidate_preview": {"row_count": 48, "sample_pdb_ids": ["1ABC"], "dropped_rows": []},
            "split_preview": {"train_count": 33, "val_count": 5, "test_count": 10},
            "diagnostics": {"status": "ready", "row_count": 48, "blockers": []},
        },
    )
    monkeypatch.setattr(service, "list_training_set_builds", lambda: [])

    workspace = service.build_workspace_payload()
    assert workspace["workspace_sections"][0] == "Project Home"
    assert "program_status" in workspace
    assert workspace["catalog"]["task_types"]
    assert workspace["catalog"]["ui_option_registry"]["optimizer_policies"]
    assert (
        workspace["catalog"]["field_help_registry"]["include_waters"]["title"] == "Include waters"
    )
    assert workspace["hardware_profile"]["recommended_preset"]
    assert workspace["stepper"]
    assert "master_agent_state" not in workspace["program_status"]
    assert [item["dataset_ref"] for item in workspace["program_status"]["known_datasets"]] == [
        "release_pp_alpha_benchmark_v1"
    ]
    assert workspace["training_set_preview"]["diagnostics"]["status"] == "ready"
