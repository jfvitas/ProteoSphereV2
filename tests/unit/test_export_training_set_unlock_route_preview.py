from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict]:
    gate_ladder = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 4,
            "assignment_ready": True,
            "fold_export_ready": False,
            "cv_fold_export_unlocked": False,
            "package_ready": False,
            "gate_ladder_status": "blocked_pending_package_gate",
            "split_dry_run_status": "aligned",
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
        "rows": [
            {
                "accession": "P00387",
                "training_set_state": "governing_ready",
                "gate_ladder_state": "governing_ready_but_package_blocked",
                "blocked_reasons": ["fold_export_ready=false"],
                "recommended_next_step": "keep_visible_for_preview_compilation",
                "source_fix_refs": [],
            },
            {
                "accession": "Q2TAC2",
                "training_set_state": "blocked_pending_acquisition",
                "gate_ladder_state": "blocked_pending_acquisition",
                "blocked_reasons": ["blocked_pending_acquisition", "modality_gap"],
                "recommended_next_step": "wait_for_source_fix:ligand:P00387",
                "source_fix_refs": ["ligand:P00387"],
            },
            {
                "accession": "P69905",
                "training_set_state": "preview_visible_non_governing",
                "gate_ladder_state": "preview_visible_non_governing",
                "blocked_reasons": ["packet_partial_or_missing"],
                "recommended_next_step": "keep_visible_as_support_only",
                "source_fix_refs": [],
            },
            {
                "accession": "Q9UCM0",
                "training_set_state": "blocked_pending_acquisition",
                "gate_ladder_state": "blocked_pending_acquisition",
                "blocked_reasons": ["blocked_pending_acquisition"],
                "recommended_next_step": "wait_for_source_fix:structure:Q9UCM0",
                "source_fix_refs": ["structure:Q9UCM0"],
            },
        ],
    }
    unblock_plan = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "impacted_accession_count": 4,
            "package_blockers": [
                {"blocker": "blocked_pending_acquisition", "accession_count": 2},
                {"blocker": "packet_partial_or_missing", "accession_count": 2},
            ],
        },
        "rows": [
            {
                "accession": "P00387",
                "direct_remediation_routes": ["keep_visible_for_preview_compilation"],
                "package_blockers": ["package_gate_closed"],
                "source_fix_refs": [],
            },
            {
                "accession": "Q2TAC2",
                "direct_remediation_routes": ["wait_for_source_fix:ligand:P00387"],
                "package_blockers": ["blocked_pending_acquisition", "modality_gap"],
                "source_fix_refs": ["ligand:P00387"],
            },
            {
                "accession": "P69905",
                "direct_remediation_routes": ["keep_visible_as_support_only"],
                "package_blockers": ["packet_partial_or_missing"],
                "source_fix_refs": [],
            },
            {
                "accession": "Q9UCM0",
                "direct_remediation_routes": ["wait_for_source_fix:structure:Q9UCM0"],
                "package_blockers": ["blocked_pending_acquisition"],
                "source_fix_refs": ["structure:Q9UCM0"],
            },
        ],
    }
    action_queue = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"queue_length": 4, "impacted_accession_count": 4},
        "rows": [
            {
                "accession": "P00387",
                "action_ref": "keep_visible_for_preview_compilation",
                "priority_bucket": "medium",
                "source_fix_refs": [],
                "supporting_artifacts": ["training_set_unblock_plan_preview"],
            },
            {
                "accession": "Q2TAC2",
                "action_ref": "wait_for_source_fix:ligand:P00387",
                "priority_bucket": "critical",
                "source_fix_refs": ["ligand:P00387"],
                "supporting_artifacts": ["packet_deficit_dashboard"],
            },
            {
                "accession": "P69905",
                "action_ref": "keep_visible_as_support_only",
                "priority_bucket": "high",
                "source_fix_refs": [],
                "supporting_artifacts": ["training_set_unblock_plan_preview"],
            },
            {
                "accession": "Q9UCM0",
                "action_ref": "wait_for_source_fix:structure:Q9UCM0",
                "priority_bucket": "critical",
                "source_fix_refs": ["structure:Q9UCM0"],
                "supporting_artifacts": ["packet_deficit_dashboard"],
            },
        ],
    }
    blocker_matrix = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_accession_count": 4, "blocked_accession_count": 4},
        "rows": [
            {
                "accession": "P00387",
                "training_set_state": "governing_ready",
                "package_blockers": ["package_gate_closed"],
                "priority_bucket": "medium",
            },
            {
                "accession": "Q2TAC2",
                "training_set_state": "blocked_pending_acquisition",
                "package_blockers": ["blocked_pending_acquisition", "modality_gap"],
                "priority_bucket": "critical",
            },
            {
                "accession": "P69905",
                "training_set_state": "preview_visible_non_governing",
                "package_blockers": ["packet_partial_or_missing"],
                "priority_bucket": "high",
            },
            {
                "accession": "Q9UCM0",
                "training_set_state": "blocked_pending_acquisition",
                "package_blockers": ["blocked_pending_acquisition"],
                "priority_bucket": "critical",
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
    return gate_ladder, unblock_plan, action_queue, blocker_matrix, package_readiness


def test_build_training_set_unlock_route_preview_orders_route() -> None:
    from scripts.export_training_set_unlock_route_preview import (
        build_training_set_unlock_route_preview,
    )

    payload = build_training_set_unlock_route_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_unlock_route_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_count"] == 4
    assert payload["summary"]["current_unlock_state"] == "blocked_pending_unlock_route"
    assert payload["summary"]["next_unlock_stage"] == "accession_remediation"
    assert payload["summary"]["blocking_gate_count"] == 3
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["fail_closed"] is True
    assert payload["unlock_route_stages"][1]["stage"] == "accession_remediation"

    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["unlock_route_state"] == "governing_ready_but_package_blocked"
    assert rows["Q2TAC2"]["unlock_route_state"] == "blocked_pending_acquisition"
    assert rows["Q2TAC2"]["next_step"] == "wait_for_source_fix:ligand:P00387"
    assert rows["Q2TAC2"]["source_fix_refs"] == ["ligand:P00387"]
    assert rows["P69905"]["next_step"] == "keep_visible_as_support_only"
    assert rows["Q9UCM0"]["priority_bucket"] == "critical"
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_unlock_route_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_unlock_route_preview as exporter

    gate_ladder, unblock_plan, action_queue, blocker_matrix, package_readiness = (
        _sample_payloads()
    )
    paths = {}
    for name, payload in {
        "gate_ladder": gate_ladder,
        "unblock": unblock_plan,
        "action_queue": action_queue,
        "blocker_matrix": blocker_matrix,
        "package": package_readiness,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_unlock_route_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_GATE_LADDER", paths["gate_ladder"])
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_UNBLOCK_PLAN", paths["unblock"])
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_ACTION_QUEUE", paths["action_queue"])
    monkeypatch.setattr(
        exporter,
        "DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX",
        paths["blocker_matrix"],
    )
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", paths["package"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_unlock_route_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["selected_count"] == 4
