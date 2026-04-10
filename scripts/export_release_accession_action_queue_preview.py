from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLOSURE_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_closure_matrix_preview.json"
)
DEFAULT_RUNTIME_MATURITY = (
    REPO_ROOT / "artifacts" / "status" / "release_runtime_maturity_preview.json"
)
DEFAULT_SOURCE_COVERAGE = (
    REPO_ROOT / "artifacts" / "status" / "release_source_coverage_depth_preview.json"
)
DEFAULT_PROVENANCE_DEPTH = (
    REPO_ROOT / "artifacts" / "status" / "release_provenance_depth_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_action_queue_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_accession_action_queue_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _release_wide_blockers(
    runtime_maturity: dict[str, Any],
    source_coverage: dict[str, Any],
    provenance_depth: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = [
        {
            "blocker": "runtime maturity",
            "state": (runtime_maturity.get("summary") or {}).get("runtime_maturity_state"),
            "next_action": (runtime_maturity.get("summary") or {}).get("next_action"),
        },
        {
            "blocker": "source coverage depth",
            "state": (source_coverage.get("summary") or {}).get("coverage_depth_state"),
            "next_action": (source_coverage.get("summary") or {}).get("next_action"),
        },
        {
            "blocker": "provenance/reporting depth",
            "state": (provenance_depth.get("summary") or {}).get("provenance_depth_state"),
            "next_action": (provenance_depth.get("summary") or {}).get("next_action"),
        },
    ]
    closed_states = {
        "qualified_for_frozen_v1_only",
        "frozen_v1_governing_sufficient",
        "row_complete_evidence_pack_ready",
    }
    return [
        row
        for row in candidates
        if row.get("state") and row.get("state") not in closed_states
    ]


def build_release_accession_action_queue_preview(
    *,
    closure_matrix: dict[str, Any],
    runtime_maturity: dict[str, Any],
    source_coverage: dict[str, Any],
    provenance_depth: dict[str, Any],
) -> dict[str, Any]:
    release_wide = _release_wide_blockers(
        runtime_maturity=runtime_maturity,
        source_coverage=source_coverage,
        provenance_depth=provenance_depth,
    )
    release_wide_labels = [row["blocker"] for row in release_wide if row.get("state")]

    lane_priority = {
        "promotion_review": 0,
        "support_only_hold": 1,
        "source_fix_followup": 2,
    }
    rows: list[dict[str, Any]] = []
    for closure_row in closure_matrix.get("rows") or []:
        closure_state = closure_row.get("closure_state")
        if closure_state == "closest_to_release":
            action_lane = "promotion_review"
            next_action = "close_release_grade_bar_then_review_promotion"
            action_summary = (
                "Closest-to-release accession. Keep the row visible, retain package-ready "
                "state, and only review promotion after the global release-grade bar clears."
            )
        elif closure_state == "blocked_pending_acquisition":
            action_lane = "source_fix_followup"
            next_action = closure_row.get("current_blocker") or closure_row.get(
                "recommended_next_step"
            )
            action_summary = (
                "Upstream source-fix or acquisition work is still required before this "
                "accession can move out of the blocked lane."
            )
        else:
            action_lane = "support_only_hold"
            next_action = closure_row.get("recommended_next_step")
            action_summary = (
                "Keep the accession visible as non-governing support while deeper coverage "
                "and release-wide evidence mature."
            )

        rows.append(
            {
                "accession": closure_row.get("accession"),
                "split": closure_row.get("split"),
                "closure_state": closure_state,
                "action_lane": action_lane,
                "priority_rank": lane_priority[action_lane],
                "benchmark_priority": closure_row.get("benchmark_priority"),
                "release_grade": closure_row.get("release_grade"),
                "package_state": closure_row.get("package_state"),
                "packet_lane": closure_row.get("packet_lane"),
                "missing_modalities": closure_row.get("missing_modalities") or [],
                "accession_specific_blockers": closure_row.get("blocker_ids") or [],
                "release_wide_blockers": release_wide_labels,
                "next_action": next_action,
                "action_summary": action_summary,
            }
        )

    rows.sort(
        key=lambda row: (
            row["priority_rank"],
            row.get("benchmark_priority") or 999,
            row["accession"],
        )
    )

    lane_counts: dict[str, int] = {}
    for row in rows:
        lane = row["action_lane"]
        lane_counts[lane] = lane_counts.get(lane, 0) + 1

    return {
        "artifact_id": "release_accession_action_queue_preview",
        "schema_id": "proteosphere-release-accession-action-queue-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "action_row_count": len(rows),
            "lane_counts": lane_counts,
            "promotion_review_count": lane_counts.get("promotion_review", 0),
            "support_only_hold_count": lane_counts.get("support_only_hold", 0),
            "source_fix_followup_count": lane_counts.get("source_fix_followup", 0),
            "top_priority_accessions": [row["accession"] for row in rows[:3]],
            "release_wide_blocker_count": len(release_wide_labels),
        },
        "release_wide_blockers": release_wide,
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This queue translates the accession closure matrix into concrete release "
                "action lanes without promoting any accession to release-ready."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    top_priority = ", ".join(summary.get("top_priority_accessions") or [])
    return "\n".join(
        [
            "# Release Accession Action Queue Preview",
            "",
            f"- Action rows: `{summary.get('action_row_count')}`",
            f"- Promotion review: `{summary.get('promotion_review_count')}`",
            f"- Support-only hold: `{summary.get('support_only_hold_count')}`",
            f"- Source-fix follow-up: `{summary.get('source_fix_followup_count')}`",
            f"- Top priority accessions: `{top_priority}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release accession action queue preview."
    )
    parser.add_argument("--closure-matrix", type=Path, default=DEFAULT_CLOSURE_MATRIX)
    parser.add_argument("--runtime-maturity", type=Path, default=DEFAULT_RUNTIME_MATURITY)
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE)
    parser.add_argument("--provenance-depth", type=Path, default=DEFAULT_PROVENANCE_DEPTH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_accession_action_queue_preview(
        closure_matrix=_read_json(args.closure_matrix),
        runtime_maturity=_read_json(args.runtime_maturity),
        source_coverage=_read_json(args.source_coverage),
        provenance_depth=_read_json(args.provenance_depth),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
