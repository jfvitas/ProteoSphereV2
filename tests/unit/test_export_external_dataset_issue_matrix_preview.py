from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict]:
    assessment = {
        "artifact_id": "external_dataset_assessment_preview",
        "generated_at": "2026-04-03T22:54:18.517444+00:00",
        "summary": {
            "dataset_accession_count": 4,
            "overall_verdict": "usable_with_caveats",
        },
    }
    leakage = {
        "artifact_id": "external_dataset_leakage_audit_preview",
        "summary": {
            "duplicate_accession_count": 1,
            "cross_split_duplicates": ["A2"],
            "blocked_accessions": ["A1", "A2"],
        },
        "findings": {
            "duplicate_accessions": ["A1"],
            "cross_split_duplicates": ["A2"],
        },
        "verdict": "blocked_pending_cleanup",
    }
    modality = {
        "artifact_id": "external_dataset_modality_audit_preview",
        "summary": {
            "candidate_only_accession_count": 1,
            "missing_mapping_accession_count": 1,
            "blocked_full_packet_accession_count": 2,
        },
        "findings": {
            "candidate_only_accessions": ["A3"],
            "missing_accessions": ["A4"],
            "blocked_accessions": ["A1", "A3"],
        },
        "verdict": "blocked_pending_mapping",
    }
    binding = {
        "artifact_id": "external_dataset_binding_audit_preview",
        "summary": {
            "supported_measurement_accessions": ["A1", "A2", "A3", "A4"],
            "measurement_type_counts": {"Kd": 2, "Ki": 1},
            "complex_type_counts": {"protein_ligand": 4},
        },
        "verdict": "usable_with_caveats",
    }
    structure = {
        "artifact_id": "external_dataset_structure_audit_preview",
        "summary": {
            "seed_structure_overlap_accessions": ["A2", "A4"],
            "future_direct_grounding_candidate_count": 0,
            "future_off_target_adjacent_context_only_count": 2,
            "adjacent_target_accession_count": 1,
        },
        "findings": {"mismatch_risk": "present"},
        "verdict": "usable_with_caveats",
    }
    provenance = {
        "artifact_id": "external_dataset_provenance_audit_preview",
        "summary": {
            "library_contract_id": "contract-1",
            "contract_status": "report_only",
            "row_level_resolution_supported": True,
            "interaction_source_count": 2,
            "binding_registry_source_counts": {"pdbbind": 4, "bindingdb": 2},
        },
        "findings": {"missing_accessions": []},
        "verdict": "usable_with_caveats",
    }
    return assessment, leakage, modality, binding, structure, provenance


def test_build_issue_matrix_preview_groups_rows_by_issue_category() -> None:
    from scripts.export_external_dataset_issue_matrix_preview import (
        build_external_dataset_issue_matrix_preview,
    )

    payload = build_external_dataset_issue_matrix_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_issue_matrix_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 4
    assert payload["summary"]["issue_row_count"] == 15
    assert payload["summary"]["overall_verdict"] == "blocked_pending_cleanup"
    assert payload["compact_verdict_view"]["overall_verdict"] == "blocked_pending_cleanup"
    assert payload["summary"]["issue_category_counts"] == {
        "binding": 4,
        "leakage": 2,
        "modality": 3,
        "provenance": 4,
        "structure": 2,
    }

    leakage_rows = [row for row in payload["rows"] if row["issue_category"] == "leakage"]
    assert {row["accession"] for row in leakage_rows} == {"A1", "A2"}
    assert all(row["verdict"] == "blocked_pending_cleanup" for row in leakage_rows)

    modality_rows = [row for row in payload["rows"] if row["issue_category"] == "modality"]
    assert any(
        row["accession"] == "A4" and row["verdict"] == "blocked_pending_mapping"
        for row in modality_rows
    )
    assert any(
        row["accession"] == "A3" and row["verdict"] == "blocked_pending_acquisition"
        for row in modality_rows
    )

    grouped = {row["accession"]: row for row in payload["grouped_by_accession"]}
    assert grouped["A1"]["worst_verdict"] == "blocked_pending_cleanup"
    assert "binding" in grouped["A1"]["issue_categories"]
    assert "provenance" in grouped["A1"]["issue_categories"]

    category_grouped = {row["issue_category"]: row for row in payload["grouped_by_issue_category"]}
    assert category_grouped["structure"]["affected_accessions"] == ["A2", "A4"]
    assert category_grouped["binding"]["worst_verdict"] == "usable_with_caveats"


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_issue_matrix_preview as exporter

    assessment, leakage, modality, binding, structure, provenance = _sample_payloads()
    paths = {}
    for name, payload in {
        "assessment": assessment,
        "leakage": leakage,
        "modality": modality,
        "binding": binding,
        "structure": structure,
        "provenance": provenance,
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_issue_matrix_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_LEAKAGE_AUDIT_PREVIEW", paths["leakage"])
    monkeypatch.setattr(exporter, "DEFAULT_MODALITY_AUDIT_PREVIEW", paths["modality"])
    monkeypatch.setattr(exporter, "DEFAULT_BINDING_AUDIT_PREVIEW", paths["binding"])
    monkeypatch.setattr(exporter, "DEFAULT_STRUCTURE_AUDIT_PREVIEW", paths["structure"])
    monkeypatch.setattr(exporter, "DEFAULT_PROVENANCE_AUDIT_PREVIEW", paths["provenance"])
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_issue_matrix_preview"
    assert saved["artifact_id"] == "external_dataset_issue_matrix_preview"
    assert saved["truth_boundary"]["report_only"] is True
