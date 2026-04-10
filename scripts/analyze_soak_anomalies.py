from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.summarize_soak_ledger import load_ledger_entries

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "artifacts" / "runtime" / "soak_ledger.jsonl"
DEFAULT_MARKDOWN_OUTPUT_PATH = REPO_ROOT / "docs" / "reports" / "p22_soak_anomalies.md"


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


def analyze_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    incident_status_counts: Counter[str] = Counter()
    queue_transition_count = 0
    incident_windows: list[dict[str, Any]] = []
    longest_healthy_streak = 0
    current_healthy_streak = 0
    working_healthy_streak = 0
    previous_queue_counts: dict[str, Any] | None = None

    for entry in entries:
        heartbeat = entry.get("supervisor_heartbeat", {})
        heartbeat_status = str(heartbeat.get("status") or "unavailable")
        observed_at = entry.get("observed_at")

        if heartbeat_status == "healthy":
            working_healthy_streak += 1
            current_healthy_streak = working_healthy_streak
            longest_healthy_streak = max(longest_healthy_streak, working_healthy_streak)
        else:
            incident_status_counts[heartbeat_status] += 1
            incident_windows.append(
                {
                    "observed_at": observed_at,
                    "status": heartbeat_status,
                    "age_seconds": heartbeat.get("age_seconds"),
                }
            )
            working_healthy_streak = 0
            current_healthy_streak = 0

        queue_counts = dict(entry.get("queue_counts", {}))
        if previous_queue_counts is not None and queue_counts != previous_queue_counts:
            queue_transition_count += 1
        previous_queue_counts = queue_counts

    first_observed_at = entries[0].get("observed_at") if entries else None
    last_observed_at = entries[-1].get("observed_at") if entries else None
    first_dt = _parse_timestamp(first_observed_at)
    last_dt = _parse_timestamp(last_observed_at)
    observed_hours = 0.0
    if first_dt and last_dt:
        observed_hours = round(max(0.0, (last_dt - first_dt).total_seconds()) / 3600, 2)

    return {
        "entry_count": len(entries),
        "first_observed_at": first_observed_at,
        "last_observed_at": last_observed_at,
        "observed_window_hours": observed_hours,
        "incident_count": len(incident_windows),
        "incident_status_counts": dict(sorted(incident_status_counts.items())),
        "queue_transition_count": queue_transition_count,
        "longest_healthy_streak": longest_healthy_streak,
        "current_healthy_streak": current_healthy_streak,
        "recent_incidents": incident_windows[-5:],
        "latest_queue_counts": dict(entries[-1].get("queue_counts", {})) if entries else {},
        "truth_boundary": dict(entries[-1].get("truth_boundary", {})) if entries else {},
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P22 Soak Anomaly Digest",
        "",
        (
            "This digest summarizes incident patterns in the soak ledger. "
            "It does not upgrade the run to a completed weeklong durability claim."
        ),
        "",
        "## Window",
        "",
        f"- Entries: `{report['entry_count']}`",
        f"- First observed at: `{report['first_observed_at']}`",
        f"- Last observed at: `{report['last_observed_at']}`",
        f"- Observed window: `{report['observed_window_hours']}` hours",
        "",
        "## Incident Pattern",
        "",
        f"- Incident count: `{report['incident_count']}`",
        f"- Incident status counts: `{report['incident_status_counts']}`",
        f"- Queue transition count: `{report['queue_transition_count']}`",
        f"- Longest healthy streak: `{report['longest_healthy_streak']}` samples",
        f"- Current healthy streak: `{report['current_healthy_streak']}` samples",
        "",
        "## Recent Incidents",
        "",
    ]

    if report["recent_incidents"]:
        for incident in report["recent_incidents"]:
            lines.append(
                f"- `{incident['observed_at']}` status=`{incident['status']}` "
                f"age_seconds=`{incident['age_seconds']}`"
            )
    else:
        lines.append("- No non-healthy incidents recorded in the current ledger window.")

    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            (
                f"- Weeklong claim allowed: "
                f"`{report['truth_boundary'].get('weeklong_soak_claim_allowed')}`"
            ),
            f"- Prototype runtime boundary: `{report['truth_boundary'].get('prototype_runtime')}`",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze incident patterns in the unattended soak ledger."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the anomaly payload as JSON.")
    args = parser.parse_args(argv)

    entries = load_ledger_entries(args.input)
    report = analyze_entries(entries)

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Soak anomaly digest: "
            f"entries={report['entry_count']} incidents={report['incident_count']} "
            f"healthy_streak={report['current_healthy_streak']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
