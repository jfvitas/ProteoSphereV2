from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict]:
    exit_criteria = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 3},
        "rows": [
            {
                "accession": "P04637",
                "preview_hold_state": "preview_hold_until_package_unlock",
                "hold_lane": "support_only_visibility_hold",
                "exit_criteria_state": "blocked_pending_package_gate_unlock",
                "next_review_step": "recheck fold export and package gates after split unlock",
                "exit_criteria": ["package gate must open before promotion"],
                "priority_bucket": "critical",
            },
            {
                "accession": "P31749",
                "preview_hold_state": "preview_hold_until_package_unlock",
                "hold_lane": "non_governing_visibility_hold",
                "exit_criteria_state": "blocked_pending_packet_and_modality_completion",
                "next_review_step": (
                    "recheck packet completeness and modality gaps after source refresh"
                ),
                "exit_criteria": ["required missing modalities must be materialized"],
                "priority_bucket": "critical",
            },
        ],
    }
    hold_register = {
        "summary": {"selected_count": 3},
        "rows": [
            {"accession": "P04637", "hold_lane": "support_only_visibility_hold"},
            {"accession": "P31749", "hold_lane": "non_governing_visibility_hold"},
        ],
    }
    return exit_criteria, hold_register


def test_build_training_set_preview_hold_clearance_batch_preview() -> None:
    from scripts.export_training_set_preview_hold_clearance_batch_preview import (
        build_training_set_preview_hold_clearance_batch_preview,
    )

    payload = build_training_set_preview_hold_clearance_batch_preview(
        *_sample_payloads()
    )

    assert payload["artifact_id"] == "training_set_preview_hold_clearance_batch_preview"
    assert payload["summary"]["selected_count"] == 3
    assert payload["summary"]["clearance_batch_row_count"] == 2
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P04637"]["clearance_batch"] == "package_gate_recheck_batch"
    assert rows["P31749"]["clearance_batch"] == "packet_modality_recheck_batch"


def test_main_writes_training_set_preview_hold_clearance_batch_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_preview_hold_clearance_batch_preview as exporter

    exit_criteria, hold_register = _sample_payloads()
    exit_path = tmp_path / "exit.json"
    hold_path = tmp_path / "hold.json"
    _write_json(exit_path, exit_criteria)
    _write_json(hold_path, hold_register)
    output_json = tmp_path / "training_set_preview_hold_clearance_batch_preview.json"

    monkeypatch.setattr(exporter, "DEFAULT_EXIT_CRITERIA_PREVIEW", exit_path)
    monkeypatch.setattr(
        exporter, "DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW", hold_path
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_preview_hold_clearance_batch_preview"
    assert output_json.exists()
