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
            "blocked_accession_count": 3,
            "package_ready": False,
            "assignment_ready": True,
            "unblock_package_blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
        "rows": [
            {
                "accession": "A1",
                "priority_bucket": "critical",
                "blocker_context": ["package_gate_closed", "fold_export_ready=false"],
                "critical_action": True,
                "package_ready": False,
            },
            {
                "accession": "A2",
                "priority_bucket": "critical",
                "blocker_context": [
                    "package_gate_closed",
                    "modality_gap",
                    "blocked_pending_acquisition",
                ],
                "critical_action": True,
                "package_ready": False,
            },
            {
                "accession": "A3",
                "priority_bucket": "high",
                "blocker_context": ["package_gate_closed", "packet_partial_or_missing"],
                "critical_action": False,
                "package_ready": False,
            },
        ],
    }
    modality = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_accession_count": 3,
            "blocked_modality_count": 2,
            "package_ready": False,
            "non_mutating": True,
        },
        "rows": [
            {
                "accession": "A1",
                "blocked_modality_count": 1,
                "gap_categories": ["ligand"],
                "package_ready": False,
                "training_set_state": "governing_ready",
                "next_step": "fill_missing_modalities:ligand",
            },
            {
                "accession": "A2",
                "blocked_modality_count": 2,
                "gap_categories": ["ligand", "structure"],
                "package_ready": False,
                "training_set_state": "blocked_pending_acquisition",
                "next_step": "wait_for_source_fix:ligand:A2",
            },
            {
                "accession": "A3",
                "blocked_modality_count": 0,
                "gap_categories": [],
                "package_ready": False,
                "training_set_state": "preview_visible_non_governing",
                "next_step": "keep_non_governing_preview_only",
            },
        ],
    }
    unblock = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 3,
            "impacted_accession_count": 3,
            "package_ready": False,
            "package_blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
        "rows": [
            {
                "accession": "A1",
                "training_set_state": "governing_ready",
                "inclusion_class": "selected",
                "package_blockers": ["package_gate_closed"],
                "direct_remediation_routes": ["preserve_selected_cohort_membership"],
                "source_fix_refs": [],
                "recommended_next_actions": ["preserve_selected_cohort_membership"],
                "packet_status": "ready",
            },
            {
                "accession": "A2",
                "training_set_state": "blocked_pending_acquisition",
                "inclusion_class": "gated",
                "package_blockers": [
                    "blocked_pending_acquisition",
                    "package_gate_closed",
                    "modality_gap",
                ],
                "direct_remediation_routes": [
                    "wait_for_source_fix:ligand:A2",
                    "fill_missing_modalities:ligand",
                ],
                "source_fix_refs": ["ligand:A2"],
                "recommended_next_actions": [
                    "wait_for_source_fix:ligand:A2",
                    "fill_missing_modalities:ligand",
                ],
                "packet_status": "partial",
            },
            {
                "accession": "A3",
                "training_set_state": "preview_visible_non_governing",
                "inclusion_class": "preview-only",
                "package_blockers": ["package_gate_closed", "packet_partial_or_missing"],
                "direct_remediation_routes": ["do_not_package_until_readiness_unlocks"],
                "source_fix_refs": [],
                "recommended_next_actions": ["do_not_package_until_readiness_unlocks"],
                "packet_status": "partial",
            },
        ],
    }
    package = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "packet_count": 3,
            "ready_for_package": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
    }
    return readiness, blocker_burndown, modality, unblock, package


def test_build_training_set_package_blocker_matrix_preview_summarizes_blockers() -> None:
    from scripts.export_training_set_package_blocker_matrix_preview import (
        build_training_set_package_blocker_matrix_preview,
    )

    payload = build_training_set_package_blocker_matrix_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_package_blocker_matrix_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_accession_count"] == 3
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["fold_export_blocked_count"] == 3
    assert payload["summary"]["modality_blocked_count"] == 2
    assert payload["summary"]["non_mutating"] is True

    blocked_reason_counts = payload["summary"]["blocked_reason_counts"]
    assert blocked_reason_counts["package_gate_closed"] == 3
    assert blocked_reason_counts["fold_export_ready=false"] == 3
    assert blocked_reason_counts["cv_fold_export_unlocked=false"] == 3
    assert blocked_reason_counts["split_post_staging_gate_closed"] == 3
    assert blocked_reason_counts["modality_gap"] == 2

    top_reasons = [row["reason"] for row in payload["summary"]["top_blocking_reasons"]]
    assert "package_gate_closed" in top_reasons
    assert "fold_export_ready=false" in top_reasons

    top_accessions = payload["summary"]["top_blocked_accessions"]
    assert top_accessions[0]["accession"] == "A2"
    assert top_accessions[0]["blocked_reason_count"] >= top_accessions[1][
        "blocked_reason_count"
    ]
    row_by_accession = {row["accession"]: row for row in payload["rows"]}
    assert row_by_accession["A1"]["fold_export_blocked"] is True
    assert row_by_accession["A2"]["modality_blocked"] is True
    assert row_by_accession["A3"]["blocked_reason_count"] >= 3
    assert payload["truth_boundary"]["non_mutating"] is True
    assert payload["truth_boundary"]["fail_closed"] is True


def test_main_writes_json_and_handles_missing_inputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_package_blocker_matrix_preview as exporter

    readiness_path = tmp_path / "training_set_readiness_preview.json"
    blocker_burndown_path = tmp_path / "training_set_blocker_burndown_preview.json"
    modality_path = tmp_path / "training_set_modality_gap_register_preview.json"
    unblock_path = tmp_path / "training_set_unblock_plan_preview.json"
    package_path = tmp_path / "package_readiness_preview.json"
    output_path = tmp_path / "training_set_package_blocker_matrix_preview.json"

    readiness, blocker_burndown, modality, unblock, package = _sample_payloads()
    _write_json(readiness_path, readiness)
    _write_json(blocker_burndown_path, blocker_burndown)
    _write_json(modality_path, modality)
    _write_json(unblock_path, unblock)
    _write_json(package_path, package)

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", readiness_path)
    monkeypatch.setattr(
        exporter, "DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN", blocker_burndown_path
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER", modality_path
    )
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", unblock_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", package_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_accession_count"] == 3
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["summary"][
        "fold_export_blocked_count"
    ] == 3

    missing_path = tmp_path / "missing.json"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", missing_path)
    output_path.unlink()

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_accession_count"] == 0
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["fold_export_blocked_count"] == 0
    assert payload["summary"]["modality_blocked_count"] == 0
