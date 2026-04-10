from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict]:
    assessment = {
        "artifact_id": "external_dataset_assessment_preview",
        "generated_at": "2026-04-03T23:58:04.794745+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "usable_with_caveats",
            "missing_mapping_accession_count": 5,
            "candidate_only_accession_count": 7,
            "measured_accession_count": 6,
            "seed_structure_overlap_accession_count": 1,
        },
    }
    admission = {
        "artifact_id": "external_dataset_admission_decision_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_decision": "blocked",
            "overall_verdict": "blocked_pending_cleanup",
            "blocking_gate_count": 1,
            "decision_reasons": [
                "1 blocking gate(s) remain",
                "overall verdict is blocked_pending_cleanup",
            ],
            "top_required_remediations": [
                "remove duplicate or cross-split rows before training",
                "resolve mapping or acquisition blockers before training",
            ],
            "advisory_only": True,
            "non_mutating": True,
        },
    }
    acceptance = {
        "artifact_id": "external_dataset_acceptance_gate_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_gate_verdict": "blocked_pending_acquisition",
            "blocked_gate_count": 1,
            "usable_with_caveats_gate_count": 7,
            "top_remediation_categories": [
                {
                    "issue_category": "modality",
                    "affected_accession_count": 5,
                    "worst_verdict": "blocked_pending_acquisition",
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
            "training_safe_acceptance": {
                "must_clear": [
                    {
                        "gate_name": "modality",
                        "verdict": "blocked_pending_acquisition",
                        "impacted_accession_count": 5,
                        "clear_condition": (
                            "resolve mapping or acquisition blockers before training"
                        ),
                    }
                ],
                "must_remain_non_governing_or_be_formally_rescoped": [],
            },
        },
    }
    resolution = {
        "artifact_id": "external_dataset_resolution_preview",
        "generated_at": "2026-04-03T23:58:04.794745+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_resolution_verdict": "blocked_pending_acquisition",
            "blocked_gate_count": 1,
            "blocked_accession_count": 5,
            "caveated_accession_count": 7,
            "resolved_accession_count": 0,
            "mapping_incomplete_accession_count": 5,
            "top_blocking_gates": [
                {
                    "gate_name": "modality",
                    "affected_accession_count": 5,
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
            "top_issue_categories": [
                {
                    "issue_category": "modality",
                    "affected_accession_count": 5,
                    "resolution_state": "blocked",
                    "worst_verdict": "blocked_pending_acquisition",
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
        },
    }
    conflict = {
        "artifact_id": "external_dataset_conflict_register_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_cleanup",
            "blocked_gate_count": 1,
            "mapping_conflict_present": True,
            "provenance_conflict_present": True,
            "top_conflict_rows": [
                {
                    "accession": "A1",
                    "issue_category": "leakage",
                    "verdict": "blocked_pending_cleanup",
                    "severity": "high",
                    "issue_summary": "Duplicate accession appears in the external dataset.",
                    "remediation_action": "remove duplicate or cross-split rows before training",
                }
            ],
            "top_conflict_categories": [
                {
                    "issue_category": "leakage",
                    "issue_row_count": 2,
                    "affected_accessions": ["A1", "A2"],
                    "worst_verdict": "blocked_pending_cleanup",
                    "remediation_action": "remove duplicate or cross-split rows before training",
                }
            ],
        },
    }
    flaw = {
        "artifact_id": "external_dataset_flaw_taxonomy_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_acquisition",
            "blocking_category_counts": {"modality": 5},
            "category_counts": {"modality": 5, "binding": 12},
            "top_blocking_categories": [
                {
                    "category": "modality",
                    "affected_accession_count": 5,
                    "resolution_state": "blocked",
                    "worst_verdict": "blocked_pending_acquisition",
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
            "remediation_priority_categories": [
                {
                    "category": "modality",
                    "affected_accession_count": 5,
                    "worst_verdict": "blocked_pending_acquisition",
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
            "blocked_accession_count": 5,
            "caveated_accession_count": 7,
            "resolved_accession_count": 0,
            "missing_required_field_count": 0,
        },
    }
    return assessment, admission, acceptance, resolution, conflict, flaw


def test_build_clearance_delta_preview_compacts_required_changes() -> None:
    from scripts.export_external_dataset_clearance_delta_preview import (
        build_external_dataset_clearance_delta_preview,
    )

    payload = build_external_dataset_clearance_delta_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_clearance_delta_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["current_clearance_state"] == "blocked"
    assert payload["summary"]["current_clearance_verdict"] == "blocked_pending_cleanup"
    assert payload["summary"]["blocking_gate_count"] == 1
    assert payload["summary"]["advisory_only"] is True
    assert payload["summary"]["non_mutating"] is True
    assert payload["summary"]["fail_closed"] is True
    assert payload["summary"]["required_change_count"] >= 3
    assert "remove duplicate or cross-split rows before training" in payload["summary"][
        "required_changes"
    ]
    assert "resolve mapping or acquisition blockers before training" in payload["summary"][
        "required_changes"
    ]
    assert any(
        row["source"] == "acceptance" and row["delta_state"] == "blocked"
        for row in payload["clearance_delta_rows"]
    )
    assert any(
        row["source"] == "flaw" and row["impacted_accession_count"] == 12
        for row in payload["clearance_delta_rows"]
    )
    assert payload["truth_boundary"]["fail_closed"] is True


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_clearance_delta_preview as exporter

    assessment, admission, acceptance, resolution, conflict, flaw = _sample_payloads()
    paths = {}
    for name, payload in {
        "assessment": assessment,
        "admission": admission,
        "acceptance": acceptance,
        "resolution": resolution,
        "conflict": conflict,
        "flaw": flaw,
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_clearance_delta_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_ADMISSION_DECISION_PREVIEW", paths["admission"])
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance"])
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_CONFLICT_REGISTER_PREVIEW", paths["conflict"])
    monkeypatch.setattr(exporter, "DEFAULT_FLAW_TAXONOMY_PREVIEW", paths["flaw"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_clearance_delta_preview"
    assert saved["artifact_id"] == "external_dataset_clearance_delta_preview"
    assert saved["summary"]["non_mutating"] is True
