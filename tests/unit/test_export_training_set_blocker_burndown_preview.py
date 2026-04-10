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
            "assignment_ready": False,
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
    action_queue = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_accession_count": 3,
            "queue_length": 5,
            "package_ready": False,
            "priority_bucket_counts": {"critical": 3, "high": 2},
        },
        "rows": [
            {
                "accession": "A1",
                "action_ref": "preserve_selected_cohort_membership",
                "priority_bucket": "high",
                "blocker_context": ["package_gate_closed"],
            },
            {
                "accession": "A2",
                "action_ref": "wait_for_source_fix:ligand:A2",
                "priority_bucket": "critical",
                "blocker_context": [
                    "blocked_pending_acquisition",
                    "modality_gap",
                    "package_gate_closed",
                ],
            },
            {
                "accession": "A2",
                "action_ref": "fill_missing_modalities:ligand",
                "priority_bucket": "critical",
                "blocker_context": [
                    "blocked_pending_acquisition",
                    "modality_gap",
                    "package_gate_closed",
                ],
            },
            {
                "accession": "A3",
                "action_ref": "do_not_package_until_readiness_unlocks",
                "priority_bucket": "high",
                "blocker_context": ["package_gate_closed", "packet_partial_or_missing"],
            },
            {
                "accession": "A3",
                "action_ref": "keep_non_governing_preview_only",
                "priority_bucket": "high",
                "blocker_context": ["package_gate_closed", "packet_partial_or_missing"],
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
    gating = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3, "gated_count": 1, "preview_only_count": 1},
        "rows": [
            {
                "accession": "A1",
                "inclusion_class": "selected",
                "inclusion_reason": "governing_ready",
                "issue_buckets": [],
                "next_actions": ["preserve_selected_cohort_membership"],
                "source_fix_refs": [],
                "training_set_state": "governing_ready",
                "packet_status": "ready",
            },
            {
                "accession": "A2",
                "inclusion_class": "gated",
                "inclusion_reason": "blocked_pending_acquisition",
                "issue_buckets": ["blocked_pending_acquisition", "modality_gap"],
                "next_actions": ["wait_for_source_fix:ligand:A2"],
                "source_fix_refs": ["ligand:A2"],
                "training_set_state": "blocked_pending_acquisition",
                "packet_status": "partial",
            },
            {
                "accession": "A3",
                "inclusion_class": "preview-only",
                "inclusion_reason": "preview_visible_non_governing",
                "issue_buckets": ["packet_partial_or_missing"],
                "next_actions": ["keep_non_governing_preview_only"],
                "source_fix_refs": [],
                "training_set_state": "preview_visible_non_governing",
                "packet_status": "partial",
            },
        ],
    }
    remediation = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 3,
            "issue_bucket_counts": {
                "package_gate_closed": 3,
                "blocked_pending_acquisition": 1,
                "modality_gap": 1,
                "packet_partial_or_missing": 1,
            },
        },
        "rows": [
            {
                "accession": "A1",
                "issue_buckets": ["package_gate_closed"],
                "recommended_actions": ["preserve_selected_cohort_membership"],
                "source_fix_refs": [],
            },
            {
                "accession": "A2",
                "issue_buckets": ["blocked_pending_acquisition", "modality_gap"],
                "recommended_actions": [
                    "wait_for_source_fix:ligand:A2",
                    "fill_missing_modalities:ligand",
                ],
                "source_fix_refs": ["ligand:A2"],
            },
            {
                "accession": "A3",
                "issue_buckets": ["packet_partial_or_missing", "package_gate_closed"],
                "recommended_actions": ["do_not_package_until_readiness_unlocks"],
                "source_fix_refs": [],
            },
        ],
    }
    return readiness, action_queue, unblock, gating, remediation


def test_build_training_set_blocker_burndown_preview_summarizes_burndown() -> None:
    from scripts.export_training_set_blocker_burndown_preview import (
        build_training_set_blocker_burndown_preview,
    )

    payload = build_training_set_blocker_burndown_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_blocker_burndown_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_accession_count"] == 3
    assert payload["summary"]["blocked_accession_count"] == 3
    assert payload["summary"]["critical_action_count"] == 1
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["assignment_ready"] is False
    assert payload["summary"]["blocker_category_counts"]["package_gate_closed"] == 3
    assert payload["summary"]["top_blocker_categories"][0]["accession_count"] == 3
    assert payload["summary"]["top_blocker_categories"][0]["blocker"] in {
        "assignment_ready=false",
        "package_gate_closed",
    }
    assert "3 selected" in payload["summary"]["remediation_progression_summary"]
    assert "1 critical actions" in payload["summary"]["remediation_progression_summary"]

    row_by_accession = {row["accession"]: row for row in payload["rows"]}
    assert row_by_accession["A2"]["priority_bucket"] == "critical"
    assert "blocked_pending_acquisition" in row_by_accession["A2"]["blocker_context"]
    assert row_by_accession["A1"]["critical_action"] is False
    assert row_by_accession["A1"]["package_ready"] is False
    assert row_by_accession["A1"]["assignment_ready"] is False
    assert payload["truth_boundary"]["non_mutating"] is True


def test_main_writes_json_and_handles_missing_inputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_blocker_burndown_preview as exporter

    readiness_path = tmp_path / "training_set_readiness_preview.json"
    action_queue_path = tmp_path / "training_set_action_queue_preview.json"
    unblock_path = tmp_path / "training_set_unblock_plan_preview.json"
    gating_path = tmp_path / "training_set_gating_evidence_preview.json"
    remediation_path = tmp_path / "training_set_remediation_plan_preview.json"
    output_path = tmp_path / "training_set_blocker_burndown_preview.json"

    readiness, action_queue, unblock, gating, remediation = _sample_payloads()
    _write_json(readiness_path, readiness)
    _write_json(action_queue_path, action_queue)
    _write_json(unblock_path, unblock)
    _write_json(gating_path, gating)
    _write_json(remediation_path, remediation)

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", readiness_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_ACTION_QUEUE", action_queue_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", unblock_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_GATING_EVIDENCE", gating_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_REMEDIATION_PLAN", remediation_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_accession_count"] == 3
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["summary"][
        "blocked_accession_count"
    ] == 3

    missing_path = tmp_path / "missing.json"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_ACTION_QUEUE", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_GATING_EVIDENCE", missing_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_REMEDIATION_PLAN", missing_path)
    output_path.unlink()

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_accession_count"] == 0
    assert payload["summary"]["blocked_accession_count"] == 0
    assert output_path.exists()
