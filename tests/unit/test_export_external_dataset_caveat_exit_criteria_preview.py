from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict, dict]:
    advisory = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"dataset_accession_count": 4},
        "rows": [
            {
                "accession": "P68871",
                "advisory_followup_state": "advisory_follow_up_required",
                "followup_lane": "structure_alignment_advisory_follow_up",
                "priority_bucket": "p1_follow_up",
                "issue_categories": ["binding", "structure"],
                "remediation_actions": [
                    "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                ],
            },
            {
                "accession": "P04637",
                "advisory_followup_state": "advisory_follow_up_required",
                "followup_lane": "binding_provenance_advisory_follow_up",
                "priority_bucket": "p2_support_context",
                "issue_categories": ["binding", "provenance"],
                "remediation_actions": [
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ],
            },
        ],
    }
    acceptance_path = {
        "rows": [
            {
                "accession": "P68871",
                "acceptance_path_state": "caveated",
                "blocking_gates": ["structure"],
            },
            {
                "accession": "P04637",
                "acceptance_path_state": "caveated",
                "blocking_gates": [],
            },
        ]
    }
    resolution = {
        "accession_resolution_rows": [
            {"accession": "P68871", "resolution_state": "caveated"},
            {"accession": "P04637", "resolution_state": "caveated"},
        ]
    }
    acceptance_gate = {
        "summary": {
            "training_safe_acceptance": {
                "must_clear": [
                    {
                        "clear_condition": (
                            "clear the blocked category rows before claiming "
                            "training-safe acceptance"
                        )
                    }
                ]
            }
        },
        "gate_reports": [
            {
                "gate_name": "issue_matrix",
                "verdict": "blocked_pending_acquisition",
            }
        ],
    }
    return advisory, acceptance_path, resolution, acceptance_gate


def test_build_external_dataset_caveat_exit_criteria_preview() -> None:
    from scripts.export_external_dataset_caveat_exit_criteria_preview import (
        build_external_dataset_caveat_exit_criteria_preview,
    )

    payload = build_external_dataset_caveat_exit_criteria_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_caveat_exit_criteria_preview"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["caveat_exit_row_count"] == 2
    assert payload["summary"]["current_exit_state"] == "caveat_exit_criteria_active"
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P68871"]["caveat_exit_state"] == (
        "caveated_pending_structure_alignment_review"
    )
    assert rows["P04637"]["caveat_exit_state"] == (
        "caveated_pending_binding_provenance_review"
    )
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_caveat_exit_criteria_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_caveat_exit_criteria_preview as exporter

    advisory, acceptance_path, resolution, acceptance_gate = _sample_payloads()
    paths = {}
    for name, payload in {
        "advisory": advisory,
        "acceptance_path": acceptance_path,
        "resolution": resolution,
        "acceptance_gate": acceptance_gate,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_caveat_exit_criteria_preview.json"
    monkeypatch.setattr(
        exporter,
        "DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW",
        paths["advisory"],
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_ACCEPTANCE_PATH_PREVIEW", paths["acceptance_path"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(
        exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_caveat_exit_criteria_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["caveat_exit_row_count"] == 2
