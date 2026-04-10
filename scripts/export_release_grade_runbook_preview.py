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
DEFAULT_CLOSURE_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_closure_queue_preview.json"
)
DEFAULT_RUNTIME = (
    REPO_ROOT / "artifacts" / "status" / "release_runtime_maturity_preview.json"
)
DEFAULT_COVERAGE = (
    REPO_ROOT / "artifacts" / "status" / "release_source_coverage_depth_preview.json"
)
DEFAULT_PROVENANCE = (
    REPO_ROOT / "artifacts" / "status" / "release_provenance_depth_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_runbook_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_grade_runbook_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_grade_runbook_preview(
    *,
    readiness: dict[str, Any],
    closure_queue: dict[str, Any],
    runtime: dict[str, Any],
    coverage: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    readiness_summary = readiness.get("summary") or {}
    closure_summary = closure_queue.get("summary") or {}
    runtime_summary = runtime.get("summary") or {}
    coverage_summary = coverage.get("summary") or {}
    provenance_summary = provenance.get("summary") or {}

    steps = [
        {
            "step_id": "refresh_release_surfaces",
            "title": "Refresh release-grade evidence surfaces",
            "command": "python scripts/export_release_grade_readiness_preview.py",
            "notes": "Rebuild the top-level release readiness summary before any review.",
        },
        {
            "step_id": "refresh_runtime_maturity",
            "title": "Refresh runtime maturity evidence",
            "command": "python scripts/export_release_runtime_maturity_preview.py",
            "notes": (
                f"Current state is {runtime_summary.get('runtime_maturity_state')} with "
                f"{runtime_summary.get('resumed_run_processed_examples')} resumed examples."
            ),
        },
        {
            "step_id": "refresh_source_coverage_depth",
            "title": "Refresh source coverage depth evidence",
            "command": "python scripts/export_release_source_coverage_depth_preview.py",
            "notes": (
                f"Thin coverage currently affects "
                f"{coverage_summary.get('thin_coverage_count')} of "
                f"{coverage_summary.get('total_accessions')} accessions."
            ),
        },
        {
            "step_id": "refresh_provenance_depth",
            "title": "Refresh provenance depth evidence",
            "command": "python scripts/export_release_provenance_depth_preview.py",
            "notes": (
                f"Release ledger blocked count is "
                f"{provenance_summary.get('ledger_blocked_count')}."
            ),
        },
        {
            "step_id": "refresh_closure_queue",
            "title": "Refresh ranked release closure queue",
            "command": "python scripts/export_release_grade_closure_queue_preview.py",
            "notes": (
                f"Current queue length is {closure_summary.get('queue_length')} and remains "
                "fully report-only."
            ),
        },
        {
            "step_id": "review_operator_recipe",
            "title": "Review release-grade operator recipe",
            "command": (
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts/operator_recipes.ps1 -Recipe release-grade-review -AsJson"
            ),
            "notes": "Use the operator recipe as the front-door review surface for the bar.",
        },
        {
            "step_id": "hold_release_claim",
            "title": "Hold release claim until blockers are closed",
            "command": "python scripts/validate_operator_state.py --json",
            "notes": (
                f"Summary remains {readiness_summary.get('release_grade_status')}; "
                "do not promote the benchmark until the queue is empty."
            ),
        },
    ]

    return {
        "artifact_id": "release_grade_runbook_preview",
        "schema_id": "proteosphere-release-grade-runbook-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "release_grade_status": readiness_summary.get("release_grade_status"),
            "command_count": len(steps),
            "queue_length": closure_summary.get("queue_length"),
            "runtime_maturity_state": runtime_summary.get("runtime_maturity_state"),
            "coverage_depth_state": coverage_summary.get("coverage_depth_state"),
            "provenance_depth_state": provenance_summary.get("provenance_depth_state"),
        },
        "steps": steps,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This runbook sequences the remaining release-grade review work without "
                "upgrading the benchmark to release-ready."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    steps = payload.get("steps") or []
    lines = [
        "# Release Grade Runbook Preview",
        "",
        f"- Release-grade status: `{summary.get('release_grade_status')}`",
        f"- Command count: `{summary.get('command_count')}`",
        "",
        "## Steps",
        "",
    ]
    for row in steps:
        lines.append(
            f"- `{row['step_id']}` `{row['title']}`: `{row['command']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the release-grade runbook preview.")
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--closure-queue", type=Path, default=DEFAULT_CLOSURE_QUEUE)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_grade_runbook_preview(
        readiness=_read_json(args.readiness),
        closure_queue=_read_json(args.closure_queue),
        runtime=_read_json(args.runtime),
        coverage=_read_json(args.coverage),
        provenance=_read_json(args.provenance),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
