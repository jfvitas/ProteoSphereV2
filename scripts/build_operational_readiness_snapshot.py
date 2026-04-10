from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.analyze_soak_anomalies import analyze_entries
from scripts.audit_truth_boundaries import audit_truth_boundaries, load_queue
from scripts.summarize_soak_ledger import load_ledger_entries, summarize_entries

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_PATH = REPO_ROOT / "tasks" / "task_queue.json"
DEFAULT_STATE_PATH = REPO_ROOT / "artifacts" / "status" / "orchestrator_state.json"
DEFAULT_HEARTBEAT_PATH = REPO_ROOT / "artifacts" / "runtime" / "supervisor.heartbeat.json"
DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
)
DEFAULT_LEDGER_PATH = REPO_ROOT / "artifacts" / "runtime" / "soak_ledger.jsonl"
DEFAULT_BENCHMARK_SUMMARY_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
)
DEFAULT_MARKDOWN_OUTPUT_PATH = (
    REPO_ROOT / "docs" / "reports" / "p22_operational_readiness_snapshot.md"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else None


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


def _heartbeat_summary(payload: dict[str, Any] | None, *, observed_at: datetime) -> dict[str, Any]:
    if not payload:
        return {
            "status": "unavailable",
            "last_heartbeat_at": None,
            "age_seconds": None,
            "iteration": None,
            "phase": None,
        }

    last_heartbeat_at = _parse_timestamp(
        payload.get("last_heartbeat_at")
        or payload.get("heartbeat_at")
        or payload.get("observed_at")
    )
    age_seconds = None
    if last_heartbeat_at is not None:
        age_seconds = max(0, int((observed_at - last_heartbeat_at).total_seconds()))

    status = str(payload.get("status") or "").strip()
    if not status:
        stale_after_seconds = payload.get("stale_after_seconds")
        if age_seconds is None or stale_after_seconds is None:
            status = "unavailable"
        else:
            status = "stale" if age_seconds > int(stale_after_seconds) else "healthy"

    return {
        "status": status or "unavailable",
        "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
        "age_seconds": age_seconds,
        "iteration": payload.get("iteration"),
        "phase": payload.get("phase"),
    }


def _procurement_supervisor_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None

    observed_active = payload.get("observed_active")
    active = payload.get("active")
    stale_active = payload.get("stale_active")
    observation_status = str(payload.get("observation_status") or "").strip() or "unavailable"
    observed_active_count = len(observed_active) if isinstance(observed_active, list) else 0
    active_count = len(active) if isinstance(active, list) else 0
    stale_active_count = len(stale_active) if isinstance(stale_active, list) else 0
    fresh_observation = observation_status == "available" and (
        observed_active_count > 0 or active_count > 0
    )

    return {
        "status": str(payload.get("status") or "").strip() or "unavailable",
        "generated_at": str(payload.get("generated_at") or "").strip() or None,
        "observation_status": observation_status,
        "observed_active_count": observed_active_count,
        "active_count": active_count,
        "stale_active_count": stale_active_count,
        "fresh_observation": fresh_observation,
    }


def _effective_supervisor_summary(
    heartbeat: dict[str, Any],
    procurement_supervisor: dict[str, Any] | None,
    *,
    observed_at: datetime,
) -> dict[str, Any]:
    supervisor = dict(heartbeat)
    supervisor["source"] = "heartbeat"

    if procurement_supervisor and procurement_supervisor["fresh_observation"]:
        effective_status = procurement_supervisor["status"]
        if effective_status not in {"healthy", "running"}:
            effective_status = "running"
        supervisor["status"] = effective_status
        supervisor["source"] = "procurement_supervisor_state"
        generated_at = _parse_timestamp(procurement_supervisor.get("generated_at"))
        if generated_at is not None:
            supervisor["age_seconds"] = max(0, int((observed_at - generated_at).total_seconds()))
        supervisor["procurement_supervisor_status"] = procurement_supervisor["status"]
        supervisor["procurement_supervisor_generated_at"] = procurement_supervisor["generated_at"]
        supervisor["procurement_supervisor_observation_status"] = procurement_supervisor[
            "observation_status"
        ]
        supervisor["procurement_supervisor_observed_active_count"] = procurement_supervisor[
            "observed_active_count"
        ]
        supervisor["procurement_supervisor_active_count"] = procurement_supervisor["active_count"]
        supervisor["procurement_supervisor_stale_active_count"] = procurement_supervisor[
            "stale_active_count"
        ]

    return supervisor


def _queue_status_counts(queue: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in queue:
        status = str(task.get("status") or "").strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _queue_drift_summary(
    current_counts: dict[str, int],
    latest_captured_counts: dict[str, Any],
    *,
    latest_captured_at: str | None,
    observed_at: datetime,
) -> dict[str, Any]:
    normalized_captured = {
        str(key): int(value)
        for key, value in latest_captured_counts.items()
        if isinstance(value, int)
    }
    captured_at = _parse_timestamp(latest_captured_at)
    capture_age_seconds = None
    if captured_at is not None:
        capture_age_seconds = max(0, int((observed_at - captured_at).total_seconds()))
    keys = sorted(set(current_counts) | set(normalized_captured))
    deltas = {
        key: current_counts.get(key, 0) - normalized_captured.get(key, 0)
        for key in keys
        if current_counts.get(key, 0) != normalized_captured.get(key, 0)
    }
    if not normalized_captured:
        status = "missing_capture"
    elif not deltas:
        status = "aligned"
    elif capture_age_seconds is not None and capture_age_seconds <= 300:
        status = "fresh_drift"
    else:
        status = "stale_drift"
    return {
        "current_queue_counts": current_counts,
        "latest_captured_queue_counts": normalized_captured,
        "latest_captured_at": captured_at.isoformat() if captured_at else None,
        "capture_age_seconds": capture_age_seconds,
        "has_drift": bool(deltas),
        "delta_counts": deltas,
        "status": status,
    }


def _release_gate_summary(
    *,
    supervisor: dict[str, Any],
    soak_summary: dict[str, Any],
    truth_audit: dict[str, Any],
    benchmark_status: str | None,
    queue_drift: dict[str, Any],
) -> dict[str, Any]:
    blocker_reasons: list[str] = []
    if supervisor.get("status") != "healthy":
        blocker_reasons.append(
            f"supervisor_status={supervisor.get('status') or 'unavailable'}"
        )
    if not soak_summary["truth_boundary"]["weeklong_requirement_met"]:
        blocker_reasons.append("weeklong_soak_window_incomplete")
    if not soak_summary["truth_boundary"]["weeklong_soak_claim_allowed"]:
        blocker_reasons.append("weeklong_claim_boundary_closed")
    if truth_audit["finding_count"] != 0:
        blocker_reasons.append(f"truth_audit_findings={truth_audit['finding_count']}")
    if benchmark_status:
        blocker_reasons.append(f"benchmark_status={benchmark_status}")
    if queue_drift["status"] in {"stale_drift", "missing_capture"}:
        blocker_reasons.append(f"queue_drift_status={queue_drift['status']}")

    return {
        "weeklong_claim_allowed": soak_summary["truth_boundary"]["weeklong_soak_claim_allowed"],
        "weeklong_requirement_met": soak_summary["truth_boundary"]["weeklong_requirement_met"],
        "truth_audit_clear": truth_audit["finding_count"] == 0,
        "operational_readiness_ready": bool(
            soak_summary["truth_boundary"]["weeklong_soak_claim_allowed"]
            and soak_summary["truth_boundary"]["weeklong_requirement_met"]
            and truth_audit["finding_count"] == 0
            and supervisor.get("status") == "healthy"
            and queue_drift["status"] not in {"stale_drift", "missing_capture"}
            and benchmark_status in {None, "ready", "ok", "release_ready"}
        ),
        "blocking_reasons": blocker_reasons,
    }


def build_operational_readiness_snapshot(
    *,
    queue_path: Path = DEFAULT_QUEUE_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
    heartbeat_path: Path = DEFAULT_HEARTBEAT_PATH,
    procurement_supervisor_state_path: Path | None = None,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    benchmark_summary_path: Path = DEFAULT_BENCHMARK_SUMMARY_PATH,
    repo_root: Path | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed = observed_at or _utc_now()
    queue = load_queue(queue_path)
    effective_repo_root = repo_root or queue_path.parents[1]
    state = _load_json(state_path) or {}
    heartbeat = _heartbeat_summary(_load_json(heartbeat_path), observed_at=observed)
    procurement_supervisor = _procurement_supervisor_summary(
        _load_json(procurement_supervisor_state_path)
        if procurement_supervisor_state_path is not None
        else None
    )
    supervisor = _effective_supervisor_summary(
        heartbeat,
        procurement_supervisor,
        observed_at=observed,
    )
    soak_entries = load_ledger_entries(ledger_path)
    soak_summary = summarize_entries(soak_entries)
    soak_anomaly = analyze_entries(soak_entries)
    truth_audit = audit_truth_boundaries(queue, repo_root=effective_repo_root)
    benchmark_summary = _load_json(benchmark_summary_path) or {}

    current_queue_counts = _queue_status_counts(queue)
    queue_drift = _queue_drift_summary(
        current_queue_counts,
        soak_summary.get("latest_queue_counts", {}),
        latest_captured_at=soak_summary.get("last_observed_at"),
        observed_at=observed,
    )

    release_gate = _release_gate_summary(
        supervisor=supervisor,
        soak_summary=soak_summary,
        truth_audit=truth_audit,
        benchmark_status=benchmark_summary.get("status"),
        queue_drift=queue_drift,
    )

    return {
        "generated_at": observed.isoformat(),
        "supervisor": supervisor,
        "supervisor_heartbeat": heartbeat,
        "procurement_supervisor": procurement_supervisor,
        "queue": {
            "active_worker_count": len(state.get("active_workers", [])),
            "dispatch_queue_count": len(state.get("dispatch_queue", [])),
            "review_queue_count": len(state.get("review_queue", [])),
            "completed_task_count": len(state.get("completed_tasks", [])),
            "blocked_task_count": len(state.get("blocked_tasks", [])),
            "status_counts": current_queue_counts,
        },
        "soak_summary": soak_summary,
        "soak_anomaly": {
            "incident_count": soak_anomaly["incident_count"],
            "incident_status_counts": soak_anomaly["incident_status_counts"],
            "longest_healthy_streak": soak_anomaly["longest_healthy_streak"],
            "current_healthy_streak": soak_anomaly["current_healthy_streak"],
            "queue_transition_count": soak_anomaly["queue_transition_count"],
        },
        "queue_drift": queue_drift,
        "truth_audit": {
            "status": truth_audit["status"],
            "finding_count": truth_audit["finding_count"],
        },
        "benchmark": {
            "status": benchmark_summary.get("status"),
        },
        "release_gate": release_gate,
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    supervisor = snapshot["supervisor"]
    soak_summary = snapshot["soak_summary"]
    soak_anomaly = snapshot["soak_anomaly"]
    queue_drift = snapshot["queue_drift"]
    truth_audit = snapshot["truth_audit"]
    release_gate = snapshot["release_gate"]

    lines = [
        "# P22 Operational Readiness Snapshot",
        "",
        (
            "This snapshot consolidates the unattended runtime health and "
            "release-boundary evidence into one artifact."
        ),
        "",
        "## Supervisor",
        "",
        f"- Status: `{supervisor['status']}`",
        f"- Last heartbeat at: `{supervisor['last_heartbeat_at']}`",
        f"- Heartbeat age: `{supervisor['age_seconds']}` seconds",
        f"- Iteration: `{supervisor['iteration']}`",
        f"- Phase: `{supervisor['phase']}`",
        "",
        "## Soak Progress",
        "",
        f"- Ledger entries: `{soak_summary['entry_count']}`",
        f"- Observed window: `{soak_summary['observed_window_hours']}` hours",
        f"- Progress ratio: `{soak_summary['observed_window_progress_ratio']}`",
        f"- Remaining hours: `{soak_summary['remaining_hours_to_weeklong']}`",
        f"- Estimated weeklong threshold at: `{soak_summary['estimated_weeklong_completion_at']}`",
        f"- Healthy ratio: `{soak_summary['healthy_ratio']}`",
        "",
        "## Queue Drift",
        "",
        f"- Current queue counts: `{queue_drift['current_queue_counts']}`",
        f"- Latest captured queue counts: `{queue_drift['latest_captured_queue_counts']}`",
        f"- Latest captured at: `{queue_drift['latest_captured_at']}`",
        f"- Capture age: `{queue_drift['capture_age_seconds']}` seconds",
        f"- Drift present: `{queue_drift['has_drift']}`",
        f"- Drift status: `{queue_drift['status']}`",
        f"- Delta counts: `{queue_drift['delta_counts']}`",
        "",
        "## Stability Signals",
        "",
        f"- Incident count: `{soak_anomaly['incident_count']}`",
        f"- Incident status counts: `{soak_anomaly['incident_status_counts']}`",
        f"- Longest healthy streak: `{soak_anomaly['longest_healthy_streak']}`",
        f"- Current healthy streak: `{soak_anomaly['current_healthy_streak']}`",
        f"- Queue transition count: `{soak_anomaly['queue_transition_count']}`",
        "",
        "## Truth Boundary",
        "",
        f"- Audit status: `{truth_audit['status']}`",
        f"- Audit findings: `{truth_audit['finding_count']}`",
        f"- Weeklong requirement met: `{release_gate['weeklong_requirement_met']}`",
        f"- Weeklong claim allowed: `{release_gate['weeklong_claim_allowed']}`",
        f"- Operational readiness ready: `{release_gate['operational_readiness_ready']}`",
        f"- Blocking reasons: `{release_gate['blocking_reasons']}`",
        "",
        "## Judgment",
        "",
    ]

    if release_gate["operational_readiness_ready"]:
        lines.append(
            "The unattended runtime evidence is strong enough to support "
            "the operational readiness gate."
        )
    else:
        lines.append(
            "The unattended runtime remains informative but not yet strong "
            "enough to satisfy the release-grade operational readiness gate."
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a consolidated operational-readiness snapshot from "
            "unattended runtime evidence."
        )
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT_PATH)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--benchmark-summary", type=Path, default=DEFAULT_BENCHMARK_SUMMARY_PATH)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    snapshot = build_operational_readiness_snapshot(
        queue_path=args.queue,
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        ledger_path=args.ledger,
        benchmark_summary_path=args.benchmark_summary,
        repo_root=REPO_ROOT,
    )

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(snapshot), encoding="utf-8")

    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(
            "Operational readiness snapshot: "
            f"supervisor={snapshot['supervisor']['status']} "
            f"progress={snapshot['soak_summary']['observed_window_progress_ratio']} "
            f"ready={snapshot['release_gate']['operational_readiness_ready']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
