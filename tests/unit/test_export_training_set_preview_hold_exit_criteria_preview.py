from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    hold_register = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3},
        "rows": [
            {
                "accession": "P04637",
                "preview_hold_state": "preview_hold_until_package_unlock",
                "hold_lane": "support_only_visibility_hold",
                "training_set_state": "preview_visible_non_governing",
                "priority_bucket": "critical",
                "hold_reasons": [
                    "packet_partial_or_missing",
                    "package_gate_closed",
                ],
                "modality_gap_categories": ["structure"],
            },
            {
                "accession": "P31749",
                "preview_hold_state": "preview_hold_until_package_unlock",
                "hold_lane": "non_governing_visibility_hold",
                "training_set_state": "preview_visible_non_governing",
                "priority_bucket": "critical",
                "hold_reasons": [
                    "modality_gap",
                    "thin_coverage",
                ],
                "modality_gap_categories": ["sequence", "ppi"],
            },
        ],
    }
    gate_ladder = {
        "rows": [
            {
                "accession": "P04637",
                "blocked_reasons": [
                    "package_gate_closed",
                    "fold_export_ready=false",
                ],
            },
            {
                "accession": "P31749",
                "blocked_reasons": ["modality_gap", "thin_coverage"],
            },
        ]
    }
    blocker_matrix = {
        "rows": [
            {
                "accession": "P04637",
                "package_blockers": ["packet_partial_or_missing"],
            },
            {
                "accession": "P31749",
                "package_blockers": ["modality_gap"],
            },
        ]
    }
    return hold_register, gate_ladder, blocker_matrix


def test_build_training_set_preview_hold_exit_criteria_preview() -> None:
    from scripts.export_training_set_preview_hold_exit_criteria_preview import (
        build_training_set_preview_hold_exit_criteria_preview,
    )

    payload = build_training_set_preview_hold_exit_criteria_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_preview_hold_exit_criteria_preview"
    assert payload["summary"]["selected_count"] == 3
    assert payload["summary"]["exit_criteria_row_count"] == 2
    assert payload["summary"]["current_exit_state"] == "preview_hold_exit_criteria_active"
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P04637"]["exit_criteria_state"] == "blocked_pending_package_gate_unlock"
    assert rows["P31749"]["exit_criteria_state"] == (
        "blocked_pending_packet_and_modality_completion"
    )
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_preview_hold_exit_criteria_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_preview_hold_exit_criteria_preview as exporter

    hold_register, gate_ladder, blocker_matrix = _sample_payloads()
    paths = {}
    for name, payload in {
        "hold_register": hold_register,
        "gate_ladder": gate_ladder,
        "blocker_matrix": blocker_matrix,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_preview_hold_exit_criteria_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW", paths["hold_register"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_GATE_LADDER_PREVIEW", paths["gate_ladder"])
    monkeypatch.setattr(
        exporter, "DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW", paths["blocker_matrix"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_preview_hold_exit_criteria_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["exit_criteria_row_count"] == 2
