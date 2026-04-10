from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from external_dataset_assessment_support import read_json, write_json  # noqa: E402

DEFAULT_INTAKE_CONTRACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_intake_contract_preview.json"
)
DEFAULT_SAMPLE_EXTERNAL_MANIFEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sample_external_dataset_manifest_preview.json"
)
DEFAULT_SAMPLE_FOLDER_PACKAGE_MANIFEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sample_folder_package_manifest_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_manifest_lint_preview.json"
)

VERDICT_RANK = {
    "unsafe_for_training": 4,
    "blocked_pending_cleanup": 3,
    "blocked_pending_mapping": 2,
    "audit_only": 1,
    "usable_with_caveats": 0,
}

SHAPE_REMEDIATION_ACTIONS = {
    "json_manifest": "restore missing manifest or row fields before accepting the intake package",
    "folder_package_manifest": (
        "restore missing package manifest or row fields before accepting the intake package"
    ),
    "unrecognized_shape": "map the intake payload to an accepted shape before assessment",
}


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _sorted_unique(*values: Any) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        for text in _listify(value):
            normalized.setdefault(text.casefold(), text)
    return sorted(normalized.values(), key=str.casefold)


def _rank_verdict(verdict: str) -> int:
    return VERDICT_RANK.get(verdict, -1)


def _shape_map(intake_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    shapes = {}
    for shape in intake_contract.get("accepted_shapes") or []:
        shape_id = str(shape.get("shape_id") or "").strip()
        if shape_id:
            shapes[shape_id] = dict(shape)
    return shapes


def _detect_shape_id(manifest: dict[str, Any], accepted_shapes: dict[str, dict[str, Any]]) -> str:
    present_keys = set(manifest.keys())
    matches: list[str] = []
    for shape_id, shape in accepted_shapes.items():
        required_top_level_keys = set(shape.get("required_top_level_keys") or [])
        if required_top_level_keys and required_top_level_keys.issubset(present_keys):
            matches.append(shape_id)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return "ambiguous_shape"
    return "unrecognized_shape"


def _shape_manifest_id(manifest: dict[str, Any]) -> str:
    return str(
        manifest.get("artifact_id")
        or manifest.get("manifest_id")
        or manifest.get("manifest_path")
        or ""
    ).strip()


def _lint_required_fields(
    manifest: dict[str, Any],
    shape: dict[str, Any],
    *,
    manifest_ref: str,
    shape_id: str,
) -> dict[str, Any]:
    required_top_level_keys = _sorted_unique(shape.get("required_top_level_keys"))
    required_row_keys = _sorted_unique(shape.get("required_row_keys"))
    present_keys = sorted((str(key) for key in manifest.keys()), key=str.casefold)
    missing_top_level_keys = sorted(
        {key for key in required_top_level_keys if key not in manifest},
        key=str.casefold,
    )

    row_records: list[dict[str, Any]] = []
    missing_row_fields: list[dict[str, Any]] = []
    rows = manifest.get("rows")
    if isinstance(rows, list):
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                row_records.append(
                    {
                        "row_index": row_index,
                        "verdict": "unsafe_for_training",
                        "missing_required_row_fields": required_row_keys,
                    }
                )
                for field in required_row_keys:
                    missing_row_fields.append(
                        {
                            "manifest_ref": manifest_ref,
                            "shape_id": shape_id,
                            "scope": "row",
                            "row_index": row_index,
                            "field": field,
                            "reason": "row_is_not_an_object",
                        }
                    )
                continue

            row_missing = sorted(
                {field for field in required_row_keys if field not in row},
                key=str.casefold,
            )
            row_verdict = "usable_with_caveats" if not row_missing else "unsafe_for_training"
            row_records.append(
                {
                    "row_index": row_index,
                    "verdict": row_verdict,
                    "missing_required_row_fields": row_missing,
                }
            )
            for field in row_missing:
                missing_row_fields.append(
                    {
                        "manifest_ref": manifest_ref,
                        "shape_id": shape_id,
                        "scope": "row",
                        "row_index": row_index,
                        "field": field,
                        "reason": "missing_required_row_field",
                    }
                )
    elif required_row_keys:
        missing_row_fields.append(
            {
                "manifest_ref": manifest_ref,
                "shape_id": shape_id,
                "scope": "top_level",
                "field": "rows",
                "reason": "rows_container_missing",
            }
        )
        missing_top_level_keys = sorted(
            _sorted_unique(missing_top_level_keys, ["rows"]),
            key=str.casefold,
        )

    missing_required_fields = [
        {
            "manifest_ref": manifest_ref,
            "shape_id": shape_id,
            "scope": "top_level",
            "field": field,
            "reason": "missing_required_top_level_field",
        }
        for field in missing_top_level_keys
    ]
    missing_required_fields.extend(missing_row_fields)

    verdict = "usable_with_caveats"
    if missing_required_fields:
        verdict = "unsafe_for_training"

    return {
        "manifest_ref": manifest_ref,
        "shape_id": shape_id,
        "verdict": verdict,
        "present_top_level_keys": present_keys,
        "required_top_level_keys": required_top_level_keys,
        "required_row_keys": required_row_keys,
        "missing_required_top_level_fields": missing_top_level_keys,
        "missing_required_row_fields": _sorted_unique(
            [field["field"] for field in missing_row_fields]
        ),
        "missing_required_fields": missing_required_fields,
        "row_records": row_records,
        "row_count": len(rows) if isinstance(rows, list) else 0,
    }


def build_external_dataset_manifest_lint_preview(
    intake_contract: dict[str, Any],
    sample_external_manifest: dict[str, Any],
    sample_folder_package_manifest: dict[str, Any],
) -> dict[str, Any]:
    accepted_shapes = _shape_map(intake_contract)
    manifest_inputs = [sample_external_manifest, sample_folder_package_manifest]

    manifest_reports: list[dict[str, Any]] = []
    per_shape: dict[str, dict[str, Any]] = {}
    missing_required_fields: list[dict[str, Any]] = []

    for shape_id, shape in accepted_shapes.items():
        per_shape[shape_id] = {
            "shape_id": shape_id,
            "sample_manifest_count": 0,
            "sample_manifest_refs": [],
            "required_top_level_keys": _sorted_unique(shape.get("required_top_level_keys")),
            "required_row_keys": _sorted_unique(shape.get("required_row_keys")),
            "missing_required_top_level_fields": [],
            "missing_required_row_fields": [],
            "missing_required_fields": [],
            "verdict": "audit_only",
            "remediation_action": SHAPE_REMEDIATION_ACTIONS.get(
                shape_id, "restore missing intake fields before accepting the manifest"
            ),
        }

    unrecognized_reports: list[dict[str, Any]] = []

    for manifest in manifest_inputs:
        manifest_ref = _shape_manifest_id(manifest)
        detected_shape_id = _detect_shape_id(manifest, accepted_shapes)
        if detected_shape_id not in accepted_shapes:
            report = {
                "manifest_ref": manifest_ref,
                "detected_shape_id": detected_shape_id,
                "verdict": "unsafe_for_training",
                "missing_required_top_level_fields": [],
                "missing_required_row_fields": [],
                "missing_required_fields": [],
                "present_top_level_keys": sorted(
                    (str(key) for key in manifest.keys()), key=str.casefold
                ),
                "remediation_action": SHAPE_REMEDIATION_ACTIONS["unrecognized_shape"],
            }
            unrecognized_reports.append(report)
            continue

        shape = accepted_shapes[detected_shape_id]
        lint = _lint_required_fields(
            manifest,
            shape,
            manifest_ref=manifest_ref,
            shape_id=detected_shape_id,
        )
        lint["detected_shape_id"] = detected_shape_id
        manifest_reports.append(lint)

        shape_report = per_shape[detected_shape_id]
        shape_report["sample_manifest_count"] += 1
        shape_report["sample_manifest_refs"].append(manifest_ref)
        shape_report["missing_required_top_level_fields"].extend(
            lint["missing_required_top_level_fields"]
        )
        shape_report["missing_required_row_fields"].extend(lint["missing_required_row_fields"])
        shape_report["missing_required_fields"].extend(lint["missing_required_fields"])
        missing_required_fields.extend(lint["missing_required_fields"])
        if lint["missing_required_fields"]:
            shape_report["verdict"] = "unsafe_for_training"
        elif shape_report["verdict"] != "unsafe_for_training":
            shape_report["verdict"] = "usable_with_caveats"

    if unrecognized_reports:
        manifest_reports.extend(unrecognized_reports)

    if unrecognized_reports:
        per_shape.setdefault(
            "unrecognized_shape",
            {
                "shape_id": "unrecognized_shape",
                "sample_manifest_count": 0,
                "sample_manifest_refs": [],
                "required_top_level_keys": [],
                "required_row_keys": [],
                "missing_required_top_level_fields": [],
                "missing_required_row_fields": [],
                "missing_required_fields": [],
                "verdict": "unsafe_for_training",
                "remediation_action": SHAPE_REMEDIATION_ACTIONS["unrecognized_shape"],
            },
        )
        per_shape["unrecognized_shape"]["sample_manifest_count"] = len(unrecognized_reports)
        for report in unrecognized_reports:
            per_shape["unrecognized_shape"]["missing_required_fields"].extend(
                report["missing_required_fields"]
            )
            missing_required_fields.extend(report["missing_required_fields"])

    for shape_report in per_shape.values():
        shape_report["sample_manifest_refs"] = _sorted_unique(shape_report["sample_manifest_refs"])
        shape_report["missing_required_top_level_fields"] = _sorted_unique(
            shape_report["missing_required_top_level_fields"]
        )
        shape_report["missing_required_row_fields"] = _sorted_unique(
            shape_report["missing_required_row_fields"]
        )
        shape_report["missing_required_fields"] = sorted(
            shape_report["missing_required_fields"],
            key=lambda item: (
                str(item.get("manifest_ref") or ""),
                str(item.get("scope") or ""),
                str(item.get("field") or ""),
                int(item.get("row_index") or -1),
            ),
        )
        if shape_report["missing_required_fields"]:
            shape_report["verdict"] = "unsafe_for_training"
        elif shape_report["sample_manifest_count"]:
            shape_report["verdict"] = "usable_with_caveats"

    overall_verdict = "usable_with_caveats"
    if any(
        report["verdict"] == "unsafe_for_training" for report in manifest_reports
    ) or any(
        report["verdict"] == "unsafe_for_training" for report in per_shape.values()
    ):
        overall_verdict = "unsafe_for_training"
    elif any(report["verdict"] == "audit_only" for report in per_shape.values()):
        overall_verdict = "audit_only"

    missing_required_field_count = sum(
        len(report["missing_required_fields"]) for report in manifest_reports
    )
    missing_required_top_level_field_count = sum(
        len(report["missing_required_top_level_fields"]) for report in manifest_reports
    )
    missing_required_row_field_count = sum(
        len(report["missing_required_row_fields"]) for report in manifest_reports
    )

    per_shape_verdicts = sorted(per_shape.values(), key=lambda item: item["shape_id"])
    shape_verdict_counts = Counter(report["verdict"] for report in per_shape_verdicts)

    missing_required_fields.sort(
        key=lambda item: (
            str(item.get("manifest_ref") or ""),
            str(item.get("shape_id") or ""),
            str(item.get("scope") or ""),
            str(item.get("field") or ""),
            int(item.get("row_index") or -1),
        )
    )

    return {
        "artifact_id": "external_dataset_manifest_lint_preview",
        "schema_id": "proteosphere-external-dataset-manifest-lint-preview-2026-04-03",
        "status": "report_only",
        "generated_at": intake_contract.get("generated_at") or "",
        "summary": {
            "intake_contract_id": intake_contract.get("artifact_id") or "",
            "accepted_shape_count": len(accepted_shapes),
            "sample_manifest_count": len(manifest_inputs),
            "linted_shape_count": len(per_shape_verdicts),
            "overall_verdict": overall_verdict,
            "shape_verdict_counts": dict(shape_verdict_counts),
            "missing_required_field_count": missing_required_field_count,
            "missing_required_top_level_field_count": missing_required_top_level_field_count,
            "missing_required_row_field_count": missing_required_row_field_count,
        },
        "per_shape_verdicts": per_shape_verdicts,
        "manifest_reports": manifest_reports,
        "missing_required_fields": missing_required_fields,
        "source_artifacts": {
            "intake_contract": intake_contract.get("artifact_id"),
            "sample_manifests": [
                sample_external_manifest.get("artifact_id"),
                sample_folder_package_manifest.get("artifact_id"),
            ],
        },
        "truth_boundary": {
            "summary": (
                "This lint preview is advisory and fail-closed. It validates the current "
                "external intake shapes against the sample manifests, but it does not "
                "ingest or authorize external datasets."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an advisory external dataset manifest lint preview."
    )
    parser.add_argument("--intake-contract", type=Path, default=DEFAULT_INTAKE_CONTRACT_PREVIEW)
    parser.add_argument(
        "--sample-external-manifest",
        type=Path,
        default=DEFAULT_SAMPLE_EXTERNAL_MANIFEST_PREVIEW,
    )
    parser.add_argument(
        "--sample-folder-package-manifest",
        type=Path,
        default=DEFAULT_SAMPLE_FOLDER_PACKAGE_MANIFEST_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_manifest_lint_preview(
        read_json(args.intake_contract),
        read_json(args.sample_external_manifest),
        read_json(args.sample_folder_package_manifest),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
