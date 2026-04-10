from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    repo_root = Path(__file__).resolve().parents[2]
    paths = [
        repo_root / "artifacts" / "status" / "external_dataset_resolution_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_leakage_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_modality_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_binding_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_structure_audit_preview.json",
        repo_root / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json",
    ]
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)  # type: ignore[return-value]


def test_build_remediation_queue_preview_prioritizes_blockers_first() -> None:
    from scripts.export_external_dataset_remediation_queue_preview import (
        build_external_dataset_remediation_queue_preview,
    )

    payload = build_external_dataset_remediation_queue_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_remediation_queue_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["remediation_queue_row_count"] == 31
    assert payload["summary"]["queue_accession_count"] == 12
    assert payload["summary"]["blocked_queue_row_count"] == 15
    assert payload["summary"]["blocked_accession_count"] == 5
    assert payload["summary"]["overall_queue_verdict"] == "blocked_pending_acquisition"
    assert payload["summary"]["priority_bucket_counts"] == {
        "p0_blocker": 15,
        "p1_follow_up": 2,
        "p2_support_context": 14,
    }
    assert payload["summary"]["top_blocking_gates"][0]["blocking_gate"] == "modality"
    assert payload["summary"]["top_blocking_gates"][0]["queue_row_count"] == 15
    assert payload["summary"]["top_priority_accessions"][0]["accession"] == "P00387"
    assert payload["summary"]["top_priority_accessions"][0]["priority_bucket"] == "p0_blocker"

    rows = payload["rows"]
    assert rows[0]["accession"] == "P00387"
    assert rows[0]["issue_category"] == "modality"
    assert rows[0]["priority_bucket"] == "p0_blocker"
    assert rows[0]["blocking_gate"] == "modality"
    assert rows[0]["worst_verdict"] == "blocked_pending_acquisition"
    assert "external_dataset_resolution_preview" in rows[0]["supporting_artifacts"]
    assert "external_dataset_issue_matrix_preview" in rows[0]["supporting_artifacts"]
    assert "external_dataset_acceptance_gate_preview" in rows[0]["supporting_artifacts"]
    assert "external_dataset_modality_audit_preview" in rows[0]["supporting_artifacts"]

    structure_row = next(
        row
        for row in rows
        if row["accession"] == "P68871" and row["issue_category"] == "structure"
    )
    assert structure_row["priority_bucket"] == "p1_follow_up"
    assert structure_row["blocking_gate"] == "structure"
    assert structure_row["worst_verdict"] == "usable_with_caveats"

    support_row = next(
        row
        for row in rows
        if row["accession"] == "P02042" and row["issue_category"] == "binding"
    )
    assert support_row["priority_bucket"] == "p2_support_context"
    assert support_row["blocking_gate"] == "binding"
    assert support_row["worst_verdict"] == "usable_with_caveats"


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_remediation_queue_preview as exporter

    resolution, issue_matrix, acceptance_gate, leakage, modality, binding, structure, provenance = (
        _sample_payloads()
    )
    payloads = {
        "resolution": resolution,
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

    output_json = tmp_path / "external_dataset_remediation_queue_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_RESOLUTION_PREVIEW", paths["resolution"])
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
    assert payload["artifact_id"] == "external_dataset_remediation_queue_preview"
    assert saved["artifact_id"] == "external_dataset_remediation_queue_preview"
    assert saved["truth_boundary"]["report_only"] is True
    assert saved["truth_boundary"]["fail_closed"] is True
    assert saved["truth_boundary"]["non_mutating"] is True
