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
DEFAULT_DELTA_REPORT_PATH = REPO_ROOT / "artifacts" / "status" / "packet_state_delta_report.json"
DEFAULT_PACKET_DEFICIT_PATH = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "packet_state_delta_summary.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "packet_state_delta_summary.md"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _comparison_boundary(delta_report: dict[str, Any]) -> dict[str, Any]:
    boundary = delta_report.get("comparison_boundary")
    if isinstance(boundary, dict) and boundary:
        return {
            "latest_label": _clean_text(boundary.get("latest_label"))
            or "preserved packet baseline",
            "freshest_label": _clean_text(boundary.get("freshest_label"))
            or "freshest run-scoped packet state",
            "latest_path": _clean_text(boundary.get("latest_path")),
            "freshest_path": _clean_text(boundary.get("freshest_path")),
        }
    return {
        "latest_label": "preserved packet baseline",
        "freshest_label": "freshest run-scoped packet state",
        "latest_path": "",
        "freshest_path": "",
    }


def _join_or_none(values: list[str]) -> str:
    cleaned = [_clean_text(value) for value in values if _clean_text(value)]
    return ", ".join(cleaned) if cleaned else "none"


def _operator_action(row: dict[str, Any]) -> str:
    latest_missing = _join_or_none(row.get("latest_missing_modalities") or [])
    freshest_missing = _join_or_none(row.get("freshest_missing_modalities") or [])
    if row["classification"] == "latest-baseline-blocker":
        if row["latest_deficit_source_refs"]:
            return (
                f"Resolve the preserved-baseline blocker in {latest_missing}; "
                f"start from source refs {_join_or_none(row['latest_deficit_source_refs'])} "
                "and rerun the packet path."
            )
        return (
            f"Resolve the preserved-baseline blocker in {latest_missing}; "
            "then rerun the packet path."
        )
    return (
        f"Repair the fresh-run regression in {freshest_missing} before any promotion attempt."
    )


def _summarize_row(row: dict[str, Any], *, classification: str) -> dict[str, Any]:
    packet_row = dict(row)
    packet_row["classification"] = classification
    packet_row["recommended_action"] = _operator_action(packet_row)
    return packet_row


def build_packet_state_delta_summary(
    *,
    delta_report_path: Path = DEFAULT_DELTA_REPORT_PATH,
    packet_deficit_path: Path = DEFAULT_PACKET_DEFICIT_PATH,
) -> dict[str, Any]:
    delta_report = _read_json(delta_report_path)
    packet_deficit = _read_json(packet_deficit_path)
    boundary = _comparison_boundary(delta_report)

    remaining_rows = [row for row in delta_report.get("remaining_gaps") or [] if isinstance(row, dict)]
    latest_baseline_blockers = [
        _summarize_row(row, classification="latest-baseline-blocker")
        for row in remaining_rows
        if int(row.get("latest_gap_count") or 0) > 0
    ]
    fresh_run_not_promotable = [
        _summarize_row(row, classification="fresh-run-not-promotable")
        for row in remaining_rows
        if int(row.get("latest_gap_count") or 0) == 0
        and int(row.get("freshest_gap_count") or 0) > 0
    ]

    latest_baseline_blockers.sort(
        key=lambda row: (
            -int(row.get("latest_gap_count") or 0),
            -int(row.get("freshest_gap_count") or 0),
            _clean_text(row.get("accession")),
        )
    )
    fresh_run_not_promotable.sort(
        key=lambda row: (
            -int(row.get("freshest_gap_count") or 0),
            _clean_text(row.get("accession")),
        )
    )

    latest_deficit_summary = packet_deficit.get("summary") or {}
    delta_summary = delta_report.get("summary") or {}
    summary = {
        "latest_baseline_blocker_count": len(latest_baseline_blockers),
        "fresh_run_not_promotable_count": len(fresh_run_not_promotable),
        "actionable_packet_count": len(latest_baseline_blockers) + len(fresh_run_not_promotable),
        "latest_preserved_gap_packet_count": int(
            latest_deficit_summary.get("packet_deficit_count") or 0
        ),
        "freshest_remaining_gap_packet_count": int(
            delta_summary.get("remaining_gap_packet_count") or 0
        ),
        "blocker_accessions": [row["accession"] for row in latest_baseline_blockers],
        "not_promotable_accessions": [row["accession"] for row in fresh_run_not_promotable],
    }

    # Keep a small read-through of the leverage refs available in the deficit artifact.
    top_leverage_refs = [
        _clean_text(row.get("source_ref"))
        for row in latest_deficit_summary.get("highest_leverage_source_fixes") or []
        if isinstance(row, dict) and _clean_text(row.get("source_ref"))
    ]

    return {
        "schema_id": "proteosphere-packet-state-delta-summary-2026-03-31",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "comparison_boundary": boundary,
        "delta_report_source_path": str(delta_report_path),
        "packet_deficit_source_path": str(packet_deficit_path),
        "summary": summary,
        "truth_boundary": {
            "latest_baseline_blocker_rule": (
                "A packet is a preserved-baseline blocker when the latest baseline still "
                "shows missing modalities and the freshest run has not cleared the packet."
            ),
            "fresh_run_not_promotable_rule": (
                "A packet is not promotable from the fresh run when the latest baseline "
                "was already complete but the freshest run introduced gaps."
            ),
            "latest_deficit_source_refs": top_leverage_refs,
        },
        "latest_baseline_blockers": latest_baseline_blockers,
        "fresh_run_not_promotable": fresh_run_not_promotable,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    boundary = payload["comparison_boundary"]
    lines = [
        "# Packet Delta Operator Summary",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        (
            "- Comparison boundary: "
            f"{boundary['latest_label']} (`{boundary['latest_path']}`) vs "
            f"{boundary['freshest_label']} (`{boundary['freshest_path']}`)"
        ),
        f"- Still latest-baseline blockers: `{summary['latest_baseline_blocker_count']}`",
        f"- Fresh-run evidence not promotable: `{summary['fresh_run_not_promotable_count']}`",
        f"- Actionable packet count: `{summary['actionable_packet_count']}`",
        f"- Latest preserved gap packets: `{summary['latest_preserved_gap_packet_count']}`",
        f"- Freshest remaining gap packets: `{summary['freshest_remaining_gap_packet_count']}`",
        "",
        "This surface only summarizes the current packet delta and deficit artifacts.",
        "It does not change the latest-promotion guard or claim anything promotable on its own.",
        "",
        "## Still Latest-Baseline Blockers",
        "",
    ]

    if payload["latest_baseline_blockers"]:
        lines.append(
            "| Accession | Latest missing | Freshest missing | Truth | Next action |"
        )
        lines.append("| --- | --- | --- | --- | --- |")
        for row in payload["latest_baseline_blockers"]:
            lines.append(
                "| "
                + f"`{row['accession']}` | "
                + f"`{_join_or_none(row['latest_missing_modalities'])}` | "
                + f"`{_join_or_none(row['freshest_missing_modalities'])}` | "
                + f"`{row['packet_level_truth']}` | "
                + f"{row['recommended_action']} |"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Fresh-Run Evidence Not Promotable", ""])
    if payload["fresh_run_not_promotable"]:
        lines.append(
            "| Accession | Latest missing | Freshest missing | Truth | Next action |"
        )
        lines.append("| --- | --- | --- | --- | --- |")
        for row in payload["fresh_run_not_promotable"]:
            lines.append(
                "| "
                + f"`{row['accession']}` | "
                + f"`{_join_or_none(row['latest_missing_modalities'])}` | "
                + f"`{_join_or_none(row['freshest_missing_modalities'])}` | "
                + f"`{row['packet_level_truth']}` | "
                + f"{row['recommended_action']} |"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            "- Preserved-baseline blockers are still blocking the latest baseline and should be fixed first.",
            "- Fresh-run not promotable items are fresh-run regressions only; they should be repaired before any promotion attempt.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export an operator-facing packet delta summary."
    )
    parser.add_argument("--delta-report", type=Path, default=DEFAULT_DELTA_REPORT_PATH)
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_packet_state_delta_summary(
        delta_report_path=args.delta_report,
        packet_deficit_path=args.packet_deficit,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))
    print(
        "Packet delta summary exported: "
        f"blockers={payload['summary']['latest_baseline_blocker_count']} "
        f"not_promotable={payload['summary']['fresh_run_not_promotable_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
