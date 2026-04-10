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
DEFAULT_DELTA_SUMMARY_PATH = REPO_ROOT / "artifacts" / "status" / "packet_state_delta_summary.json"
DEFAULT_PACKET_DEFICIT_PATH = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "packet_operator_blocker_surface.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "packet_operator_blocker_surface.md"


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


def _join_or_none(values: list[str]) -> str:
    cleaned = [_clean_text(value) for value in values if _clean_text(value)]
    return ", ".join(cleaned) if cleaned else "none"


def _comparison_boundary(delta_summary: dict[str, Any], delta_report: dict[str, Any]) -> dict[str, Any]:
    boundary = delta_summary.get("comparison_boundary")
    if not isinstance(boundary, dict) or not boundary:
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


def _rescue_candidates(packet_deficit: dict[str, Any]) -> list[dict[str, Any]]:
    by_source_ref: dict[str, dict[str, Any]] = {}
    modality_order: dict[str, int] = {}
    for modality_index, modality_row in enumerate(packet_deficit.get("modality_deficits") or []):
        if not isinstance(modality_row, dict):
            continue
        modality = _clean_text(modality_row.get("modality"))
        if modality and modality not in modality_order:
            modality_order[modality] = modality_index
        modality_missing_packet_count = int(modality_row.get("missing_packet_count") or 0)
        for candidate in modality_row.get("top_source_fix_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            source_ref = _clean_text(candidate.get("source_ref"))
            if not source_ref or source_ref in by_source_ref:
                continue
            source_name = (
                _clean_text(candidate.get("source_name"))
                or _clean_text(modality_row.get("source_name"))
                or modality
                or source_ref
            )
            packet_accessions = [
                _clean_text(value)
                for value in candidate.get("packet_accessions") or []
                if _clean_text(value)
            ]
            by_source_ref[source_ref] = {
                "source_ref": source_ref,
                "source_name": source_name,
                "modality": modality,
                "modality_missing_packet_count": modality_missing_packet_count,
                "priority_rank": int(candidate.get("priority_rank") or 0),
                "affected_packet_count": int(candidate.get("affected_packet_count") or 0),
                "missing_modality_count": int(candidate.get("missing_modality_count") or 0),
                "missing_modalities": [
                    _clean_text(value)
                    for value in candidate.get("missing_modalities") or []
                    if _clean_text(value)
                ],
                "packet_accessions": packet_accessions,
                "packet_ids": [
                    _clean_text(value)
                    for value in candidate.get("packet_ids") or []
                    if _clean_text(value)
                ],
                "modality_order": modality_order.get(modality, 999),
            }
    rescues = list(by_source_ref.values())
    rescues.sort(
        key=lambda row: (
            -int(row["modality_missing_packet_count"]),
            row["modality_order"],
            -int(row["affected_packet_count"]),
            -int(row["missing_modality_count"]),
            row["source_ref"],
        )
    )
    return rescues


def _best_rescue_for_accession(
    accession: str,
    latest_deficit_source_refs: list[str],
    rescue_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    accession = _clean_text(accession).upper()
    for rescue in rescue_index.values():
        if accession in rescue["packet_accessions"]:
            return rescue
    for source_ref in latest_deficit_source_refs:
        rescue = rescue_index.get(_clean_text(source_ref))
        if rescue and accession in rescue["packet_accessions"]:
            return rescue
    return None


def _preserved_blocker_rows(
    delta_summary: dict[str, Any], rescue_index: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in delta_summary.get("latest_baseline_blockers") or []:
        if not isinstance(row, dict):
            continue
        latest_deficit_source_refs = [
            _clean_text(value)
            for value in row.get("latest_deficit_source_refs") or []
            if _clean_text(value)
        ]
        rescue = _best_rescue_for_accession(
            _clean_text(row.get("accession")),
            latest_deficit_source_refs,
            rescue_index,
        )
        next_action = (
            f"Apply {rescue['source_ref']} to clear {_clean_text(row.get('accession')).upper()}."
            if rescue
            else "Resolve the preserved-baseline blocker and rerun the packet path."
        )
        rows.append(
            {
                "accession": _clean_text(row.get("accession")).upper(),
                "packet_level_truth": _clean_text(row.get("packet_level_truth")),
                "evidence_level_truth": _clean_text(row.get("evidence_level_truth")),
                "latest_gap_count": int(row.get("latest_gap_count") or 0),
                "freshest_gap_count": int(row.get("freshest_gap_count") or 0),
                "latest_missing_modalities": [
                    _clean_text(value)
                    for value in row.get("latest_missing_modalities") or []
                    if _clean_text(value)
                ],
                "freshest_missing_modalities": [
                    _clean_text(value)
                    for value in row.get("freshest_missing_modalities") or []
                    if _clean_text(value)
                ],
                "latest_deficit_source_refs": latest_deficit_source_refs,
                "next_rescue_source_ref": rescue["source_ref"] if rescue else "",
                "next_rescue_source_name": rescue["source_name"] if rescue else "",
                "next_rescue_action": next_action,
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["latest_gap_count"]),
            -int(row["freshest_gap_count"]),
            row["accession"],
        )
    )
    return rows


def _fresh_run_not_promotable_rows(delta_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in delta_summary.get("fresh_run_not_promotable") or []:
        if not isinstance(row, dict):
            continue
        freshest_missing = [
            _clean_text(value)
            for value in row.get("freshest_missing_modalities") or []
            if _clean_text(value)
        ]
        rows.append(
            {
                "accession": _clean_text(row.get("accession")).upper(),
                "packet_level_truth": _clean_text(row.get("packet_level_truth")),
                "evidence_level_truth": _clean_text(row.get("evidence_level_truth")),
                "latest_gap_count": int(row.get("latest_gap_count") or 0),
                "freshest_gap_count": int(row.get("freshest_gap_count") or 0),
                "latest_missing_modalities": [
                    _clean_text(value)
                    for value in row.get("latest_missing_modalities") or []
                    if _clean_text(value)
                ],
                "freshest_missing_modalities": freshest_missing,
                "recommended_action": (
                    _clean_text(row.get("recommended_action"))
                    or f"Repair the fresh-run regression in {_join_or_none(freshest_missing)} before any promotion attempt."
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["freshest_gap_count"]),
            row["accession"],
        )
    )
    return rows


def build_packet_operator_blocker_surface(
    *,
    delta_report_path: Path = DEFAULT_DELTA_REPORT_PATH,
    delta_summary_path: Path = DEFAULT_DELTA_SUMMARY_PATH,
    packet_deficit_path: Path = DEFAULT_PACKET_DEFICIT_PATH,
) -> dict[str, Any]:
    delta_report = _read_json(delta_report_path)
    delta_summary = _read_json(delta_summary_path)
    packet_deficit = _read_json(packet_deficit_path)
    boundary = _comparison_boundary(delta_summary, delta_report)
    rescue_candidates = _rescue_candidates(packet_deficit)
    rescue_index = {row["source_ref"]: row for row in rescue_candidates}

    preserved_latest_blockers = _preserved_blocker_rows(delta_summary, rescue_index)
    fresh_run_not_promotable = _fresh_run_not_promotable_rows(delta_summary)

    next_best_actionable_rescues: list[dict[str, Any]] = []
    for rescue in rescue_candidates:
        blocker_accessions = [
            row["accession"]
            for row in preserved_latest_blockers
            if row["accession"] in rescue["packet_accessions"]
        ]
        not_promotable_accessions = [
            row["accession"]
            for row in fresh_run_not_promotable
            if row["accession"] in rescue["packet_accessions"]
        ]
        next_best_actionable_rescues.append(
            {
                **rescue,
                "blocker_accessions": blocker_accessions,
                "not_promotable_accessions": not_promotable_accessions,
                "next_action": (
                    f"Apply {rescue['source_ref']} to clear "
                    f"{_join_or_none(blocker_accessions) if blocker_accessions else _join_or_none(rescue['packet_accessions'])}."
                ),
            }
        )

    summary = {
        "preserved_latest_blocker_count": len(preserved_latest_blockers),
        "fresh_run_regression_count": len(fresh_run_not_promotable),
        "next_best_rescue_count": len(next_best_actionable_rescues),
        "protected_latest_gap_count": int(
            (delta_summary.get("summary") or {}).get("latest_preserved_gap_packet_count") or 0
        ),
        "freshest_remaining_gap_count": int(
            (delta_summary.get("summary") or {}).get("freshest_remaining_gap_packet_count") or 0
        ),
        "blocker_accessions": [row["accession"] for row in preserved_latest_blockers],
        "not_promotable_accessions": [
            row["accession"] for row in fresh_run_not_promotable
        ],
        "rescue_source_refs": [
            row["source_ref"] for row in next_best_actionable_rescues
        ],
    }

    return {
        "schema_id": "proteosphere-packet-operator-blocker-surface-2026-03-31",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "inputs": {
            "delta_report_path": str(delta_report_path),
            "delta_summary_path": str(delta_summary_path),
            "packet_deficit_path": str(packet_deficit_path),
        },
        "comparison_boundary": boundary,
        "summary": summary,
        "truth_boundary": {
            "preserved_latest_blocker_rule": (
                "A preserved latest blocker is a packet that still has missing modalities in the protected latest baseline."
            ),
            "fresh_run_not_promotable_rule": (
                "A fresh-run regression is not promotable when the latest baseline was already complete but the freshest run introduced gaps."
            ),
            "rescue_rule": (
                "Rescues are source-level fixes from the protected deficit dashboard; they describe the next best fix, not a promotion decision."
            ),
        },
        "preserved_latest_blockers": preserved_latest_blockers,
        "fresh_run_regressions_not_promotable": fresh_run_not_promotable,
        "next_best_actionable_rescues": next_best_actionable_rescues,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    boundary = payload["comparison_boundary"]
    lines = [
        "# Packet Operator Blocker Surface",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        (
            "- Comparison boundary: "
            f"{boundary['latest_label']} (`{boundary['latest_path']}`) vs "
            f"{boundary['freshest_label']} (`{boundary['freshest_path']}`)"
        ),
        f"- Preserved latest blockers: `{summary['preserved_latest_blocker_count']}`",
        f"- Fresh-run regressions not promotable: `{summary['fresh_run_regression_count']}`",
        f"- Next-best actionable rescues: `{summary['next_best_rescue_count']}`",
        "",
        "This surface is operator-facing only. It summarizes the current protected packet deficit dashboard, the packet delta summary, and the delta report without changing promotion rules.",
        "",
        "## Preserved Latest Blockers",
        "",
    ]

    if payload["preserved_latest_blockers"]:
        lines.append(
            "| Accession | Latest missing | Freshest missing | Next rescue | Next action |"
        )
        lines.append("| --- | --- | --- | --- | --- |")
        for row in payload["preserved_latest_blockers"]:
            lines.append(
                "| "
                + f"`{row['accession']}` | "
                + f"`{_join_or_none(row['latest_missing_modalities'])}` | "
                + f"`{_join_or_none(row['freshest_missing_modalities'])}` | "
                + f"`{row['next_rescue_source_ref'] or 'none'}` | "
                + f"{row['next_rescue_action']} |"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Fresh-Run Regressions Not Promotable", ""])
    if payload["fresh_run_regressions_not_promotable"]:
        lines.append("| Accession | Freshest missing | Truth | Next action |")
        lines.append("| --- | --- | --- | --- |")
        for row in payload["fresh_run_regressions_not_promotable"]:
            lines.append(
                "| "
                + f"`{row['accession']}` | "
                + f"`{_join_or_none(row['freshest_missing_modalities'])}` | "
                + f"`{row['packet_level_truth']}` | "
                + f"{row['recommended_action']} |"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Next-Best Actionable Rescues", ""])
    if payload["next_best_actionable_rescues"]:
        lines.append(
            "| Source ref | Packet accessions | Leverage | Blockers cleared | Next action |"
        )
        lines.append("| --- | --- | --- | --- | --- |")
        for row in payload["next_best_actionable_rescues"]:
            lines.append(
                "| "
                + f"`{row['source_ref']}` | "
                + f"`{_join_or_none(row['packet_accessions'])}` | "
                + f"`{row['modality_missing_packet_count']}` | "
                + f"`{_join_or_none(row['blocker_accessions'])}` | "
                + f"{row['next_action']} |"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            "- Preserved latest blockers are still blockers in the protected baseline.",
            "- Fresh-run regressions are not promotable and remain separate from the preserved baseline blockers.",
            "- Rescues are source-level fixes only and do not imply promotion.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export an operator-facing packet blocker surface."
    )
    parser.add_argument("--delta-report", type=Path, default=DEFAULT_DELTA_REPORT_PATH)
    parser.add_argument("--delta-summary", type=Path, default=DEFAULT_DELTA_SUMMARY_PATH)
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_packet_operator_blocker_surface(
        delta_report_path=args.delta_report,
        delta_summary_path=args.delta_summary,
        packet_deficit_path=args.packet_deficit,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))
    print(
        "Packet operator blocker surface exported: "
        f"blockers={payload['summary']['preserved_latest_blocker_count']} "
        f"not_promotable={payload['summary']['fresh_run_regression_count']} "
        f"rescues={payload['summary']['next_best_rescue_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
