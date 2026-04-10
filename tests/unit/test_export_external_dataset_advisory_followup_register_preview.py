from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    caveat = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"dataset_accession_count": 4},
        "rows": [
            {
                "accession": "P68871",
                "execution_lane": "structure_alignment_caveat_follow_up",
                "priority_bucket": "p1_follow_up",
                "acceptance_path_state": "caveated",
                "resolution_state": "caveated",
                "issue_categories": ["binding", "structure"],
                "remediation_actions": [
                    "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                ],
                "next_execution_step": "preserve_structure_alignment_caveat",
                "queue_row_count": 3,
            },
            {
                "accession": "P04637",
                "execution_lane": "binding_provenance_caveat_follow_up",
                "priority_bucket": "p2_support_context",
                "acceptance_path_state": "caveated",
                "resolution_state": "caveated",
                "issue_categories": ["binding", "provenance"],
                "remediation_actions": [
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ],
                "next_execution_step": "preserve_binding_and_provenance_caveats",
                "queue_row_count": 2,
            },
        ],
    }
    resolution = {
        "accession_resolution_rows": [
            {"accession": "P68871", "resolution_state": "caveated"},
            {"accession": "P04637", "resolution_state": "caveated"},
        ]
    }
    risk = {
        "top_risk_rows": [
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
        ]
    }
    return caveat, resolution, risk


def test_build_external_dataset_advisory_followup_register_preview() -> None:
    from scripts.export_external_dataset_advisory_followup_register_preview import (
        build_external_dataset_advisory_followup_register_preview,
    )

    payload = build_external_dataset_advisory_followup_register_preview(
        *_sample_payloads()
    )

    assert payload["artifact_id"] == "external_dataset_advisory_followup_register_preview"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["advisory_followup_row_count"] == 2
    assert payload["summary"]["current_followup_state"] == (
        "advisory_follow_up_register_active"
    )
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P68871"]["followup_lane"] == "structure_alignment_advisory_follow_up"
    assert rows["P04637"]["followup_lane"] == "binding_provenance_advisory_follow_up"
    assert payload["truth_boundary"]["training_safe_acceptance_not_implied"] is True


def test_main_writes_external_dataset_advisory_followup_register_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_external_dataset_advisory_followup_register_preview as exporter

    caveat, resolution, risk = _sample_payloads()
    paths = {}
    for name, payload in {
        "caveat": caveat,
        "resolution": resolution,
        "risk": risk,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "external_dataset_advisory_followup_register_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_CAVEAT_EXECUTION_PREVIEW", paths["caveat"])
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_RISK_REGISTER_PREVIEW", paths["risk"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "external_dataset_advisory_followup_register_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["advisory_followup_row_count"] == 2
