from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    transition = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 4},
        "rows": [
            {
                "accession": "P04637",
                "current_transition_state": "package_transition_blocked",
                "route_state": "preview_visible_non_governing",
                "training_set_state": "preview_visible_non_governing",
                "split": "train",
                "bucket": "rich_coverage",
                "next_transition": "unlock_package_transition",
                "supporting_artifacts": ["training_set_transition_contract_preview"],
            },
            {
                "accession": "P31749",
                "current_transition_state": "package_transition_blocked",
                "route_state": "governing_ready_but_package_blocked",
                "training_set_state": "governing_ready",
                "split": "val",
                "bucket": "rich_coverage",
                "next_transition": "unlock_package_transition",
                "supporting_artifacts": ["training_set_transition_contract_preview"],
            },
            {
                "accession": "Q9NZD4",
                "current_transition_state": "source_fix_transition_pending",
            },
        ],
    }
    package_blocker = {
        "rows": [
            {
                "accession": "P04637",
                "blocked_reason_count": 5,
                "blocked_reasons": ["packet_partial_or_missing", "package_gate_closed"],
                "package_blockers": [
                    "packet_partial_or_missing",
                    "package_gate_closed",
                    "preview_only_non_governing",
                ],
                "modality_gap_categories": ["structure", "ligand"],
                "fold_export_blocked": True,
                "package_ready": False,
                "priority_bucket": "critical",
                "recommended_next_step": "keep_visible_as_support_only",
            },
            {
                "accession": "P31749",
                "blocked_reason_count": 4,
                "blocked_reasons": ["packet_partial_or_missing", "package_gate_closed"],
                "package_blockers": [
                    "packet_partial_or_missing",
                    "package_gate_closed",
                ],
                "modality_gap_categories": ["structure"],
                "fold_export_blocked": True,
                "package_ready": False,
                "priority_bucket": "critical",
                "recommended_next_step": "unlock_fold_export_lane",
            },
        ]
    }
    package_readiness = {
        "summary": {
            "ready_for_package": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
            ]
        }
    }
    return transition, package_blocker, package_readiness


def test_build_training_set_package_transition_batch_preview() -> None:
    from scripts.export_training_set_package_transition_batch_preview import (
        build_training_set_package_transition_batch_preview,
    )

    payload = build_training_set_package_transition_batch_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_package_transition_batch_preview"
    assert payload["summary"]["selected_count"] == 4
    assert payload["summary"]["package_transition_batch_row_count"] == 2
    assert payload["summary"]["current_batch_state"] == (
        "blocked_pending_package_transition_batch"
    )
    assert payload["summary"]["preview_visible_package_count"] == 1
    assert payload["summary"]["governing_ready_package_count"] == 1
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P04637"]["next_package_action"] == "keep_visible_as_support_only"
    assert rows["P31749"]["next_package_action"] == "unlock_fold_export_lane"
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_package_transition_batch_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_package_transition_batch_preview as exporter

    transition, package_blocker, package_readiness = _sample_payloads()
    paths = {}
    for name, payload in {
        "transition": transition,
        "package_blocker": package_blocker,
        "package_readiness": package_readiness,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_package_transition_batch_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_TRANSITION_CONTRACT_PREVIEW", paths["transition"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW", paths["package_blocker"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_PACKAGE_READINESS_PREVIEW", paths["package_readiness"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_package_transition_batch_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["package_transition_batch_row_count"] == 2
