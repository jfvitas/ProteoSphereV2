from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    repo_root = Path(__file__).resolve().parents[2]
    paths = [
        repo_root / "artifacts" / "status" / "external_dataset_assessment_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_leakage_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_modality_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_binding_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_structure_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json",
    ]
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)  # type: ignore[return-value]


def test_build_resolution_preview_uses_current_artifacts() -> None:
    from scripts.export_external_dataset_resolution_preview import (
        build_external_dataset_resolution_preview,
    )

    payload = build_external_dataset_resolution_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_resolution_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["accession_row_count"] == 12
    assert payload["summary"]["issue_category_row_count"] == 4
    assert payload["summary"]["blocked_accession_count"] == 5
    assert payload["summary"]["caveated_accession_count"] == 7
    assert payload["summary"]["resolved_accession_count"] == 0
    assert payload["summary"]["mapping_incomplete_accession_count"] == 0
    assert payload["summary"]["resolution_state_counts"] == {
        "blocked": 5,
        "caveated": 7,
        "resolved": 0,
    }
    assert payload["summary"]["top_blocking_gates"][0]["gate_name"] == "modality"
    assert payload["summary"]["top_blocking_gates"][0]["affected_accession_count"] == 5

    rows = {row["accession"]: row for row in payload["accession_resolution_rows"]}
    assert rows["P00387"]["resolution_state"] == "blocked"
    assert rows["P00387"]["blocking_gates"] == ["modality"]
    assert rows["P00387"]["worst_verdict"] == "blocked_pending_acquisition"
    assert rows["P68871"]["resolution_state"] == "caveated"
    assert rows["P68871"]["blocking_gates"] == []
    assert "external_dataset_modality_audit_preview" in rows["P00387"]["supporting_artifacts"]

    categories = {
        row["issue_category"]: row for row in payload["issue_resolution_rows"]
    }
    assert categories["modality"]["resolution_state"] == "blocked"
    assert categories["binding"]["resolution_state"] == "caveated"
    assert categories["provenance"]["resolution_state"] == "caveated"
    assert categories["structure"]["resolution_state"] == "caveated"


def test_build_resolution_preview_marks_mapping_incomplete_accessions() -> None:
    from scripts.export_external_dataset_resolution_preview import (
        build_external_dataset_resolution_preview,
    )

    assessment, issue_matrix, acceptance_gate, leakage, modality, binding, structure, provenance = (
        _sample_payloads()
    )
    issue_matrix = deepcopy(issue_matrix)
    modality = deepcopy(modality)

    for row in issue_matrix["rows"]:
        if row["accession"] == "Q9NZD4" and row["issue_category"] == "modality":
            row["verdict"] = "blocked_pending_mapping"
    modality["findings"]["missing_accessions"] = ["Q9NZD4"]
    modality["summary"]["missing_mapping_accession_count"] = 1
    modality["summary"]["blocked_full_packet_accession_count"] = 4

    payload = build_external_dataset_resolution_preview(
        assessment,
        issue_matrix,
        acceptance_gate,
        leakage,
        modality,
        binding,
        structure,
        provenance,
    )

    rows = {row["accession"]: row for row in payload["accession_resolution_rows"]}
    assert rows["Q9NZD4"]["resolution_state"] == "mapping-incomplete"
    assert "modality" in rows["Q9NZD4"]["blocking_gates"]
    categories = {
        row["issue_category"]: row for row in payload["issue_resolution_rows"]
    }
    assert categories["modality"]["resolution_state"] == "mapping-incomplete"
    assert payload["summary"]["mapping_incomplete_accession_count"] == 1


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_resolution_preview as exporter

    assessment, issue_matrix, acceptance_gate, leakage, modality, binding, structure, provenance = (
        _sample_payloads()
    )
    payloads = {
        "assessment": assessment,
        "issue_matrix": issue_matrix,
        "acceptance_gate": acceptance_gate,
        "leakage": leakage,
        "modality": modality,
        "binding": binding,
        "structure": structure,
        "provenance": provenance,
    }
    paths = {}
    for name, payload in payloads.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_resolution_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_ISSUE_MATRIX_PREVIEW", paths["issue_matrix"])
    monkeypatch.setattr(exporter, "DEFAULT_ACCEPTANCE_GATE_PREVIEW", paths["acceptance_gate"])
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
    assert payload["artifact_id"] == "external_dataset_resolution_preview"
    assert saved["artifact_id"] == "external_dataset_resolution_preview"
    assert saved["truth_boundary"]["report_only"] is True
    assert saved["truth_boundary"]["non_mutating"] is True
