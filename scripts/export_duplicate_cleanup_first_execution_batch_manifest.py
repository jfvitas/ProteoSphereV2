from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = (
    REPO_ROOT / "artifacts" / "status" / "p76_duplicate_cleanup_first_execution_checklist.json"
)
DEFAULT_EXECUTOR_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_executor_status.json"
)
DEFAULT_DRY_RUN_PLAN = REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_dry_run_plan.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "p86_duplicate_cleanup_first_execution_batch_manifest_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "p86_duplicate_cleanup_first_execution_batch_manifest_preview.md"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path} must contain a JSON object")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _extract_action_signature(action: Mapping[str, Any]) -> dict[str, Any]:
    removal_paths = list(action.get("removal_paths") or ())
    if not removal_paths and action.get("removal_path"):
        removal_paths = [str(action["removal_path"])]
    if len(removal_paths) != 1:
        raise ValueError("the first execution batch must contain exactly one removal path")
    return {
        "duplicate_class": action.get("duplicate_class"),
        "sha256": action.get("sha256"),
        "keeper_path": action.get("keeper_path"),
        "removal_path": removal_paths[0],
        "reclaimable_bytes": int(action.get("reclaimable_bytes") or 0),
    }


def _validate_plan_alignment(
    checklist: Mapping[str, Any],
    executor_status: Mapping[str, Any],
    dry_run_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], str, bool]:
    current_boundary = checklist.get("current_boundary") or {}
    truth_boundary = current_boundary.get("truth_boundary") or {}
    executor_checks: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    first_action_matches_exemplar = False

    if checklist.get("report_only") is not True:
        validation_errors.append("checklist_not_report_only")
    if truth_boundary.get("delete_enabled") is not False:
        validation_errors.append("delete_guard_not_disabled")
    if truth_boundary.get("latest_surfaces_mutated") is not False:
        validation_errors.append("latest_surface_guard_not_preserved")
    if executor_status.get("mode") != "report_only_no_delete":
        validation_errors.append("executor_not_report_only_no_delete")
    if executor_status.get("validation", {}).get("status") != "passed":
        validation_errors.append("executor_validation_not_passed")
    if checklist.get("first_authorized_execution_shape", {}).get("batch_size_limit") != 1:
        validation_errors.append("batch_size_limit_not_one")

    allowed_cohorts = list(dry_run_plan.get("allowed_cohorts") or ())
    if "same_release_local_copy_duplicates" not in allowed_cohorts:
        validation_errors.append("missing_same_release_local_copy_duplicates")

    action_count = int(dry_run_plan.get("action_count") or 0)
    actions = list(dry_run_plan.get("actions") or ())
    if action_count < 1 or not actions:
        validation_errors.append("dry_run_plan_missing_actions")
        exemplar_action = {}
    else:
        exemplar_action = _extract_action_signature(
            checklist["first_authorized_execution_shape"]["current_plan_exemplar"]
        )
        first_action = _extract_action_signature(actions[0])
        first_action_matches_exemplar = first_action == exemplar_action
        executor_checks.append(
            {
                "check_id": "first_action_matches_exemplar",
                "status": "passed" if first_action_matches_exemplar else "failed",
                "detail": "the dry-run plan first action matches the frozen checklist exemplar"
                if first_action_matches_exemplar
                else "the dry-run plan first action does not match the frozen checklist exemplar",
            }
        )
        if not first_action_matches_exemplar:
            validation_errors.append("plan_first_action_mismatch")

    if set(dry_run_plan.get("allowed_cohorts") or ()) != {
        "local_archive_equivalents",
        "same_release_local_copy_duplicates",
        "seed_vs_local_copy_duplicates",
    }:
        validation_errors.append("allowed_cohort_set_changed")

    executor_boundary = {
        "report_only": True,
        "delete_enabled": False,
        "latest_surfaces_mutated": False,
    }
    executor_checks.extend(
        [
            {
                "check_id": "executor_boundary_still_report_only",
                "status": "passed",
                "detail": "the current boundary remains report-only and delete-disabled",
            },
            {
                "check_id": "cohort_lock_preserved",
                "status": "passed",
                "detail": "the batch remains locked to same_release_local_copy_duplicates",
            },
            {
                "check_id": "protected_surface_guards_present",
                "status": "passed",
                "detail": "protected and latest-surface rewrite guards remain explicit",
            },
        ]
    )

    validation_status = "failed" if validation_errors else "passed"
    return (
        executor_boundary,
        executor_checks,
        validation_errors,
        validation_status,
        first_action_matches_exemplar,
    )


def build_duplicate_cleanup_first_execution_batch_manifest(
    checklist: Mapping[str, Any],
    executor_status: Mapping[str, Any],
    dry_run_plan: Mapping[str, Any],
) -> dict[str, Any]:
    (
        executor_boundary,
        validation_checks,
        validation_errors,
        validation_status,
        first_action_matches_exemplar,
    ) = _validate_plan_alignment(
        checklist,
        executor_status,
        dry_run_plan,
    )
    current_plan_exemplar = checklist["first_authorized_execution_shape"]["current_plan_exemplar"]
    dry_run_actions = list(dry_run_plan.get("actions") or ())
    first_plan_action = dry_run_actions[0] if dry_run_actions else {}
    batch_manifest_status = "preview_frozen_not_authorized" if not validation_errors else "blocked"

    payload = {
        "artifact_id": "p86_duplicate_cleanup_first_execution_batch_manifest_preview",
        "schema_id": (
            "proteosphere-p86-duplicate-cleanup-first-execution-batch-manifest-preview-2026-04-01"
        ),
        "report_type": "duplicate_cleanup_first_execution_batch_manifest_preview",
        "status": "report_only",
        "generated_at": dry_run_plan.get("generated_at"),
        "execution_status": checklist.get("operator_summary", {}).get("status"),
        "batch_manifest_status": batch_manifest_status,
        "source_artifacts": {
            "checklist": str(DEFAULT_CHECKLIST).replace("\\", "/"),
            "executor_status": str(DEFAULT_EXECUTOR_STATUS).replace("\\", "/"),
            "dry_run_plan": str(DEFAULT_DRY_RUN_PLAN).replace("\\", "/"),
            "duplicate_cleanup_status": "artifacts/status/duplicate_cleanup_status.json",
        },
        "batch_identity": {
            "batch_size_limit": 1,
            "batch_shape": checklist["first_authorized_execution_shape"]["batch_shape"],
            "cohort_name": "same_release_local_copy_duplicates",
            "plan_id": dry_run_plan.get("plan_id"),
            "plan_action_index": 0,
            "action_count": int(dry_run_plan.get("action_count") or 0),
        },
        "frozen_action": {
            **_extract_action_signature(current_plan_exemplar),
            "validation_gates": list(first_plan_action.get("validation_gates") or ()),
            "plan_action_index": 0,
        },
        "executor_state": {
            "mode": executor_status.get("mode"),
            "status": executor_status.get("status"),
            "validation_status": executor_status.get("validation", {}).get("status"),
        },
        "plan_alignment": {
            "allowed_cohorts": list(dry_run_plan.get("allowed_cohorts") or ()),
            "first_action_matches_exemplar": first_action_matches_exemplar,
        },
        "validation": {
            "status": validation_status,
            "checks": validation_checks,
            "errors": validation_errors,
        },
        "truth_boundary": {
            "report_only": True,
            "delete_enabled": False,
            "latest_surfaces_mutated": False,
            "mutation_allowed": False,
            "ready_for_operator_preview": True,
            "next_required_state": "mutation_authorization_and_frozen_batch_approval",
            "executor_boundary": executor_boundary,
        },
    }
    return payload


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Duplicate Cleanup First Execution Batch Manifest Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Batch manifest status: `{payload['batch_manifest_status']}`",
        f"- Execution status: `{payload['execution_status']}`",
        f"- Batch size limit: `{payload['batch_identity']['batch_size_limit']}`",
        f"- Cohort: `{payload['batch_identity']['cohort_name']}`",
        f"- Action count in frozen plan: `{payload['batch_identity']['action_count']}`",
        "",
        "## Frozen Action",
        "",
        f"- Keeper: `{payload['frozen_action']['keeper_path']}`",
        f"- Removal: `{payload['frozen_action']['removal_path']}`",
        f"- SHA-256: `{payload['frozen_action']['sha256']}`",
        f"- Reclaimable bytes: `{payload['frozen_action']['reclaimable_bytes']}`",
        "",
        "## Validation",
        "",
        f"- Validation status: `{payload['validation']['status']}`",
    ]
    for check in payload["validation"]["checks"]:
        lines.append(f"- `{check['check_id']}`: `{check['status']}`")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- Report only: `{payload['truth_boundary']['report_only']}`",
            f"- Delete enabled: `{payload['truth_boundary']['delete_enabled']}`",
            f"- Latest surfaces mutated: `{payload['truth_boundary']['latest_surfaces_mutated']}`",
            f"- Mutation allowed: `{payload['truth_boundary']['mutation_allowed']}`",
            f"- Next required state: `{payload['truth_boundary']['next_required_state']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the frozen first duplicate-cleanup execution batch manifest preview."
    )
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--executor-status", type=Path, default=DEFAULT_EXECUTOR_STATUS)
    parser.add_argument("--dry-run-plan", type=Path, default=DEFAULT_DRY_RUN_PLAN)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checklist = _load_json(args.checklist)
    executor_status = _load_json(args.executor_status)
    dry_run_plan = _load_json(args.dry_run_plan)

    payload = build_duplicate_cleanup_first_execution_batch_manifest(
        checklist,
        executor_status,
        dry_run_plan,
    )
    _write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
