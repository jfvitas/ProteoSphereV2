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

from training_set_builder_preview_support import read_json, write_json  # noqa: E402

DEFAULT_PACKAGE_TRANSITION_BATCH_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_package_transition_batch_preview.json"
)
DEFAULT_UNBLOCK_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_PACKAGE_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_execution_preview.json"
)


def _load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


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


def _rows_by_accession(rows: Any) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return indexed
    for row in rows:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def build_training_set_package_execution_preview(
    package_transition_batch_preview: dict[str, Any],
    unblock_plan_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any],
) -> dict[str, Any]:
    batch_rows = package_transition_batch_preview.get("rows") or []
    unblock_rows = unblock_plan_preview.get("rows") or []
    package_summary = package_readiness_preview.get("summary") or {}

    unblock_by_accession = _rows_by_accession(unblock_rows)

    rows: list[dict[str, Any]] = []
    execution_lane_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()

    for batch_row in batch_rows:
        if not isinstance(batch_row, dict):
            continue
        accession = str(batch_row.get("accession") or "").strip()
        if not accession:
            continue

        unblock_row = unblock_by_accession.get(accession, {})
        next_package_action = str(batch_row.get("next_package_action") or "").strip()
        direct_routes = _listify(unblock_row.get("direct_remediation_routes"))
        recommended_actions = _listify(unblock_row.get("recommended_next_actions"))

        if "keep_visible_as_support_only" in next_package_action:
            execution_lane = "preview_hold_until_package_unlock"
        else:
            execution_lane = "package_unlock_follow_up"

        for action in [next_package_action, *recommended_actions]:
            if action:
                action_counts[action] += 1
        for blocker in _listify(batch_row.get("package_blockers")):
            blocker_counts[blocker] += 1
        execution_lane_counts[execution_lane] += 1

        rows.append(
            {
                "accession": accession,
                "package_execution_state": "package_transition_blocked",
                "execution_lane": execution_lane,
                "training_set_state": batch_row.get("training_set_state"),
                "priority_bucket": batch_row.get("priority_bucket"),
                "next_package_action": next_package_action or "unlock_package_transition",
                "direct_remediation_routes": direct_routes,
                "recommended_next_actions": recommended_actions,
                "package_blockers": _listify(batch_row.get("package_blockers")),
                "global_package_gate_blockers": _listify(
                    batch_row.get("global_package_gate_blockers")
                    or package_summary.get("blocked_reasons")
                ),
                "supporting_artifacts": _listify(batch_row.get("supporting_artifacts"))
                or _listify(unblock_row.get("supporting_artifacts"))
                or [
                    "training_set_package_transition_batch_preview",
                    "training_set_unblock_plan_preview",
                    "package_readiness_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if str(row.get("execution_lane") or "") == "preview_hold_until_package_unlock"
            else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_execution_lane = rows[0]["execution_lane"] if rows else None

    return {
        "artifact_id": "training_set_package_execution_preview",
        "schema_id": "proteosphere-training-set-package-execution-preview-2026-04-03",
        "status": "report_only",
        "generated_at": package_transition_batch_preview.get("generated_at")
        or unblock_plan_preview.get("generated_at")
        or package_readiness_preview.get("generated_at"),
        "summary": {
            "selected_count": int(
                (package_transition_batch_preview.get("summary") or {}).get(
                    "selected_count"
                )
                or 0
            ),
            "package_execution_row_count": len(rows),
            "current_execution_state": (
                "package_execution_follow_up_required"
                if rows
                else "no_package_execution_follow_up_required"
            ),
            "next_execution_lane": next_execution_lane,
            "preview_hold_count": execution_lane_counts.get(
                "preview_hold_until_package_unlock", 0
            ),
            "unlock_follow_up_count": execution_lane_counts.get(
                "package_unlock_follow_up", 0
            ),
            "top_next_actions": [
                {"next_action": item, "accession_count": count}
                for item, count in action_counts.most_common(8)
            ],
            "top_package_blockers": [
                {"package_blocker": item, "accession_count": count}
                for item, count in blocker_counts.most_common(8)
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_package_transition_batch_preview": str(
                DEFAULT_PACKAGE_TRANSITION_BATCH_PREVIEW
            ).replace("\\", "/"),
            "training_set_unblock_plan_preview": str(
                DEFAULT_UNBLOCK_PLAN_PREVIEW
            ).replace("\\", "/"),
            "package_readiness_preview": str(DEFAULT_PACKAGE_READINESS_PREVIEW).replace(
                "\\", "/"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This package execution preview is report-only and fail-closed. "
                "It organizes package-follow-up work, but it does not unlock packaging "
                "or authorize release."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set package execution preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_training_set_package_execution_preview(
        _load_payload(DEFAULT_PACKAGE_TRANSITION_BATCH_PREVIEW),
        _load_payload(DEFAULT_UNBLOCK_PLAN_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_READINESS_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
