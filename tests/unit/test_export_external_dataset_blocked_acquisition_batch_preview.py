from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    remediation_readiness = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"dataset_accession_count": 4},
        "rows": [
            {
                "accession": "P00387",
                "remediation_readiness_state": "blocked_pending_acquisition",
                "acceptance_path_state": "blocked",
                "resolution_state": "blocked",
                "worst_verdict": "blocked_pending_acquisition",
                "priority_bucket": "p0_blocker",
                "next_action": "wait_for_acquisition_or_mapping_fix",
                "blocking_dependencies": ["modality", "binding"],
                "remediation_actions": [
                    "resolve mapping or acquisition blockers before training"
                ],
                "issue_categories": ["modality", "binding"],
                "supporting_artifacts": [
                    "external_dataset_remediation_readiness_preview"
                ],
            },
            {
                "accession": "Q9NZD4",
                "remediation_readiness_state": "blocked_pending_acquisition",
                "acceptance_path_state": "blocked",
                "resolution_state": "blocked",
                "worst_verdict": "blocked_pending_acquisition",
                "priority_bucket": "p0_blocker",
                "next_action": "wait_for_acquisition_or_mapping_fix",
                "blocking_dependencies": ["modality", "provenance"],
                "remediation_actions": [
                    "resolve mapping or acquisition blockers before training"
                ],
                "issue_categories": ["modality", "provenance"],
                "supporting_artifacts": [
                    "external_dataset_remediation_readiness_preview"
                ],
            },
            {
                "accession": "P68871",
                "remediation_readiness_state": "advisory_follow_up",
            },
        ],
    }
    acceptance_gate = {
        "gate_reports": [
            {
                "gate_name": "issue_matrix",
                "verdict": "blocked_pending_acquisition",
            }
        ]
    }
    issue_matrix = {
        "rows": [
            {
                "accession": "P00387",
                "issue_category": "modality",
                "verdict": "blocked_pending_acquisition",
                "remediation_action": (
                    "resolve mapping or acquisition blockers before training"
                ),
                "source_artifacts": ["external_dataset_modality_audit_preview"],
            },
            {
                "accession": "Q9NZD4",
                "issue_category": "modality",
                "verdict": "blocked_pending_acquisition",
                "remediation_action": (
                    "resolve mapping or acquisition blockers before training"
                ),
                "source_artifacts": ["external_dataset_modality_audit_preview"],
            },
            {
                "accession": "P68871",
                "issue_category": "structure",
                "verdict": "usable_with_caveats",
            },
        ]
    }
    return remediation_readiness, acceptance_gate, issue_matrix


def test_build_external_dataset_blocked_acquisition_batch_preview() -> None:
    from scripts.export_external_dataset_blocked_acquisition_batch_preview import (
        build_external_dataset_blocked_acquisition_batch_preview,
    )

    payload = build_external_dataset_blocked_acquisition_batch_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_blocked_acquisition_batch_preview"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["blocked_acquisition_row_count"] == 2
    assert payload["summary"]["current_batch_state"] == (
        "blocked_pending_acquisition_batch"
    )
    assert payload["summary"]["p0_blocker_count"] == 2
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["lead_blocking_gate"] == "issue_matrix"
    assert rows["Q9NZD4"]["next_blocked_action"] == "wait_for_acquisition_or_mapping_fix"
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_blocked_acquisition_batch_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_blocked_acquisition_batch_preview as exporter

    remediation_readiness, acceptance_gate, issue_matrix = _sample_payloads()
    paths = {}
    for name, payload in {
        "remediation_readiness": remediation_readiness,
        "acceptance_gate": acceptance_gate,
        "issue_matrix": issue_matrix,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_blocked_acquisition_batch_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_REMEDIATION_READINESS_PREVIEW", paths["remediation_readiness"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_ISSUE_MATRIX_PREVIEW", paths["issue_matrix"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_blocked_acquisition_batch_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["blocked_acquisition_row_count"] == 2
