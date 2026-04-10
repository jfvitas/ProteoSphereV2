from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict]:
    unlock = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_count": 3,
            "current_unlock_state": "blocked_pending_unlock_route",
            "next_unlock_stage": "accession_remediation",
        },
        "rows": [
            {
                "accession": "P00387",
                "unlock_route_state": "governing_ready_but_package_blocked",
                "current_training_set_state": "governing_ready",
                "source_fix_refs": [],
                "supporting_artifacts": ["training_set_unlock_route_preview"],
            },
            {
                "accession": "Q2TAC2",
                "unlock_route_state": "blocked_pending_acquisition",
                "current_training_set_state": "blocked_pending_acquisition",
                "source_fix_refs": ["ligand:P00387"],
                "supporting_artifacts": ["training_set_unlock_route_preview"],
            },
            {
                "accession": "P69905",
                "unlock_route_state": "preview_visible_non_governing",
                "current_training_set_state": "preview_visible_non_governing",
                "source_fix_refs": [],
                "supporting_artifacts": ["training_set_unlock_route_preview"],
            },
        ],
    }
    gate = {
        "rows": [
            {"accession": "P00387", "training_set_state": "governing_ready"},
            {"accession": "Q2TAC2", "training_set_state": "blocked_pending_acquisition"},
            {"accession": "P69905", "training_set_state": "preview_visible_non_governing"},
        ],
    }
    split = {
        "summary": {
            "dry_run_validation_status": "aligned",
            "fold_export_ready": False,
            "cv_fold_export_unlocked": False,
            "package_blocking_factors": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
            ],
        },
        "rows": [
            {"accession": "P00387", "split": "train", "bucket": "moderate_coverage"},
            {"accession": "Q2TAC2", "split": "val", "bucket": "moderate_coverage"},
            {"accession": "P69905", "split": "test", "bucket": "rich_coverage"},
        ],
    }
    package = {
        "summary": {
            "ready_for_package": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
            ],
        }
    }
    blocker_matrix = {
        "rows": [
            {"accession": "P00387", "package_blockers": ["package_gate_closed"]},
            {
                "accession": "Q2TAC2",
                "package_blockers": ["blocked_pending_acquisition", "modality_gap"],
            },
            {"accession": "P69905", "package_blockers": []},
        ]
    }
    return unlock, gate, split, package, blocker_matrix


def test_build_training_set_transition_contract_preview() -> None:
    from scripts.export_training_set_transition_contract_preview import (
        build_training_set_transition_contract_preview,
    )

    payload = build_training_set_transition_contract_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_transition_contract_preview"
    assert payload["summary"]["selected_count"] == 3
    assert payload["summary"]["current_transition_state"] == "blocked_pending_transition_contract"
    assert payload["summary"]["next_transition_contract"] == "accession_remediation"
    assert payload["summary"]["source_fix_transition_pending_count"] == 1
    assert payload["summary"]["package_transition_blocked_count"] == 1
    assert payload["summary"]["preview_transition_hold_count"] == 1
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["Q2TAC2"]["current_transition_state"] == "source_fix_transition_pending"
    assert rows["Q2TAC2"]["next_transition"] == "clear_source_fix_route"
    assert rows["P00387"]["current_transition_state"] == "package_transition_blocked"
    assert rows["P69905"]["current_transition_state"] == "preview_transition_hold"
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_transition_contract_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_transition_contract_preview as exporter

    unlock, gate, split, package, blocker_matrix = _sample_payloads()
    paths = {}
    for name, payload in {
        "unlock": unlock,
        "gate": gate,
        "split": split,
        "package": package,
        "blocker_matrix": blocker_matrix,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_transition_contract_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_UNLOCK_ROUTE_PREVIEW", paths["unlock"])
    monkeypatch.setattr(exporter, "DEFAULT_GATE_LADDER_PREVIEW", paths["gate"])
    monkeypatch.setattr(exporter, "DEFAULT_SPLIT_SIMULATION_PREVIEW", paths["split"])
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS_PREVIEW", paths["package"])
    monkeypatch.setattr(
        exporter, "DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW", paths["blocker_matrix"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_transition_contract_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["selected_count"] == 3
