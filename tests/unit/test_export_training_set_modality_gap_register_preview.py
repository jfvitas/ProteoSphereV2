from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads():
    readiness = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 3,
            "assignment_ready": True,
            "package_ready": False,
        },
        "readiness_rows": [
            {
                "accession": "A1",
                "training_set_state": "governing_ready",
                "recommended_next_step": "keep_visible_for_preview_compilation",
            },
            {
                "accession": "A2",
                "training_set_state": "blocked_pending_acquisition",
                "recommended_next_step": "wait_for_source_fix:ligand:A2",
            },
            {
                "accession": "A3",
                "training_set_state": "preview_visible_non_governing",
                "recommended_next_step": "keep_non_governing_preview_only",
            },
        ],
    }
    blocker_burndown = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_accession_count": 3,
            "blocked_accession_count": 2,
            "critical_action_count": 2,
            "package_ready": False,
            "assignment_ready": True,
            "top_blocker_categories": [
                {"blocker": "modality_gap", "accession_count": 2},
                {"blocker": "package_gate_closed", "accession_count": 3},
            ],
            "unblock_package_blocked_reasons": ["fold_export_ready=false"],
        },
        "rows": [
            {
                "accession": "A1",
                "priority_bucket": "critical",
                "blocker_context": ["modality_gap", "package_gate_closed"],
            },
            {
                "accession": "A2",
                "priority_bucket": "critical",
                "blocker_context": ["modality_gap", "package_gate_closed"],
            },
            {
                "accession": "A3",
                "priority_bucket": "high",
                "blocker_context": ["package_gate_closed"],
            },
        ],
    }
    action_queue = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_accession_count": 3,
            "queue_length": 4,
            "package_ready": False,
            "priority_bucket_counts": {"critical": 2, "high": 2},
        },
        "rows": [
            {
                "accession": "A1",
                "action_ref": "fill_missing_modalities:ligand,structure",
                "affected_modalities": ["ligand", "structure"],
                "priority_bucket": "critical",
            },
            {
                "accession": "A2",
                "action_ref": "wait_for_source_fix:ligand:A2",
                "affected_modalities": ["ligand"],
                "priority_bucket": "critical",
            },
            {
                "accession": "A3",
                "action_ref": "fill_missing_modalities:ppi",
                "affected_modalities": ["ppi"],
                "priority_bucket": "high",
            },
            {
                "accession": "A3",
                "action_ref": "preserve_current_preview_state",
                "priority_bucket": "high",
            },
        ],
    }
    unblock = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 3,
            "impacted_accession_count": 3,
            "package_ready": False,
            "package_blocked_reasons": ["fold_export_ready=false"],
        },
        "rows": [
            {
                "accession": "A1",
                "package_blockers": ["package_gate_closed", "modality_gap"],
                "direct_remediation_routes": ["fill_missing_modalities:ligand,structure"],
                "recommended_next_actions": ["fill_missing_modalities:ligand,structure"],
            },
            {
                "accession": "A2",
                "package_blockers": ["package_gate_closed", "modality_gap"],
                "direct_remediation_routes": ["wait_for_source_fix:ligand:A2"],
                "recommended_next_actions": ["wait_for_source_fix:ligand:A2"],
            },
            {
                "accession": "A3",
                "package_blockers": ["package_gate_closed"],
                "direct_remediation_routes": ["fill_missing_modalities:ppi"],
                "recommended_next_actions": ["fill_missing_modalities:ppi"],
            },
        ],
    }
    matrix = {
        "generated_at": "2026-04-03T00:00:00Z",
        "row_count": 3,
        "rows": [
            {
                "accession": "A1",
                "family_presence": {
                    "protein": True,
                    "protein_variant": True,
                    "structure_unit": False,
                },
            },
            {
                "accession": "A2",
                "family_presence": {
                    "protein": True,
                    "protein_variant": False,
                    "structure_unit": False,
                },
            },
            {
                "accession": "A3",
                "family_presence": {
                    "protein": True,
                    "protein_variant": False,
                    "structure_unit": True,
                },
            },
        ],
        "summary": {"protein_accession_count": 3},
    }
    package = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "packet_count": 3,
            "ready_for_package": False,
            "blocked_reasons": ["fold_export_ready=false"],
        },
    }
    return readiness, blocker_burndown, action_queue, unblock, matrix, package


def test_build_training_set_modality_gap_register_preview_summarizes_modalities() -> None:
    from scripts.export_training_set_modality_gap_register_preview import (
        build_training_set_modality_gap_register_preview,
    )

    payload = build_training_set_modality_gap_register_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_modality_gap_register_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_accession_count"] == 3
    assert payload["summary"]["blocked_modality_count"] == 3
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["non_mutating"] is True
    assert payload["summary"]["gap_category_counts"]["ligand"] >= 2
    assert payload["summary"]["gap_category_counts"]["structure"] >= 1
    assert payload["summary"]["top_gap_modalities"][0]["modality"] in {
        "ligand",
        "structure",
        "ppi",
    }

    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["A1"]["blocked_modality_count"] >= 2
    assert "ligand" in rows["A1"]["gap_categories"]
    assert rows["A2"]["package_ready"] is False
    assert payload["truth_boundary"]["non_mutating"] is True


def test_main_writes_json_and_handles_missing_inputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_modality_gap_register_preview as exporter

    readiness_path = tmp_path / "training_set_readiness_preview.json"
    blocker_burndown_path = tmp_path / "training_set_blocker_burndown_preview.json"
    action_queue_path = tmp_path / "training_set_action_queue_preview.json"
    unblock_path = tmp_path / "training_set_unblock_plan_preview.json"
    matrix_path = tmp_path / "summary_library_operator_accession_matrix.json"
    package_path = tmp_path / "package_readiness_preview.json"
    output_path = tmp_path / "training_set_modality_gap_register_preview.json"

    readiness, blocker_burndown, action_queue, unblock, matrix, package = _sample_payloads()
    _write_json(readiness_path, readiness)
    _write_json(blocker_burndown_path, blocker_burndown)
    _write_json(action_queue_path, action_queue)
    _write_json(unblock_path, unblock)
    _write_json(matrix_path, matrix)
    _write_json(package_path, package)

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", readiness_path)
    monkeypatch.setattr(
        exporter, "DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN", blocker_burndown_path
    )
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_ACTION_QUEUE", action_queue_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", unblock_path)
    monkeypatch.setattr(exporter, "DEFAULT_OPERATOR_ACCESSION_MATRIX", matrix_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", package_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_accession_count"] == 3
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["summary"][
        "blocked_modality_count"
    ] == 3

    missing_path = tmp_path / "missing.json"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_ACTION_QUEUE", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_OPERATOR_ACCESSION_MATRIX", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", missing_path)
    output_path.unlink()

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_accession_count"] == 0
    assert payload["summary"]["blocked_modality_count"] == 0
    assert payload["truth_boundary"]["non_mutating"] is True
