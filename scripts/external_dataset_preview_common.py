from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_JSON_MANIFEST = REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
DEFAULT_PACKAGE_DIR = REPO_ROOT / "artifacts" / "bundles" / "preview"
DEFAULT_OPERATOR_DASHBOARD = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "operator_dashboard.json"
)
DEFAULT_EXTERNAL_COHORT_AUDIT = REPO_ROOT / "artifacts" / "status" / "external_cohort_audit.json"
DEFAULT_MISSING_DATA_POLICY = (
    REPO_ROOT / "artifacts" / "status" / "missing_data_policy_preview.json"
)
DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_BUNDLE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "live_bundle_manifest_validation.json"
)
DEFAULT_OUTPUT_CONTRACT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_intake_contract_preview.json"
)
DEFAULT_OUTPUT_CONTRACT_MD = (
    REPO_ROOT / "docs" / "reports" / "external_dataset_intake_contract_preview.md"
)
DEFAULT_OUTPUT_ASSESSMENT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_OUTPUT_ASSESSMENT_MD = (
    REPO_ROOT / "docs" / "reports" / "external_dataset_assessment_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("/", "\\")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _bundle_manifest_flavor(payload: Mapping[str, Any]) -> str:
    keys = set(payload.keys())
    if {"bundle_id", "artifact_files"} <= keys:
        return "bundle_manifest"
    if {"package_id", "selected_examples", "raw_manifests"} <= keys:
        return "package_manifest"
    if {"manifest_id", "source_name"} <= keys:
        return "raw_cache_manifest"
    return "unknown"


def _release_manifest_flavor(payload: Mapping[str, Any]) -> str:
    keys = set(payload.keys())
    if {"bundle_filename", "bundle_sha256", "checksum_filename"} <= keys:
        return "release_manifest"
    if {"package_id", "selected_examples", "raw_manifests"} <= keys:
        return "package_manifest"
    return "unknown"


def _bundle_manifest_required_fields(flavor: str) -> list[str]:
    if flavor == "bundle_manifest":
        return ["bundle_id", "bundle_kind", "bundle_version", "artifact_files"]
    if flavor == "package_manifest":
        return ["package_id", "selected_examples", "raw_manifests"]
    if flavor == "raw_cache_manifest":
        return ["manifest_id", "source_name", "retrieval_mode"]
    return []


def _release_manifest_required_fields(flavor: str) -> list[str]:
    if flavor == "release_manifest":
        return ["bundle_filename", "bundle_sha256", "checksum_filename", "source_libraries"]
    if flavor == "package_manifest":
        return ["package_id", "selected_examples", "raw_manifests"]
    return []


def _load_calibration_signals() -> dict[str, Any]:
    dashboard = _read_json(DEFAULT_OPERATOR_DASHBOARD)
    external_audit = _read_json(DEFAULT_EXTERNAL_COHORT_AUDIT)
    missing_policy = _read_json(DEFAULT_MISSING_DATA_POLICY)
    eligibility = _read_json(DEFAULT_ELIGIBILITY_MATRIX)
    bundle_validation = _read_json(DEFAULT_BUNDLE_VALIDATION)
    return {
        "operator_dashboard": {
            "dashboard_status": dashboard.get("dashboard_status"),
            "operator_go_no_go": dashboard.get("operator_go_no_go"),
            "ready_for_next_wave": dashboard.get("ready_for_next_wave"),
            "leakage_ready": dashboard.get("leakage_ready"),
        },
        "external_cohort_audit": {
            "overall_decision": (
                external_audit.get("audit_results", {})
                .get("overall", {})
                .get("decision")
            ),
            "leakage_status": external_audit.get("audit_results", {})
            .get("leakage", {})
            .get("status"),
            "ligand_follow_through": external_audit.get("audit_results", {})
            .get("ligand_follow_through", {})
            .get("decision"),
        },
        "missing_data_policy": {
            "status": missing_policy.get("status"),
            "candidate_only_rows_non_governing": missing_policy.get("truth_boundary", {}).get(
                "candidate_only_rows_non_governing"
            ),
            "deletion_default": missing_policy.get("truth_boundary", {}).get("deletion_default"),
        },
        "eligibility_matrix": {
            "row_count": eligibility.get("row_count"),
            "grounded_ligand_accessions": eligibility.get("summary", {}).get(
                "grounded_ligand_accessions"
            ),
            "candidate_only_ligand_accessions": eligibility.get("summary", {}).get(
                "candidate_only_ligand_accessions"
            ),
        },
        "bundle_validation": {
            "status": bundle_validation.get("overall_assessment", {}).get("status"),
            "checksum_verified": bundle_validation.get("asset_validation", {}).get(
                "checksum_verified"
            ),
            "required_assets_present": bundle_validation.get("asset_validation", {}).get(
                "required_assets_present"
            ),
        },
    }


def _shape_contract_entries() -> list[dict[str, Any]]:
    return [
        {
            "shape_order": 1,
            "shape_id": "json_manifest",
            "shape_kind": "file",
            "accepted_flavors": [
                "bundle_manifest",
                "package_manifest",
                "raw_cache_manifest",
            ],
            "required_operator_fields": [
                "manifest_id or bundle_id or package_id",
                "source_name when provenance is present",
                "release_version or release_date when release-stamped",
                "artifact_files or selected_examples or raw_manifests",
            ],
            "blocked_when_missing": [
                "unknown manifest flavor",
                "missing required fields",
                "non-object payload",
            ],
            "truth_note": (
                "A single JSON manifest is accepted only when it carries a recognized manifest "
                "flavor and the minimum provenance fields needed for report-only previewing."
            ),
        },
        {
            "shape_order": 2,
            "shape_id": "folder_package_manifest",
            "shape_kind": "directory",
            "accepted_flavors": [
                "release_manifest",
                "package_manifest",
            ],
            "required_operator_fields": [
                "bundle_filename or manifest.json",
                "bundle_sha256 or checksum_root",
                "checksum_filename when a release manifest is present",
                "payload asset files under the intake folder",
            ],
            "blocked_when_missing": [
                "missing manifest file",
                "missing checksum file",
                "checksum mismatch",
                "ambiguous manifest location",
            ],
            "truth_note": (
                "A folder/package intake is accepted only when the manifest file is found, the "
                "checksum can be verified, and the payload files are present."
            ),
        },
    ]


def build_external_dataset_intake_contract_preview() -> dict[str, Any]:
    calibration_signals = _load_calibration_signals()
    accepted_shapes = _shape_contract_entries()
    return {
        "artifact_id": "external_dataset_intake_contract_preview",
        "schema_id": "proteosphere-external-dataset-intake-contract-preview-2026-04-03",
        "status": "complete",
        "report_only": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "accepted_intake_shapes": accepted_shapes,
        "calibration_defaults": {
            "json_manifest": _repo_relative(DEFAULT_JSON_MANIFEST),
            "folder_package_manifest": _repo_relative(DEFAULT_PACKAGE_DIR),
            "operator_dashboard": _repo_relative(DEFAULT_OPERATOR_DASHBOARD),
            "external_cohort_audit": _repo_relative(DEFAULT_EXTERNAL_COHORT_AUDIT),
            "missing_data_policy": _repo_relative(DEFAULT_MISSING_DATA_POLICY),
            "eligibility_matrix": _repo_relative(DEFAULT_ELIGIBILITY_MATRIX),
            "bundle_validation": _repo_relative(DEFAULT_BUNDLE_VALIDATION),
        },
        "calibration_signals": calibration_signals,
        "operator_ready_fields": [
            "intake_shape",
            "manifest_flavor",
            "source_name",
            "manifest_id",
            "package_id",
            "bundle_filename",
            "bundle_sha256",
            "checksum_filename",
            "checksum_verified",
            "required_assets_present",
            "missing_required_fields",
            "assessment_verdict",
            "next_operator_action",
        ],
        "verdict_vocabulary": [
            "json_manifest_accepted_for_report_only_preview",
            "folder_package_manifest_accepted_for_report_only_preview",
            "blocked_unknown_shape",
            "blocked_missing_required_fields",
            "blocked_missing_manifest",
            "blocked_checksum_mismatch",
            "blocked_missing_required_assets",
        ],
        "truth_boundary": {
            "summary": (
                "This preview contract accepts only two intake routes: a JSON manifest or a "
                "folder/package manifest. Unknown shapes, missing provenance, and checksum "
                "gaps are blocked by default."
            ),
            "report_only": True,
            "fail_closed": True,
            "calibration_only": True,
            "external_acceptance_authorized": False,
        },
    }


def _assess_json_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "intake_shape": "json_manifest",
            "input_path": str(path),
            "exists": False,
            "manifest_flavor": "unknown",
            "shape_verdict": "blocked_missing_manifest",
            "missing_required_fields": ["file does not exist"],
            "required_fields_present": False,
            "calibration_match": False,
            "notes": ["No JSON manifest was supplied."],
        }
    payload = _read_json(path)
    flavor = _bundle_manifest_flavor(payload)
    required_fields = _bundle_manifest_required_fields(flavor)
    missing_required_fields = [field for field in required_fields if field not in payload]
    required_fields_present = flavor != "unknown" and not missing_required_fields
    verdict = (
        "json_manifest_accepted_for_report_only_preview"
        if required_fields_present
        else "blocked_unknown_shape"
        if flavor == "unknown"
        else "blocked_missing_required_fields"
    )
    notes = []
    if flavor == "unknown":
        notes.append("The manifest did not match a supported JSON manifest flavor.")
    if missing_required_fields:
        notes.append("Missing required manifest fields were detected.")
    return {
        "intake_shape": "json_manifest",
        "input_path": str(path),
        "exists": True,
        "manifest_flavor": flavor,
        "shape_verdict": verdict,
        "required_fields": required_fields,
        "missing_required_fields": missing_required_fields,
        "required_fields_present": required_fields_present,
        "calibration_match": required_fields_present,
        "notes": notes,
    }


def _manifest_file_for_package(package_dir: Path) -> Path | None:
    if not package_dir.exists() or not package_dir.is_dir():
        return None
    manifest_json = package_dir / "manifest.json"
    if manifest_json.exists():
        return manifest_json
    release_manifests = sorted(package_dir.glob("*.release_manifest.json"))
    if len(release_manifests) == 1:
        return release_manifests[0]
    return None


def _checksum_filename_candidates(manifest_payload: Mapping[str, Any]) -> list[str]:
    candidates = [
        _clean_text(manifest_payload.get("checksum_filename")),
        _clean_text(manifest_payload.get("checksum_file")),
        _clean_text(manifest_payload.get("checksum_root")),
    ]
    return [candidate for candidate in candidates if candidate]


def _payload_filename(manifest_payload: Mapping[str, Any]) -> str | None:
    return _clean_text(manifest_payload.get("bundle_filename")) or None


def _assess_folder_package_manifest(package_dir: Path) -> dict[str, Any]:
    if not package_dir.exists():
        return {
            "intake_shape": "folder_package_manifest",
            "input_path": str(package_dir),
            "exists": False,
            "manifest_file": None,
            "manifest_flavor": "unknown",
            "shape_verdict": "blocked_missing_manifest",
            "missing_required_fields": ["folder does not exist"],
            "required_files_present": False,
            "checksum_verified": False,
            "notes": ["No package folder was supplied."],
        }
    if not package_dir.is_dir():
        return {
            "intake_shape": "folder_package_manifest",
            "input_path": str(package_dir),
            "exists": True,
            "manifest_file": None,
            "manifest_flavor": "unknown",
            "shape_verdict": "blocked_unknown_shape",
            "missing_required_fields": ["input is not a directory"],
            "required_files_present": False,
            "checksum_verified": False,
            "notes": ["The supplied intake path is not a directory."],
        }

    manifest_file = _manifest_file_for_package(package_dir)
    if manifest_file is None:
        return {
            "intake_shape": "folder_package_manifest",
            "input_path": str(package_dir),
            "exists": True,
            "manifest_file": None,
            "manifest_flavor": "unknown",
            "shape_verdict": "blocked_missing_manifest",
            "missing_required_fields": ["manifest file"],
            "required_files_present": False,
            "checksum_verified": False,
            "notes": [
                "The package folder must contain either manifest.json or a single *.release_manifest.json file.",
            ],
        }

    payload = _read_json(manifest_file)
    flavor = _release_manifest_flavor(payload)
    required_fields = _release_manifest_required_fields(flavor)
    missing_required_fields = [field for field in required_fields if field not in payload]
    bundle_filename = _payload_filename(payload)
    checksum_candidates = _checksum_filename_candidates(payload)
    bundle_path = package_dir / bundle_filename if bundle_filename else None
    checksum_verified = False
    checksum_path = None
    if checksum_candidates:
        for candidate in checksum_candidates:
            candidate_path = package_dir / candidate
            if candidate_path.exists():
                checksum_path = candidate_path
                break
    if bundle_path and checksum_path and bundle_path.exists():
        expected_hash = _clean_text(payload.get("bundle_sha256"))
        checksum_text = checksum_path.read_text(encoding="utf-8").strip()
        checksum_hash = checksum_text.split()[0] if checksum_text else ""
        actual_hash = _sha256(bundle_path)
        checksum_verified = (
            bool(expected_hash)
            and expected_hash == actual_hash
            and checksum_hash == actual_hash
        )

    required_files_present = (
        flavor != "unknown"
        and not missing_required_fields
        and bundle_path is not None
        and bundle_path.exists()
        and checksum_path is not None
        and checksum_path.exists()
    )
    verdict = (
        "folder_package_manifest_accepted_for_report_only_preview"
        if required_files_present and checksum_verified
        else "blocked_unknown_shape"
        if flavor == "unknown"
        else "blocked_checksum_mismatch"
        if bundle_path is not None and bundle_path.exists() and not checksum_verified
        else "blocked_missing_required_assets"
        if bundle_path is None or not bundle_path.exists() or checksum_path is None
        else "blocked_missing_required_fields"
    )
    notes: list[str] = []
    if flavor == "unknown":
        notes.append("The folder manifest did not match a supported release manifest flavor.")
    if missing_required_fields:
        notes.append("The release manifest is missing required fields.")
    if bundle_path is not None and bundle_path.exists() and not checksum_verified:
        notes.append("The bundle checksum did not match the expected hash.")
    if bundle_path is None or not bundle_path.exists() or checksum_path is None:
        notes.append("The folder is missing a required payload or checksum file.")

    return {
        "intake_shape": "folder_package_manifest",
        "input_path": str(package_dir),
        "exists": True,
        "manifest_file": str(manifest_file),
        "manifest_flavor": flavor,
        "shape_verdict": verdict,
        "required_fields": required_fields,
        "missing_required_fields": missing_required_fields,
        "required_files_present": required_files_present,
        "checksum_verified": checksum_verified,
        "checksum_file": str(checksum_path) if checksum_path is not None else None,
        "bundle_file": str(bundle_path) if bundle_path is not None else None,
        "notes": notes,
    }


def build_external_dataset_assessment_preview(
    *,
    json_manifest_path: Path = DEFAULT_JSON_MANIFEST,
    package_dir: Path = DEFAULT_PACKAGE_DIR,
) -> dict[str, Any]:
    calibration_signals = _load_calibration_signals()
    json_manifest_assessment = _assess_json_manifest(json_manifest_path)
    folder_package_assessment = _assess_folder_package_manifest(package_dir)
    supported = [
        item
        for item in (json_manifest_assessment, folder_package_assessment)
        if item.get("shape_verdict") in {
            "json_manifest_accepted_for_report_only_preview",
            "folder_package_manifest_accepted_for_report_only_preview",
        }
    ]
    blocked = [
        item
        for item in (json_manifest_assessment, folder_package_assessment)
        if item.get("shape_verdict") not in {
            "json_manifest_accepted_for_report_only_preview",
            "folder_package_manifest_accepted_for_report_only_preview",
        }
    ]
    overall_verdict = (
        "ready_for_report_only_preview"
        if len(supported) == 2 and not blocked
        else "attention_needed"
    )
    next_operator_action = (
        "hold_external_intake_in_report_only_preview"
        if blocked
        else "safe_to_stage_after_manual_review"
    )
    return {
        "artifact_id": "external_dataset_assessment_preview",
        "schema_id": "proteosphere-external-dataset-assessment-preview-2026-04-03",
        "status": "complete",
        "report_only": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "assessed_inputs": {
            "json_manifest": json_manifest_assessment,
            "folder_package_manifest": folder_package_assessment,
        },
        "assessment_summary": {
            "supported_shape_count": len(supported),
            "blocked_shape_count": len(blocked),
            "supported_shapes": [item["intake_shape"] for item in supported],
            "blocked_shapes": [item["intake_shape"] for item in blocked],
            "overall_verdict": overall_verdict,
            "next_operator_action": next_operator_action,
        },
        "calibration_signals": calibration_signals,
        "verdict_vocabulary": [
            "json_manifest_accepted_for_report_only_preview",
            "folder_package_manifest_accepted_for_report_only_preview",
            "blocked_unknown_shape",
            "blocked_missing_manifest",
            "blocked_missing_required_fields",
            "blocked_missing_required_assets",
            "blocked_checksum_mismatch",
            "attention_needed",
            "ready_for_report_only_preview",
        ],
        "truth_boundary": {
            "summary": (
                "This assessment is fail-closed and report-only. It accepts JSON manifests "
                "and folder/package manifests only when the shape is recognized and the "
                "required provenance and checksum checks pass."
            ),
            "report_only": True,
            "fail_closed": True,
            "calibration_only": True,
            "external_acceptance_authorized": False,
        },
    }


def render_intake_contract_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# External Dataset Intake Contract Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Report only: `{payload.get('report_only')}`",
        "",
        "## Accepted Intake Shapes",
        "",
    ]
    for shape in payload.get("accepted_intake_shapes", []):
        lines.append(
            f"- `{shape['shape_order']}` `{shape['shape_id']}` -> "
            f"`{', '.join(shape['accepted_flavors'])}`"
        )
        lines.append(f"  - Truth note: {shape['truth_note']}")
    lines.extend(
        [
            "",
            "## Calibration Defaults",
            "",
        ]
    )
    for key, value in payload.get("calibration_defaults", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Verdict Vocabulary",
            "",
        ]
    )
    for item in payload.get("verdict_vocabulary", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload.get('truth_boundary', {}).get('summary')}", ""])
    return "\n".join(lines)


def render_assessment_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("assessment_summary", {})
    inputs = payload.get("assessed_inputs", {})
    lines = [
        "# External Dataset Assessment Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Overall verdict: `{summary.get('overall_verdict')}`",
        f"- Next operator action: `{summary.get('next_operator_action')}`",
        "",
        "## Input Assessments",
        "",
    ]
    for key in ("json_manifest", "folder_package_manifest"):
        assessed = inputs.get(key, {})
        lines.append(
            f"- `{key}`: `{assessed.get('shape_verdict')}` / "
            f"`{assessed.get('manifest_flavor')}`"
        )
        if assessed.get("missing_required_fields"):
            lines.append(
                f"  - Missing fields: `{', '.join(assessed.get('missing_required_fields') or [])}`"
            )
        if assessed.get("notes"):
            lines.append(f"  - Notes: `{'; '.join(assessed.get('notes') or [])}`")
    lines.extend(
        [
            "",
            "## Calibration Signals",
            "",
        ]
    )
    dashboard = payload.get("calibration_signals", {}).get("operator_dashboard", {})
    external_audit = payload.get("calibration_signals", {}).get("external_cohort_audit", {})
    eligibility = payload.get("calibration_signals", {}).get("eligibility_matrix", {})
    bundle_validation = payload.get("calibration_signals", {}).get("bundle_validation", {})
    lines.extend(
        [
            f"- Operator dashboard status: `{dashboard.get('dashboard_status')}` / "
            f"`{dashboard.get('operator_go_no_go')}`",
            f"- External cohort audit decision: `{external_audit.get('overall_decision')}`",
            f"- Missing data policy candidate-only non-governing: "
            f"`{payload.get('calibration_signals', {}).get('missing_data_policy', {}).get('candidate_only_rows_non_governing')}`",
            f"- Eligibility grounded ligand accessions: "
            f"`{', '.join(eligibility.get('grounded_ligand_accessions') or []) or 'none'}`",
            f"- Bundle checksum verified: `{bundle_validation.get('checksum_verified')}`",
        ]
    )
    lines.extend(["", "## Truth Boundary", "", f"- {payload.get('truth_boundary', {}).get('summary')}", ""])
    return "\n".join(lines)
