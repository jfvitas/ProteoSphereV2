from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    batch = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"dataset_accession_count": 4},
        "rows": [
            {
                "accession": "P00387",
                "priority_bucket": "p0_blocker",
                "resolution_state": "blocked",
                "lead_blocking_gate": "issue_matrix",
                "next_blocked_action": "wait_for_acquisition_or_mapping_fix",
                "issue_categories": ["binding", "modality"],
                "remediation_actions": [
                    "resolve mapping or acquisition blockers before training"
                ],
                "supporting_artifacts": [
                    "external_dataset_blocked_acquisition_batch_preview"
                ],
            },
            {
                "accession": "Q9NZD4",
                "priority_bucket": "p0_blocker",
                "resolution_state": "blocked",
                "lead_blocking_gate": "issue_matrix",
                "next_blocked_action": "resolve_mapping_then_retry",
                "issue_categories": ["modality", "provenance"],
                "remediation_actions": [
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ],
                "supporting_artifacts": [
                    "external_dataset_blocked_acquisition_batch_preview"
                ],
            },
        ],
    }
    acceptance = {
        "rows": [
            {"accession": "P00387", "acceptance_path_state": "blocked"},
            {"accession": "Q9NZD4", "acceptance_path_state": "blocked"},
        ]
    }
    queue = {
        "rows": [
            {
                "accession": "P00387",
                "remediation_action": (
                    "resolve mapping or acquisition blockers before training"
                ),
            },
            {
                "accession": "Q9NZD4",
                "remediation_action": (
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ),
            },
        ]
    }
    return batch, acceptance, queue


def test_build_external_dataset_acquisition_unblock_preview() -> None:
    from scripts.export_external_dataset_acquisition_unblock_preview import (
        build_external_dataset_acquisition_unblock_preview,
    )

    payload = build_external_dataset_acquisition_unblock_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_acquisition_unblock_preview"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["acquisition_unblock_row_count"] == 2
    assert payload["summary"]["current_unblock_state"] == (
        "blocked_acquisition_follow_up_required"
    )
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["unblock_lane"] == "acquisition_blocker_follow_up"
    assert rows["Q9NZD4"]["unblock_lane"] == "mapping_or_resolution_follow_up"
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_acquisition_unblock_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_acquisition_unblock_preview as exporter

    batch, acceptance, queue = _sample_payloads()
    paths = {}
    for name, payload in {
        "batch": batch,
        "acceptance": acceptance,
        "queue": queue,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_acquisition_unblock_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_BLOCKED_ACQUISITION_BATCH_PREVIEW", paths["batch"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_PATH_PREVIEW", paths["acceptance"])
    monkeypatch.setattr(exporter, "DEFAULT_REMEDIATION_QUEUE_PREVIEW", paths["queue"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_acquisition_unblock_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["acquisition_unblock_row_count"] == 2
