from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    assessment = {
        "artifact_id": "external_dataset_assessment_preview",
        "generated_at": "2026-04-03T23:38:04.794745+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "usable_with_caveats",
            "missing_mapping_accession_count": 5,
        },
    }
    flaw_taxonomy = {
        "artifact_id": "external_dataset_flaw_taxonomy_preview",
        "generated_at": "2026-04-03T23:38:04.794745+00:00",
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
            "resolved_category_counts": {
                "binding": 12,
                "provenance": 12,
                "structure": 2,
            },
            "top_blocking_categories": [
                {
                    "category": "modality",
                    "affected_accession_count": 5,
                    "resolution_state": "blocked",
                    "worst_verdict": "blocked_pending_acquisition",
                    "remediation_action": "resolve mapping or acquisition blockers before training",
                }
            ],
            "blocked_accession_count": 5,
            "caveated_accession_count": 7,
            "resolved_accession_count": 0,
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
    provenance = {
        "artifact_id": "external_dataset_provenance_audit_preview",
        "summary": {
            "binding_registry_source_counts": {
                "pdbbind": 23010,
                "chembl_lightweight": 24,
                "bindingdb": 5150,
            },
        },
        "verdict": "usable_with_caveats",
    }
    binding = {
        "artifact_id": "external_dataset_binding_audit_preview",
        "summary": {
            "measured_accession_count": 12,
        },
        "verdict": "usable_with_caveats",
    }
    structure = {
        "artifact_id": "external_dataset_structure_audit_preview",
        "summary": {
            "seed_structure_overlap_accession_count": 2,
            "future_off_target_adjacent_context_only_count": 8,
        },
        "verdict": "usable_with_caveats",
    }
    remediation = {
        "artifact_id": "external_dataset_remediation_queue_preview",
        "generated_at": "2026-04-03T23:38:04.794745+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_queue_verdict": "blocked_pending_acquisition",
            "blocked_accession_count": 5,
        },
        "rows": [
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
    return assessment, flaw_taxonomy, acceptance_gate, provenance, binding, structure, remediation


def test_build_risk_register_preview_compacts_fail_closed() -> None:
    from scripts.export_external_dataset_risk_register_preview import (
        build_external_dataset_risk_register_preview,
    )

    payload = build_external_dataset_risk_register_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_risk_register_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["overall_verdict"] == "blocked_pending_acquisition"
    assert payload["summary"]["risk_category_counts"] == {
        "binding": 12,
        "modality": 5,
        "provenance": 12,
        "structure": 2,
    }
    assert payload["summary"]["blocked_gate_count"] == 1
    assert payload["summary"]["patent_or_provenance_risk_present"] is True
    assert payload["summary"]["mapping_risk_present"] is True
    assert payload["summary"]["non_mutating"] is True
    assert payload["truth_boundary"]["fail_closed"] is True
    assert len(payload["top_risk_rows"]) == 2
    assert payload["top_risk_rows"][0]["accession"] == "P09105"
    assert payload["top_risk_rows"][0]["issue_category"] == "modality"
    assert payload["summary"]["highest_risk_categories"][0]["category"] == "modality"


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_risk_register_preview as exporter

    payloads = _sample_payloads()
    names = (
        "assessment",
        "flaw_taxonomy",
        "acceptance_gate",
        "provenance",
        "binding",
        "structure",
        "remediation_queue",
    )
    paths = {}
    for name, payload in zip(names, payloads, strict=True):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_risk_register_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_FLAW_TAXONOMY_PREVIEW", paths["flaw_taxonomy"])
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"])
    monkeypatch.setattr(exporter, "DEFAULT_PROVENANCE_AUDIT_PREVIEW", paths["provenance"])
    monkeypatch.setattr(exporter, "DEFAULT_BINDING_AUDIT_PREVIEW", paths["binding"])
    monkeypatch.setattr(exporter, "DEFAULT_STRUCTURE_AUDIT_PREVIEW", paths["structure"])
    monkeypatch.setattr(exporter, "DEFAULT_REMEDIATION_QUEUE_PREVIEW", paths["remediation_queue"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_risk_register_preview"
    assert saved["artifact_id"] == "external_dataset_risk_register_preview"
    assert saved["summary"]["non_mutating"] is True
