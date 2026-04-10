from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    batch = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 4},
        "rows": [
            {
                "accession": "P04637",
                "training_set_state": "preview_visible_non_governing",
                "priority_bucket": "critical",
                "next_package_action": "keep_visible_as_support_only",
                "package_blockers": ["packet_partial_or_missing", "package_gate_closed"],
                "global_package_gate_blockers": ["fold_export_ready=false"],
                "supporting_artifacts": [
                    "training_set_package_transition_batch_preview"
                ],
            },
            {
                "accession": "P31749",
                "training_set_state": "preview_visible_non_governing",
                "priority_bucket": "critical",
                "next_package_action": "unlock_fold_export_lane",
                "package_blockers": ["package_gate_closed"],
                "global_package_gate_blockers": ["cv_fold_export_unlocked=false"],
                "supporting_artifacts": [
                    "training_set_package_transition_batch_preview"
                ],
            },
        ],
    }
    unblock = {
        "rows": [
            {
                "accession": "P04637",
                "direct_remediation_routes": ["keep_visible_as_support_only"],
                "recommended_next_actions": ["preserve_current_preview_state"],
            },
            {
                "accession": "P31749",
                "direct_remediation_routes": ["unlock_fold_export_lane"],
                "recommended_next_actions": ["do_not_package_until_readiness_unlocks"],
            },
        ]
    }
    package = {"summary": {"blocked_reasons": ["fold_export_ready=false"]}}
    return batch, unblock, package


def test_build_training_set_package_execution_preview() -> None:
    from scripts.export_training_set_package_execution_preview import (
        build_training_set_package_execution_preview,
    )

    payload = build_training_set_package_execution_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_package_execution_preview"
    assert payload["summary"]["selected_count"] == 4
    assert payload["summary"]["package_execution_row_count"] == 2
    assert payload["summary"]["current_execution_state"] == (
        "package_execution_follow_up_required"
    )
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P04637"]["execution_lane"] == "preview_hold_until_package_unlock"
    assert rows["P31749"]["execution_lane"] == "package_unlock_follow_up"
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_package_execution_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_package_execution_preview as exporter

    batch, unblock, package = _sample_payloads()
    paths = {}
    for name, payload in {
        "batch": batch,
        "unblock": unblock,
        "package": package,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_package_execution_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_PACKAGE_TRANSITION_BATCH_PREVIEW", paths["batch"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_UNBLOCK_PLAN_PREVIEW", paths["unblock"])
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS_PREVIEW", paths["package"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_package_execution_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["package_execution_row_count"] == 2
