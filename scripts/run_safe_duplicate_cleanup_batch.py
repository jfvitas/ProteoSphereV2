from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_dry_run_plan.json"
DEFAULT_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "safe_duplicate_cleanup_execution_log.json"
)
DEFAULT_LIMIT = 10
ALLOWED_COHORT = "same_release_local_copy_duplicates"
ALLOWED_REMOVAL_PREFIX = "data\\raw\\local_copies\\raw_rcsb\\"
PROTECTED_FRAGMENTS = (
    "\\latest.json",
    "\\data\\canonical\\",
    "\\data\\packages\\",
    "\\runs\\real_data_benchmark\\full_results\\",
    "\\artifacts\\status\\",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _normalize(path_text: str) -> str:
    return str(path_text or "").replace("/", "\\").lower()


def _is_protected_path(path_text: str) -> bool:
    normalized = _normalize(path_text)
    if ".part" in normalized or ".partial" in normalized:
        return True
    return any(fragment in normalized for fragment in PROTECTED_FRAGMENTS)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_action(action: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    cohort_name = str(action.get("cohort_name") or "")
    duplicate_class = str(action.get("duplicate_class") or "")
    keeper_path = str(action.get("keeper_path") or "")
    removal_paths = [str(path) for path in (action.get("removal_paths") or [])]
    expected_sha = str(action.get("sha256") or "").lower()

    if cohort_name != ALLOWED_COHORT:
        reasons.append("cohort_not_allowed")
    if not duplicate_class.startswith("exact_duplicate"):
        reasons.append("duplicate_class_not_exact")
    if not keeper_path:
        reasons.append("keeper_path_missing")
    if not removal_paths:
        reasons.append("removal_paths_missing")
    if not expected_sha:
        reasons.append("sha256_missing")
    if _is_protected_path(keeper_path):
        reasons.append("keeper_path_protected")
    if any(_is_protected_path(path) for path in removal_paths):
        reasons.append("removal_path_protected")
    if any(not _normalize(path).startswith(ALLOWED_REMOVAL_PREFIX) for path in removal_paths):
        reasons.append("removal_path_outside_allowed_prefix")

    keeper_abs = REPO_ROOT / keeper_path
    if not keeper_abs.exists():
        reasons.append("keeper_path_absent")
        return False, reasons

    keeper_hash = _sha256(keeper_abs).lower()
    if keeper_hash != expected_sha:
        reasons.append("keeper_hash_mismatch")

    for removal_path in removal_paths:
        removal_abs = REPO_ROOT / removal_path
        if not removal_abs.exists():
            reasons.append(f"removal_path_absent:{removal_path}")
            continue
        removal_hash = _sha256(removal_abs).lower()
        if removal_hash != expected_sha:
            reasons.append(f"removal_hash_mismatch:{removal_path}")

    return not reasons, reasons


def run_safe_cleanup_batch(plan: dict[str, Any], *, limit: int) -> dict[str, Any]:
    deleted_actions: list[dict[str, Any]] = []
    skipped_actions: list[dict[str, Any]] = []
    reclaimed_bytes = 0

    for action in plan.get("actions") or []:
        if len(deleted_actions) >= limit:
            break

        action_row = dict(action)
        valid, reasons = _validate_action(action_row)
        if not valid:
            skipped_actions.append(
                {
                    "keeper_path": action_row.get("keeper_path"),
                    "removal_paths": action_row.get("removal_paths") or [],
                    "reasons": reasons,
                }
            )
            continue

        keeper_path = str(action_row["keeper_path"])
        removal_paths = [str(path) for path in action_row.get("removal_paths") or []]
        expected_sha = str(action_row["sha256"]).lower()

        deleted_now: list[str] = []
        for removal_path in removal_paths:
            removal_abs = REPO_ROOT / removal_path
            removal_abs.unlink()
            deleted_now.append(removal_path)

        keeper_abs = REPO_ROOT / keeper_path
        keeper_still_exists = keeper_abs.exists()
        keeper_hash_after = _sha256(keeper_abs).lower() if keeper_still_exists else None
        removals_gone = all(not (REPO_ROOT / path).exists() for path in removal_paths)

        deleted_actions.append(
            {
                "cohort_name": action_row.get("cohort_name"),
                "duplicate_class": action_row.get("duplicate_class"),
                "keeper_path": keeper_path,
                "removal_paths": deleted_now,
                "sha256": expected_sha,
                "keeper_still_exists": keeper_still_exists,
                "keeper_hash_after": keeper_hash_after,
                "removals_gone": removals_gone,
                "reclaimable_bytes": int(action_row.get("reclaimable_bytes") or 0),
            }
        )
        reclaimed_bytes += int(action_row.get("reclaimable_bytes") or 0)

    return {
        "artifact_id": "safe_duplicate_cleanup_execution_log",
        "schema_id": "proteosphere-safe-duplicate-cleanup-execution-log-2026-04-02",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "explicit_user_authorized_narrow_exact_duplicate_cleanup",
        "allowed_cohort": ALLOWED_COHORT,
        "allowed_removal_prefix": ALLOWED_REMOVAL_PREFIX,
        "deleted_action_count": len(deleted_actions),
        "skipped_action_count": len(skipped_actions),
        "reclaimed_bytes": reclaimed_bytes,
        "deleted_actions": deleted_actions,
        "skipped_actions": skipped_actions[:25],
        "truth_boundary": {
            "summary": (
                "This executor only deletes exact same-release duplicates within the "
                "raw_rcsb mirror after verifying keeper presence, exact SHA-256 parity, "
                "non-protected paths, and post-delete keeper survival."
            ),
            "destructive": True,
            "scope_narrowed_to_allowed_prefix": True,
            "partial_files_touched": False,
            "latest_surfaces_touched": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a narrow, verified duplicate cleanup batch."
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = _read_json(args.plan)
    payload = run_safe_cleanup_batch(plan, limit=args.limit)
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
