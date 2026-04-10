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
DEFAULT_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "release_source_fix_followup_batch_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "release_source_fix_followup_batch_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_source_fix_followup_batch_preview(
    *,
    action_queue: dict[str, Any],
    unblock_plan: dict[str, Any],
) -> dict[str, Any]:
    unblock_by_accession = {
        row.get("accession"): row
        for row in (unblock_plan.get("rows") or [])
        if row.get("accession")
    }
    source_fix_rows = [
        row
        for row in (action_queue.get("rows") or [])
        if row.get("action_lane") == "source_fix_followup"
    ]

    rows = []
    all_source_fix_refs: list[str] = []
    for row in source_fix_rows:
        accession = row.get("accession")
        unblock_row = unblock_by_accession.get(accession) or {}
        source_fix_refs = unblock_row.get("source_fix_refs") or []
        all_source_fix_refs.extend(source_fix_refs)
        rows.append(
            {
                "accession": accession,
                "split": row.get("split"),
                "benchmark_priority": row.get("benchmark_priority"),
                "closure_state": row.get("closure_state"),
                "current_followup": row.get("next_action"),
                "source_fix_refs": source_fix_refs,
                "recommended_next_actions": unblock_row.get("recommended_next_actions") or [],
                "missing_modalities": row.get("missing_modalities") or [],
                "accession_specific_blockers": row.get("accession_specific_blockers") or [],
            }
        )

    source_fix_ref_counts: dict[str, int] = {}
    for ref in all_source_fix_refs:
        source_fix_ref_counts[ref] = source_fix_ref_counts.get(ref, 0) + 1
    top_source_fix_refs = [
        {"source_fix_ref": ref, "count": count}
        for ref, count in sorted(
            source_fix_ref_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]

    return {
        "artifact_id": "release_source_fix_followup_batch_preview",
        "schema_id": "proteosphere-release-source-fix-followup-batch-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "batch_row_count": len(rows),
            "blocked_accession_count": len(rows),
            "shared_source_fix_ref_count": len(source_fix_ref_counts),
            "top_source_fix_refs": top_source_fix_refs,
            "next_batch_state": (
                "source_fix_followup_active" if rows else "no_source_fix_followup_rows"
            ),
        },
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This batch isolates the release-accession rows that still need upstream "
                "source-fix or acquisition follow-up. It does not mutate source artifacts."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    return "\n".join(
        [
            "# Release Source-Fix Follow-Up Batch Preview",
            "",
            f"- Batch rows: `{summary.get('batch_row_count')}`",
            f"- Blocked accessions: `{summary.get('blocked_accession_count')}`",
            f"- Shared source-fix refs: `{summary.get('shared_source_fix_ref_count')}`",
            f"- Next batch state: `{summary.get('next_batch_state')}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release source-fix follow-up batch preview."
    )
    parser.add_argument("--action-queue", type=Path, default=DEFAULT_ACTION_QUEUE)
    parser.add_argument("--unblock-plan", type=Path, default=DEFAULT_UNBLOCK_PLAN)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_source_fix_followup_batch_preview(
        action_queue=_read_json(args.action_queue),
        unblock_plan=_read_json(args.unblock_plan),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
