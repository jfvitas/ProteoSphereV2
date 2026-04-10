from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_MANIFEST_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "sample_external_dataset_manifest_preview.json"
)
DEFAULT_FOLDER_PACKAGE_MANIFEST_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "sample_folder_package_manifest_preview.json"
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_sample_external_dataset_manifests() -> dict[str, dict[str, Any]]:
    json_manifest = {
        "artifact_id": "sample_external_dataset_manifest_preview",
        "schema_id": "proteosphere-sample-external-dataset-manifest-preview-2026-04-03",
        "status": "report_only",
        "manifest_id": "sample-external-dataset-v1",
        "dataset_name": "Sample External Dataset",
        "rows": [
            {
                "row_id": "sample-row-001",
                "accession": "P00387",
                "split": "train",
                "pdb_id": "1Y01",
                "measurement_family": "Kd",
                "measurement_value": "22.5nM",
                "provenance": {
                    "source_name": "bindingdb",
                    "pmid": "12345678",
                },
                "modalities": ["sequence", "structure", "ligand"],
            },
            {
                "row_id": "sample-row-002",
                "accession": "Q9NZD4",
                "split": "test",
                "pdb_id": "4HHB",
                "measurement_family": "IC50",
                "measurement_value": "1.2uM",
                "provenance": {
                    "source_name": "chembl",
                    "patent_id": "WO-2026-000001",
                },
                "modalities": ["sequence", "structure"],
            },
        ],
        "truth_boundary": {
            "summary": (
                "This sample manifest is report-only and conservative. It is "
                "intended for dry-run assessment and does not mutate or authorize "
                "training inputs."
            ),
            "report_only": True,
            "non_mutating": True,
            "conservative_defaults": True,
        },
    }

    folder_package_manifest = {
        "artifact_id": "sample_folder_package_manifest_preview",
        "schema_id": "proteosphere-sample-folder-package-manifest-preview-2026-04-03",
        "status": "report_only",
        "manifest_path": "external/sample-package/LATEST.json",
        "dataset_name": "Sample Folder Package Dataset",
        "rows": [
            {
                "accession": "P31749",
                "package_ref": "packet://sample-package/P31749",
                "split": "train",
                "modalities": ["sequence", "ligand", "ppi"],
            },
            {
                "accession": "P04637",
                "package_ref": "packet://sample-package/P04637",
                "split": "val",
                "modalities": ["sequence", "structure"],
            },
        ],
        "truth_boundary": {
            "summary": (
                "This sample folder-package manifest is report-only and "
                "non-mutating. It is intended for dry-run assessor flows only."
            ),
            "report_only": True,
            "non_mutating": True,
            "conservative_defaults": True,
        },
    }

    return {
        "json_manifest": json_manifest,
        "folder_package_manifest": folder_package_manifest,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate conservative sample external dataset manifests."
    )
    parser.add_argument(
        "--json-manifest-output",
        type=Path,
        default=DEFAULT_JSON_MANIFEST_OUTPUT,
    )
    parser.add_argument(
        "--folder-package-manifest-output",
        type=Path,
        default=DEFAULT_FOLDER_PACKAGE_MANIFEST_OUTPUT,
    )
    parser.add_argument(
        "--stdout-summary",
        action="store_true",
        help="Print the generated payload summary to stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = build_sample_external_dataset_manifests()
    _write_json(args.json_manifest_output, payloads["json_manifest"])
    _write_json(args.folder_package_manifest_output, payloads["folder_package_manifest"])
    if args.stdout_summary:
        print(
            json.dumps(
                {
                    "json_manifest_output": str(args.json_manifest_output),
                    "folder_package_manifest_output": str(
                        args.folder_package_manifest_output
                    ),
                    "manifest_ids": {
                        "json_manifest": payloads["json_manifest"]["manifest_id"],
                        "folder_package_manifest": payloads[
                            "folder_package_manifest"
                        ]["manifest_path"],
                    },
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
