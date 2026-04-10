from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict]:
    repo_root = Path(__file__).resolve().parents[2]
    intake_contract = json.loads(
        (
            repo_root
            / "artifacts"
            / "status"
            / "external_dataset_intake_contract_preview.json"
        ).read_text(encoding="utf-8")
    )
    sample_external_manifest = json.loads(
        (
            repo_root
            / "artifacts"
            / "status"
            / "sample_external_dataset_manifest_preview.json"
        ).read_text(encoding="utf-8")
    )
    sample_folder_package_manifest = json.loads(
        (
            repo_root
            / "artifacts"
            / "status"
            / "sample_folder_package_manifest_preview.json"
        ).read_text(encoding="utf-8")
    )
    return intake_contract, sample_external_manifest, sample_folder_package_manifest


def test_build_manifest_lint_preview_reports_shape_verdicts_from_sample_manifests() -> None:
    from scripts.export_external_dataset_manifest_lint_preview import (
        build_external_dataset_manifest_lint_preview,
    )

    payload = build_external_dataset_manifest_lint_preview(*_sample_payloads())

    assert payload["artifact_id"] == "external_dataset_manifest_lint_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["accepted_shape_count"] == 2
    assert payload["summary"]["sample_manifest_count"] == 2
    assert payload["summary"]["missing_required_field_count"] == 0
    assert payload["summary"]["overall_verdict"] == "usable_with_caveats"
    assert payload["summary"]["shape_verdict_counts"] == {"usable_with_caveats": 2}
    assert payload["missing_required_fields"] == []

    per_shape = {item["shape_id"]: item for item in payload["per_shape_verdicts"]}
    assert per_shape["json_manifest"]["verdict"] == "usable_with_caveats"
    assert per_shape["json_manifest"]["sample_manifest_count"] == 1
    assert per_shape["json_manifest"]["missing_required_fields"] == []
    assert per_shape["folder_package_manifest"]["verdict"] == "usable_with_caveats"
    assert per_shape["folder_package_manifest"]["sample_manifest_count"] == 1
    assert per_shape["folder_package_manifest"]["missing_required_fields"] == []

    reports = {item["manifest_ref"]: item for item in payload["manifest_reports"]}
    assert reports["sample_external_dataset_manifest_preview"]["detected_shape_id"] == (
        "json_manifest"
    )
    assert reports["sample_folder_package_manifest_preview"]["detected_shape_id"] == (
        "folder_package_manifest"
    )


def test_build_manifest_lint_preview_is_fail_closed_for_missing_required_fields() -> None:
    from scripts.export_external_dataset_manifest_lint_preview import (
        build_external_dataset_manifest_lint_preview,
    )

    intake_contract, sample_external_manifest, sample_folder_package_manifest = _sample_payloads()
    broken_manifest = dict(sample_external_manifest)
    broken_manifest["rows"] = [
        {
            "split": "train",
            "pdb_id": "1Y01",
        }
    ]

    payload = build_external_dataset_manifest_lint_preview(
        intake_contract,
        broken_manifest,
        sample_folder_package_manifest,
    )

    assert payload["summary"]["overall_verdict"] == "unsafe_for_training"
    assert payload["summary"]["missing_required_field_count"] == 1
    assert payload["summary"]["missing_required_row_field_count"] == 1
    per_shape = {item["shape_id"]: item for item in payload["per_shape_verdicts"]}
    assert per_shape["json_manifest"]["verdict"] == "unsafe_for_training"
    assert per_shape["json_manifest"]["missing_required_row_fields"] == ["accession"]
    assert payload["missing_required_fields"][0]["field"] == "accession"
    assert payload["missing_required_fields"][0]["scope"] == "row"


def test_main_writes_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_external_dataset_manifest_lint_preview as exporter

    intake_contract, sample_external_manifest, sample_folder_package_manifest = _sample_payloads()
    paths = {}
    for name, payload in {
        "intake_contract": intake_contract,
        "sample_external_manifest": sample_external_manifest,
        "sample_folder_package_manifest": sample_folder_package_manifest,
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    output_json = tmp_path / "external_dataset_manifest_lint_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_INTAKE_CONTRACT_PREVIEW", paths["intake_contract"])
    monkeypatch.setattr(
        exporter,
        "DEFAULT_SAMPLE_EXTERNAL_MANIFEST_PREVIEW",
        paths["sample_external_manifest"],
    )
    monkeypatch.setattr(
        exporter,
        "DEFAULT_SAMPLE_FOLDER_PACKAGE_MANIFEST_PREVIEW",
        paths["sample_folder_package_manifest"],
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "external_dataset_manifest_lint_preview"
    assert saved["artifact_id"] == "external_dataset_manifest_lint_preview"
    assert saved["truth_boundary"]["report_only"] is True
