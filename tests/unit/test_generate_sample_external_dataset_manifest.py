from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_sample_external_dataset_manifest import (
    build_sample_external_dataset_manifests,
)


def test_sample_external_dataset_manifest_builder_is_conservative_and_non_mutating() -> None:
    payloads = build_sample_external_dataset_manifests()

    assert set(payloads) == {"json_manifest", "folder_package_manifest"}

    json_manifest = payloads["json_manifest"]
    assert json_manifest["status"] == "report_only"
    assert json_manifest["manifest_id"] == "sample-external-dataset-v1"
    assert json_manifest["dataset_name"] == "Sample External Dataset"
    assert json_manifest["truth_boundary"]["report_only"] is True
    assert json_manifest["truth_boundary"]["non_mutating"] is True
    assert json_manifest["truth_boundary"]["conservative_defaults"] is True
    assert [row["accession"] for row in json_manifest["rows"]] == ["P00387", "Q9NZD4"]
    assert [row["split"] for row in json_manifest["rows"]] == ["train", "test"]
    assert json_manifest["rows"][0]["provenance"]["source_name"] == "bindingdb"
    assert json_manifest["rows"][1]["provenance"]["patent_id"] == "WO-2026-000001"

    folder_manifest = payloads["folder_package_manifest"]
    assert folder_manifest["status"] == "report_only"
    assert folder_manifest["manifest_path"] == "external/sample-package/LATEST.json"
    assert folder_manifest["dataset_name"] == "Sample Folder Package Dataset"
    assert folder_manifest["truth_boundary"]["report_only"] is True
    assert folder_manifest["truth_boundary"]["non_mutating"] is True
    assert folder_manifest["truth_boundary"]["conservative_defaults"] is True
    assert [row["accession"] for row in folder_manifest["rows"]] == ["P31749", "P04637"]
    assert [row["split"] for row in folder_manifest["rows"]] == ["train", "val"]
    assert folder_manifest["rows"][0]["package_ref"] == "packet://sample-package/P31749"
    assert folder_manifest["rows"][1]["package_ref"] == "packet://sample-package/P04637"


def test_sample_external_dataset_manifest_cli_writes_only_requested_outputs(tmp_path: Path) -> None:
    json_output = tmp_path / "sample_external_dataset_manifest_preview.json"
    folder_output = tmp_path / "sample_folder_package_manifest_preview.json"

    result = subprocess.run(
        [
            sys.executable,
            str(Path("scripts") / "generate_sample_external_dataset_manifest.py"),
            "--json-manifest-output",
            str(json_output),
            "--folder-package-manifest-output",
            str(folder_output),
            "--stdout-summary",
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json_output.exists()
    assert folder_output.exists()
    assert json.loads(json_output.read_text(encoding="utf-8"))["manifest_id"] == (
        "sample-external-dataset-v1"
    )
    assert json.loads(folder_output.read_text(encoding="utf-8"))["manifest_path"] == (
        "external/sample-package/LATEST.json"
    )
    assert "json_manifest_output" in result.stdout
    assert "folder_package_manifest_output" in result.stdout
    extra_sample_outputs = [
        path
        for path in tmp_path.iterdir()
        if path not in {json_output, folder_output} and path.name.startswith("sample_")
    ]
    assert extra_sample_outputs == []
