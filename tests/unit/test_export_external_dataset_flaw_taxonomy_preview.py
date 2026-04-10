from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    assessment = {
        "artifact_id": "external_dataset_assessment_preview",
        "generated_at": "2026-04-03T23:38:04.794745+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_verdict": "usable_with_caveats",
        },
    }
    remediation_queue = {
        "artifact_id": "external_dataset_remediation_queue_preview",
        "generated_at": "2026-04-03T23:38:04.794745+00:00",
        "summary": {
            "dataset_accession_count": 12,
            "overall_queue_verdict": "blocked_pending_acquisition",
            "blocked_accession_count": 5,
        },
    }
    resolution = {
        "artifact_id": "external_dataset_resolution_preview",
        "summary": {
            "dataset_accession_count": 12,
            "overall_resolution_verdict": "blocked_pending_acquisition",
            "resolved_accession_count": 0,
            "caveated_accession_count": 7,
            "blocked_accession_count": 5,
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
                },
                {
                    "issue_category": "binding",
                    "affected_accession_count": 12,
                    "resolution_state": "caveated",
                    "worst_verdict": "usable_with_caveats",
                    "remediation_action": (
                        "keep binding rows support-only until case-specific validation passes"
                    ),
                },
                {
                    "issue_category": "provenance",
                    "affected_accession_count": 12,
                    "resolution_state": "caveated",
                    "worst_verdict": "usable_with_caveats",
                    "remediation_action": (
                        "keep provenance explicit and avoid collapsing mixed trust tiers"
                    ),
                },
                {
                    "issue_category": "structure",
                    "affected_accession_count": 2,
                    "resolution_state": "caveated",
                    "worst_verdict": "usable_with_caveats",
                    "remediation_action": (
                        "preserve PDB-to-UniProt alignment and keep adjacent context separate"
                    ),
                },
            ],
        },
        "issue_resolution_rows": [
            {
                "issue_category": "modality",
                "resolution_state": "blocked",
                "worst_verdict": "blocked_pending_acquisition",
                "affected_accessions": ["P00387", "P09105", "Q2TAC2", "Q9NZD4", "Q9UCM0"],
                "blocking_gates": ["modality"],
                "remediation_actions": ["resolve mapping or acquisition blockers before training"],
            },
            {
                "issue_category": "binding",
                "resolution_state": "caveated",
                "worst_verdict": "usable_with_caveats",
                "affected_accessions": [
                    "P00387",
                    "P02042",
                    "P02100",
                    "P04637",
                    "P09105",
                    "P31749",
                    "P68871",
                    "P69892",
                    "P69905",
                    "Q2TAC2",
                    "Q9NZD4",
                    "Q9UCM0",
                ],
                "blocking_gates": [],
                "remediation_actions": [
                    "keep binding rows support-only until case-specific validation passes"
                ],
            },
        ],
    }
    acceptance_gate = {
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
        },
        "gate_reports": [
            {
                "gate_name": "issue_matrix",
                "verdict": "blocked_pending_acquisition",
                "impact": {"impacted_accession_count": 5},
            }
        ],
    }
    manifest_lint = {
        "artifact_id": "external_dataset_manifest_lint_preview",
        "summary": {
            "accepted_shape_count": 2,
            "missing_required_field_count": 0,
            "missing_required_top_level_field_count": 0,
            "missing_required_row_field_count": 0,
            "overall_verdict": "usable_with_caveats",
        },
        "per_shape_verdicts": [
            {"shape_id": "json_manifest", "verdict": "usable_with_caveats"},
            {"shape_id": "folder_package_manifest", "verdict": "usable_with_caveats"},
        ],
    }
    binding = {
        "artifact_id": "external_dataset_binding_audit_preview",
        "status": "attention_needed",
        "summary": {
            "measured_accession_count": 12,
            "measurement_type_counts": {"Kd": 11013, "Ki": 5205, "IC50": 11917, "EC50": 28},
            "complex_type_counts": {
                "protein_ligand": 24211,
                "protein_protein": 2798,
                "protein_nucleic_acid": 1032,
                "nucleic_acid_ligand": 143,
            },
        },
        "verdict": "usable_with_caveats",
    }
    structure = {
        "artifact_id": "external_dataset_structure_audit_preview",
        "status": "attention_needed",
        "summary": {
            "seed_structure_overlap_accession_count": 2,
            "seed_structure_overlap_accessions": ["P68871", "P69905"],
            "future_direct_grounding_candidate_count": 0,
            "future_off_target_adjacent_context_only_count": 8,
            "adjacent_target_accession_count": 2,
        },
        "findings": {"mismatch_risk": "present"},
        "verdict": "usable_with_caveats",
    }
    provenance = {
        "artifact_id": "external_dataset_provenance_audit_preview",
        "status": "attention_needed",
        "summary": {
            "library_contract_id": "p50_training_set_creator_library_contract",
            "contract_status": "report_only",
            "row_level_resolution_supported": True,
            "interaction_source_count": None,
            "binding_registry_source_counts": {
                "pdbbind": 23010,
                "chembl_lightweight": 24,
                "bindingdb": 5150,
            },
        },
        "findings": {"missing_accessions": []},
        "verdict": "usable_with_caveats",
    }
    return (
        assessment,
        remediation_queue,
        resolution,
        acceptance_gate,
        manifest_lint,
        binding,
        structure,
        provenance,
    )


def test_build_flaw_taxonomy_preview_summarizes_categories_and_fail_closed() -> None:
    from scripts.export_external_dataset_flaw_taxonomy_preview import (
        build_external_dataset_flaw_taxonomy_preview,
    )

    payload = build_external_dataset_flaw_taxonomy_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_flaw_taxonomy_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["category_counts"] == {
        "binding": 12,
        "modality": 5,
        "provenance": 12,
        "structure": 2,
    }
    assert payload["summary"]["blocking_category_counts"] == {"modality": 5}
    assert payload["summary"]["resolved_category_counts"] == {
        "binding": 12,
        "provenance": 12,
        "structure": 2,
    }
    assert payload["summary"]["worst_verdict"] == "blocked_pending_acquisition"
    assert payload["summary"]["lint_failures_present"] is False
    assert payload["summary"]["non_mutating"] is True
    assert payload["truth_boundary"]["fail_closed"] is True

    top_blocking = payload["summary"]["top_blocking_categories"]
    assert top_blocking[0]["category"] == "modality"
    assert top_blocking[0]["affected_accession_count"] == 5

    categories = {row["category"]: row for row in payload["category_rows"]}
    assert categories["modality"]["resolution_state"] == "blocked"
    assert categories["binding"]["worst_verdict"] == "usable_with_caveats"


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_flaw_taxonomy_preview as exporter

    payloads = _sample_payloads()
    paths = {}
    for name, payload in {
        "assessment": payloads[0],
        "remediation_queue": payloads[1],
        "resolution": payloads[2],
        "acceptance_gate": payloads[3],
        "manifest_lint": payloads[4],
        "binding": payloads[5],
        "structure": payloads[6],
        "provenance": payloads[7],
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_flaw_taxonomy_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_REMEDIATION_QUEUE_PREVIEW", paths["remediation_queue"])
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"])
    monkeypatch.setattr(exporter, "DEFAULT_MANIFEST_LINT_PREVIEW", paths["manifest_lint"])
    monkeypatch.setattr(exporter, "DEFAULT_BINDING_AUDIT_PREVIEW", paths["binding"])
    monkeypatch.setattr(exporter, "DEFAULT_STRUCTURE_AUDIT_PREVIEW", paths["structure"])
    monkeypatch.setattr(exporter, "DEFAULT_PROVENANCE_AUDIT_PREVIEW", paths["provenance"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_flaw_taxonomy_preview"
    assert saved["artifact_id"] == "external_dataset_flaw_taxonomy_preview"
    assert saved["truth_boundary"]["non_mutating"] is True
