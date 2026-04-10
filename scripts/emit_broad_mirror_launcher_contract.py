from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LANE_PLAN_PATH = REPO_ROOT / "artifacts" / "status" / "broad_mirror_lane_plan.json"
DEFAULT_TRANSFER_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "broad_mirror_launcher_contract.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "broad_mirror_launcher_contract.md"
DEFAULT_SOURCE_DOWNLOADER = REPO_ROOT / "protein_data_scope" / "download_all_sources.py"
DEFAULT_DEST_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _casefold(value: Any) -> str:
    return str(value or "").strip().casefold()


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _active_file_names(transfer_status: dict[str, Any]) -> list[str]:
    active_rows = [row for row in transfer_status.get("actively_transferring_now") or [] if isinstance(row, dict)]
    return sorted(
        {
            str(row.get("filename") or "").strip()
            for row in active_rows
            if str(row.get("filename") or "").strip()
        }
    )


def _select_launch_batch(lane_plan: dict[str, Any]) -> dict[str, Any]:
    batches = [row for row in lane_plan.get("recommended_sidecar_launch_order") or [] if isinstance(row, dict)]
    for batch in batches:
        if _casefold(batch.get("value_class")) == "direct-value":
            return batch
    raise ValueError("lane plan does not contain a direct-value batch to launch")


def _launch_command(batch: dict[str, Any], *, dest_root: Path, source_downloader: Path) -> tuple[list[str], str]:
    files = [str(filename).strip() for filename in batch.get("files") or [] if str(filename).strip()]
    argv = [
        "python",
        _repo_relative(source_downloader),
        "--dest",
        dest_root.resolve().as_posix(),
        "--tiers",
        "direct",
        "--sources",
        str(batch["source_id"]),
        "--files",
        *files,
    ]
    text = (
        "python "
        f"{_repo_relative(source_downloader)} "
        f'--dest "{dest_root.resolve().as_posix()}" '
        "--tiers direct "
        f"--sources {batch['source_id']} "
        "--files "
        + " ".join(files)
    )
    return argv, text


def build_launcher_contract(
    *,
    lane_plan_path: Path = DEFAULT_LANE_PLAN_PATH,
    transfer_status_path: Path = DEFAULT_TRANSFER_STATUS_PATH,
    source_downloader: Path = DEFAULT_SOURCE_DOWNLOADER,
    dest_root: Path = DEFAULT_DEST_ROOT,
) -> dict[str, Any]:
    lane_plan = _read_json(lane_plan_path)
    transfer_status = _read_json(transfer_status_path)
    selected_batch = _select_launch_batch(lane_plan)

    selected_files = [
        str(filename).strip()
        for filename in selected_batch.get("files") or []
        if str(filename).strip()
    ]
    active_files = _active_file_names(transfer_status)
    overlapping_files = sorted(set(selected_files).intersection(active_files))
    if overlapping_files:
        raise ValueError(
            "selected batch overlaps with active transfers: " + ", ".join(overlapping_files)
        )

    launch_argv, launch_command_text = _launch_command(
        selected_batch,
        dest_root=dest_root,
        source_downloader=source_downloader,
    )

    expected_outputs = [
        {
            "path": f"data/raw/protein_data_scope_seed/{selected_batch['source_id']}/{filename}",
            "kind": "downloaded_file",
        }
        for filename in selected_files
    ]
    expected_outputs.extend(
        [
            {
                "path": f"data/raw/protein_data_scope_seed/{selected_batch['source_id']}/_source_metadata.json",
                "kind": "source_metadata",
            },
            {
                "path": "data/raw/protein_data_scope_seed/download_run_<UTC timestamp>.log",
                "kind": "run_log",
            },
            {
                "path": "data/raw/protein_data_scope_seed/download_run_<UTC timestamp>.json",
                "kind": "run_manifest",
            },
        ]
    )

    return {
        "schema_id": "proteosphere-broad-mirror-launcher-contract-2026-03-31",
        "report_type": "broad_mirror_launcher_contract",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ready_for_launch",
        "basis": {
            "lane_plan_path": _repo_relative(lane_plan_path),
            "transfer_status_path": _repo_relative(transfer_status_path),
            "source_downloader_path": _repo_relative(source_downloader),
            "dest_root": dest_root.resolve().as_posix(),
        },
        "selected_batch": {
            "rank": selected_batch.get("rank"),
            "batch_id": selected_batch.get("batch_id"),
            "source_id": selected_batch.get("source_id"),
            "source_name": selected_batch.get("source_name"),
            "source_role": selected_batch.get("source_role"),
            "value_class": selected_batch.get("value_class"),
            "file_count": len(selected_files),
            "files": selected_files,
            "rationale": selected_batch.get("rationale"),
            "expected_impact": selected_batch.get("expected_impact"),
        },
        "launch": {
            "cwd": REPO_ROOT.resolve().as_posix(),
            "shell": "powershell",
            "command_argv": launch_argv,
            "command_text": launch_command_text,
        },
        "expected_outputs": expected_outputs,
        "duplicate_process_avoidance": {
            "active_files_observed": active_files,
            "overlapping_files": overlapping_files,
            "avoidance_notes": [
                "This batch is limited to the current lane plan's direct-value UniProt backbone files.",
                "It does not request any file currently observed as active in the transfer-status artifact.",
                "It does not include the already-active UniProt bulk files or any STRING filenames.",
            ],
        },
        "summary": {
            "selected_file_count": len(selected_files),
            "active_file_count": len(active_files),
            "overlap_count": len(overlapping_files),
            "expected_output_count": len(expected_outputs),
        },
        "notes": [
            "The command is derived from the current lane plan and the live remaining-transfer-status artifact.",
            "Selection is intentionally narrow: only the still-not-started UniProt direct-value backbone batch is launched.",
            "The launcher uses `download_all_sources.py` with explicit source and file filters so it does not widen into the active bulk lanes.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    batch = payload["selected_batch"]
    summary = payload["summary"]
    lines = [
        "# Broad Mirror Launcher Contract",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Basis: `{payload['basis']['lane_plan_path']}`",
        f"- Transfer status: `{payload['basis']['transfer_status_path']}`",
        f"- Selected batch: `{batch['batch_id']}`",
        f"- Files: `{summary['selected_file_count']}`",
        f"- Active overlap: `{summary['overlap_count']}`",
        "",
        "## Launch Command",
        "",
        "```powershell",
        payload["launch"]["command_text"],
        "```",
        "",
        "## Expected Outputs",
        "",
    ]
    for item in payload["expected_outputs"]:
        lines.append(f"- `{item['path']}` ({item['kind']})")

    lines.extend(["", "## Duplicate-Process Avoidance", ""])
    for note in payload["duplicate_process_avoidance"]["avoidance_notes"]:
        lines.append(f"- {note}")
    if payload["duplicate_process_avoidance"]["overlapping_files"]:
        lines.append(
            "- Overlap detected: "
            + ", ".join(f"`{name}`" for name in payload["duplicate_process_avoidance"]["overlapping_files"])
        )
    else:
        lines.append("- Overlap detected: none")

    lines.extend(["", "## Why This Batch", ""])
    lines.append(f"- Source: `{batch['source_id']}` ({batch['source_role']})")
    lines.append(f"- Value class: `{batch['value_class']}`")
    lines.append(f"- Rationale: {batch['rationale']}")
    lines.append(f"- Expected impact: {batch['expected_impact']}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a narrow broad-mirror launcher contract.")
    parser.add_argument("--lane-plan", type=Path, default=DEFAULT_LANE_PLAN_PATH)
    parser.add_argument("--transfer-status", type=Path, default=DEFAULT_TRANSFER_STATUS_PATH)
    parser.add_argument("--source-downloader", type=Path, default=DEFAULT_SOURCE_DOWNLOADER)
    parser.add_argument("--dest-root", type=Path, default=DEFAULT_DEST_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_launcher_contract(
        lane_plan_path=args.lane_plan,
        transfer_status_path=args.transfer_status,
        source_downloader=args.source_downloader,
        dest_root=args.dest_root,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Broad mirror launcher contract exported: "
            f"batch={payload['selected_batch']['batch_id']} "
            f"files={payload['summary']['selected_file_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
