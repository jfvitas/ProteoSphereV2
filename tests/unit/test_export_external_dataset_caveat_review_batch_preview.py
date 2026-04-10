from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict]:
    exit_criteria = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"dataset_accession_count": 4},
        "rows": [
            {
                "accession": "P68871",
                "followup_lane": "structure_alignment_advisory_follow_up",
                "caveat_exit_state": "caveated_pending_structure_alignment_review",
                "allowed_current_use": "advisory_only_structure_context",
                "next_review_action": (
                    "recheck PDB-to-UniProt alignment and adjacent-context separation"
                ),
                "issue_categories": ["binding", "structure"],
                "priority_bucket": "p1_follow_up",
            },
            {
                "accession": "P04637",
                "followup_lane": "binding_provenance_advisory_follow_up",
                "caveat_exit_state": "caveated_pending_binding_provenance_review",
                "allowed_current_use": "advisory_only_binding_support_context",
                "next_review_action": (
                    "recheck binding and provenance caveats before any escalation"
                ),
                "issue_categories": ["binding", "provenance"],
                "priority_bucket": "p2_support_context",
            },
        ],
    }
    advisory = {
        "summary": {"dataset_accession_count": 4},
        "rows": [
            {"accession": "P68871", "followup_lane": "structure_alignment_advisory_follow_up"},
            {"accession": "P04637", "followup_lane": "binding_provenance_advisory_follow_up"},
        ],
    }
    return exit_criteria, advisory


def test_build_external_dataset_caveat_review_batch_preview() -> None:
    from scripts.export_external_dataset_caveat_review_batch_preview import (
        build_external_dataset_caveat_review_batch_preview,
    )

    payload = build_external_dataset_caveat_review_batch_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_caveat_review_batch_preview"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["review_batch_row_count"] == 2
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P68871"]["review_batch"] == "structure_alignment_review_batch"
    assert rows["P04637"]["review_batch"] == "binding_provenance_review_batch"


def test_main_writes_external_dataset_caveat_review_batch_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_caveat_review_batch_preview as exporter

    exit_criteria, advisory = _sample_payloads()
    exit_path = tmp_path / "exit.json"
    advisory_path = tmp_path / "advisory.json"
    _write_json(exit_path, exit_criteria)
    _write_json(advisory_path, advisory)
    output_json = tmp_path / "external_dataset_caveat_review_batch_preview.json"

    monkeypatch.setattr(exporter, "DEFAULT_CAVEAT_EXIT_CRITERIA_PREVIEW", exit_path)
    monkeypatch.setattr(
        exporter, "DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW", advisory_path
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_caveat_review_batch_preview"
    assert output_json.exists()
