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
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
            ],
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
    package_readiness = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "ready_for_package": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
    }
    remediation = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3},
        "rows": [
            {
                "accession": "A1",
                "issue_buckets": ["package_gate_closed"],
                "recommended_actions": ["preserve_current_preview_state"],
                "source_fix_refs": [],
            },
            {
                "accession": "A2",
                "issue_buckets": [
                    "blocked_pending_acquisition",
                    "modality_gap",
                    "package_gate_closed",
                ],
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
    rationale = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_accessions": ["A1", "A2", "A3"]},
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
    packet_deficit = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "highest_leverage_source_fixes": [
                {
                    "source_ref": "ligand:A2",
                    "affected_packet_count": 1,
                    "missing_modality_count": 1,
                    "missing_modalities": ["ligand"],
                    "packet_accessions": ["A2"],
                    "packet_ids": ["packet-A2"],
                }
            ],
            "source_fix_candidate_count": 1,
        },
        "modality_deficits": [
            {
                "modality": "ligand",
                "packet_accessions": ["A2"],
                "top_source_fix_refs": ["ligand:A2"],
                "top_source_fix_candidates": [{"source_ref": "ligand:A2"}],
            }
        ],
        "source_fix_candidates": [
            {
                "source_ref": "ligand:A2",
                "missing_modality_count": 1,
                "affected_packet_count": 1,
                "missing_modalities": ["ligand"],
                "packet_accessions": ["A2"],
                "packet_ids": ["packet-A2"],
            }
        ],
        "packets": [
            {
                "accession": "A2",
                "packet_id": "packet-A2",
                "status": "partial",
                "missing_modalities": ["ligand"],
                "deficit_source_refs": ["ligand:A2"],
                "missing_source_refs": {"ligand": ["ligand:A2"]},
            }
        ],
    }
    return readiness, package_readiness, remediation, rationale, packet_deficit


def test_build_training_set_unblock_plan_preview_summarizes_blockers_and_routes() -> None:
    from scripts.export_training_set_unblock_plan_preview import (
        build_training_set_unblock_plan_preview,
    )

    payload = build_training_set_unblock_plan_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_unblock_plan_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["impacted_accession_count"] == 3
    assert payload["summary"]["package_blocked_reasons"] == [
        "fold_export_ready=false",
        "cv_fold_export_unlocked=false",
        "split_post_staging_gate_closed",
    ]
    assert payload["summary"]["package_blockers"][0] == {
        "blocker": "package_gate_closed",
        "accession_count": 3,
        "accessions": ["A1", "A2", "A3"],
    }
    assert payload["summary"]["top_source_fix_refs"][0]["source_fix_ref"] == "ligand:A2"
    assert payload["summary"]["top_source_fix_refs"][0]["accessions"] == ["A2"]
    assert any(
        row["route"] == "wait_for_source_fix:ligand:A2"
        for row in payload["summary"]["direct_remediation_routes"]
    )
    assert any(
        row["action"] == "wait_for_source_fix:ligand:A2"
        for row in payload["summary"]["recommended_next_actions"]
    )

    row_by_accession = {row["accession"]: row for row in payload["rows"]}
    assert row_by_accession["A2"]["impacted"] is True
    assert "package_gate_closed" in row_by_accession["A2"]["package_blockers"]
    assert "ligand:A2" in row_by_accession["A2"]["source_fix_refs"]
    assert "fill_missing_modalities:ligand" in row_by_accession["A2"][
        "direct_remediation_routes"
    ]
    assert row_by_accession["A1"]["package_blockers"] == ["package_gate_closed"]
    assert payload["truth_boundary"]["non_mutating"] is True


def test_main_writes_default_json_and_fails_closed_on_missing_input(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_unblock_plan_preview as exporter

    readiness_path = tmp_path / "training_set_readiness_preview.json"
    package_path = tmp_path / "package_readiness_preview.json"
    remediation_path = tmp_path / "training_set_remediation_plan_preview.json"
    rationale_path = tmp_path / "cohort_inclusion_rationale_preview.json"
    packet_path = tmp_path / "packet_deficit_dashboard.json"
    output_path = tmp_path / "training_set_unblock_plan_preview.json"

    readiness, package_readiness, remediation, rationale, packet_deficit = _sample_payloads()
    _write_json(readiness_path, readiness)
    _write_json(package_path, package_readiness)
    _write_json(remediation_path, remediation)
    _write_json(rationale_path, rationale)
    _write_json(packet_path, packet_deficit)

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", readiness_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", package_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_REMEDIATION_PLAN", remediation_path)
    monkeypatch.setattr(exporter, "DEFAULT_COHORT_INCLUSION_RATIONALE", rationale_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKET_DEFICIT_DASHBOARD", packet_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_count"] == 3
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["summary"][
        "impacted_accession_count"
    ] == 3

    missing_readiness_path = tmp_path / "missing_training_set_readiness_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", missing_readiness_path)
    output_path.unlink()

    try:
        exporter.main([])
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError for missing required artifact")

    assert not output_path.exists()
