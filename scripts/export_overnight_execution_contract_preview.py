from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.export_overnight_queue_backlog_preview import (  # noqa: E402
    build_overnight_queue_backlog_preview,
)
from scripts.export_scrape_gap_matrix_preview import (  # noqa: E402
    build_scrape_gap_matrix_preview,
)
from scripts.overnight_planning_common import (  # noqa: E402
    REPO_ROOT as COMMON_REPO_ROOT,
)
from scripts.overnight_planning_common import (  # noqa: E402
    RUNTIME_CHECKPOINT_DIR,
    load_live_bundle_validation,
    load_procurement_status_board,
    load_runtime_state,
    load_scrape_readiness_registry,
    load_source_coverage_matrix,
    read_json,
    write_json,
    write_text,
)

assert REPO_ROOT == COMMON_REPO_ROOT

DEFAULT_GAP_MATRIX = REPO_ROOT / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
DEFAULT_BACKLOG = REPO_ROOT / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
DEFAULT_RUNTIME_STATE = REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
DEFAULT_BUNDLE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "live_bundle_manifest_validation.json"
)
DEFAULT_PROCUREMENT_BOARD = REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "overnight_execution_contract_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "overnight_execution_contract_preview.md"


def _load_gap_matrix(path: Path) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return build_scrape_gap_matrix_preview(
        load_source_coverage_matrix(),
        load_scrape_readiness_registry(),
        load_procurement_status_board(),
    )


def _load_backlog(path: Path) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return build_overnight_queue_backlog_preview(load_runtime_state())


def build_overnight_execution_contract_preview(
    gap_matrix: dict[str, Any],
    backlog: dict[str, Any],
    runtime_state: dict[str, Any],
    live_bundle_validation: dict[str, Any],
    procurement_status_board: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_files = sorted(path.name for path in RUNTIME_CHECKPOINT_DIR.glob("*.json"))
    active_count = int(backlog.get("active_job_count") or 0)
    pending_count = int(backlog.get("supervisor_pending_job_count") or 0)
    catalog_count = int(backlog.get("catalog_job_count") or 0)
    health_checkpoints = [
        {
            "checkpoint_id": "t0_reconcile_runtime",
            "t_plus_hours": 0,
            "required_artifacts": [
                "artifacts/runtime/procurement_supervisor_state.json",
                "artifacts/runtime/procurement_supervisor.pid",
            ],
            "pass_condition": (
                "The supervisor snapshot still reports the same active observed "
                "download families and no duplicate launch has been queued."
            ),
            "block_condition": (
                "Any new duplicate download command appears or the active observed "
                "job families change without a matching runtime update."
            ),
        },
        {
            "checkpoint_id": "t3_validate_gap_matrix",
            "t_plus_hours": 3,
            "required_artifacts": [
                "artifacts/status/scrape_gap_matrix_preview.json",
                "artifacts/status/source_coverage_matrix.json",
                "artifacts/status/scrape_readiness_registry_preview.json",
            ],
            "pass_condition": (
                "The gap matrix still reports only implemented, partial, or missing "
                "lane states and the missing STRING lane remains the same blocker."
            ),
            "block_condition": (
                "A lane state regresses or a new missing source appears without being "
                "reflected in the backlog contract."
            ),
        },
        {
            "checkpoint_id": "t6_reconcile_backlog",
            "t_plus_hours": 6,
            "required_artifacts": [
                "artifacts/status/overnight_queue_backlog_preview.json",
                "artifacts/status/procurement_status_board.json",
                "artifacts/runtime_checkpoints",
            ],
            "pass_condition": (
                "The backlog still ranks the observed active jobs first, the pending "
                "supervisor jobs next, and the catalog jobs after that."
            ),
            "block_condition": (
                "A catalog job is launched ahead of the active or pending queue without "
                "a truth-preserving reason."
            ),
        },
        {
            "checkpoint_id": "t12_bundle_and_queue_health",
            "t_plus_hours": 12,
            "required_artifacts": [
                "artifacts/status/live_bundle_manifest_validation.json",
                "artifacts/status/procurement_status_board.json",
                "artifacts/runtime_checkpoints",
            ],
            "pass_condition": (
                "The live bundle validation still reports aligned status and the "
                "queue contract remains consistent with the runtime checkpoints."
            ),
            "block_condition": (
                "Bundle validation no longer aligns or the runtime checkpoints disagree "
                "with the queue snapshot."
            ),
        },
    ]
    phase_plan = [
        {
            "phase": "observe_and_protect",
            "hours": [0, 3],
            "intent": (
                "Keep the observed active download families running and avoid any "
                "duplicate launch while the gap matrix remains stable."
            ),
            "target_jobs": ["observed_active"],
        },
        {
            "phase": "stabilize_and_review",
            "hours": [3, 6],
            "intent": (
                "Reconcile the supervisor pending jobs against the backlog and keep "
                "the missing STRING lane report-only."
            ),
            "target_jobs": ["supervisor_pending"],
        },
        {
            "phase": "drain_overnight_catalog",
            "hours": [6, 12],
            "intent": (
                "Advance the top catalog jobs only after the observed and pending "
                "jobs stay in a consistent truth boundary."
            ),
            "target_jobs": ["overnight_catalog"],
        },
    ]
    return {
        "artifact_id": "overnight_execution_contract_preview",
        "schema_id": "proteosphere-overnight-execution-contract-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "execution_window_hours": 12,
        "queue_contract": {
            "active_job_count": active_count,
            "supervisor_pending_job_count": pending_count,
            "catalog_job_count": catalog_count,
            "total_job_count": int(backlog.get("job_count") or 0),
            "observed_active_source_keys": backlog.get("summary", {}).get(
                "observed_active_source_keys", []
            ),
            "checkpoint_file_count": len(checkpoint_files),
            "checkpoint_files": checkpoint_files,
        },
        "phase_plan": phase_plan,
        "health_checkpoints": health_checkpoints,
        "source_paths": {
            "gap_matrix": "artifacts/status/scrape_gap_matrix_preview.json",
            "backlog": "artifacts/status/overnight_queue_backlog_preview.json",
            "runtime_state": "artifacts/runtime/procurement_supervisor_state.json",
            "live_bundle_validation": "artifacts/status/live_bundle_manifest_validation.json",
            "procurement_status_board": "artifacts/status/procurement_status_board.json",
        },
        "summary": {
            "top_level_driver": "powershell_interface.ps1",
            "poll_seconds": 60,
            "full_sweep_every": 10,
            "target_hours": 12,
            "estimated_cycles": 720,
            "active_worker_count_snapshot": active_count,
            "procurement_handoff_required": True,
            "implemented_lane_count": int(
                gap_matrix.get("summary", {}).get("implemented_lane_count") or 0
            ),
            "partial_lane_count": int(gap_matrix.get("summary", {}).get("partial_lane_count") or 0),
            "missing_lane_count": int(gap_matrix.get("summary", {}).get("missing_lane_count") or 0),
            "bundle_validation_status": str(
                live_bundle_validation.get("overall_assessment", {}).get("status")
                or live_bundle_validation.get("status")
                or "unknown"
            ),
            "procurement_status": str(procurement_status_board.get("status") or "unknown"),
            "runtime_status": str(runtime_state.get("status") or "unknown"),
        },
        "pause_conditions": [
            "stale_supervisor_heartbeat",
            "repeated_reviewer_failure",
            "stop_file_present",
            "procurement_freeze_inconsistency",
        ],
        "truth_boundary": {
            "summary": (
                "This is a 12-hour execution contract preview. It describes queue "
                "ordering and health checkpoints only; it does not launch jobs or "
                "override the current active download families."
            ),
            "report_only": True,
            "no_duplicate_launches": True,
            "active_jobs_remain_observed_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Overnight Execution Contract Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Window hours: `{payload['execution_window_hours']}`",
        f"- Total jobs: `{payload['queue_contract']['total_job_count']}`",
        f"- Health checkpoints: `{len(payload['health_checkpoints'])}`",
        "",
        "## Phase Plan",
        "",
    ]
    for phase in payload["phase_plan"]:
        lines.append(
            f"- `{phase['phase']}` hours `{phase['hours'][0]}-{phase['hours'][1]}`: "
            f"{phase['intent']}"
        )
    lines.extend(["", "## Health Checkpoints", ""])
    for checkpoint in payload["health_checkpoints"]:
        lines.append(f"- `{checkpoint['checkpoint_id']}` @ +{checkpoint['t_plus_hours']}h")
        lines.append(f"  required: {', '.join(checkpoint['required_artifacts'])}")
        lines.append(f"  pass: {checkpoint['pass_condition']}")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only overnight execution contract preview."
    )
    parser.add_argument("--gap-matrix", type=Path, default=DEFAULT_GAP_MATRIX)
    parser.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--runtime-state", type=Path, default=DEFAULT_RUNTIME_STATE)
    parser.add_argument(
        "--live-bundle-validation",
        type=Path,
        default=DEFAULT_BUNDLE_VALIDATION,
    )
    parser.add_argument(
        "--procurement-status-board",
        type=Path,
        default=DEFAULT_PROCUREMENT_BOARD,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gap_matrix = _load_gap_matrix(args.gap_matrix)
    backlog = _load_backlog(args.backlog)
    runtime_state = (
        load_runtime_state()
        if args.runtime_state == DEFAULT_RUNTIME_STATE
        else read_json(args.runtime_state)
    )
    live_bundle_validation = (
        load_live_bundle_validation()
        if args.live_bundle_validation == DEFAULT_BUNDLE_VALIDATION
        else read_json(args.live_bundle_validation)
    )
    procurement_status_board = (
        load_procurement_status_board()
        if args.procurement_status_board == DEFAULT_PROCUREMENT_BOARD
        else read_json(args.procurement_status_board)
    )
    payload = build_overnight_execution_contract_preview(
        gap_matrix,
        backlog,
        runtime_state,
        live_bundle_validation,
        procurement_status_board,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
