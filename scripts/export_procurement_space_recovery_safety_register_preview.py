from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_candidates_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_safety_register_preview.json"
)
GIB = 1024**3


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _looks_extracted(path: str) -> bool:
    lowered = path.lower()
    return "extracted" in lowered or "__extracted" in lowered


def _classify_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped_by_filename: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_by_filename[str(row.get("filename") or "")].append(row)

    classified_rows: list[dict[str, Any]] = []
    for row in rows:
        path = str(row.get("path") or "")
        reason = str(row.get("reason") or "")
        filename = str(row.get("filename") or "")
        filename_group = grouped_by_filename.get(filename, [])

        if reason == "duplicate_name_and_size_detected":
            extracted_present = any(
                _looks_extracted(str(group_row.get("path") or ""))
                for group_row in filename_group
            )
            non_extracted_present = any(
                not _looks_extracted(str(group_row.get("path") or ""))
                for group_row in filename_group
            )
            if extracted_present and non_extracted_present:
                safety_category = "archive_and_extracted_pair"
            else:
                safety_category = "duplicate_name_and_size_detected"
        elif reason == "large_extracted_local_copy" or _looks_extracted(path):
            safety_category = "extracted_local_copy_only"
        else:
            safety_category = "review_required_large_unique"

        classified_rows.append(
            {
                "path": path,
                "filename": filename,
                "reason": reason,
                "safety_tier": row.get("safety_tier"),
                "size_gib": row.get("size_gib"),
                "reclaim_gib_if_removed": row.get("reclaim_gib_if_removed"),
                "safety_category": safety_category,
            }
        )

    return classified_rows


def build_procurement_space_recovery_safety_register_preview(
    recovery_candidates_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    summary = (
        recovery_candidates_preview.get("summary")
        if isinstance(recovery_candidates_preview.get("summary"), dict)
        else {}
    )
    candidate_rows = recovery_candidates_preview.get("rows")
    if not isinstance(candidate_rows, list):
        candidate_rows = []

    classified_rows = _classify_rows(candidate_rows)
    category_counts: dict[str, int] = defaultdict(int)
    category_reclaim_bytes: dict[str, int] = defaultdict(int)
    for row in classified_rows:
        category = str(row.get("safety_category") or "review_required_large_unique")
        category_counts[category] += 1
        category_reclaim_bytes[category] += int(
            round(float(row.get("reclaim_gib_if_removed") or 0.0) * GIB)
        )

    grouped_rows = []
    for category in sorted(category_counts):
        rows_for_category = [
            row for row in classified_rows if row.get("safety_category") == category
        ]
        grouped_rows.append(
            {
                "safety_category": category,
                "row_count": category_counts[category],
                "total_reclaim_gib": round(category_reclaim_bytes[category] / GIB, 3),
                "rows": rows_for_category[:5],
            }
        )

    review_required_count = category_counts.get("review_required_large_unique", 0)
    duplicate_first_count = category_counts.get("duplicate_name_and_size_detected", 0)
    archive_pair_count = category_counts.get("archive_and_extracted_pair", 0)

    if not classified_rows:
        safety_state = "no_safety_rows_detected"
        next_action = "No ranked candidates are available to classify into recovery-safety lanes."
    elif review_required_count > 0 and (duplicate_first_count > 0 or archive_pair_count > 0):
        safety_state = "mixed_safety_lane_requires_manual_review"
        next_action = (
            "Prioritize the duplicate and archive/extracted lanes first, then manually review "
            "the remaining large unique candidates."
        )
    elif duplicate_first_count > 0 or archive_pair_count > 0:
        safety_state = "duplicate_first_safety_lane_available"
        next_action = (
            "The current ranked recovery lane is dominated by duplicate-safe or extracted-pair "
            "candidates and can be reviewed in that order."
        )
    else:
        safety_state = "review_required_lane_only"
        next_action = "Only review-required large unique candidates remain in the ranked lane."

    return {
        "artifact_id": "procurement_space_recovery_safety_register_preview",
        "schema_id": "proteosphere-procurement-space-recovery-safety-register-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "safety_state": safety_state,
            "ranked_candidate_count": _coerce_int(summary.get("ranked_candidate_count")),
            "safety_category_counts": dict(category_counts),
            "duplicate_first_category_count": duplicate_first_count + archive_pair_count,
            "review_required_category_count": review_required_count,
            "non_mutating": True,
            "report_only": True,
        },
        "rows_by_safety_category": grouped_rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_candidates_preview": str(
                DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH
            ).replace("\\", "/")
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only safety register derived from the ranked recovery "
                "candidates. It does not move or delete files, and its categories are "
                "heuristic review aids rather than proofs of semantic redundancy."
            ),
            "report_only": True,
            "non_mutating": True,
            "heuristic_categorization": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery safety register preview."
    )
    parser.add_argument(
        "--recovery-candidates-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_space_recovery_safety_register_preview(
        _load_json_or_default(args.recovery_candidates_preview_path, {})
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
