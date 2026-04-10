from __future__ import annotations
# ruff: noqa: I001

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.post_tail_runner_support import (
        move_step,
        python_step,
        read_json as read_json_default,
        run_steps,
        write_json,
    )
    from scripts.pre_tail_readiness_support import read_json
except ModuleNotFoundError:  # pragma: no cover
    from post_tail_runner_support import (  # type: ignore[no-redef]
        move_step,
        python_step,
        read_json as read_json_default,
        run_steps,
        write_json,
    )
    from pre_tail_readiness_support import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOWNLOAD_LOCATION_AUDIT = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_PROCUREMENT_STATUS_BOARD = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_STALE_PART_AUDIT = (
    REPO_ROOT / "artifacts" / "status" / "procurement_stale_part_audit_preview.json"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "post_tail_unlock_dry_run_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "post_tail_unlock_dry_run_preview.md"
DEFAULT_EXECUTION_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "post_tail_unlock_execution_preview.json"
)
DEFAULT_EXECUTION_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "post_tail_unlock_execution_preview.md"
)
DEFAULT_STATE_PATH = REPO_ROOT / "artifacts" / "runtime" / "post_tail_unlock_state.json"
DEFAULT_LEDGER_PATH = REPO_ROOT / "artifacts" / "runtime" / "post_tail_unlock_ledger.jsonl"
DEFAULT_UNIREF_SOURCE = Path(r"C:\Users\jfvit\Downloads\uniref100.xml.gz")
DEFAULT_UNIREF_DEST = Path(
    r"C:\CSTEMP\ProteoSphereV2_overflow\protein_data_scope_seed\uniprot\uniref100.xml.gz"
)


def _row_by_filename(location_audit: dict[str, Any], filename: str) -> dict[str, Any]:
    for row in location_audit.get("rows") or []:
        if isinstance(row, dict) and str(row.get("filename") or "").strip() == filename:
            return dict(row)
    return {}


def build_post_tail_unlock_dry_run_preview(
    download_location_audit: dict[str, Any],
    procurement_status_board: dict[str, Any],
    stale_part_audit: dict[str, Any],
    procurement_source_completion: dict[str, Any],
) -> dict[str, Any]:
    uniref = _row_by_filename(download_location_audit, "uniref100.xml.gz")
    string_full = _row_by_filename(download_location_audit, "protein.links.full.v12.0.txt.gz")
    live_complete = (
        bool(uniref.get("final_locations"))
        and not bool(uniref.get("in_process_locations"))
        and bool(string_full.get("final_locations"))
        and not bool(string_full.get("in_process_locations"))
    )
    steps = [
        {
            "step": "verify live downloads complete at actual locations",
            "ready": live_complete,
            "detail": {
                "uniref_primary_location": uniref.get("primary_location"),
                "string_primary_location": string_full.get("primary_location"),
            },
        },
        {
            "step": "refresh overflow-aware location audit and procurement board",
            "ready": True,
            "detail": {"board_status": procurement_status_board.get("status")},
        },
        {
            "step": "quarantine stale .part residue",
            "ready": True,
            "detail": {
                "stale_residue_count": (
                    (stale_part_audit.get("summary") or {}).get("stale_residue_count", 0)
                )
            },
        },
        {
            "step": "leave completed UniRef on C: if D: consolidation is still unsafe",
            "ready": True,
            "detail": {"default_final_uniref_authority": "C_overflow_allowed"},
        },
        {
            "step": "launch STRING interaction materialization",
            "ready": bool(procurement_source_completion.get("string_completion_ready")),
            "detail": {
                "script": "scripts/export_string_interaction_materialization_preview.py"
            },
        },
        {
            "step": "launch UniRef cluster materialization",
            "ready": live_complete,
            "detail": {"script": "scripts/export_uniref_cluster_materialization_plan_preview.py"},
        },
        {
            "step": (
                "refresh scrape gap matrix, execution wave, canonical corpus, "
                "sidecars, and dashboard"
            ),
            "ready": True,
            "detail": {
                "scripts": [
                    "scripts/export_scrape_gap_matrix_preview.py",
                    "scripts/export_scrape_execution_wave_preview.py",
                    "scripts/export_seed_plus_neighbors_structured_corpus_preview.py",
                    "scripts/export_seed_plus_neighbors_baseline_sidecar_preview.py",
                    "scripts/export_seed_plus_neighbors_multimodal_sidecar_preview.py",
                    "scripts/export_operator_dashboard.py",
                ]
            },
        },
        {
            "step": "rerun operator validation",
            "ready": True,
            "detail": {"script": "scripts/validate_operator_state.py --json"},
        },
    ]
    return {
        "artifact_id": "post_tail_unlock_dry_run_preview",
        "schema_id": "proteosphere-post-tail-unlock-dry-run-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "live_downloads_complete": live_complete,
            "ready_step_count": sum(1 for step in steps if step["ready"]),
            "blocked_step_count": sum(1 for step in steps if not step["ready"]),
        },
        "steps": steps,
        "truth_boundary": {
            "summary": (
                "This runbook is a zero-decision dry run for post-tail unlock. It prepares the "
                "ordered actions without launching materialization before downloads are complete."
            ),
            "report_only": True,
            "non_mutating": True,
            "dry_run": True,
        },
    }


def build_post_tail_unlock_execution_preview(
    *,
    state: dict[str, Any],
    download_location_audit: dict[str, Any],
    procurement_status_board: dict[str, Any],
    stale_part_audit: dict[str, Any],
    procurement_source_completion: dict[str, Any],
    uniref_source: Path,
    uniref_dest: Path,
) -> dict[str, Any]:
    uniref = _row_by_filename(download_location_audit, "uniref100.xml.gz")
    string_full = _row_by_filename(download_location_audit, "protein.links.full.v12.0.txt.gz")
    source_completion_index = procurement_source_completion.get("source_completion_index") or {}
    return {
        "artifact_id": "post_tail_unlock_execution_preview",
        "schema_id": "proteosphere-post-tail-unlock-execution-preview-2026-04-05",
        "status": "completed" if state.get("last_failed_step") is None else "failed",
        "generated_at": datetime.now(UTC).isoformat(),
        "uniref_move": {
            "source_path": str(uniref_source).replace("\\", "/"),
            "destination_path": str(uniref_dest).replace("\\", "/"),
            "destination_exists": uniref_dest.exists(),
            "source_exists_after_move": uniref_source.exists(),
        },
        "summary": {
            "executed_step_count": sum(
                1
                for step in (state.get("steps") or {}).values()
                if isinstance(step, dict) and step.get("status") == "completed"
            ),
            "failed_step_count": sum(
                1
                for step in (state.get("steps") or {}).values()
                if isinstance(step, dict) and step.get("status") == "failed"
            ),
            "live_downloads_complete": (
                bool(uniref.get("final_locations"))
                and not bool(uniref.get("in_process_locations"))
                and bool(string_full.get("final_locations"))
                and not bool(string_full.get("in_process_locations"))
            ),
            "string_completion_status": procurement_source_completion.get(
                "string_completion_status"
            ),
            "uniprot_completion_status": procurement_source_completion.get(
                "uniprot_completion_status"
            ),
            "completed_off_primary_root": bool(
                (source_completion_index.get("uniprot") or {}).get("completed_off_primary_root")
            ),
            "stale_residue_count": (stale_part_audit.get("summary") or {}).get(
                "stale_residue_count", 0
            ),
            "board_status": procurement_status_board.get("status"),
        },
        "steps": state.get("steps") or {},
        "restart_hint": state.get("restart_hint"),
        "truth_boundary": {
            "summary": (
                "This execution preview records the real post-tail unlock truth-refresh run. "
                "It mutates file placement only for the finished UniRef artifact and then "
                "refreshes report-only procurement surfaces."
            ),
            "report_only": False,
            "non_mutating_after_move": True,
            "allow_c_overflow_authority": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Post-Tail Unlock Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Live downloads complete: `{payload.get('summary', {}).get('live_downloads_complete')}`",
        "",
    ]
    steps = payload.get("steps") or []
    if isinstance(steps, dict):
        steps = [
            {"step": step_id, **step_payload}
            for step_id, step_payload in steps.items()
            if isinstance(step_payload, dict)
        ]
    for step in steps:
        if isinstance(step, dict) and "ready" in step:
            lines.append(f"- `{step['step']}` / ready `{step['ready']}`")
        elif isinstance(step, dict):
            lines.append(f"- `{step['step']}` / status `{step.get('status')}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the post-tail unlock dry-run preview."
    )
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    )
    parser.add_argument(
        "--procurement-status-board",
        type=Path,
        default=DEFAULT_PROCUREMENT_STATUS_BOARD,
    )
    parser.add_argument(
        "--stale-part-audit",
        type=Path,
        default=DEFAULT_STALE_PART_AUDIT,
    )
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-c-overflow-authority", action="store_true")
    parser.add_argument("--uniref-source", type=Path, default=DEFAULT_UNIREF_SOURCE)
    parser.add_argument("--uniref-dest", type=Path, default=DEFAULT_UNIREF_DEST)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--ledger-path", type=Path, default=DEFAULT_LEDGER_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_json = args.output_json or (
        DEFAULT_EXECUTION_OUTPUT_JSON if args.execute else DEFAULT_OUTPUT_JSON
    )
    output_md = args.output_md or (
        DEFAULT_EXECUTION_OUTPUT_MD if args.execute else DEFAULT_OUTPUT_MD
    )
    if not args.execute:
        payload = build_post_tail_unlock_dry_run_preview(
            read_json(args.download_location_audit),
            read_json(args.procurement_status_board),
            read_json(args.stale_part_audit),
            read_json(args.procurement_source_completion),
        )
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(payload), encoding="utf-8")
        print(output_json)
        return

    if not args.allow_c_overflow_authority:
        raise SystemExit(
            "--allow-c-overflow-authority is required for execute mode to confirm "
            "the intended C: destination."
        )

    steps = [
        move_step(
            "move_completed_uniref_to_overflow",
            "Move the completed UniRef artifact from Downloads into the overflow authority path.",
            source=str(args.uniref_source),
            destination=str(args.uniref_dest),
        ),
        python_step(
            "refresh_download_location_audit",
            "Refresh the cross-drive download location audit.",
            "scripts/export_download_location_audit_preview.py",
            expected_outputs=["artifacts/status/download_location_audit_preview.json"],
        ),
        python_step(
            "refresh_stale_part_audit",
            "Refresh the stale .part residue audit.",
            "scripts/export_procurement_stale_part_audit_preview.py",
            expected_outputs=["artifacts/status/procurement_stale_part_audit_preview.json"],
        ),
        python_step(
            "refresh_procurement_source_completion",
            "Refresh per-source completion truth.",
            "scripts/export_procurement_source_completion_preview.py",
            expected_outputs=["artifacts/status/procurement_source_completion_preview.json"],
        ),
        python_step(
            "refresh_broad_mirror_progress",
            "Refresh broad mirror progress with cross-drive authority.",
            "scripts/emit_broad_mirror_progress.py",
            expected_outputs=["artifacts/status/broad_mirror_progress.json"],
        ),
        python_step(
            "refresh_broad_mirror_remaining_gaps",
            "Refresh broad mirror remaining gaps after authority reconciliation.",
            "scripts/emit_broad_mirror_remaining_gaps.py",
            expected_outputs=["artifacts/status/broad_mirror_remaining_gaps.json"],
        ),
        python_step(
            "refresh_broad_mirror_remaining_transfer_status",
            "Refresh broad mirror remaining transfer status.",
            "scripts/emit_broad_mirror_remaining_transfer_status.py",
            expected_outputs=["artifacts/status/broad_mirror_remaining_transfer_status.json"],
        ),
        python_step(
            "refresh_procurement_status_board",
            "Refresh the procurement status board.",
            "scripts/export_procurement_status_board.py",
            expected_outputs=["artifacts/status/procurement_status_board.json"],
        ),
        python_step(
            "refresh_procurement_tail_freeze_gate",
            "Refresh the procurement tail freeze gate.",
            "scripts/export_procurement_tail_freeze_gate_preview.py",
            expected_outputs=["artifacts/status/procurement_tail_freeze_gate_preview.json"],
        ),
    ]
    state, _ = run_steps(
        runner_name="post_tail_unlock",
        steps=steps,
        state_path=args.state_path,
        ledger_path=args.ledger_path,
        resume=args.resume,
    )

    payload = build_post_tail_unlock_execution_preview(
        state=state,
        download_location_audit=read_json_default(args.download_location_audit),
        procurement_status_board=read_json_default(args.procurement_status_board),
        stale_part_audit=read_json_default(args.stale_part_audit),
        procurement_source_completion=read_json_default(args.procurement_source_completion),
        uniref_source=args.uniref_source,
        uniref_dest=args.uniref_dest,
    )
    write_json(output_json, payload)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(output_json)


if __name__ == "__main__":
    main()
