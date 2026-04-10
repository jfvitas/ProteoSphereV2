from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    execution = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 4},
        "rows": [
            {
                "accession": "P04637",
                "execution_lane": "preview_hold_until_package_unlock",
                "training_set_state": "preview_visible_non_governing",
                "priority_bucket": "critical",
                "next_package_action": "keep_visible_as_support_only",
                "package_blockers": ["packet_partial_or_missing", "package_gate_closed"],
                "supporting_artifacts": [
                    "training_set_package_execution_preview"
                ],
            },
            {
                "accession": "P31749",
                "execution_lane": "preview_hold_until_package_unlock",
                "training_set_state": "preview_visible_non_governing",
                "priority_bucket": "critical",
                "next_package_action": "keep_non_governing_until_real_ligand_rows_exist",
                "package_blockers": ["preview_only_non_governing"],
            },
        ],
    }
    unlock = {
        "rows": [
            {
                "accession": "P04637",
                "unlock_route_state": "preview_visible_non_governing",
                "next_step": "keep_visible_as_support_only",
                "source_fix_refs": [],
            },
            {
                "accession": "P31749",
                "unlock_route_state": "preview_visible_non_governing",
                "next_step": "keep_non_governing_until_real_ligand_rows_exist",
                "source_fix_refs": ["ligand:P31749"],
            },
        ]
    }
    blocker = {
        "rows": [
            {
                "accession": "P04637",
                "modality_gap_categories": ["structure", "ligand"],
                "package_blockers": ["packet_partial_or_missing", "package_gate_closed"],
            },
            {
                "accession": "P31749",
                "modality_gap_categories": ["sequence", "ppi"],
                "package_blockers": ["preview_only_non_governing"],
            },
        ]
    }
    return execution, unlock, blocker


def test_build_training_set_preview_hold_register_preview() -> None:
    from scripts.export_training_set_preview_hold_register_preview import (
        build_training_set_preview_hold_register_preview,
    )

    payload = build_training_set_preview_hold_register_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_preview_hold_register_preview"
    assert payload["summary"]["selected_count"] == 4
    assert payload["summary"]["preview_hold_row_count"] == 2
    assert payload["summary"]["current_hold_state"] == "preview_hold_register_active"
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P04637"]["hold_lane"] == "support_only_visibility_hold"
    assert rows["P31749"]["hold_lane"] == "non_governing_visibility_hold"
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_preview_hold_register_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_preview_hold_register_preview as exporter

    execution, unlock, blocker = _sample_payloads()
    paths = {}
    for name, payload in {
        "execution": execution,
        "unlock": unlock,
        "blocker": blocker,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_preview_hold_register_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_EXECUTION_PREVIEW", paths["execution"])
    monkeypatch.setattr(exporter, "DEFAULT_UNLOCK_ROUTE_PREVIEW", paths["unlock"])
    monkeypatch.setattr(
        exporter, "DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW", paths["blocker"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_preview_hold_register_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["preview_hold_row_count"] == 2
