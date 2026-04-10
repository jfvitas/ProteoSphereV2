from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MONITOR_SNAPSHOT_PATH = REPO_ROOT / "artifacts" / "runtime" / "monitor_snapshot.json"
ORCHESTRATOR_STATE_PATH = REPO_ROOT / "artifacts" / "status" / "orchestrator_state.json"
HEARTBEAT_PATH = REPO_ROOT / "artifacts" / "runtime" / "supervisor.heartbeat.json"
HEARTBEAT_HISTORY_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "supervisor.heartbeat.history.jsonl"
)
BENCHMARK_SUMMARY_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
)
BENCHMARK_RUN_SUMMARY_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "runtime" / "soak_ledger.jsonl"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _read_json(path: Path) -> tuple[bool, dict[str, Any] | None, str | None]:
    if not path.exists():
        return False, None, f"missing input: {path}"
    last_error: str | None = None
    for attempt in range(3):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive guard
            last_error = f"unreadable input: {path}: {exc}"
            if attempt < 2:
                time.sleep(0.05)
                continue
            return True, None, last_error
        if not isinstance(payload, dict):
            last_error = f"expected JSON object: {path}"
            if attempt < 2:
                time.sleep(0.05)
                continue
            return True, None, last_error
        return True, payload, None
    return True, None, last_error


def _read_history(path: Path) -> tuple[bool, int, dict[str, Any] | None, str | None]:
    if not path.exists():
        return False, 0, None, None
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception as exc:  # pragma: no cover - defensive guard
        return True, 0, None, f"unreadable input: {path}: {exc}"

    last_entry: dict[str, Any] | None = None
    if lines:
        try:
            payload = json.loads(lines[-1])
            if isinstance(payload, dict):
                last_entry = payload
        except Exception:  # pragma: no cover - defensive guard
            last_entry = None
    return True, len(lines), last_entry, None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(UTC)
    except ValueError:
        return None


def _heartbeat_state(
    heartbeat_payload: dict[str, Any] | None,
    *,
    now: datetime,
) -> dict[str, Any]:
    if heartbeat_payload is None:
        return {
            "status": "unavailable",
            "last_heartbeat_at": None,
            "age_seconds": None,
            "stale_after_seconds": None,
            "is_stale": None,
            "iteration": None,
            "phase": None,
        }

    last_heartbeat_at = _parse_timestamp(heartbeat_payload.get("last_heartbeat_at"))
    stale_after_seconds = heartbeat_payload.get("stale_after_seconds")
    age_seconds: int | None = None
    is_stale: bool | None = None
    status = "unavailable"
    if last_heartbeat_at is not None and stale_after_seconds is not None:
        age_seconds = max(0, int((now - last_heartbeat_at).total_seconds()))
        is_stale = age_seconds > int(stale_after_seconds)
        status = "stale" if is_stale else "healthy"

    return {
        "status": status,
        "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
        "age_seconds": age_seconds,
        "stale_after_seconds": stale_after_seconds,
        "is_stale": is_stale,
        "iteration": heartbeat_payload.get("iteration"),
        "phase": heartbeat_payload.get("phase"),
    }


def build_soak_ledger_entry(
    *,
    monitor_snapshot: dict[str, Any] | None,
    orchestrator_state: dict[str, Any] | None,
    heartbeat_payload: dict[str, Any] | None,
    heartbeat_history_count: int,
    benchmark_summary: dict[str, Any] | None,
    benchmark_run_summary: dict[str, Any] | None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    now = observed_at or _utc_now()
    heartbeat = _heartbeat_state(heartbeat_payload, now=now)
    queue_counts = dict((monitor_snapshot or {}).get("queue_counts", {}))

    return {
        "observed_at": now.isoformat(),
        "queue_counts": queue_counts,
        "ready_count": (monitor_snapshot or {}).get("ready_count", 0),
        "dependency_ready_pending_count": (monitor_snapshot or {}).get(
            "dependency_ready_pending_count", 0
        ),
        "active_worker_count": len((orchestrator_state or {}).get("active_workers", [])),
        "dispatch_queue_count": len((orchestrator_state or {}).get("dispatch_queue", [])),
        "review_queue_count": len((orchestrator_state or {}).get("review_queue", [])),
        "completed_task_count": len((orchestrator_state or {}).get("completed_tasks", [])),
        "blocked_task_count": len((orchestrator_state or {}).get("blocked_tasks", [])),
        "last_tick_completed_at": (orchestrator_state or {}).get("last_tick_completed_at"),
        "supervisor_heartbeat": heartbeat,
        "supervisor_heartbeat_history_count": heartbeat_history_count,
        "benchmark_completion_status": (benchmark_summary or {}).get("status"),
        "benchmark_run_status": (benchmark_run_summary or {}).get("status"),
        "runtime_surface": (benchmark_run_summary or {}).get("runtime_surface"),
        "remaining_gap_count": len((benchmark_run_summary or {}).get("remaining_gaps", [])),
        "truth_boundary": {
            "prototype_runtime": True,
            "weeklong_soak_claim_allowed": False,
        },
    }


def append_soak_ledger(
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    monitor_snapshot_path: Path = MONITOR_SNAPSHOT_PATH,
    orchestrator_state_path: Path = ORCHESTRATOR_STATE_PATH,
    heartbeat_path: Path = HEARTBEAT_PATH,
    heartbeat_history_path: Path = HEARTBEAT_HISTORY_PATH,
    benchmark_summary_path: Path = BENCHMARK_SUMMARY_PATH,
    benchmark_run_summary_path: Path = BENCHMARK_RUN_SUMMARY_PATH,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    _, monitor_snapshot, _ = _read_json(monitor_snapshot_path)
    _, orchestrator_state, _ = _read_json(orchestrator_state_path)
    _, heartbeat_payload, _ = _read_json(heartbeat_path)
    _, heartbeat_history_count, heartbeat_history_entry, _ = _read_history(heartbeat_history_path)
    if heartbeat_payload is None and heartbeat_history_entry is not None:
        heartbeat_payload = heartbeat_history_entry
    _, benchmark_summary, _ = _read_json(benchmark_summary_path)
    _, benchmark_run_summary, _ = _read_json(benchmark_run_summary_path)

    entry = build_soak_ledger_entry(
        monitor_snapshot=monitor_snapshot,
        orchestrator_state=orchestrator_state,
        heartbeat_payload=heartbeat_payload,
        heartbeat_history_count=heartbeat_history_count,
        benchmark_summary=benchmark_summary,
        benchmark_run_summary=benchmark_run_summary,
        observed_at=observed_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        (output_path.read_text(encoding="utf-8") if output_path.exists() else "")
        + json.dumps(entry, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Append a runtime and queue snapshot to the soak audit ledger."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--json", action="store_true", help="Print the appended entry as JSON.")
    args = parser.parse_args(argv)

    entry = append_soak_ledger(output_path=args.output)
    if args.json:
        print(json.dumps(entry, indent=2, sort_keys=True))
    else:
        print(
            "Captured soak ledger entry: "
            f"heartbeat={entry['supervisor_heartbeat']['status']}, "
            f"queue={entry['queue_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
