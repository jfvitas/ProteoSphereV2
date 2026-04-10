from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UNIPROT_DIR = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "uniprot"
DEFAULT_VALIDATION_PATH = (
    REPO_ROOT / "artifacts" / "status" / "protein_data_scope_seed_validation.json"
)
DEFAULT_STATUS_PATH = REPO_ROOT / "artifacts" / "runtime" / "uniprot_direct_watch.json"
DEFAULT_LOG_PATH = REPO_ROOT / "artifacts" / "runtime" / "uniprot_direct_watch.log"

REQUIRED_UNIPROT_FILES = (
    "uniprot_sprot.dat.gz",
    "uniprot_sprot.fasta.gz",
    "idmapping.dat.gz",
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_active_uniprot_procurement_pids() -> tuple[int, ...]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match "
        "'protein_data_scope\\\\download_all_sources.py "
        "--sources uniprot --required-core-only' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    pids: list[int] = []
    for line in completed.stdout.splitlines():
        text = line.strip()
        if text.isdigit():
            pids.append(int(text))
    return tuple(pids)


@dataclass(frozen=True, slots=True)
class WatchState:
    status: str
    active_pids: tuple[int, ...]
    partial_files: tuple[str, ...]
    missing_required_files: tuple[str, ...]

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


def evaluate_watch_state(
    *,
    uniprot_dir: Path,
    active_pids: tuple[int, ...],
) -> WatchState:
    partial_files = tuple(sorted(path.name for path in uniprot_dir.glob("*.part")))
    missing_required_files = tuple(
        filename
        for filename in REQUIRED_UNIPROT_FILES
        if not (uniprot_dir / filename).exists()
    )
    if active_pids:
        return WatchState(
            status="waiting_for_process",
            active_pids=active_pids,
            partial_files=partial_files,
            missing_required_files=missing_required_files,
        )
    if partial_files:
        return WatchState(
            status="waiting_for_partial_cleanup",
            active_pids=active_pids,
            partial_files=partial_files,
            missing_required_files=missing_required_files,
        )
    if missing_required_files:
        return WatchState(
            status="blocked_missing_required_files",
            active_pids=active_pids,
            partial_files=partial_files,
            missing_required_files=missing_required_files,
        )
    return WatchState(
        status="ready",
        active_pids=active_pids,
        partial_files=partial_files,
        missing_required_files=missing_required_files,
    )


def run_repo_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def build_status_payload(
    *,
    phase: str,
    watch_state: WatchState,
    validation_status: str | None = None,
    promotion_status: str | None = None,
    post_pipeline_status: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "phase": phase,
        "watch_state": watch_state.status,
        "active_pids": list(watch_state.active_pids),
        "partial_files": list(watch_state.partial_files),
        "missing_required_files": list(watch_state.missing_required_files),
        "validation_status": validation_status,
        "promotion_status": promotion_status,
        "post_pipeline_status": post_pipeline_status,
        "note": note,
    }


def watch_and_finalize(
    *,
    uniprot_dir: Path,
    validation_path: Path,
    status_path: Path,
    log_path: Path,
    poll_seconds: int,
    once: bool,
) -> int:
    while True:
        watch_state = evaluate_watch_state(
            uniprot_dir=uniprot_dir,
            active_pids=list_active_uniprot_procurement_pids(),
        )
        if not watch_state.is_ready:
            _write_json(
                status_path,
                build_status_payload(
                    phase="waiting",
                    watch_state=watch_state,
                    note="waiting for uniprot required-core procurement to finish",
                ),
            )
            _append_log(
                log_path,
                "waiting: "
                f"state={watch_state.status} "
                f"partials={list(watch_state.partial_files)} "
                f"pids={list(watch_state.active_pids)}",
            )
            if once:
                return 0
            time.sleep(poll_seconds)
            continue

        _append_log(log_path, "ready: launching validation")
        validation_result = run_repo_command(
            ["python", "scripts\\validate_protein_data_scope_seed.py"]
        )
        validation_status = None
        if validation_path.exists():
            validation_status = str(_read_json(validation_path).get("status") or "").strip() or None
        if validation_result.returncode != 0 or validation_status != "passed":
            _write_json(
                status_path,
                build_status_payload(
                    phase="validation_failed",
                    watch_state=watch_state,
                    validation_status=validation_status,
                    note=(
                        validation_result.stderr.strip()
                        or validation_result.stdout.strip()
                        or None
                    ),
                ),
            )
            _append_log(
                log_path,
                "validation failed: "
                f"returncode={validation_result.returncode} "
                f"status={validation_status}",
            )
            return 1

        _append_log(log_path, "validation passed: launching promotion")
        promotion_result = run_repo_command(
            ["python", "scripts\\promote_protein_data_scope_seed.py"]
        )
        if promotion_result.returncode != 0:
            _write_json(
                status_path,
                build_status_payload(
                    phase="promotion_failed",
                    watch_state=watch_state,
                    validation_status=validation_status,
                    promotion_status="failed",
                    post_pipeline_status=None,
                    note=promotion_result.stderr.strip() or promotion_result.stdout.strip() or None,
                ),
            )
            _append_log(log_path, f"promotion failed: returncode={promotion_result.returncode}")
            return 1

        _append_log(log_path, "promotion passed: launching post-tier1 pipeline")
        post_pipeline_result = run_repo_command(
            ["python", "scripts\\run_post_tier1_direct_pipeline.py"]
        )
        if post_pipeline_result.returncode != 0:
            _write_json(
                status_path,
                build_status_payload(
                    phase="post_pipeline_failed",
                    watch_state=watch_state,
                    validation_status=validation_status,
                    promotion_status="promoted",
                    post_pipeline_status="failed",
                    note=(
                        post_pipeline_result.stderr.strip()
                        or post_pipeline_result.stdout.strip()
                        or None
                    ),
                ),
            )
            _append_log(
                log_path,
                f"post-tier1 pipeline failed: returncode={post_pipeline_result.returncode}",
            )
            return 1

        _write_json(
            status_path,
            build_status_payload(
                phase="completed",
                watch_state=watch_state,
                validation_status=validation_status,
                promotion_status="promoted",
                post_pipeline_status="passed",
                note="uniprot direct procurement finalized successfully",
            ),
        )
        _append_log(log_path, "completed: validation, promotion, and post-tier1 pipeline succeeded")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch the UniProt direct required-core run and finalize Tier 1 promotion."
    )
    parser.add_argument("--uniprot-dir", type=Path, default=DEFAULT_UNIPROT_DIR)
    parser.add_argument("--validation-path", type=Path, default=DEFAULT_VALIDATION_PATH)
    parser.add_argument("--status-path", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return watch_and_finalize(
        uniprot_dir=args.uniprot_dir,
        validation_path=args.validation_path,
        status_path=args.status_path,
        log_path=args.log_path,
        poll_seconds=args.poll_seconds,
        once=args.once,
    )


if __name__ == "__main__":
    raise SystemExit(main())
