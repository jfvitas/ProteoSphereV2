from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_external_dataset_binding_audit_preview import (
    build_external_dataset_binding_audit_preview,
)
from scripts.export_external_dataset_leakage_audit_preview import (
    build_external_dataset_leakage_audit_preview,
)
from scripts.export_external_dataset_modality_audit_preview import (
    build_external_dataset_modality_audit_preview,
)
from scripts.export_external_dataset_provenance_audit_preview import (
    build_external_dataset_provenance_audit_preview,
)
from scripts.export_external_dataset_structure_audit_preview import (
    build_external_dataset_structure_audit_preview,
)
from scripts.export_sample_external_dataset_assessment_bundle import (
    build_sample_external_dataset_assessment_bundle_preview,
)
from scripts.external_dataset_assessment_support import (
    DEFAULT_ACCESSION_BINDING_SUPPORT,
    DEFAULT_BINDING_REGISTRY,
    DEFAULT_ELIGIBILITY_MATRIX,
    DEFAULT_EXTERNAL_COHORT_AUDIT,
    DEFAULT_FUTURE_STRUCTURE_TRIAGE,
    DEFAULT_INTERACTION_CONTEXT,
    DEFAULT_LIBRARY_CONTRACT,
    DEFAULT_OFF_TARGET_ADJACENT_PROFILE,
    DEFAULT_OPERATOR_ACCESSION_MATRIX,
    DEFAULT_SPLIT_LABELS,
    build_external_dataset_audits,
    read_json,
)
from scripts.generate_sample_external_dataset_manifest import (
    build_sample_external_dataset_manifests,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATHS = (
    DEFAULT_SPLIT_LABELS,
    DEFAULT_LIBRARY_CONTRACT,
    DEFAULT_EXTERNAL_COHORT_AUDIT,
    DEFAULT_ELIGIBILITY_MATRIX,
    DEFAULT_BINDING_REGISTRY,
    DEFAULT_ACCESSION_BINDING_SUPPORT,
    DEFAULT_OPERATOR_ACCESSION_MATRIX,
    DEFAULT_FUTURE_STRUCTURE_TRIAGE,
    DEFAULT_OFF_TARGET_ADJACENT_PROFILE,
    DEFAULT_INTERACTION_CONTEXT,
)


def _load_inputs() -> tuple[dict[str, object], ...]:
    return tuple(read_json(path) for path in INPUT_PATHS)


def _strip_generated_at(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _strip_generated_at(inner)
            for key, inner in value.items()
            if key != "generated_at"
        }
    if isinstance(value, list):
        return [_strip_generated_at(item) for item in value]
    return value


def test_sample_external_dataset_assessment_bundle_builder_is_report_only() -> None:
    sample_manifests = build_sample_external_dataset_manifests()
    inputs = _load_inputs()
    audits = build_external_dataset_audits(*inputs)
    payload = build_sample_external_dataset_assessment_bundle_preview(
        sample_manifests["json_manifest"],
        sample_manifests["folder_package_manifest"],
        audits["top_level"],
        build_external_dataset_leakage_audit_preview(*inputs),
        build_external_dataset_modality_audit_preview(*inputs),
        build_external_dataset_binding_audit_preview(*inputs),
        build_external_dataset_structure_audit_preview(*inputs),
        build_external_dataset_provenance_audit_preview(*inputs),
    )

    assert payload["artifact_id"] == "sample_external_dataset_assessment_bundle_preview"
    assert payload["status"] == "report_only"
    assert payload["bundle_status"] == "report_only_composite_preview"
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["non_mutating"] is True
    assert payload["truth_boundary"]["package_not_authorized"] is True
    assert payload["summary"]["sample_manifest_count"] == 2
    assert payload["summary"]["sample_manifest_row_count"] == 4
    assert payload["summary"]["assessment_overall_verdict"] == "usable_with_caveats"
    assert payload["summary"]["sub_audit_count"] == 5
    assert payload["summary"]["sub_audits_all_usable_with_caveats"] is True
    assert set(payload["sections"]) == {
        "sample_manifests",
        "external_dataset_assessment",
        "sub_audits",
    }


def test_sample_external_dataset_assessment_bundle_cli_writes_expected_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "sample_external_dataset_assessment_bundle_preview.json"
    output_md = tmp_path / "sample_external_dataset_assessment_bundle_preview.md"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_sample_external_dataset_assessment_bundle.py"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_json.exists()
    assert output_md.exists()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "sample_external_dataset_assessment_bundle_preview"
    assert payload["summary"]["sample_manifest_count"] == 2
    assert payload["summary"]["assessment_dataset_accession_count"] == 12
    assert "Sample External Dataset Assessment Bundle Preview" in output_md.read_text(
        encoding="utf-8"
    )
    assert "truth boundary" in output_md.read_text(encoding="utf-8").lower()
