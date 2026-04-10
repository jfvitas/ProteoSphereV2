from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    repo_root = Path(__file__).resolve().parents[2]
    paths = {
        "assessment": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_assessment_preview.json",
        "issue_matrix": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_issue_matrix_preview.json",
        "manifest_lint": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_manifest_lint_preview.json",
        "leakage": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_leakage_audit_preview.json",
        "modality": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_modality_audit_preview.json",
        "binding": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_binding_audit_preview.json",
        "structure": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_structure_audit_preview.json",
        "provenance": repo_root
        / "artifacts"
        / "status"
        / "external_dataset_provenance_audit_preview.json",
    }
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths.values())  # type: ignore[return-value]


def test_build_acceptance_gate_preview_prioritizes_modality_blocker() -> None:
    from scripts.export_external_dataset_acceptance_gate_preview import (
        build_external_dataset_acceptance_gate_preview,
    )

    payload = build_external_dataset_acceptance_gate_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_acceptance_gate_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["dataset_accession_count"] == 12
    assert payload["summary"]["blocked_accession_count"] == 5
    assert payload["summary"]["usable_with_caveats_accession_count"] == 7
    assert payload["summary"]["overall_gate_verdict"] == "blocked_pending_acquisition"
    assert payload["summary"]["top_remediation_categories"][0]["issue_category"] == "modality"
    assert payload["summary"]["top_remediation_categories"][0]["affected_accession_count"] == 5

    gate_reports = {item["gate_name"]: item for item in payload["gate_reports"]}
    assert gate_reports["issue_matrix"]["verdict"] == "blocked_pending_acquisition"
    assert gate_reports["issue_matrix"]["impact"]["impacted_accession_count"] == 5
    assert gate_reports["manifest_lint"]["verdict"] == "usable_with_caveats"
    assert gate_reports["leakage"]["impact"]["impacted_accession_count"] == 5
    assert gate_reports["modality"]["impact"]["impacted_accession_count"] == 5
    assert gate_reports["binding"]["verdict"] == "usable_with_caveats"

    category_reports = {
        item["gate_name"]: item for item in payload["issue_category_reports"]
    }
    assert category_reports["modality"]["impact"]["impacted_accession_count"] == 5
    assert category_reports["binding"]["impact"]["impacted_accession_count"] == 12
    assert any(
        item["gate_name"] == "issue_matrix"
        and item["verdict"] == "blocked_pending_acquisition"
        for item in payload["summary"]["training_safe_acceptance"]["must_clear"]
    )


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_acceptance_gate_preview as exporter

    assessment, issue_matrix, manifest_lint, leakage, modality, binding, structure, provenance = (
        _sample_payloads()
    )
    payloads = {
        "assessment": assessment,
        "issue_matrix": issue_matrix,
        "manifest_lint": manifest_lint,
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

    output_json = tmp_path / "external_dataset_acceptance_gate_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_ASSESSMENT_PREVIEW", paths["assessment"])
    monkeypatch.setattr(exporter, "DEFAULT_ISSUE_MATRIX_PREVIEW", paths["issue_matrix"])
    monkeypatch.setattr(exporter, "DEFAULT_MANIFEST_LINT_PREVIEW", paths["manifest_lint"])
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
    assert payload["artifact_id"] == "external_dataset_acceptance_gate_preview"
    assert saved["artifact_id"] == "external_dataset_acceptance_gate_preview"
    assert saved["truth_boundary"]["report_only"] is True
    assert saved["truth_boundary"]["non_mutating"] is True
