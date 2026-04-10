from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRY_RUN_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_dry_run_plan.json"
)
DEFAULT_EXECUTOR_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_executor_status.json"
)
DEFAULT_BLOCKER = (
    REPO_ROOT / "artifacts" / "status" / "p87_duplicate_cleanup_real_execution_blocker.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_delete_ready_manifest_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "duplicate_cleanup_delete_ready_manifest_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_protected_path(path_text: str) -> bool:
    normalized = str(path_text or "").replace("/", "\\").lower()
    if ".part" in normalized or ".partial" in normalized:
        return True
    protected_fragments = (
        "\\latest.json",
        "\\data\\canonical\\",
        "\\data\\packages\\",
        "\\runs\\real_data_benchmark\\full_results\\",
        "\\artifacts\\status\\",
    )
    return any(fragment in normalized for fragment in protected_fragments)


def _select_current_valid_action(actions: list[dict[str, Any]]) -> dict[str, Any]:
    for action in actions:
        keeper_path = str(action.get("keeper_path") or "")
        removal_paths = [str(path) for path in (action.get("removal_paths") or [])]
        if not keeper_path or not removal_paths:
            continue
        if not (REPO_ROOT / keeper_path).exists():
            continue
        if not all((REPO_ROOT / path).exists() for path in removal_paths):
            continue
        return dict(action)
    return {}


def build_duplicate_cleanup_delete_ready_manifest_preview(
    dry_run_plan: dict[str, Any],
    executor_status: dict[str, Any],
    blocker: dict[str, Any],
) -> dict[str, Any]:
    first_action = _select_current_valid_action(list(dry_run_plan.get("actions") or []))
    removal_paths = list(first_action.get("removal_paths") or [])
    keeper_path = str(first_action.get("keeper_path") or "")
    duplicate_class = str(first_action.get("duplicate_class") or "")
    sha256 = str(first_action.get("sha256") or "")
    exact_duplicate_only = duplicate_class.startswith("exact_duplicate")
    no_partial_paths = not any(
        ".part" in str(path).lower() or ".partial" in str(path).lower()
        for path in [keeper_path, *removal_paths]
    )
    no_latest_json = not any(
        str(path).replace("/", "\\").lower().endswith("\\latest.json")
        for path in [keeper_path, *removal_paths]
    )
    keeper_exists = (REPO_ROOT / keeper_path).exists() if keeper_path else False
    removal_paths_present = all((REPO_ROOT / str(path)).exists() for path in removal_paths)
    protected_path_hits = [path for path in removal_paths if _is_protected_path(str(path))]
    primary_copy_preserved = bool(keeper_path) and not _is_protected_path(keeper_path)
    checksum_present = bool(sha256)
    all_constraints_satisfied_preview = all(
        (
            bool(first_action),
            exact_duplicate_only,
            no_partial_paths,
            no_latest_json,
            keeper_exists,
            removal_paths_present,
            primary_copy_preserved,
            checksum_present,
            not protected_path_hits,
        )
    )
    return {
        "artifact_id": "duplicate_cleanup_delete_ready_manifest_preview",
        "schema_id": "proteosphere-duplicate-cleanup-delete-ready-manifest-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "plan_id": dry_run_plan.get("plan_id"),
        "preview_manifest_status": (
            "frozen_preview_pending_authorization"
            if first_action
            else "no_current_valid_batch_requires_refresh"
        ),
        "execution_blocked": not bool((blocker.get("answer") or {}).get("safe_to_execute_today")),
        "executor_validation_status": executor_status.get("validation", {}).get("status"),
        "action_count": 1 if first_action else 0,
        "constraint_checks": {
            "exact_duplicates_only": exact_duplicate_only,
            "no_partial_paths": no_partial_paths,
            "no_latest_json": no_latest_json,
            "keeper_path_exists": keeper_exists,
            "removal_paths_present": removal_paths_present,
            "checksum_present": checksum_present,
            "primary_copy_preserved": primary_copy_preserved,
            "protected_path_hits": protected_path_hits,
            "all_constraints_satisfied_preview": all_constraints_satisfied_preview,
        },
        "delete_batch": {
            "cohort_name": first_action.get("cohort_name"),
            "duplicate_class": duplicate_class,
            "keeper_path": keeper_path,
            "removal_paths": removal_paths,
            "sha256": sha256,
            "reclaimable_bytes": int(first_action.get("reclaimable_bytes") or 0),
            "validation_gates": first_action.get("validation_gates") or [],
        },
        "truth_boundary": {
            "report_only": True,
            "delete_enabled": False,
            "mutation_allowed": False,
            "surviving_canonical_copy_required": True,
            "separate_authorization_required": True,
            "requires_plan_refresh_when_consumed": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    batch = payload["delete_batch"]
    lines = [
        "# Duplicate Cleanup Delete-Ready Manifest Preview",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Preview status: `{payload['preview_manifest_status']}`",
        f"- Execution blocked: `{payload['execution_blocked']}`",
        "- Constraint checks satisfied: "
        f"`{payload['constraint_checks']['all_constraints_satisfied_preview']}`",
        f"- Cohort: `{batch['cohort_name']}`",
        f"- Duplicate class: `{batch['duplicate_class']}`",
        f"- Reclaimable bytes: `{batch['reclaimable_bytes']}`",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a non-destructive delete-ready duplicate cleanup manifest preview."
    )
    parser.add_argument("--dry-run-plan", type=Path, default=DEFAULT_DRY_RUN_PLAN)
    parser.add_argument("--executor-status", type=Path, default=DEFAULT_EXECUTOR_STATUS)
    parser.add_argument("--blocker", type=Path, default=DEFAULT_BLOCKER)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_duplicate_cleanup_delete_ready_manifest_preview(
        _read_json(args.dry_run_plan),
        _read_json(args.executor_status),
        _read_json(args.blocker),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
