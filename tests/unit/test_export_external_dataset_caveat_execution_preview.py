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
                "accession": "P68871",
                "remediation_readiness_state": "advisory_follow_up",
                "resolution_state": "caveated",
                "priority_bucket": "p1_follow_up",
                "issue_categories": ["binding", "provenance", "structure"],
                "blocking_dependencies": ["structure", "binding"],
                "remediation_actions": [
                    "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                ],
                "supporting_artifacts": [
                    "external_dataset_remediation_readiness_preview"
                ],
            },
            {
                "accession": "P04637",
                "remediation_readiness_state": "advisory_follow_up",
                "resolution_state": "caveated",
                "priority_bucket": "p2_support_context",
                "issue_categories": ["binding", "provenance"],
                "blocking_dependencies": ["binding", "provenance"],
                "remediation_actions": [
                    "keep binding rows support-only until case-specific validation passes"
                ],
                "supporting_artifacts": [
                    "external_dataset_remediation_readiness_preview"
                ],
            },
            {
                "accession": "Q9NZD4",
                "remediation_readiness_state": "blocked_pending_acquisition",
            },
        ],
    }
    acceptance_path = {
        "rows": [
            {
                "accession": "P68871",
                "acceptance_path_state": "caveated",
                "priority_bucket": "p1_follow_up",
            },
            {
                "accession": "P04637",
                "acceptance_path_state": "caveated",
                "priority_bucket": "p2_support_context",
            },
        ]
    }
    remediation_queue = {
        "rows": [
            {
                "accession": "P68871",
                "issue_category": "structure",
                "remediation_action": (
                    "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                ),
            },
            {
                "accession": "P04637",
                "issue_category": "binding",
                "remediation_action": (
                    "keep binding rows support-only until case-specific validation passes"
                ),
            },
            {
                "accession": "P04637",
                "issue_category": "provenance",
                "remediation_action": (
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ),
            },
        ]
    }
    return remediation_readiness, acceptance_path, remediation_queue


def test_build_external_dataset_caveat_execution_preview() -> None:
    from scripts.export_external_dataset_caveat_execution_preview import (
        build_external_dataset_caveat_execution_preview,
    )

    payload = build_external_dataset_caveat_execution_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_caveat_execution_preview"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["caveat_execution_row_count"] == 2
    assert payload["summary"]["current_execution_state"] == "caveat_follow_up_ready"
    assert payload["summary"]["structure_sensitive_follow_up_count"] == 1
    assert payload["summary"]["binding_follow_up_count"] == 2
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P68871"]["execution_lane"] == "structure_alignment_caveat_follow_up"
    assert rows["P04637"]["execution_lane"] == "binding_provenance_caveat_follow_up"
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_caveat_execution_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_caveat_execution_preview as exporter

    remediation_readiness, acceptance_path, remediation_queue = _sample_payloads()
    paths = {}
    for name, payload in {
        "remediation_readiness": remediation_readiness,
        "acceptance_path": acceptance_path,
        "remediation_queue": remediation_queue,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_caveat_execution_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_REMEDIATION_READINESS_PREVIEW", paths["remediation_readiness"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_ACCEPTANCE_PATH_PREVIEW", paths["acceptance_path"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_REMEDIATION_QUEUE_PREVIEW", paths["remediation_queue"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_caveat_execution_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["caveat_execution_row_count"] == 2
