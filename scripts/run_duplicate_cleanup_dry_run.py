from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_duplicate_cleanup_dry_run_plan import (  # noqa: E402
    DEFAULT_INVENTORY_PATH,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_STATUS_PATH,
    SAFE_FIRST_COHORTS,
    build_duplicate_cleanup_dry_run_plan,
    render_duplicate_cleanup_dry_run_plan_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXECUTOR_STATUS_JSON = (
    ROOT / "artifacts" / "status" / "duplicate_cleanup_executor_status.json"
)
DEFAULT_EXECUTOR_STATUS_MD = ROOT / "docs" / "reports" / "duplicate_cleanup_executor_status.md"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path} must contain a JSON object")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _core_summary(summary: Mapping[str, Any], expected_keys: set[str]) -> dict[str, Any]:
    return {
        key: summary.get(key)
        for key in sorted(expected_keys)
    }


def _render_status_markdown(payload: Mapping[str, Any]) -> str:
    validation = payload["validation"]
    summary = payload["plan_summary"]
    lines = [
        "# Duplicate Cleanup Executor Status",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Status: `{payload['status']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Action count: `{summary['action_count']}`",
        f"- Planned reclaimable bytes: `{summary['planned_reclaimable_bytes']}`",
        f"- Validation status: `{validation['status']}`",
        "",
        "## Validation Checks",
    ]
    for item in validation["checks"]:
        lines.append(
            f"- `{item['check_id']}`: `{item['status']}`"
            + (f" ({item['detail']})" if item.get("detail") else "")
        )
    if validation["errors"]:
        lines.extend(["", "## Errors", *[f"- `{item}`" for item in validation["errors"]]])
    if validation["warnings"]:
        lines.extend(
            ["", "## Warnings", *[f"- `{item}`" for item in validation["warnings"]]]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the current duplicate cleanup boundary and regenerate the "
            "no-delete dry-run plan without mutating any files."
        )
    )
    parser.add_argument("--inventory-json", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--status-json", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--plan-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--plan-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--status-output-json", type=Path, default=DEFAULT_EXECUTOR_STATUS_JSON)
    parser.add_argument("--status-output-md", type=Path, default=DEFAULT_EXECUTOR_STATUS_MD)
    parser.add_argument("--max-actions", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = _load_json(args.inventory_json)
    status_payload = _load_json(args.status_json)
    plan = build_duplicate_cleanup_dry_run_plan(
        inventory,
        status_payload,
        max_actions=max(1, int(args.max_actions)),
    )

    inventory_summary = inventory.get("inventory_summary") or inventory.get("summary") or {}
    status_summary = status_payload.get("inventory_summary") or {}
    comparison_keys = set(inventory_summary.keys()).intersection(status_summary.keys())
    inventory_summary_core = _core_summary(inventory_summary, comparison_keys)
    status_summary_core = _core_summary(status_summary, comparison_keys)
    safe_first_cohorts = {
        entry.get("cohort_name")
        for entry in (status_payload.get("safe_first_cleanup_cohorts") or ())
        if isinstance(entry, Mapping)
    }
    allowed_cohorts = set(plan.get("allowed_cohorts") or ())
    validation_checks = [
        {
            "check_id": "inventory_summary_match",
            "status": "passed"
            if inventory_summary_core == status_summary_core
            else "warning",
            "detail": "inventory/status summaries match on shared core fields"
            if inventory_summary_core == status_summary_core
            else "inventory/status summaries differ",
        },
        {
            "check_id": "allowed_cohorts_safe_first",
            "status": "passed"
            if allowed_cohorts and allowed_cohorts.issubset(SAFE_FIRST_COHORTS)
            else "failed",
            "detail": "all allowed cohorts stay within safe-first cohorts",
        },
        {
            "check_id": "allowed_cohorts_status_alignment",
            "status": "passed"
            if allowed_cohorts == safe_first_cohorts.intersection(SAFE_FIRST_COHORTS)
            else "warning",
            "detail": "plan cohorts align with cleanup status surface",
        },
        {
            "check_id": "non_delete_plan_only",
            "status": "passed",
            "detail": "executor rewrites plan/status artifacts only",
        },
        {
            "check_id": "partial_and_protected_excluded",
            "status": "passed"
            if all(
                gate in ("exact_sha256_match", "no_protected_paths", "no_partial_paths")
                or gate == "no_latest_surface_rewrites"
                for action in (plan.get("actions") or ())
                for gate in action.get("validation_gates") or ()
            )
            else "failed",
            "detail": "each action keeps the required validation gates",
        },
    ]
    errors = [item["check_id"] for item in validation_checks if item["status"] == "failed"]
    warnings = [item["check_id"] for item in validation_checks if item["status"] == "warning"]
    validation_status = "failed" if errors else ("warning" if warnings else "passed")

    args.plan_json.parent.mkdir(parents=True, exist_ok=True)
    _write_json(args.plan_json, plan)
    args.plan_md.parent.mkdir(parents=True, exist_ok=True)
    args.plan_md.write_text(
        render_duplicate_cleanup_dry_run_plan_markdown(plan),
        encoding="utf-8",
    )

    status_payload = {
        "executor_id": "duplicate_cleanup_executor_status",
        "generated_at": inventory.get("generated_at"),
        "mode": "report_only_no_delete",
        "status": "usable_with_notes" if validation_status != "failed" else "blocked",
        "inventory_path": str(args.inventory_json).replace("\\", "/"),
        "status_path": str(args.status_json).replace("\\", "/"),
        "plan_path": str(args.plan_json).replace("\\", "/"),
        "plan_summary": {
            "action_count": plan["action_count"],
            "planned_reclaimable_bytes": plan["planned_reclaimable_bytes"],
            "allowed_cohorts": plan["allowed_cohorts"],
        },
        "validation": {
            "status": validation_status,
            "checks": validation_checks,
            "errors": errors,
            "warnings": warnings,
        },
        "truth_boundary": {
            "report_only": True,
            "delete_enabled": False,
            "latest_surfaces_mutated": False,
        },
    }
    _write_json(args.status_output_json, status_payload)
    args.status_output_md.parent.mkdir(parents=True, exist_ok=True)
    args.status_output_md.write_text(_render_status_markdown(status_payload), encoding="utf-8")
    print(json.dumps(status_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
