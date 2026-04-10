from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.external_dataset_preview_common import (
    build_external_dataset_assessment_preview,
    build_external_dataset_intake_contract_preview,
    render_assessment_markdown,
    render_intake_contract_markdown,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_intake_contract_preview_orders_supported_shapes_and_uses_current_calibration() -> None:
    payload = build_external_dataset_intake_contract_preview()

    assert payload["status"] == "complete"
    assert payload["report_only"] is True
    assert [shape["shape_id"] for shape in payload["accepted_intake_shapes"]] == [
        "json_manifest",
        "folder_package_manifest",
    ]
    assert payload["accepted_intake_shapes"][0]["accepted_flavors"][0] == "bundle_manifest"
    assert payload["accepted_intake_shapes"][1]["accepted_flavors"][0] == "release_manifest"
    assert payload["calibration_defaults"]["json_manifest"].endswith(
        "lightweight_bundle_manifest.json"
    )
    assert payload["calibration_defaults"]["folder_package_manifest"].endswith(
        "artifacts\\bundles\\preview"
    )
    assert payload["calibration_signals"]["operator_dashboard"]["dashboard_status"] == (
        "blocked_on_release_grade_bar"
    )
    assert payload["truth_boundary"]["fail_closed"] is True

    markdown = render_intake_contract_markdown(payload)
    assert "# External Dataset Intake Contract Preview" in markdown
    assert "json_manifest" in markdown
    assert "folder_package_manifest" in markdown


def test_assessment_preview_accepts_report_only_json_and_folder_package_shapes(
    tmp_path: Path,
) -> None:
    json_manifest_path = tmp_path / "demo_manifest.json"
    json_manifest_payload = {
        "bundle_id": "demo-bundle",
        "bundle_kind": "debug_bundle",
        "bundle_version": "0.0.1-preview",
        "artifact_files": [
            {
                "filename": "demo.sqlite.zst",
                "size_bytes": 9,
                "required": True,
                "role": "core_bundle",
                "sha256": "",
            },
            {
                "filename": "demo.release_manifest.json",
                "size_bytes": 0,
                "required": True,
                "role": "manifest",
                "sha256": "",
            },
            {
                "filename": "demo.sha256",
                "size_bytes": 0,
                "required": True,
                "role": "checksum_root",
                "sha256": "",
            },
        ],
        "required_assets": [
            "demo.sqlite.zst",
            "demo.release_manifest.json",
            "demo.sha256",
        ],
        "optional_assets": [],
        "table_families": [],
    }
    json_manifest_path.write_text(json.dumps(json_manifest_payload, indent=2), encoding="utf-8")

    package_dir = tmp_path / "package"
    package_dir.mkdir()
    bundle_path = package_dir / "demo.sqlite.zst"
    bundle_path.write_bytes(b"preview-bundle")
    bundle_sha = _sha256(bundle_path)
    (package_dir / "demo.sha256").write_text(
        f"{bundle_sha}  demo.sqlite.zst\n",
        encoding="utf-8",
    )
    release_manifest_payload = {
        "artifact_id": "demo_release_manifest",
        "schema_id": "demo-release-manifest-2026-04-03",
        "status": "preview_generated_assets",
        "bundle_filename": "demo.sqlite.zst",
        "bundle_sha256": bundle_sha,
        "bundle_size_bytes": bundle_path.stat().st_size,
        "checksum_filename": "demo.sha256",
        "source_libraries": {
            "protein": "summary-library:protein-materialized:v1"
        },
        "record_counts": {"proteins": 1},
    }
    (package_dir / "demo.release_manifest.json").write_text(
        json.dumps(release_manifest_payload, indent=2),
        encoding="utf-8",
    )

    payload = build_external_dataset_assessment_preview(
        json_manifest_path=json_manifest_path,
        package_dir=package_dir,
    )

    assert payload["status"] == "complete"
    assert payload["report_only"] is True
    assert (
        payload["assessed_inputs"]["json_manifest"]["shape_verdict"]
        == "json_manifest_accepted_for_report_only_preview"
    )
    assert (
        payload["assessed_inputs"]["folder_package_manifest"]["shape_verdict"]
        == "folder_package_manifest_accepted_for_report_only_preview"
    )
    assert payload["assessed_inputs"]["folder_package_manifest"]["checksum_verified"] is True
    assert payload["assessment_summary"]["overall_verdict"] == "ready_for_report_only_preview"
    assert payload["assessment_summary"]["next_operator_action"] == (
        "safe_to_stage_after_manual_review"
    )

    markdown = render_assessment_markdown(payload)
    assert "# External Dataset Assessment Preview" in markdown
    assert "json_manifest" in markdown
    assert "folder_package_manifest" in markdown


def test_assessment_preview_blocks_unknown_shapes(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text(json.dumps({"foo": "bar"}, indent=2), encoding="utf-8")
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    payload = build_external_dataset_assessment_preview(
        json_manifest_path=bad_json,
        package_dir=empty_dir,
    )

    assert payload["assessment_summary"]["overall_verdict"] == "attention_needed"
    assert payload["assessed_inputs"]["json_manifest"]["shape_verdict"] == "blocked_unknown_shape"
    assert (
        payload["assessed_inputs"]["folder_package_manifest"]["shape_verdict"]
        == "blocked_missing_manifest"
    )
    assert payload["truth_boundary"]["fail_closed"] is True
