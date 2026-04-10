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

from scripts.tasklib import save_json  # noqa: E402

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_candidates_preview.json"
)
GIB = 1024**3


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _walk_files(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        rows.append(
            {
                "path": path,
                "name": path.name,
                "size_bytes": int(size),
            }
        )
    return rows


def build_procurement_space_recovery_candidates_preview(
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    local_copies_root = REPO_ROOT / "data" / "raw" / "local_copies"
    seed_root = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"

    local_rows = _walk_files(local_copies_root)
    seed_rows = _walk_files(seed_root)
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in local_rows + seed_rows:
        groups[(row["name"], row["size_bytes"])].append(row)

    candidates: list[dict[str, Any]] = []
    for row in local_rows:
        path = row["path"]
        key = (row["name"], row["size_bytes"])
        matches = groups.get(key, [])
        reason = None
        reclaim_bytes = row["size_bytes"]
        safety_tier = "review_required"

        if len(matches) > 1:
            reason = "duplicate_name_and_size_detected"
            safety_tier = "better_candidate"
        elif "__extracted" in str(path).replace("\\", "/"):
            reason = "large_extracted_local_copy"
        elif path.suffix.lower() in {".gz", ".zip", ".tar", ".db"}:
            reason = "large_local_copy_archive_or_db"
        else:
            continue

        candidates.append(
            {
                "path": str(path).replace("\\", "/"),
                "filename": row["name"],
                "size_bytes": row["size_bytes"],
                "size_gib": round(row["size_bytes"] / GIB, 3),
                "reason": reason,
                "safety_tier": safety_tier,
                "duplicate_match_count": len(matches),
                "reclaim_bytes_if_removed": reclaim_bytes,
                "reclaim_gib_if_removed": round(reclaim_bytes / GIB, 3),
            }
        )

    candidates.sort(
        key=lambda row: (
            0 if row["safety_tier"] == "better_candidate" else 1,
            -(row["reclaim_bytes_if_removed"] or 0),
        )
    )

    top_candidates = candidates[:15]
    total_ranked_reclaim_bytes = sum(
        int(row.get("reclaim_bytes_if_removed") or 0) for row in top_candidates
    )
    duplicate_candidate_count = sum(
        1 for row in top_candidates if row.get("reason") == "duplicate_name_and_size_detected"
    )

    if not top_candidates:
        recovery_state = "no_candidates_detected"
        next_action = "No local space-recovery candidates were detected in the scanned roots."
    elif duplicate_candidate_count > 0:
        recovery_state = "duplicate_first_recovery_lane_available"
        next_action = (
            "Start with the duplicate-name-and-size local-copy candidates "
            "before touching unique large files."
        )
    else:
        recovery_state = "manual_review_recovery_lane_only"
        next_action = (
            "Only review-required large local-copy candidates were detected; "
            "inspect manually before deleting anything."
        )

    return {
        "artifact_id": "procurement_space_recovery_candidates_preview",
        "schema_id": "proteosphere-procurement-space-recovery-candidates-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "recovery_state": recovery_state,
            "scanned_local_copy_file_count": len(local_rows),
            "scanned_seed_file_count": len(seed_rows),
            "ranked_candidate_count": len(top_candidates),
            "duplicate_first_candidate_count": duplicate_candidate_count,
            "total_ranked_reclaim_bytes": total_ranked_reclaim_bytes,
            "total_ranked_reclaim_gib": round(total_ranked_reclaim_bytes / GIB, 3),
            "non_mutating": True,
            "report_only": True,
        },
        "rows": top_candidates,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "local_copies_root": str(local_copies_root).replace("\\", "/"),
            "protein_data_scope_seed_root": str(seed_root).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only ranked list of potential local file-space "
                "recovery candidates. It does not move or delete anything and "
                "does not prove semantic safety beyond the reported heuristics."
            ),
            "report_only": True,
            "non_mutating": True,
            "heuristic_candidate_ranking": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery candidates preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_space_recovery_candidates_preview()
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
