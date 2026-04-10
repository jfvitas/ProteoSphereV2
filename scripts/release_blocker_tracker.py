from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD_PATH = REPO_ROOT / "artifacts" / "status" / "bug_bash_dashboard.json"
DEFAULT_RELEASE_BLOCKERS_PATH = REPO_ROOT / "artifacts" / "status" / "release_blockers.json"
DEFAULT_INTAKE_PATH = REPO_ROOT / "artifacts" / "status" / "bug_bash_intake.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "release_blocker_tracker.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "release_blocker_tracker.md"

OPEN_CLOSURE_STATES = {
    "open",
    "active",
    "accepted",
    "assigned",
    "new",
    "in_progress",
    "in-progress",
    "blocked",
    "triaged",
}
CLOSED_CLOSURE_STATES = {
    "closed",
    "resolved",
    "done",
    "fixed",
    "duplicate",
    "deferred",
    "wont_fix",
    "won_t_fix",
}
UNKNOWN_CLOSURE_STATES = {
    "unknown",
    "unspecified",
    "pending",
    "tbd",
    "n_a",
    "na",
}
EMPTY_OWNER_STATES = {
    "",
    "none",
    "unassigned",
    "unowned",
    "n_a",
    "na",
}
UNKNOWN_OWNER_STATES = {
    "unknown",
    "unspecified",
    "tbd",
    "pending",
}
SEVERITY_RANK = {
    "blocker": 0,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "minor": 5,
    "trivial": 6,
    "unknown": 7,
}
PRIORITY_RANK = {
    "p0": 0,
    "p1": 1,
    "p2": 2,
    "p3": 3,
    "p4": 4,
}
TRIAGE_RANK = {
    "blocked": 0,
    "in_progress": 1,
    "accepted": 2,
    "triaged": 3,
    "new": 4,
    "open": 5,
    "resolved": 6,
    "deferred": 7,
    "duplicate": 8,
    "wont_fix": 9,
    "unknown": 10,
}
CLOSURE_RANK = {
    "open": 0,
    "unknown": 1,
    "closed": 2,
}
OWNERSHIP_RANK = {
    "unowned": 0,
    "unknown": 1,
    "owned": 2,
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_token(value: Any) -> str:
    return _clean_text(value).lower().replace(" ", "_").replace("-", "_")


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    return token in {"1", "true", "yes", "y", "open", "active", "blocked", "on"}


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


def _truth_boundary() -> dict[str, Any]:
    return {
        "summary": (
            "This release blocker tracker is report-only and non-governing. It ranks "
            "blockers by normalized closure and ownership semantics without changing "
            "release authority."
        ),
        "report_only": True,
        "release_authority": False,
        "no_governance_change": True,
    }


def _coerce_rows(payload: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in (
        "release_blockers",
        "bug_bash_items",
        "intake_items",
        "items",
        "rows",
        "blockers",
    ):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _blocker_id(raw_row: dict[str, Any]) -> str:
    for key in ("blocker_id", "bug_id", "id", "issue_id", "release_blocker_id"):
        candidate = _clean_text(raw_row.get(key))
        if candidate:
            return candidate
    title = _clean_text(raw_row.get("title"))
    return title or "unknown-blocker"


def _owner_value(raw_row: dict[str, Any]) -> str:
    for key in ("owner", "assignee", "assigned_to", "lead", "responsible"):
        candidate = _clean_text(raw_row.get(key))
        if candidate:
            return candidate
    return ""


def _owner_status(raw_row: dict[str, Any]) -> tuple[str, str]:
    owner = _owner_value(raw_row)
    token = _normalize_token(owner)
    if not owner or token in EMPTY_OWNER_STATES:
        return "unowned", owner
    if token in UNKNOWN_OWNER_STATES:
        return "unknown", owner
    return "owned", owner


def _severity_value(raw_row: dict[str, Any]) -> str:
    for key in ("severity", "impact", "level"):
        candidate = _normalize_token(raw_row.get(key))
        if candidate:
            return candidate
    if _normalize_bool(raw_row.get("release_blocker")):
        return "blocker"
    return "unknown"


def _priority_value(raw_row: dict[str, Any]) -> str:
    candidate = _normalize_token(raw_row.get("priority"))
    if candidate in PRIORITY_RANK:
        return candidate.upper()
    return "P3"


def _triage_state(raw_row: dict[str, Any]) -> str:
    for key in ("triage_state", "status", "state"):
        candidate = _normalize_token(raw_row.get(key))
        if candidate:
            if candidate in {"inprogress"}:
                return "in_progress"
            if candidate in {"wontfix"}:
                return "wont_fix"
            return candidate
    return "unknown"


def _closure_status(raw_row: dict[str, Any]) -> tuple[str, bool, str]:
    explicit = _normalize_token(
        raw_row.get("closure_state")
        or raw_row.get("closure_status")
        or raw_row.get("resolution")
    )
    triage_state = _triage_state(raw_row)
    release_blocker = _normalize_bool(raw_row.get("release_blocker"))
    blocker_flag = _normalize_bool(raw_row.get("blocker") or raw_row.get("is_blocker"))
    open_flag = _normalize_bool(raw_row.get("open") or raw_row.get("active"))
    closed_flag = _normalize_bool(raw_row.get("closed") or raw_row.get("is_closed"))

    closed_evidence = {
        triage_state in CLOSED_CLOSURE_STATES,
        explicit in CLOSED_CLOSURE_STATES,
        closed_flag,
    }
    open_evidence = {
        release_blocker,
        blocker_flag,
        open_flag,
        triage_state in OPEN_CLOSURE_STATES,
        explicit in OPEN_CLOSURE_STATES,
    }
    closed = any(closed_evidence)
    open_ = any(open_evidence)

    if explicit in CLOSED_CLOSURE_STATES:
        return "closed", True, f"explicit closure_state={explicit}"
    if explicit in OPEN_CLOSURE_STATES:
        return "open", True, f"explicit closure_state={explicit}"
    if explicit in UNKNOWN_CLOSURE_STATES:
        return "unknown", False, f"explicit closure_state={explicit}"

    if open_ and closed:
        return "unknown", False, "conflicting open and closed evidence"
    if open_:
        reasons = []
        if release_blocker:
            reasons.append("release_blocker=true")
        if blocker_flag:
            reasons.append("blocker=true")
        if open_flag:
            reasons.append("open=true")
        if triage_state in OPEN_CLOSURE_STATES:
            reasons.append(f"triage_state={triage_state}")
        return "open", True, ", ".join(reasons) or "open evidence"
    if closed:
        reasons = []
        if closed_flag:
            reasons.append("closed=true")
        if triage_state in CLOSED_CLOSURE_STATES:
            reasons.append(f"triage_state={triage_state}")
        return "closed", True, ", ".join(reasons) or "closed evidence"

    return "unknown", False, "insufficient closure evidence"


def _triage_rank_value(triage_state: str) -> int:
    return TRIAGE_RANK.get(triage_state, TRIAGE_RANK["unknown"])


def _sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        CLOSURE_RANK.get(record["closure_status"], CLOSURE_RANK["unknown"]),
        OWNERSHIP_RANK.get(record["owner_status"], OWNERSHIP_RANK["unknown"]),
        SEVERITY_RANK.get(record["severity"], SEVERITY_RANK["unknown"]),
        PRIORITY_RANK.get(_normalize_token(record["priority"]), PRIORITY_RANK["p3"]),
        _triage_rank_value(record["triage_state"]),
        record["title"].lower(),
        record["blocker_id"].lower(),
    )


def _normalize_blocker_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    blocker_id = _blocker_id(raw_row)
    owner_status, owner = _owner_status(raw_row)
    closure_status, closure_confirmed, closure_reason = _closure_status(raw_row)
    triage_state = _triage_state(raw_row)
    severity = _severity_value(raw_row)
    priority = _priority_value(raw_row)
    release_blocker = _normalize_bool(raw_row.get("release_blocker")) or severity in {
        "blocker",
        "critical",
    }
    conflicting_semantics = closure_status == "unknown" and closure_reason.startswith(
        "conflicting"
    )
    status = f"{closure_status}_{owner_status}"
    return {
        "blocker_id": blocker_id,
        "title": _clean_text(raw_row.get("title")) or blocker_id,
        "owner": owner,
        "owner_status": owner_status,
        "closure_status": closure_status,
        "closure_confirmed": closure_confirmed,
        "closure_reason": closure_reason,
        "triage_state": triage_state,
        "severity": severity,
        "priority": priority,
        "release_blocker": release_blocker,
        "open_release_blocker": release_blocker and closure_status == "open",
        "is_open": closure_status == "open",
        "is_closed": closure_status == "closed",
        "is_ambiguous": closure_status == "unknown",
        "conflicting_semantics": conflicting_semantics,
        "source": _clean_text(raw_row.get("source") or raw_row.get("reported_by")),
        "notes": [
            _clean_text(note)
            for note in (raw_row.get("notes") or [])
            if _clean_text(note)
        ],
        "tracker_status": status,
        "state_normalization_error": "",
        "ownership_normalization_error": "",
        "sort_key": list(_sort_key(
            {
                "closure_status": closure_status,
                "owner_status": owner_status,
                "severity": severity,
                "priority": priority,
                "triage_state": triage_state,
                "title": _clean_text(raw_row.get("title")) or blocker_id,
                "blocker_id": blocker_id,
            }
        )),
    }


def _choose_rows(
    dashboard_payload: dict[str, Any] | list[dict[str, Any]] | None,
    release_blockers_payload: dict[str, Any] | list[dict[str, Any]] | None,
    intake_payload: dict[str, Any] | list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], str]:
    if dashboard_payload is not None:
        rows = _coerce_rows(dashboard_payload)
        if rows:
            return rows, "dashboard"

    rows = _coerce_rows(release_blockers_payload)
    if rows:
        return rows, "release_blockers"

    rows = _coerce_rows(intake_payload)
    if rows:
        return rows, "intake"

    return [], "empty"


def build_release_blocker_tracker(
    dashboard_payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    release_blockers_payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    intake_payload: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    raw_rows, source_mode = _choose_rows(
        dashboard_payload, release_blockers_payload, intake_payload
    )
    records = [_normalize_blocker_row(row) for row in raw_rows]
    records.sort(key=_sort_key)

    closure_counts = {"open": 0, "unknown": 0, "closed": 0}
    ownership_counts = {"owned": 0, "unowned": 0, "unknown": 0}
    severity_counts: dict[str, int] = {key: 0 for key in SEVERITY_RANK}
    priority_counts: dict[str, int] = {key.upper(): 0 for key in PRIORITY_RANK}
    tracker_status_counts: dict[str, int] = {}

    for record in records:
        closure_counts[record["closure_status"]] = (
            closure_counts.get(record["closure_status"], 0) + 1
        )
        ownership_counts[record["owner_status"]] = (
            ownership_counts.get(record["owner_status"], 0) + 1
        )
        severity_counts[record["severity"]] = severity_counts.get(record["severity"], 0) + 1
        priority_counts[record["priority"]] = priority_counts.get(record["priority"], 0) + 1
        tracker_status_counts[record["tracker_status"]] = (
            tracker_status_counts.get(record["tracker_status"], 0) + 1
        )

    open_rows = [row for row in records if row["closure_status"] == "open"]
    ambiguous_rows = [row for row in records if row["closure_status"] == "unknown"]
    closed_rows = [row for row in records if row["closure_status"] == "closed"]

    return {
        "artifact_id": "release_blocker_tracker",
        "schema_id": "proteosphere-release-blocker-tracker-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "source_mode": source_mode,
            "dashboard_row_count": len(_coerce_rows(dashboard_payload)),
            "release_blockers_row_count": len(_coerce_rows(release_blockers_payload)),
            "intake_row_count": len(_coerce_rows(intake_payload)),
            "combined_row_count": len(raw_rows),
        },
        "summary": {
            "total_rows": len(records),
            "open_blocker_count": len(open_rows),
            "closure_unknown_count": len(ambiguous_rows),
            "closed_blocker_count": len(closed_rows),
            "owned_count": ownership_counts["owned"],
            "unowned_count": ownership_counts["unowned"],
            "unknown_owner_count": ownership_counts["unknown"],
            "release_blocker_count": sum(1 for row in records if row["release_blocker"]),
            "open_release_blocker_count": sum(
                1 for row in records if row["open_release_blocker"]
            ),
            "tracker_status_counts": {
                key: count for key, count in sorted(tracker_status_counts.items()) if count
            },
            "closure_status_counts": {
                key: count for key, count in closure_counts.items() if count
            },
            "ownership_status_counts": {
                key: count for key, count in ownership_counts.items() if count
            },
            "severity_counts": {
                key: count for key, count in severity_counts.items() if count
            },
            "priority_counts": {
                key: count for key, count in priority_counts.items() if count
            },
            "blocked_release_gate": len(open_rows) > 0,
            "release_gate_state": (
                "blocked_pending_open_release_blockers"
                if open_rows
                else "clear_but_report_only"
            ),
        },
        "ranking_rules": [
            "open blockers rank ahead of ambiguous blockers, which rank ahead of closed blockers",
            "unowned blockers rank ahead of unknown ownership, which rank ahead of owned blockers",
            "severity and priority break ties before triage state, title, and blocker identifier",
            "conflicting closure evidence is fail-closed into the ambiguous bucket",
        ],
        "truth_boundary": _truth_boundary(),
        "release_readiness": {
            "rc_signoff_state": "report_only",
            "release_claim_allowed": False,
            "report_only": True,
            "open_blockers_prevent_release_claim": len(open_rows) > 0,
        },
        "blockers": [
            {
                "blocker_id": record["blocker_id"],
                "title": record["title"],
                "owner": record["owner"],
                "owner_status": record["owner_status"],
                "closure_status": record["closure_status"],
                "closure_confirmed": record["closure_confirmed"],
                "closure_reason": record["closure_reason"],
                "triage_state": record["triage_state"],
                "severity": record["severity"],
                "priority": record["priority"],
                "release_blocker": record["release_blocker"],
                "open_release_blocker": record["open_release_blocker"],
                "is_open": record["is_open"],
                "is_closed": record["is_closed"],
                "is_ambiguous": record["is_ambiguous"],
                "conflicting_semantics": record["conflicting_semantics"],
                "source": record["source"],
                "notes": record["notes"],
                "tracker_status": record["tracker_status"],
                "sort_key": record["sort_key"],
            }
            for record in records
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Release Blocker Tracker",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Source mode: `{payload['inputs']['source_mode']}`",
        f"- Open blockers: `{summary['open_blocker_count']}`",
        f"- Closure unknown: `{summary['closure_unknown_count']}`",
        f"- Closed blockers: `{summary['closed_blocker_count']}`",
        f"- Owned: `{summary['owned_count']}`",
        f"- Unowned: `{summary['unowned_count']}`",
        "",
        "## Truth Boundary",
        "",
        f"- Report only: `{payload['truth_boundary']['report_only']}`",
        f"- Release authority: `{payload['truth_boundary']['release_authority']}`",
        "",
        "## Ranked Blockers",
        "",
    ]

    if payload["blockers"]:
        lines.append(
            "| Rank | Blocker | Tracker status | Closure | Ownership | Severity | Priority |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for index, row in enumerate(payload["blockers"], start=1):
            lines.append(
                "| "
                + f"{index} | "
                + f"`{row['blocker_id']}` {row['title']} | "
                + f"`{row['tracker_status']}` | "
                + f"`{row['closure_status']}` | "
                + f"`{row['owner_status']}` | "
                + f"`{row['severity']}` | "
                + f"`{row['priority']}` |"
            )
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only release blocker tracker."
    )
    parser.add_argument("--dashboard", type=Path, default=DEFAULT_DASHBOARD_PATH)
    parser.add_argument("--release-blockers", type=Path, default=DEFAULT_RELEASE_BLOCKERS_PATH)
    parser.add_argument("--intake", type=Path, default=DEFAULT_INTAKE_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--no-markdown", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dashboard_payload = _read_json_if_exists(args.dashboard)
    release_blockers_payload = _read_json_if_exists(args.release_blockers)
    intake_payload = _read_json_if_exists(args.intake)
    payload = build_release_blocker_tracker(
        dashboard_payload=dashboard_payload,
        release_blockers_payload=release_blockers_payload,
        intake_payload=intake_payload,
    )
    _write_json(args.output_json, payload)
    if not args.no_markdown:
        _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
