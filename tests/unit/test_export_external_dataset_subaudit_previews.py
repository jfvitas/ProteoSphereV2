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

SCRIPT_CASES = [
    (
        "export_external_dataset_leakage_audit_preview.py",
        "external_dataset_leakage_audit_preview.json",
        "external_dataset_leakage_audit_preview.md",
        "External Dataset Leakage Audit Preview",
        "leakage",
        build_external_dataset_leakage_audit_preview,
    ),
    (
        "export_external_dataset_modality_audit_preview.py",
        "external_dataset_modality_audit_preview.json",
        "external_dataset_modality_audit_preview.md",
        "External Dataset Modality Audit Preview",
        "modality",
        build_external_dataset_modality_audit_preview,
    ),
    (
        "export_external_dataset_binding_audit_preview.py",
        "external_dataset_binding_audit_preview.json",
        "external_dataset_binding_audit_preview.md",
        "External Dataset Binding Audit Preview",
        "binding",
        build_external_dataset_binding_audit_preview,
    ),
    (
        "export_external_dataset_structure_audit_preview.py",
        "external_dataset_structure_audit_preview.json",
        "external_dataset_structure_audit_preview.md",
        "External Dataset Structure Audit Preview",
        "structure",
        build_external_dataset_structure_audit_preview,
    ),
    (
        "export_external_dataset_provenance_audit_preview.py",
        "external_dataset_provenance_audit_preview.json",
        "external_dataset_provenance_audit_preview.md",
        "External Dataset Provenance Audit Preview",
        "provenance",
        build_external_dataset_provenance_audit_preview,
    ),
]


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


def test_standalone_subaudit_builders_reuse_shared_assessment_flow() -> None:
    inputs = _load_inputs()
    audits = build_external_dataset_audits(*inputs)

    for _, _, _, _, audit_key, builder in SCRIPT_CASES:
        payload = builder(*inputs)
        assert _strip_generated_at(payload) == _strip_generated_at(audits[audit_key])
        assert payload["artifact_id"].endswith(f"_{audit_key}_audit_preview")
        assert payload["verdict"] in {
            "usable_with_caveats",
            "blocked_pending_cleanup",
            "blocked_pending_mapping",
            "audit_only",
        }


def test_standalone_subaudit_exporters_write_expected_cli_outputs(tmp_path: Path) -> None:
    inputs = _load_inputs()
    audits = build_external_dataset_audits(*inputs)

    for script_name, json_name, md_name, title, audit_key, _ in SCRIPT_CASES:
        output_json = tmp_path / json_name
        output_md = tmp_path / md_name
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / script_name),
                "--output-json",
                str(output_json),
                "--output-md",
                str(output_md),
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert _strip_generated_at(payload) == _strip_generated_at(audits[audit_key])
        assert payload["artifact_id"] == audits[audit_key]["artifact_id"]
        assert output_md.exists()
        assert title in output_md.read_text(encoding="utf-8")
