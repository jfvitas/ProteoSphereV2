from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "artifacts" / "runtime" / "soak_ledger.jsonl"
DEFAULT_MARKDOWN_OUTPUT_PATH = REPO_ROOT / "docs" / "reports" / "p22_soak_rollup.md"
WEEKLONG_SECONDS = 7 * 24 * 60 * 60


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


def load_ledger_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def summarize_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    queue_samples = Counter()
    incident_count = 0
    max_heartbeat_age_seconds = 0
    latest_queue_counts: dict[str, Any] = {}
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    prototype_runtime = False
    weeklong_claim_allowed = False
    latest_benchmark_status = None

    for entry in entries:
        observed_at = _parse_timestamp(entry.get("observed_at"))
        if observed_at is not None:
            if first_observed_at is None or observed_at < first_observed_at:
                first_observed_at = observed_at
            if last_observed_at is None or observed_at > last_observed_at:
                last_observed_at = observed_at

        heartbeat = entry.get("supervisor_heartbeat", {})
        heartbeat_status = str(heartbeat.get("status") or "unavailable")
        status_counts[heartbeat_status] += 1
        if heartbeat_status != "healthy":
            incident_count += 1

        heartbeat_age = heartbeat.get("age_seconds")
        if isinstance(heartbeat_age, int):
            max_heartbeat_age_seconds = max(max_heartbeat_age_seconds, heartbeat_age)

        latest_queue_counts = dict(entry.get("queue_counts", {}))
        for key in ("blocked", "dispatched", "done", "pending", "ready"):
            queue_value = latest_queue_counts.get(key)
            if isinstance(queue_value, int):
                queue_samples[key] = max(queue_samples[key], queue_value)

        truth_boundary = entry.get("truth_boundary", {})
        prototype_runtime = prototype_runtime or bool(truth_boundary.get("prototype_runtime"))
        weeklong_claim_allowed = weeklong_claim_allowed or bool(
            truth_boundary.get("weeklong_soak_claim_allowed")
        )
        latest_benchmark_status = (
            entry.get("benchmark_completion_status") or latest_benchmark_status
        )

    observed_window_seconds = 0
    if first_observed_at is not None and last_observed_at is not None:
        observed_window_seconds = max(
            0, int((last_observed_at - first_observed_at).total_seconds())
        )

    observed_window_hours = round(observed_window_seconds / 3600, 2)
    remaining_seconds_to_weeklong = max(0, WEEKLONG_SECONDS - observed_window_seconds)
    remaining_hours_to_weeklong = round(remaining_seconds_to_weeklong / 3600, 2)
    progress_ratio = round(
        min(1.0, observed_window_seconds / WEEKLONG_SECONDS) if WEEKLONG_SECONDS else 0.0,
        4,
    )
    healthy_samples = status_counts.get("healthy", 0)
    healthy_ratio = round((healthy_samples / len(entries)), 4) if entries else 0.0
    estimated_weeklong_completion_at = None
    if first_observed_at is not None:
        estimated_weeklong_completion_at = datetime.fromtimestamp(
            first_observed_at.timestamp() + WEEKLONG_SECONDS,
            tz=UTC,
        ).isoformat()

    return {
        "entry_count": len(entries),
        "first_observed_at": first_observed_at.isoformat() if first_observed_at else None,
        "last_observed_at": last_observed_at.isoformat() if last_observed_at else None,
        "observed_window_seconds": observed_window_seconds,
        "observed_window_hours": observed_window_hours,
        "remaining_seconds_to_weeklong": remaining_seconds_to_weeklong,
        "remaining_hours_to_weeklong": remaining_hours_to_weeklong,
        "observed_window_progress_ratio": progress_ratio,
        "estimated_weeklong_completion_at": estimated_weeklong_completion_at,
        "heartbeat_status_counts": dict(sorted(status_counts.items())),
        "incident_count": incident_count,
        "healthy_ratio": healthy_ratio,
        "max_heartbeat_age_seconds": max_heartbeat_age_seconds,
        "latest_queue_counts": latest_queue_counts,
        "queue_high_watermarks": dict(sorted(queue_samples.items())),
        "latest_benchmark_completion_status": latest_benchmark_status,
        "truth_boundary": {
            "prototype_runtime": prototype_runtime,
            "weeklong_soak_claim_allowed": weeklong_claim_allowed,
            "weeklong_requirement_seconds": WEEKLONG_SECONDS,
            "weeklong_requirement_met": observed_window_seconds >= WEEKLONG_SECONDS,
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    heartbeat_counts = summary["heartbeat_status_counts"]
    latest_queue_counts = summary["latest_queue_counts"]
    truth_boundary = summary["truth_boundary"]

    lines = [
        "# P22 Rolling Soak Evidence Summary",
        "",
        (
            "This report summarizes the current append-only soak ledger. "
            "It is not a claim that the weeklong soak has already completed."
        ),
        "",
        "## Current Window",
        "",
        f"- Ledger entries: `{summary['entry_count']}`",
        f"- First observed at: `{summary['first_observed_at']}`",
        f"- Last observed at: `{summary['last_observed_at']}`",
        f"- Observed window: `{summary['observed_window_hours']}` hours",
        f"- Progress to weeklong threshold: `{summary['observed_window_progress_ratio']}`",
        f"- Remaining to weeklong threshold: `{summary['remaining_hours_to_weeklong']}` hours",
        f"- Estimated weeklong threshold at: `{summary['estimated_weeklong_completion_at']}`",
        "",
        "## Heartbeat Quality",
        "",
        f"- Status counts: `{heartbeat_counts}`",
        f"- Non-healthy incidents: `{summary['incident_count']}`",
        f"- Healthy sample ratio: `{summary['healthy_ratio']}`",
        f"- Max heartbeat age seen: `{summary['max_heartbeat_age_seconds']}` seconds",
        "",
        "## Queue Snapshot",
        "",
        f"- Latest queue counts: `{latest_queue_counts}`",
        f"- Queue high-water marks: `{summary['queue_high_watermarks']}`",
        f"- Latest benchmark completion status: `{summary['latest_benchmark_completion_status']}`",
        "",
        "## Truth Boundary",
        "",
        f"- Prototype runtime boundary remains active: `{truth_boundary['prototype_runtime']}`",
        f"- Weeklong requirement met: `{truth_boundary['weeklong_requirement_met']}`",
        f"- Weeklong claim allowed: `{truth_boundary['weeklong_soak_claim_allowed']}`",
        "",
        "## Judgment",
        "",
    ]

    if truth_boundary["weeklong_requirement_met"] and truth_boundary["weeklong_soak_claim_allowed"]:
        lines.append(
            "The observed ledger window satisfies the configured weeklong "
            "threshold and the truth-boundary gate allows that claim."
        )
    else:
        lines.append(
            "The rolling ledger is useful for unattended validation, but "
            "it does not yet justify a completed weeklong durability claim."
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the rolling unattended-soak ledger into JSON or markdown."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the computed summary as JSON.")
    args = parser.parse_args(argv)

    entries = load_ledger_entries(args.input)
    summary = summarize_entries(entries)

    markdown_output = args.markdown_output
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(render_markdown(summary), encoding="utf-8")

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "Summarized soak ledger: "
            f"entries={summary['entry_count']}, "
            f"window_hours={summary['observed_window_hours']}, "
            f"incidents={summary['incident_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
