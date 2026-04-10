from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = REPO_ROOT / "artifacts" / "status" / "bug_bash_intake.json"
DEFAULT_RELEASE_BLOCKERS = REPO_ROOT / "artifacts" / "status" / "release_blockers.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "bug_bash_dashboard.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "bug_bash_dashboard.md"

OPEN_TRIAGE_STATES = {
    "new",
    "triaged",
    "accepted",
    "in_progress",
    "blocked",
}
CLOSED_TRIAGE_STATES = {
    "resolved",
    "deferred",
    "duplicate",
    "wont_fix",
}
ALL_TRIAGE_STATES = OPEN_TRIAGE_STATES | CLOSED_TRIAGE_STATES

BLOCKER_TRANSITIONS: dict[str, dict[str, str]] = {
    "new": {
        "triage": "triaged",
        "defer": "deferred",
        "duplicate": "duplicate",
        "wont_fix": "wont_fix",
    },
    "triaged": {
        "accept": "accepted",
        "defer": "deferred",
        "duplicate": "duplicate",
        "wont_fix": "wont_fix",
    },
    "accepted": {
        "start_fix": "in_progress",
        "block": "blocked",
        "resolve": "resolved",
        "defer": "deferred",
        "wont_fix": "wont_fix",
    },
    "in_progress": {
        "block": "blocked",
        "resolve": "resolved",
        "defer": "deferred",
        "wont_fix": "wont_fix",
    },
    "blocked": {
        "unblock": "in_progress",
        "resolve": "resolved",
        "defer": "deferred",
        "wont_fix": "wont_fix",
    },
    "resolved": {
        "reopen": "triaged",
    },
    "deferred": {
        "reopen": "triaged",
    },
    "duplicate": {
        "reopen": "triaged",
    },
    "wont_fix": {
        "reopen": "triaged",
    },
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _normalize_triage_state(value: Any) -> tuple[str, str | None]:
    state = _clean_text(value).lower().replace(" ", "_")
    if not state:
        return "new", None
    if state in ALL_TRIAGE_STATES:
        return state, None
    return "new", f"unrecognized triage state {state!r}"


def _normalize_priority(value: Any) -> str:
    priority = _clean_text(value).upper()
    if priority in {"P0", "P1", "P2", "P3", "P4"}:
        return priority
    return "P3"


def _truth_boundary() -> dict[str, Any]:
    return {
        "summary": (
            "This bug-bash dashboard is report-only and non-governing. It summarizes "
            "intake and blocker triage state without changing RC signoff or release authority."
        ),
        "report_only": True,
        "rc_signoff_locked": True,
        "release_authority": False,
        "no_governance_change": True,
    }


def advance_blocker_triage_state(current_state: str, event: str) -> str:
    state = _normalize_triage_state(current_state)[0]
    event_name = _clean_text(event).lower().replace(" ", "_")
    if not event_name:
        return state
    next_state = BLOCKER_TRANSITIONS.get(state, {}).get(event_name)
    if next_state is None:
        raise ValueError(f"invalid blocker triage transition: {state!r} -> {event_name!r}")
    return next_state


def simulate_blocker_triage_history(
    initial_state: str,
    events: Iterable[Any],
) -> dict[str, Any]:
    state, normalization_error = _normalize_triage_state(initial_state)
    transition_log: list[dict[str, Any]] = []
    errors: list[str] = []

    for raw_event in events:
        event_name = _clean_text(raw_event)
        if not event_name:
            continue
        try:
            next_state = advance_blocker_triage_state(state, event_name)
        except ValueError as exc:
            errors.append(str(exc))
            transition_log.append(
                {
                    "from_state": state,
                    "event": event_name,
                    "to_state": state,
                    "allowed": False,
                    "error": str(exc),
                }
            )
            continue
        transition_log.append(
            {
                "from_state": state,
                "event": event_name,
                "to_state": next_state,
                "allowed": True,
            }
        )
        state = next_state

    return {
        "initial_state": _normalize_triage_state(initial_state)[0],
        "current_state": state,
        "transition_log": transition_log,
        "normalization_error": normalization_error,
        "transition_errors": errors,
    }


def _record_release_blocker(raw_row: dict[str, Any]) -> dict[str, Any]:
    bug_id = (
        _clean_text(raw_row.get("bug_id"))
        or _clean_text(raw_row.get("id"))
        or _clean_text(raw_row.get("issue_id"))
        or _clean_text(raw_row.get("blocker_id"))
    )
    triage_state, normalization_error = _normalize_triage_state(
        raw_row.get("triage_state") or raw_row.get("status")
    )
    history = raw_row.get("triage_events") or raw_row.get("state_history") or []
    triage_simulation = simulate_blocker_triage_history(triage_state, history)
    current_state = triage_simulation["current_state"]
    severity = _clean_text(raw_row.get("severity")).lower()
    release_blocker = bool(raw_row.get("release_blocker"))
    if not release_blocker:
        release_blocker = severity in {"blocker", "critical"}
    open_release_blocker = release_blocker and current_state not in CLOSED_TRIAGE_STATES

    record = {
        "bug_id": bug_id,
        "title": _clean_text(raw_row.get("title")),
        "area": _clean_text(
            raw_row.get("area") or raw_row.get("surface") or raw_row.get("component")
        ),
        "priority": _normalize_priority(raw_row.get("priority")),
        "severity": severity or "unknown",
        "release_blocker": release_blocker,
        "open_release_blocker": open_release_blocker,
        "triage_state": current_state,
        "initial_triage_state": triage_simulation["initial_state"],
        "triage_transition_log": triage_simulation["transition_log"],
        "owner": _clean_text(raw_row.get("owner") or raw_row.get("assignee")),
        "source": _clean_text(raw_row.get("source") or raw_row.get("reported_by")),
        "notes": [
            _clean_text(note)
            for note in (raw_row.get("notes") or [])
            if _clean_text(note)
        ],
        "reported_at": _clean_text(raw_row.get("reported_at")),
        "updated_at": _clean_text(raw_row.get("updated_at")),
        "state_normalization_error": normalization_error,
        "triage_transition_errors": triage_simulation["transition_errors"],
    }
    return record


def _coerce_intake_rows(
    intake_payload: dict[str, Any] | list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if intake_payload is None:
        return []
    if isinstance(intake_payload, list):
        return [row for row in intake_payload if isinstance(row, dict)]
    if not isinstance(intake_payload, dict):
        return []
    rows = intake_payload.get("bug_bash_items")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    rows = intake_payload.get("intake_items")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    rows = intake_payload.get("items")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _coerce_blocker_rows(
    blockers_payload: dict[str, Any] | list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if blockers_payload is None:
        return []
    if isinstance(blockers_payload, list):
        return [row for row in blockers_payload if isinstance(row, dict)]
    if not isinstance(blockers_payload, dict):
        return []
    rows = blockers_payload.get("release_blockers")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    rows = blockers_payload.get("blockers")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def build_bug_bash_dashboard(
    intake_payload: dict[str, Any] | list[dict[str, Any]] | None,
    blockers_payload: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    intake_rows = [_record_release_blocker(row) for row in _coerce_intake_rows(intake_payload)]
    blocker_rows = [
        _record_release_blocker(row) for row in _coerce_blocker_rows(blockers_payload)
    ]
    combined_rows = intake_rows + blocker_rows
    release_blockers = [row for row in combined_rows if row["release_blocker"]]
    open_release_blockers = [row for row in release_blockers if row["open_release_blocker"]]
    triage_state_counts: dict[str, int] = {state: 0 for state in sorted(ALL_TRIAGE_STATES)}
    priority_counts: dict[str, int] = {priority: 0 for priority in ("P0", "P1", "P2", "P3", "P4")}

    for row in combined_rows:
        triage_state_counts[row["triage_state"]] = (
            triage_state_counts.get(row["triage_state"], 0) + 1
        )
        priority_counts[row["priority"]] = priority_counts.get(row["priority"], 0) + 1

    blockers_by_state = {
        state: [row for row in release_blockers if row["triage_state"] == state]
        for state in sorted(ALL_TRIAGE_STATES)
    }
    blocked_on_release_gate = len(open_release_blockers) > 0

    return {
        "artifact_id": "bug_bash_dashboard",
        "schema_id": "proteosphere-bug-bash-dashboard-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "intake_count": len(intake_rows),
            "blocker_count": len(blocker_rows),
            "combined_row_count": len(combined_rows),
        },
        "summary": {
            "intake_count": len(intake_rows),
            "release_blocker_count": len(release_blockers),
            "open_release_blocker_count": len(open_release_blockers),
            "closed_release_blocker_count": len(release_blockers) - len(open_release_blockers),
            "blocked_on_release_gate": blocked_on_release_gate,
            "release_gate_state": (
                "blocked_pending_open_release_blockers"
                if blocked_on_release_gate
                else "clear_but_report_only"
            ),
            "triage_state_counts": {
                state: count for state, count in triage_state_counts.items() if count
            },
            "priority_counts": {
                priority: count
                for priority, count in priority_counts.items()
                if count
            },
        },
        "blockers_by_state": {
            state: [
                {
                    "bug_id": row["bug_id"],
                    "title": row["title"],
                    "area": row["area"],
                    "priority": row["priority"],
                    "severity": row["severity"],
                    "owner": row["owner"],
                    "source": row["source"],
                    "triage_state": row["triage_state"],
                    "open_release_blocker": row["open_release_blocker"],
                    "triage_transition_log": row["triage_transition_log"],
                }
                for row in rows
            ]
            for state, rows in blockers_by_state.items()
            if rows
        },
        "release_blockers": [
            {
                "bug_id": row["bug_id"],
                "title": row["title"],
                "area": row["area"],
                "priority": row["priority"],
                "severity": row["severity"],
                "release_blocker": row["release_blocker"],
                "open_release_blocker": row["open_release_blocker"],
                "triage_state": row["triage_state"],
                "initial_triage_state": row["initial_triage_state"],
                "triage_transition_log": row["triage_transition_log"],
                "owner": row["owner"],
                "source": row["source"],
                "notes": row["notes"],
                "state_normalization_error": row["state_normalization_error"],
                "triage_transition_errors": row["triage_transition_errors"],
            }
            for row in release_blockers
        ],
        "intake_rows": [
            {
                "bug_id": row["bug_id"],
                "title": row["title"],
                "area": row["area"],
                "priority": row["priority"],
                "severity": row["severity"],
                "release_blocker": row["release_blocker"],
                "open_release_blocker": row["open_release_blocker"],
                "triage_state": row["triage_state"],
                "owner": row["owner"],
                "source": row["source"],
                "notes": row["notes"],
                "state_normalization_error": row["state_normalization_error"],
                "triage_transition_log": row["triage_transition_log"],
            }
            for row in intake_rows
        ],
        "truth_boundary": _truth_boundary(),
        "release_readiness": {
            "rc_signoff_state": "report_only",
            "release_claim_allowed": False,
            "report_only": True,
            "open_blockers_prevent_release_claim": blocked_on_release_gate,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Bug Bash Dashboard",
        "",
        f"- Release gate state: `{payload['summary']['release_gate_state']}`",
        f"- Open release blockers: `{payload['summary']['open_release_blocker_count']}`",
        f"- Closed release blockers: `{payload['summary']['closed_release_blocker_count']}`",
        "",
        "## Truth Boundary",
        "",
        f"- Report only: `{payload['truth_boundary']['report_only']}`",
        f"- Release authority: `{payload['truth_boundary']['release_authority']}`",
        f"- RC signoff locked: `{payload['truth_boundary']['rc_signoff_locked']}`",
        "",
    ]
    if payload["summary"]["triage_state_counts"]:
        lines.extend(["## Triage State Counts", ""])
        for state, count in payload["summary"]["triage_state_counts"].items():
            lines.append(f"- `{state}`: `{count}`")
        lines.append("")
    if payload["release_blockers"]:
        lines.extend(["## Release Blockers", ""])
        for row in payload["release_blockers"]:
            lines.append(
                f"- `{row['bug_id']}` `{row['triage_state']}` "
                f"blocker=`{row['release_blocker']}` open=`{row['open_release_blocker']}`"
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a machine-readable bug-bash intake and release blocker dashboard."
    )
    parser.add_argument("--intake", type=Path, default=DEFAULT_INTAKE)
    parser.add_argument("--release-blockers", type=Path, default=DEFAULT_RELEASE_BLOCKERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    intake_payload = _read_json_if_exists(args.intake)
    blockers_payload = _read_json_if_exists(args.release_blockers)
    payload = build_bug_bash_dashboard(intake_payload, blockers_payload)
    _write_json(args.output, payload)
    _write_text(args.markdown_output, render_markdown(payload))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
