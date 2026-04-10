from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict, dict]:
    acceptance_path = {
        "generated_at": "2026-04-03T00:00:00Z",
        "rows": [
            {
                "accession": "P00387",
                "acceptance_path_state": "blocked",
                "worst_verdict": "blocked_pending_acquisition",
                "blocking_gates": ["modality"],
                "remediation_actions": ["resolve mapping blockers before training"],
                "issue_categories": ["modality"],
                "priority_bucket": "p0_blocker",
                "supporting_artifacts": ["external_dataset_acceptance_path_preview"],
            },
            {
                "accession": "P69905",
                "acceptance_path_state": "caveated",
                "worst_verdict": "usable_with_caveats",
                "blocking_gates": ["binding"],
                "remediation_actions": ["keep binding rows support-only until validated"],
                "issue_categories": ["binding"],
                "priority_bucket": "p1_follow_up",
                "supporting_artifacts": ["external_dataset_acceptance_path_preview"],
            },
            {
                "accession": "P02042",
                "acceptance_path_state": "advisory_only",
                "worst_verdict": "usable_with_caveats",
                "blocking_gates": [],
                "remediation_actions": [],
                "issue_categories": ["provenance"],
                "priority_bucket": "p2_support_context",
                "supporting_artifacts": ["external_dataset_acceptance_path_preview"],
            },
        ],
    }
    remediation_queue = {
        "summary": {"remediation_queue_row_count": 2},
        "rows": [
            {
                "accession": "P00387",
                "blocking_gate": "modality",
                "remediation_action": "resolve mapping blockers before training",
                "priority_bucket": "p0_blocker",
            },
            {
                "accession": "P69905",
                "blocking_gate": "binding",
                "remediation_action": "keep binding rows support-only until validated",
                "priority_bucket": "p1_follow_up",
            },
        ],
    }
    resolution = {
        "summary": {
            "blocked_accession_count": 1,
            "overall_resolution_verdict": "blocked_pending_acquisition",
        },
        "accession_resolution_rows": [
            {
                "accession": "P00387",
                "resolution_state": "blocked",
                "worst_verdict": "blocked_pending_acquisition",
                "issue_categories": ["modality"],
                "blocking_gates": ["modality"],
                "remediation_actions": ["resolve mapping blockers before training"],
                "supporting_artifacts": ["external_dataset_resolution_preview"],
            },
            {
                "accession": "P69905",
                "resolution_state": "caveated",
                "worst_verdict": "usable_with_caveats",
                "issue_categories": ["binding"],
                "blocking_gates": [],
                "remediation_actions": ["keep binding rows support-only until validated"],
                "supporting_artifacts": ["external_dataset_resolution_preview"],
            },
            {
                "accession": "P02042",
                "resolution_state": "resolved",
                "worst_verdict": "usable_with_caveats",
                "issue_categories": ["provenance"],
                "blocking_gates": [],
                "remediation_actions": [],
                "supporting_artifacts": ["external_dataset_resolution_preview"],
            },
        ],
    }
    clearance = {
        "summary": {
            "current_clearance_state": "blocked",
            "required_change_count": 2,
        }
    }
    return acceptance_path, remediation_queue, resolution, clearance


def test_build_external_dataset_remediation_readiness_preview() -> None:
    from scripts.export_external_dataset_remediation_readiness_preview import (
        build_external_dataset_remediation_readiness_preview,
    )

    payload = build_external_dataset_remediation_readiness_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_remediation_readiness_preview"
    assert payload["summary"]["dataset_accession_count"] == 3
    assert payload["summary"]["current_readiness_state"] == "blocked_pending_remediation"
    assert payload["summary"]["next_ready_batch"] == "resolution"
    assert payload["summary"]["blocked_pending_acquisition_count"] == 1
    assert payload["summary"]["advisory_follow_up_count"] == 1
    assert payload["summary"]["executable_now_count"] == 1
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["remediation_readiness_state"] == "blocked_pending_acquisition"
    assert rows["P69905"]["remediation_readiness_state"] == "advisory_follow_up"
    assert rows["P02042"]["remediation_readiness_state"] == "executable_now"
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_remediation_readiness_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_remediation_readiness_preview as exporter

    acceptance_path, remediation_queue, resolution, clearance = _sample_payloads()
    paths = {}
    for name, payload in {
        "acceptance_path": acceptance_path,
        "remediation_queue": remediation_queue,
        "resolution": resolution,
        "clearance": clearance,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_remediation_readiness_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_ACCEPTANCE_PATH_PREVIEW", paths["acceptance_path"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_REMEDIATION_QUEUE_PREVIEW", paths["remediation_queue"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_CLEARANCE_DELTA_PREVIEW", paths["clearance"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_remediation_readiness_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["dataset_accession_count"] == 3
