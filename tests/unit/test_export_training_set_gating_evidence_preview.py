from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads():
    readiness = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3},
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
    remediation = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3},
        "rows": [
            {
                "accession": "A1",
                "issue_buckets": [],
                "recommended_actions": ["preserve_selected_cohort_membership"],
                "source_fix_refs": [],
            },
            {
                "accession": "A2",
                "issue_buckets": ["blocked_pending_acquisition", "modality_gap"],
                "recommended_actions": ["wait_for_source_fix:ligand:A2"],
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
                "next_actions": ["preserve_selected_cohort_membership"],
                "source_fix_refs": [],
                "training_set_state": "governing_ready",
                "packet_status": "ready",
            },
            {
                "accession": "A2",
                "inclusion_class": "gated",
                "inclusion_reason": "blocked_pending_acquisition",
                "next_actions": ["wait_for_source_fix:ligand:A2"],
                "source_fix_refs": ["ligand:A2"],
                "training_set_state": "blocked_pending_acquisition",
                "packet_status": "partial",
            },
            {
                "accession": "A3",
                "inclusion_class": "preview-only",
                "inclusion_reason": "preview_visible_non_governing",
                "next_actions": ["keep_non_governing_preview_only"],
                "source_fix_refs": [],
                "training_set_state": "preview_visible_non_governing",
                "packet_status": "partial",
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
    packet_deficit = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "highest_leverage_source_fixes": [
                {
                    "source_ref": "ligand:A2",
                    "affected_packet_count": 1,
                    "missing_modality_count": 1,
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
                "affected_packet_count": 1,
                "missing_modality_count": 1,
            }
        ],
        "packets": [
            {
                "accession": "A2",
                "missing_source_refs": {"ligand": ["ligand:A2"]},
                "deficit_source_refs": ["ligand:A2"],
            }
        ],
    }
    return readiness, remediation, rationale, unblock, packet_deficit


def test_build_training_set_gating_evidence_preview_exposes_per_accession_evidence() -> None:
    from scripts.export_training_set_gating_evidence_preview import (
        build_training_set_gating_evidence_preview,
    )

    payload = build_training_set_gating_evidence_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_gating_evidence_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_count"] == 3
    assert payload["summary"]["gated_count"] == 1
    assert payload["summary"]["preview_only_count"] == 1
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["top_package_blockers"][0]["blocker"] == "package_gate_closed"
    assert payload["summary"]["top_source_fix_refs"][0]["source_fix_ref"] == "ligand:A2"

    row_by_accession = {row["accession"]: row for row in payload["rows"]}
    assert row_by_accession["A2"]["inclusion_class"] == "gated"
    assert row_by_accession["A2"]["training_set_state"] == "blocked_pending_acquisition"
    assert "package_gate_closed" in row_by_accession["A2"]["package_blockers"]
    assert "wait_for_source_fix:ligand:A2" in row_by_accession["A2"]["next_action_refs"]
    assert row_by_accession["A2"]["evidence_fields"][
        "cohort_inclusion_rationale.inclusion_reason"
    ] == "blocked_pending_acquisition"
    assert any(
        snippet.startswith("training_set_readiness.training_set_state=")
        for snippet in row_by_accession["A2"]["evidence_snippets"]
    )
    assert row_by_accession["A1"]["evidence_fields"][
        "training_set_unblock_plan.package_blockers"
    ] == ["package_gate_closed"]
    assert row_by_accession["A3"]["inclusion_class"] == "preview-only"
    assert payload["truth_boundary"]["non_mutating"] is True


def test_main_writes_json_and_fails_closed_on_missing_required_input(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_gating_evidence_preview as exporter

    readiness_path = tmp_path / "training_set_readiness_preview.json"
    remediation_path = tmp_path / "training_set_remediation_plan_preview.json"
    rationale_path = tmp_path / "cohort_inclusion_rationale_preview.json"
    unblock_path = tmp_path / "training_set_unblock_plan_preview.json"
    packet_path = tmp_path / "packet_deficit_dashboard.json"
    output_path = tmp_path / "training_set_gating_evidence_preview.json"

    readiness, remediation, rationale, unblock, packet_deficit = _sample_payloads()
    _write_json(readiness_path, readiness)
    _write_json(remediation_path, remediation)
    _write_json(rationale_path, rationale)
    _write_json(unblock_path, unblock)
    _write_json(packet_path, packet_deficit)

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", readiness_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_REMEDIATION_PLAN", remediation_path)
    monkeypatch.setattr(exporter, "DEFAULT_COHORT_INCLUSION_RATIONALE", rationale_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", unblock_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKET_DEFICIT_DASHBOARD", packet_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_count"] == 3
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["summary"][
        "gated_count"
    ] == 1

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
