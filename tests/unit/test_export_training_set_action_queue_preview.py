from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads():
    unblock = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 3,
            "impacted_accession_count": 3,
            "package_ready": False,
            "package_blocked_reasons": [],
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
                    "modality_gap",
                    "package_gate_closed",
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
        "summary": {"selected_count": 3, "package_ready": False},
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
                "next_actions": ["do_not_package_until_readiness_unlocks"],
                "source_fix_refs": [],
                "training_set_state": "preview_visible_non_governing",
                "packet_status": "partial",
            },
        ],
    }
    remediation = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3},
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
                }
            ]
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
                "packet_accessions": ["A2"],
                "missing_modalities": ["ligand"],
                "affected_packet_count": 1,
                "missing_modality_count": 1,
            }
        ],
        "packets": [
            {
                "accession": "A2",
                "missing_modalities": ["ligand"],
                "deficit_source_refs": ["ligand:A2"],
                "missing_source_refs": {"ligand": ["ligand:A2"]},
                "status": "partial",
            }
        ],
    }
    return unblock, gating, remediation, packet_deficit


def test_build_training_set_action_queue_preview_prioritizes_actions_and_sources() -> None:
    from scripts.export_training_set_action_queue_preview import (
        build_training_set_action_queue_preview,
    )

    unblock, gating, remediation, packet_deficit = _sample_payloads()
    payload = build_training_set_action_queue_preview(
        unblock,
        gating,
        remediation,
        packet_deficit,
    )

    assert payload["artifact_id"] == "training_set_action_queue_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_accession_count"] == 3
    assert payload["summary"]["queue_length"] == 4
    assert payload["summary"]["priority_bucket_counts"] == {"critical": 2, "high": 2}
    assert payload["summary"]["top_source_fix_refs"][0] == {
        "source_fix_ref": "ligand:A2",
        "count": 1,
    }

    rows = payload["rows"]
    assert [row["accession"] for row in rows] == ["A2", "A2", "A3", "A1"]
    assert rows[0]["action_ref"] == "wait_for_source_fix:ligand:A2"
    assert rows[0]["priority_bucket"] == "critical"
    assert rows[0]["affected_modalities"] == ["ligand"]
    assert "packet_deficit_dashboard" in rows[0]["supporting_artifacts"]
    assert rows[1]["action_ref"] == "fill_missing_modalities:ligand"
    assert rows[2]["action_ref"] == "do_not_package_until_readiness_unlocks"
    assert rows[2]["priority_bucket"] == "high"
    assert rows[3]["action_ref"] == "preserve_selected_cohort_membership"
    assert "package_gate_closed" in rows[3]["blocker_context"]
    assert "package_readiness_preview" in rows[3]["supporting_artifacts"]
    assert payload["truth_boundary"]["non_mutating"] is True


def test_main_writes_json_and_fails_closed_on_missing_required_input(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_action_queue_preview as exporter

    unblock_path = tmp_path / "training_set_unblock_plan_preview.json"
    gating_path = tmp_path / "training_set_gating_evidence_preview.json"
    remediation_path = tmp_path / "training_set_remediation_plan_preview.json"
    packet_path = tmp_path / "packet_deficit_dashboard.json"
    output_path = tmp_path / "training_set_action_queue_preview.json"

    unblock, gating, remediation, packet_deficit = _sample_payloads()
    _write_json(unblock_path, unblock)
    _write_json(gating_path, gating)
    _write_json(remediation_path, remediation)
    _write_json(packet_path, packet_deficit)

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", unblock_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_GATING_EVIDENCE", gating_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_REMEDIATION_PLAN", remediation_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKET_DEFICIT_DASHBOARD", packet_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["queue_length"] == 4
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["summary"][
        "selected_accession_count"
    ] == 3

    missing_unblock_path = tmp_path / "missing_training_set_unblock_plan_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", missing_unblock_path)
    output_path.unlink()

    try:
        exporter.main([])
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError for missing required artifact")

    assert not output_path.exists()
