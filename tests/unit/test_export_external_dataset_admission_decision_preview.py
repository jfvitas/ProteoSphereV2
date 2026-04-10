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
        },
    }
    acceptance_gate = {
        "artifact_id": "external_dataset_acceptance_gate_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_gate_verdict": "blocked_pending_acquisition",
            "blocked_gate_count": 1,
            "usable_with_caveats_gate_count": 7,
        },
    }
    flaw_taxonomy = {
        "artifact_id": "external_dataset_flaw_taxonomy_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_acquisition",
            "category_counts": {
                "modality": 5,
                "binding": 12,
                "provenance": 12,
                "structure": 2,
            },
            "blocking_category_counts": {"modality": 5},
            "top_blocking_categories": [
                {
                    "category": "modality",
                    "affected_accession_count": 5,
                    "resolution_state": "blocked",
                    "worst_verdict": "blocked_pending_acquisition",
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
        },
    }
    risk_register = {
        "artifact_id": "external_dataset_risk_register_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_acquisition",
            "blocked_gate_count": 1,
            "patent_or_provenance_risk_present": True,
            "mapping_risk_present": True,
            "blocked_accession_count": 5,
            "caveated_accession_count": 7,
            "resolved_accession_count": 0,
        },
        "top_risk_rows": [
            {
                "accession": "P09105",
                "issue_category": "modality",
                "priority_bucket": "p0_blocker",
                "blocking_gate": "modality",
                "worst_verdict": "blocked_pending_acquisition",
                "remediation_action": "resolve mapping or acquisition blockers before training",
                "supporting_artifacts": ["external_dataset_flaw_taxonomy_preview"],
            },
            {
                "accession": "P04637",
                "issue_category": "structure",
                "priority_bucket": "p1_follow_up",
                "blocking_gate": "structure",
                "worst_verdict": "usable_with_caveats",
                "remediation_action": (
                    "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                ),
                "supporting_artifacts": ["external_dataset_structure_audit_preview"],
            },
        ],
    }
    conflict_register = {
        "artifact_id": "external_dataset_conflict_register_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_cleanup",
            "blocked_gate_count": 1,
            "mapping_conflict_present": True,
            "provenance_conflict_present": True,
        },
        "top_conflict_rows": [
            {
                "accession": "A1",
                "issue_category": "leakage",
                "verdict": "blocked_pending_cleanup",
                "severity": "high",
                "issue_summary": "Duplicate accession appears in the external dataset.",
                "remediation_action": "remove duplicate or cross-split rows before training",
                "source_artifacts": ["external_dataset_leakage_audit_preview"],
            },
            {
                "accession": "A2",
                "issue_category": "provenance",
                "verdict": "blocked_pending_mapping",
                "severity": "high",
                "issue_summary": "Provenance conflict should remain explicit.",
                "remediation_action": (
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ),
                "source_artifacts": ["external_dataset_provenance_audit_preview"],
            },
        ],
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
        },
        "top_required_remediations": [
            "remove duplicate or cross-split rows before training",
            "resolve mapping or acquisition blockers before training",
        ],
    }
    return assessment, acceptance_gate, flaw_taxonomy, risk_register, conflict_register, resolution


def test_build_admission_decision_preview_compacts_fail_closed() -> None:
    from scripts.export_external_dataset_admission_decision_preview import (
        build_external_dataset_admission_decision_preview,
    )

    payload = build_external_dataset_admission_decision_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_admission_decision_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["overall_decision"] == "blocked"
    assert payload["summary"]["overall_verdict"] == "blocked_pending_cleanup"
    assert payload["summary"]["blocking_gate_count"] == 1
    assert payload["summary"]["advisory_only"] is True
    assert payload["summary"]["non_mutating"] is True
    assert payload["truth_boundary"]["fail_closed"] is True
    assert payload["summary"]["decision_reasons"][0] == "1 blocking gate(s) remain"
    assert any(
        "blocking flaw categories" in reason for reason in payload["summary"]["decision_reasons"]
    )
    assert "remove duplicate or cross-split rows before training" in payload["summary"][
        "top_required_remediations"
    ]
    assert "resolve mapping or acquisition blockers before training" in payload["summary"][
        "top_required_remediations"
    ]
    assert "keep provenance explicit and avoid collapsing mixed trust tiers" in payload["summary"][
        "top_required_remediations"
    ]


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_admission_decision_preview as exporter

    (
        assessment,
        acceptance_gate,
        flaw_taxonomy,
        risk_register,
        conflict_register,
        resolution,
    ) = _sample_payloads()
    paths = {}
    for name, payload in {
        "assessment": assessment,
        "acceptance_gate": acceptance_gate,
        "flaw_taxonomy": flaw_taxonomy,
        "risk_register": risk_register,
        "conflict_register": conflict_register,
        "resolution": resolution,
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_admission_decision_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"])
    monkeypatch.setattr(exporter, "DEFAULT_FLAW_TAXONOMY_PREVIEW", paths["flaw_taxonomy"])
    monkeypatch.setattr(exporter, "DEFAULT_RISK_REGISTER_PREVIEW", paths["risk_register"])
    monkeypatch.setattr(exporter, "DEFAULT_CONFLICT_REGISTER_PREVIEW", paths["conflict_register"])
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_admission_decision_preview"
    assert saved["artifact_id"] == "external_dataset_admission_decision_preview"
    assert saved["summary"]["non_mutating"] is True
