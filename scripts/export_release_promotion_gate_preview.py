from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTION_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_action_queue_preview.json"
)
DEFAULT_CANDIDATE_PROMOTION = (
    REPO_ROOT / "artifacts" / "status" / "release_candidate_promotion_preview.json"
)
DEFAULT_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_promotion_gate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_promotion_gate_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_promotion_gate_preview(
    *,
    action_queue: dict[str, Any],
    candidate_promotion: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    release_grade_status = (readiness.get("summary") or {}).get("release_grade_status")
    action_rows = action_queue.get("rows") or []
    promotion_rows = [
        row for row in action_rows if row.get("action_lane") == "promotion_review"
    ]
    release_wide_blockers = action_queue.get("release_wide_blockers") or []
    gate_open = len(release_wide_blockers) == 0

    rows = []
    for row in promotion_rows:
        rows.append(
            {
                "accession": row.get("accession"),
                "split": row.get("split"),
                "benchmark_priority": row.get("benchmark_priority"),
                "gate_state": (
                    "open_for_governing_review"
                    if gate_open
                    else "blocked_on_release_grade_bar"
                ),
                "package_state": row.get("package_state"),
                "packet_lane": row.get("packet_lane"),
                "missing_modalities": row.get("missing_modalities") or [],
                "accession_specific_blockers": row.get("accession_specific_blockers") or [],
                "release_wide_blockers": row.get("release_wide_blockers") or [],
                "required_before_promotion": (
                    [
                        blocker.get("next_action")
                        for blocker in release_wide_blockers
                        if blocker.get("next_action")
                    ]
                    if not gate_open
                    else []
                ),
                "next_action": (
                    "review_governing_promotion_for_frozen_v1"
                    if gate_open
                    else row.get("next_action")
                ),
            }
        )

    return {
        "artifact_id": "release_promotion_gate_preview",
        "schema_id": "proteosphere-release-promotion-gate-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "release_grade_status": release_grade_status,
            "candidate_count": len(rows),
            "promotion_gate_state": (
                "open_for_governing_review"
                if gate_open
                else "blocked_on_release_grade_bar"
            ),
            "promotion_ready_now": gate_open and len(rows) > 0,
            "release_wide_blocker_count": len(release_wide_blockers),
            "top_candidate_accessions": (
                (candidate_promotion.get("summary") or {}).get("top_candidate_accessions") or []
            ),
        },
        "release_wide_blockers": release_wide_blockers,
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This gate explains why the closest release candidates cannot be promoted yet. "
                "It does not authorize promotion or clear the release-grade bar."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    top_candidates = ", ".join(summary.get("top_candidate_accessions") or [])
    return "\n".join(
        [
            "# Release Promotion Gate Preview",
            "",
            f"- Candidate count: `{summary.get('candidate_count')}`",
            f"- Promotion gate state: `{summary.get('promotion_gate_state')}`",
            f"- Promotion ready now: `{str(summary.get('promotion_ready_now')).lower()}`",
            f"- Top candidate accessions: `{top_candidates}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release promotion gate preview."
    )
    parser.add_argument("--action-queue", type=Path, default=DEFAULT_ACTION_QUEUE)
    parser.add_argument(
        "--candidate-promotion", type=Path, default=DEFAULT_CANDIDATE_PROMOTION
    )
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_promotion_gate_preview(
        action_queue=_read_json(args.action_queue),
        candidate_promotion=_read_json(args.candidate_promotion),
        readiness=_read_json(args.readiness),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
