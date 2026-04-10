from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_readiness_preview.json"
)
DEFAULT_FINAL_BUNDLE = (
    REPO_ROOT / "artifacts" / "status" / "final_structured_dataset_bundle_preview.json"
)
DEFAULT_COMPLETION_SUMMARY = (
    REPO_ROOT / "artifacts" / "status" / "post_tail_completion_summary.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_closure_queue_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_grade_closure_queue_preview.md"
)
DEFAULT_EXPANSION_BACKLOG = (
    REPO_ROOT / "docs" / "reports" / "procurement_expansion_inventory_2026_04_05.md"
)
DEFAULT_RESOLUTION_BOARD = (
    REPO_ROOT / "artifacts" / "status" / "release_blocker_resolution_board_preview.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_grade_closure_queue_preview(
    *,
    readiness: dict[str, Any],
    final_bundle: dict[str, Any],
    completion_summary: dict[str, Any],
) -> dict[str, Any]:
    resolution_board = _read_json(DEFAULT_RESOLUTION_BOARD)
    board_summary = resolution_board.get("summary") or {}
    readiness_summary = readiness.get("summary") or {}
    final_bundle_summary = final_bundle.get("summary") or {}
    blocker_rows = readiness.get("blocker_rows") or []
    evidence_paths = readiness.get("evidence_paths") or {}

    evidence_lookup = {
        "runtime maturity": evidence_paths.get("run_summary"),
        "source coverage depth": evidence_paths.get("source_coverage"),
        "provenance/reporting depth": evidence_paths.get("release_corpus_evidence_ledger"),
    }

    queue_rows = []
    if board_summary.get("release_v1_bar_state") != "closed":
        queue_rows = [
            {
                "rank": row.get("rank"),
                "action_id": (
                    "release-grade-"
                    + str(row.get("blocker", "unknown")).lower().replace(" ", "-")
                ),
                "blocker": row.get("blocker"),
                "current_state": row.get("current_state"),
                "next_action": row.get("next_action"),
                "evidence_path": evidence_lookup.get(row.get("blocker")),
                "depends_on_final_dataset_bundle": True,
                "ready_to_execute": bool(final_bundle.get("status") == "completed"),
            }
            for row in blocker_rows
        ]

    return {
        "artifact_id": "release_grade_closure_queue_preview",
        "schema_id": "proteosphere-release-grade-closure-queue-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "release_grade_status": readiness_summary.get("release_grade_status"),
            "queue_length": len(queue_rows),
            "ready_to_execute_count": sum(1 for row in queue_rows if row["ready_to_execute"]),
            "final_dataset_bundle_present": final_bundle.get("status") == "completed",
            "post_tail_completion_status": completion_summary.get("status"),
            "package_readiness_state": final_bundle_summary.get("package_readiness_state"),
            "strict_governing_training_view_count": final_bundle_summary.get(
                "strict_governing_training_view_count"
            ),
            "all_visible_training_candidates_view_count": final_bundle_summary.get(
                "all_visible_training_candidates_view_count"
            ),
            "next_phase_backlog_path": str(DEFAULT_EXPANSION_BACKLOG).replace("\\", "/"),
            "release_v1_bar_state": board_summary.get("release_v1_bar_state"),
            "deferred_to_v2_count": board_summary.get("deferred_to_v2_count"),
        },
        "queue_rows": queue_rows,
        "evidence_paths": {
            "release_grade_readiness_preview": str(DEFAULT_READINESS).replace("\\", "/"),
            "final_structured_dataset_bundle_preview": str(DEFAULT_FINAL_BUNDLE).replace(
                "\\", "/"
            ),
            "post_tail_completion_summary": str(DEFAULT_COMPLETION_SUMMARY).replace("\\", "/"),
            "procurement_expansion_inventory": str(DEFAULT_EXPANSION_BACKLOG).replace("\\", "/"),
            "release_blocker_resolution_board_preview": str(DEFAULT_RESOLUTION_BOARD).replace(
                "\\", "/"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This queue ranks the remaining release-grade blockers without upgrading "
                "the benchmark summary to release-ready. It is an execution-planning "
                "surface only."
            ),
            "report_only": True,
            "release_authority": False,
            "uses_existing_evidence_only": True,
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    queue_rows = payload.get("queue_rows") or []
    lines = [
        "# Release Grade Closure Queue Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Release-grade status: `{summary.get('release_grade_status')}`",
        f"- Queue length: `{summary.get('queue_length')}`",
        f"- Final dataset bundle present: `{summary.get('final_dataset_bundle_present')}`",
        f"- Strict governing rows: `{summary.get('strict_governing_training_view_count')}`",
        "",
        "## Ranked Actions",
        "",
    ]
    for row in queue_rows:
        lines.append(
            f"- `{row['rank']}` `{row['blocker']}` -> `{row['next_action']}` "
            f"(ready_to_execute=`{str(row['ready_to_execute']).lower()}`)"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            "- Report only: `true`",
            "- Release authority: `false`",
            "- Expansion backlog deferred until new storage is available",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the ranked release-grade closure queue preview."
    )
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--final-bundle", type=Path, default=DEFAULT_FINAL_BUNDLE)
    parser.add_argument("--completion-summary", type=Path, default=DEFAULT_COMPLETION_SUMMARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_grade_closure_queue_preview(
        readiness=_read_json(args.readiness),
        final_bundle=_read_json(args.final_bundle),
        completion_summary=_read_json(args.completion_summary),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
