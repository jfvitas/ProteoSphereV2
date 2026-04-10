from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    issue_matrix = {
        "artifact_id": "external_dataset_issue_matrix_preview",
        "generated_at": "2026-04-03T23:58:00+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_cleanup",
            "issue_category_counts": {
                "leakage": 2,
                "modality": 5,
                "binding": 12,
                "provenance": 12,
                "structure": 2,
            },
        },
        "grouped_by_issue_category": [
            {
                "issue_category": "leakage",
                "issue_row_count": 2,
                "affected_accessions": ["A1", "A2"],
                "worst_verdict": "blocked_pending_cleanup",
                "remediation_action": "remove duplicate or cross-split rows before training",
            },
            {
                "issue_category": "modality",
                "issue_row_count": 5,
                "affected_accessions": ["A1", "A2", "A3", "A4", "A5"],
                "worst_verdict": "blocked_pending_mapping",
                "remediation_action": "resolve mapping or acquisition blockers before training",
            },
            {
                "issue_category": "binding",
                "issue_row_count": 12,
                "affected_accessions": ["A1", "A2"],
                "worst_verdict": "usable_with_caveats",
                "remediation_action": (
                    "keep binding rows support-only until case-specific validation passes"
                ),
            },
            {
                "issue_category": "provenance",
                "issue_row_count": 12,
                "affected_accessions": ["A1", "A2"],
                "worst_verdict": "usable_with_caveats",
                "remediation_action": (
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ),
            },
            {
                "issue_category": "structure",
                "issue_row_count": 2,
                "affected_accessions": ["A2", "A4"],
                "worst_verdict": "usable_with_caveats",
                "remediation_action": (
                    "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                ),
            },
        ],
        "rows": [
            {
                "accession": "A1",
                "issue_category": "leakage",
                "verdict": "blocked_pending_cleanup",
                "severity": "high",
                "issue_summary": "Duplicate accession appears in the external dataset.",
                "remediation_action": (
                    "remove duplicate or cross-split rows before training"
                ),
                "source_artifacts": ["external_dataset_leakage_audit_preview"],
            },
            {
                "accession": "A2",
                "issue_category": "modality",
                "verdict": "blocked_pending_mapping",
                "severity": "high",
                "issue_summary": "Accession is missing mapping coverage needed for training.",
                "remediation_action": (
                    "resolve mapping or acquisition blockers before training"
                ),
                "source_artifacts": ["external_dataset_modality_audit_preview"],
            },
            {
                "accession": "A3",
                "issue_category": "binding",
                "verdict": "usable_with_caveats",
                "severity": "low",
                "issue_summary": "Accession has binding coverage in the current preview.",
                "remediation_action": (
                    "keep binding rows support-only until case-specific validation passes"
                ),
                "source_artifacts": ["external_dataset_binding_audit_preview"],
            },
        ],
    }
    risk_register = {
        "artifact_id": "external_dataset_risk_register_preview",
        "generated_at": "2026-04-03T23:58:00+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "blocked_pending_acquisition",
            "blocked_gate_count": 1,
            "patent_or_provenance_risk_present": True,
            "mapping_risk_present": True,
            "top_risk_row_count": 2,
            "blocked_accession_count": 5,
            "caveated_accession_count": 7,
            "resolved_accession_count": 0,
        },
        "top_risk_rows": [
            {
                "accession": "A1",
                "issue_category": "modality",
                "priority_bucket": "p0_blocker",
                "blocking_gate": "modality",
                "worst_verdict": "blocked_pending_acquisition",
                "remediation_action": (
                    "resolve mapping or acquisition blockers before training"
                ),
                "supporting_artifacts": ["external_dataset_modality_audit_preview"],
            },
            {
                "accession": "A2",
                "issue_category": "provenance",
                "priority_bucket": "p0_blocker",
                "blocking_gate": "provenance",
                "worst_verdict": "blocked_pending_acquisition",
                "remediation_action": (
                    "keep provenance explicit and avoid collapsing mixed trust tiers"
                ),
                "supporting_artifacts": ["external_dataset_provenance_audit_preview"],
            },
        ],
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
        },
    }
    binding_audit = {
        "artifact_id": "external_dataset_binding_audit_preview",
        "verdict": "usable_with_caveats",
        "summary": {"measured_accession_count": 12},
    }
    structure_audit = {
        "artifact_id": "external_dataset_structure_audit_preview",
        "verdict": "usable_with_caveats",
        "summary": {
            "seed_structure_overlap_accession_count": 2,
            "future_off_target_adjacent_context_only_count": 8,
        },
    }
    provenance_audit = {
        "artifact_id": "external_dataset_provenance_audit_preview",
        "verdict": "usable_with_caveats",
        "summary": {
            "binding_registry_source_counts": {"pdbbind": 1, "bindingdb": 2},
            "contract_status": "report_only",
        },
    }
    resolution = {
        "artifact_id": "external_dataset_resolution_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_resolution_verdict": "blocked_pending_acquisition",
            "blocked_accession_count": 5,
            "caveated_accession_count": 7,
        },
    }
    return (
        issue_matrix,
        risk_register,
        flaw_taxonomy,
        binding_audit,
        structure_audit,
        provenance_audit,
        resolution,
    )


def test_build_conflict_register_preview_compacts_fail_closed() -> None:
    from scripts.export_external_dataset_conflict_register_preview import (
        build_external_dataset_conflict_register_preview,
    )

    payload = build_external_dataset_conflict_register_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_conflict_register_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["overall_verdict"] == "blocked_pending_cleanup"
    assert payload["summary"]["conflict_category_counts"] == {
        "binding": 12,
        "leakage": 2,
        "modality": 5,
        "provenance": 12,
        "structure": 2,
    }
    assert payload["summary"]["mapping_conflict_present"] is True
    assert payload["summary"]["provenance_conflict_present"] is True
    assert payload["summary"]["non_mutating"] is True
    assert payload["truth_boundary"]["fail_closed"] is True
    assert len(payload["top_conflict_rows"]) == 3
    assert payload["top_conflict_rows"][0]["accession"] == "A1"
    assert payload["top_conflict_rows"][0]["issue_category"] == "leakage"
    assert payload["summary"]["top_conflict_categories"][0]["issue_category"] == "binding"


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_conflict_register_preview as exporter

    (
        issue_matrix,
        risk_register,
        flaw_taxonomy,
        binding_audit,
        structure_audit,
        provenance_audit,
        resolution,
    ) = _sample_payloads()
    paths = {}
    for name, payload in {
        "issue_matrix": issue_matrix,
        "risk_register": risk_register,
        "flaw_taxonomy": flaw_taxonomy,
        "binding": binding_audit,
        "structure": structure_audit,
        "provenance": provenance_audit,
        "resolution": resolution,
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_conflict_register_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ISSUE_MATRIX_PREVIEW", paths["issue_matrix"])
    monkeypatch.setattr(exporter, "DEFAULT_RISK_REGISTER_PREVIEW", paths["risk_register"])
    monkeypatch.setattr(exporter, "DEFAULT_FLAW_TAXONOMY_PREVIEW", paths["flaw_taxonomy"])
    monkeypatch.setattr(exporter, "DEFAULT_BINDING_AUDIT_PREVIEW", paths["binding"])
    monkeypatch.setattr(exporter, "DEFAULT_STRUCTURE_AUDIT_PREVIEW", paths["structure"])
    monkeypatch.setattr(exporter, "DEFAULT_PROVENANCE_AUDIT_PREVIEW", paths["provenance"])
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_conflict_register_preview"
    assert saved["artifact_id"] == "external_dataset_conflict_register_preview"
    assert saved["summary"]["non_mutating"] is True
