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

DEFAULT_PACKAGE_EXECUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_execution_preview.json"
)
DEFAULT_UNLOCK_ROUTE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unlock_route_preview.json"
)
DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_preview_hold_register_preview.json"
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


def build_training_set_preview_hold_register_preview(
    package_execution_preview: dict[str, Any],
    unlock_route_preview: dict[str, Any],
    package_blocker_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    execution_rows = package_execution_preview.get("rows") or []
    unlock_rows = unlock_route_preview.get("rows") or []
    blocker_rows = package_blocker_matrix_preview.get("rows") or []

    unlock_by_accession = _rows_by_accession(unlock_rows)
    blocker_by_accession = _rows_by_accession(blocker_rows)

    rows: list[dict[str, Any]] = []
    hold_lane_counts: Counter[str] = Counter()
    hold_reason_counts: Counter[str] = Counter()
    next_step_counts: Counter[str] = Counter()

    for execution_row in execution_rows:
        if not isinstance(execution_row, dict):
            continue
        if str(execution_row.get("execution_lane") or "").strip() != (
            "preview_hold_until_package_unlock"
        ):
            continue

        accession = str(execution_row.get("accession") or "").strip()
        if not accession:
            continue

        unlock_row = unlock_by_accession.get(accession, {})
        blocker_row = blocker_by_accession.get(accession, {})
        training_set_state = str(execution_row.get("training_set_state") or "").strip()
        next_package_action = str(execution_row.get("next_package_action") or "").strip()
        next_step = str(unlock_row.get("next_step") or next_package_action).strip()

        if next_package_action == "keep_visible_as_support_only":
            hold_lane = "support_only_visibility_hold"
        else:
            hold_lane = "non_governing_visibility_hold"

        hold_reasons = _listify(
            execution_row.get("package_blockers") or blocker_row.get("package_blockers")
        )
        if not hold_reasons:
            hold_reasons = _listify(
                blocker_row.get("blocked_reasons") or unlock_row.get("blocking_context")
            )

        for reason in hold_reasons:
            hold_reason_counts[reason] += 1
        if next_step:
            next_step_counts[next_step] += 1
        hold_lane_counts[hold_lane] += 1

        rows.append(
            {
                "accession": accession,
                "preview_hold_state": "preview_hold_until_package_unlock",
                "hold_lane": hold_lane,
                "training_set_state": training_set_state,
                "unlock_route_state": unlock_row.get("unlock_route_state"),
                "priority_bucket": execution_row.get("priority_bucket")
                or blocker_row.get("priority_bucket"),
                "next_package_action": next_package_action
                or "keep_visible_as_support_only",
                "next_unlock_step": next_step or "preserve_current_preview_state",
                "hold_reasons": hold_reasons,
                "source_fix_refs": _listify(unlock_row.get("source_fix_refs")),
                "modality_gap_categories": _listify(
                    blocker_row.get("modality_gap_categories")
                ),
                "supporting_artifacts": _listify(
                    execution_row.get("supporting_artifacts")
                )
                or _listify(unlock_row.get("supporting_artifacts"))
                or [
                    "training_set_package_execution_preview",
                    "training_set_unlock_route_preview",
                    "training_set_package_blocker_matrix_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if str(row.get("hold_lane") or "") == "support_only_visibility_hold"
            else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_hold_lane = rows[0]["hold_lane"] if rows else None

    return {
        "artifact_id": "training_set_preview_hold_register_preview",
        "schema_id": "proteosphere-training-set-preview-hold-register-preview-2026-04-03",
        "status": "report_only",
        "generated_at": package_execution_preview.get("generated_at")
        or unlock_route_preview.get("generated_at")
        or package_blocker_matrix_preview.get("generated_at"),
        "summary": {
            "selected_count": int(
                (package_execution_preview.get("summary") or {}).get("selected_count")
                or 0
            ),
            "preview_hold_row_count": len(rows),
            "current_hold_state": (
                "preview_hold_register_active"
                if rows
                else "no_preview_hold_register_entries"
            ),
            "next_hold_lane": next_hold_lane,
            "support_only_hold_count": hold_lane_counts.get(
                "support_only_visibility_hold", 0
            ),
            "non_governing_hold_count": hold_lane_counts.get(
                "non_governing_visibility_hold", 0
            ),
            "top_hold_reasons": [
                {"hold_reason": item, "accession_count": count}
                for item, count in hold_reason_counts.most_common(8)
            ],
            "top_next_steps": [
                {"next_step": item, "accession_count": count}
                for item, count in next_step_counts.most_common(8)
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_package_execution_preview": str(
                DEFAULT_PACKAGE_EXECUTION_PREVIEW
            ).replace("\\", "/"),
            "training_set_unlock_route_preview": str(
                DEFAULT_UNLOCK_ROUTE_PREVIEW
            ).replace("\\", "/"),
            "training_set_package_blocker_matrix_preview": str(
                DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This preview-hold register is report-only and fail-closed. "
                "It organizes visibility-hold rows for operator review, but it does "
                "not unlock packaging, upgrade readiness, or authorize release."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set preview hold register preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_training_set_preview_hold_register_preview(
        _load_payload(DEFAULT_PACKAGE_EXECUTION_PREVIEW),
        _load_payload(DEFAULT_UNLOCK_ROUTE_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
