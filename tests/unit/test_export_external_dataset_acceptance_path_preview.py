from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    assessment = {
        "artifact_id": "external_dataset_assessment_preview",
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "dataset_accession_count": 4,
            "overall_verdict": "blocked_pending_mapping",
        },
    }
    acceptance_gate = {
        "artifact_id": "external_dataset_acceptance_gate_preview",
        "summary": {
            "overall_gate_verdict": "blocked_pending_acquisition",
            "blocked_gate_count": 1,
        },
    }
    admission = {
        "artifact_id": "external_dataset_admission_decision_preview",
        "summary": {
            "dataset_accession_count": 4,
            "overall_decision": "blocked",
            "overall_verdict": "blocked_pending_cleanup",
            "blocking_gate_count": 1,
        },
    }
    clearance = {
        "artifact_id": "external_dataset_clearance_delta_preview",
        "summary": {
            "dataset_accession_count": 4,
            "current_clearance_state": "blocked",
            "current_clearance_verdict": "blocked_pending_cleanup",
            "blocking_gate_count": 1,
            "required_change_count": 3,
            "required_changes": [
                "remove duplicate rows before training",
                "resolve mapping blockers before training",
            ],
        },
    }
    resolution = {
        "artifact_id": "external_dataset_resolution_preview",
        "summary": {
            "dataset_accession_count": 4,
            "blocked_accession_count": 2,
            "mapping_incomplete_accession_count": 1,
            "overall_resolution_verdict": "blocked_pending_mapping",
        },
        "accession_resolution_rows": [
            {
                "accession": "P04637",
                "resolution_state": "blocked",
                "worst_verdict": "blocked_pending_cleanup",
                "issue_categories": ["leakage", "provenance"],
                "blocking_gates": ["leakage"],
                "remediation_actions": ["remove duplicate rows before training"],
                "supporting_artifacts": ["external_dataset_issue_matrix_preview"],
            },
            {
                "accession": "P31749",
                "resolution_state": "mapping-incomplete",
                "worst_verdict": "blocked_pending_mapping",
                "issue_categories": ["modality"],
                "blocking_gates": ["modality"],
                "remediation_actions": ["resolve mapping blockers before training"],
                "supporting_artifacts": ["external_dataset_issue_matrix_preview"],
            },
            {
                "accession": "P69905",
                "resolution_state": "caveated",
                "worst_verdict": "usable_with_caveats",
                "issue_categories": ["binding"],
                "blocking_gates": [],
                "remediation_actions": ["keep binding rows support-only until validated"],
                "supporting_artifacts": ["external_dataset_issue_matrix_preview"],
            },
        ],
    }
    remediation_queue = {
        "artifact_id": "external_dataset_remediation_queue_preview",
        "summary": {
            "dataset_accession_count": 4,
            "remediation_queue_row_count": 3,
        },
        "rows": [
            {
                "accession": "P04637",
                "blocking_gate": "leakage",
                "priority_bucket": "critical",
                "remediation_action": "remove duplicate rows before training",
                "supporting_artifacts": ["external_dataset_acceptance_gate_preview"],
            },
            {
                "accession": "P31749",
                "blocking_gate": "modality",
                "priority_bucket": "critical",
                "remediation_action": "resolve mapping blockers before training",
                "supporting_artifacts": ["external_dataset_acceptance_gate_preview"],
            },
            {
                "accession": "P69905",
                "blocking_gate": "binding",
                "priority_bucket": "medium",
                "remediation_action": "keep binding rows support-only until validated",
                "supporting_artifacts": ["external_dataset_acceptance_gate_preview"],
            },
        ],
    }
    issue_matrix = {
        "artifact_id": "external_dataset_issue_matrix_preview",
        "summary": {
            "dataset_accession_count": 4,
            "issue_row_count": 3,
        },
        "rows": [
            {
                "accession": "P04637",
                "issue_category": "leakage",
                "verdict": "blocked_pending_cleanup",
                "source_artifacts": ["external_dataset_leakage_audit_preview"],
            },
            {
                "accession": "P31749",
                "issue_category": "modality",
                "verdict": "blocked_pending_mapping",
                "source_artifacts": ["external_dataset_modality_audit_preview"],
            },
            {
                "accession": "P69905",
                "issue_category": "binding",
                "verdict": "usable_with_caveats",
                "source_artifacts": ["external_dataset_binding_audit_preview"],
            },
        ],
    }
    return (
        assessment,
        acceptance_gate,
        admission,
        clearance,
        resolution,
        remediation_queue,
        issue_matrix,
    )


def test_build_external_dataset_acceptance_path_preview_orders_path() -> None:
    from scripts.export_external_dataset_acceptance_path_preview import (
        build_external_dataset_acceptance_path_preview,
    )

    payload = build_external_dataset_acceptance_path_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_acceptance_path_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["current_path_state"] == "blocked"
    assert payload["summary"]["overall_decision"] == "blocked"
    assert payload["summary"]["next_acceptance_stage"] == "assessment"
    assert payload["summary"]["required_change_count"] == 3
    assert payload["summary"]["fail_closed"] is True
    assert payload["acceptance_path_stages"][1]["stage"] == "issue_resolution"

    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P04637"]["acceptance_path_state"] == "blocked"
    assert rows["P04637"]["next_step"] == "remove duplicate rows before training"
    assert rows["P31749"]["resolution_state"] == "mapping-incomplete"
    assert rows["P31749"]["blocking_gates"] == ["modality"]
    assert rows["P69905"]["acceptance_path_state"] == "caveated"
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_acceptance_path_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_acceptance_path_preview as exporter

    (
        assessment,
        acceptance_gate,
        admission,
        clearance,
        resolution,
        remediation_queue,
        issue_matrix,
    ) = _sample_payloads()
    paths = {}
    for name, payload in {
        "assessment": assessment,
        "acceptance_gate": acceptance_gate,
        "admission": admission,
        "clearance": clearance,
        "resolution": resolution,
        "remediation_queue": remediation_queue,
        "issue_matrix": issue_matrix,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_acceptance_path_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"])
    monkeypatch.setattr(exporter, "DEFAULT_ADMISSION_DECISION_PREVIEW", paths["admission"])
    monkeypatch.setattr(exporter, "DEFAULT_CLEARANCE_DELTA_PREVIEW", paths["clearance"])
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_REMEDIATION_QUEUE_PREVIEW", paths["remediation_queue"])
    monkeypatch.setattr(exporter, "DEFAULT_ISSUE_MATRIX_PREVIEW", paths["issue_matrix"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_acceptance_path_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["dataset_accession_count"] == 4
