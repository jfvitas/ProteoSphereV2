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
DEFAULT_COMPARISON_PATH = REPO_ROOT / "artifacts" / "status" / "packet_state_comparison.json"
DEFAULT_PACKET_DEFICIT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "packet_state_delta_report.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "packet_state_delta_report.md"


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


def _comparison_boundary(comparison: dict[str, Any]) -> dict[str, Any]:
    boundary = comparison.get("comparison_boundary")
    if isinstance(boundary, dict) and boundary:
        return {
            "latest_label": _clean_text(boundary.get("latest_label"))
            or "preserved packet baseline",
            "freshest_label": _clean_text(boundary.get("freshest_label"))
            or "freshest run-scoped packet state",
            "latest_path": _clean_text(boundary.get("latest_path"))
            or _clean_text(comparison.get("latest_path")),
            "freshest_path": _clean_text(boundary.get("freshest_path"))
            or _clean_text(comparison.get("freshest_path")),
        }
    return {
        "latest_label": "preserved packet baseline",
        "freshest_label": "freshest run-scoped packet state",
        "latest_path": _clean_text(comparison.get("latest_path")),
        "freshest_path": _clean_text(comparison.get("freshest_path")),
    }


def _packet_deficit_index(packet_deficit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in packet_deficit.get("packets") or []:
        if not isinstance(row, dict):
            continue
        accession = _clean_text(row.get("accession")).upper()
        if accession:
            indexed[accession] = dict(row)
    return indexed


def _resolve_manifest_path(path_text: str) -> Path | None:
    text = _clean_text(path_text)
    if not text:
        return None
    path = Path(text)
    if path.is_file():
        return path
    if not path.is_absolute():
        candidate = REPO_ROOT / path
        if candidate.is_file():
            return candidate
    return None


def _manifest_evidence_summary(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return {
            "artifact_count": 0,
            "note_count": 0,
            "present_modality_count": 0,
            "missing_modality_count": 0,
        }
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), list) else []
    notes = manifest.get("notes") if isinstance(manifest.get("notes"), list) else []
    present_modalities = (
        manifest.get("present_modalities")
        if isinstance(manifest.get("present_modalities"), list)
        else []
    )
    missing_modalities = (
        manifest.get("missing_modalities")
        if isinstance(manifest.get("missing_modalities"), list)
        else []
    )
    return {
        "artifact_count": len(artifacts),
        "note_count": len(notes),
        "present_modality_count": len(present_modalities),
        "missing_modality_count": len(missing_modalities),
    }


def _delta_kind(latest_gap_count: int, freshest_gap_count: int) -> str:
    if freshest_gap_count < latest_gap_count:
        return "improved"
    if freshest_gap_count > latest_gap_count:
        return "regressed"
    return "unchanged"


def _evidence_kind(
    latest_evidence: dict[str, Any],
    freshest_evidence: dict[str, Any],
) -> str:
    artifact_delta = int(freshest_evidence["artifact_count"]) - int(latest_evidence["artifact_count"])
    note_delta = int(freshest_evidence["note_count"]) - int(latest_evidence["note_count"])
    improved = artifact_delta > 0 or note_delta < 0
    regressed = artifact_delta < 0 or note_delta > 0
    if improved and not regressed:
        return "improved"
    if regressed and not improved:
        return "regressed"
    if improved and regressed:
        return "mixed"
    return "unchanged"


def _delta_row(
    comparison_row: dict[str, Any],
    *,
    latest_deficit_row: dict[str, Any] | None,
    latest_manifest: dict[str, Any] | None,
    freshest_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    latest_missing_modalities = [
        _clean_text(value)
        for value in (latest_deficit_row or {}).get("missing_modalities") or []
        if _clean_text(value)
    ]
    freshest_missing_modalities = [
        _clean_text(value)
        for value in comparison_row.get("freshest_missing_modalities") or []
        if _clean_text(value)
    ]
    latest_gap_count = int(
        (latest_deficit_row or {}).get("missing_modality_count")
        or len(latest_missing_modalities)
        or 0
    )
    freshest_gap_count = len(freshest_missing_modalities)
    delta = freshest_gap_count - latest_gap_count
    kind = _delta_kind(latest_gap_count, freshest_gap_count)
    latest_deficit_refs = [
        _clean_text(value)
        for value in (latest_deficit_row or {}).get("deficit_source_refs") or []
        if _clean_text(value)
    ]
    latest_evidence = _manifest_evidence_summary(latest_manifest)
    freshest_evidence = _manifest_evidence_summary(freshest_manifest)
    evidence_kind = _evidence_kind(latest_evidence, freshest_evidence)
    packet_level_truth = (
        "fresh-run-improved"
        if kind == "improved"
        else "fresh-run-regressed"
        if kind == "regressed"
        else "fresh-run-unchanged"
    )
    evidence_level_truth = (
        "fresh-run-evidence-improved"
        if evidence_kind == "improved"
        else "fresh-run-evidence-regressed"
        if evidence_kind == "regressed"
        else "fresh-run-evidence-mixed"
        if evidence_kind == "mixed"
        else "fresh-run-evidence-unchanged"
    )
    return {
        "accession": _clean_text(comparison_row.get("accession")).upper(),
        "latest_status": _clean_text(comparison_row.get("latest_status")),
        "freshest_status": _clean_text(comparison_row.get("freshest_status")),
        "latest_gap_count": latest_gap_count,
        "freshest_gap_count": freshest_gap_count,
        "delta_gap_count": delta,
        "delta_kind": kind,
        "packet_level_truth": packet_level_truth,
        "latest_artifact_count": latest_evidence["artifact_count"],
        "freshest_artifact_count": freshest_evidence["artifact_count"],
        "latest_note_count": latest_evidence["note_count"],
        "freshest_note_count": freshest_evidence["note_count"],
        "evidence_artifact_delta": int(freshest_evidence["artifact_count"])
        - int(latest_evidence["artifact_count"]),
        "evidence_note_delta": int(freshest_evidence["note_count"])
        - int(latest_evidence["note_count"]),
        "evidence_delta_kind": evidence_kind,
        "evidence_level_truth": evidence_level_truth,
        "latest_missing_modalities": latest_missing_modalities,
        "freshest_missing_modalities": freshest_missing_modalities,
        "latest_deficit_source_refs": latest_deficit_refs,
        "freshest_manifest_path": _clean_text(comparison_row.get("freshest_manifest_path")),
        "latest_manifest_path": _clean_text(comparison_row.get("latest_manifest_path")),
    }


def build_packet_state_delta_report(
    *,
    comparison_path: Path = DEFAULT_COMPARISON_PATH,
    packet_deficit_path: Path = DEFAULT_PACKET_DEFICIT_PATH,
) -> dict[str, Any]:
    comparison = _read_json(comparison_path)
    packet_deficit = _read_json(packet_deficit_path)
    boundary = _comparison_boundary(comparison)
    deficit_index = _packet_deficit_index(packet_deficit)

    rows: list[dict[str, Any]] = []
    for comparison_row in comparison.get("packets") or []:
        if not isinstance(comparison_row, dict):
            continue
        accession = _clean_text(comparison_row.get("accession")).upper()
        if not accession:
            continue
        latest_deficit_row = deficit_index.get(accession)
        latest_manifest = _resolve_manifest_path(
            _clean_text((latest_deficit_row or {}).get("manifest_path"))
        )
        freshest_manifest = _resolve_manifest_path(
            _clean_text(comparison_row.get("freshest_manifest_path"))
        )
        row = _delta_row(
            comparison_row,
            latest_deficit_row=latest_deficit_row,
            latest_manifest=(
                _read_json(latest_manifest) if latest_manifest is not None else None
            ),
            freshest_manifest=(
                _read_json(freshest_manifest) if freshest_manifest is not None else None
            ),
        )
        if row["latest_gap_count"] == 0 and row["freshest_gap_count"] == 0:
            continue
        rows.append(row)

    improved_rows = [row for row in rows if row["delta_kind"] == "improved"]
    regressed_rows = [row for row in rows if row["delta_kind"] == "regressed"]
    unchanged_rows = [row for row in rows if row["delta_kind"] == "unchanged"]
    remaining_rows = [row for row in rows if row["freshest_gap_count"] > 0]
    evidence_improved_rows = [row for row in rows if row["evidence_delta_kind"] == "improved"]
    evidence_regressed_rows = [
        row for row in rows if row["evidence_delta_kind"] == "regressed"
    ]
    evidence_mixed_rows = [row for row in rows if row["evidence_delta_kind"] == "mixed"]
    evidence_unchanged_rows = [
        row for row in rows if row["evidence_delta_kind"] == "unchanged"
    ]

    def improved_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row["delta_gap_count"],
            -row["freshest_gap_count"],
            row["accession"],
        )

    def regressed_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            -row["delta_gap_count"],
            -row["freshest_gap_count"],
            row["accession"],
        )

    def remaining_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            -row["freshest_gap_count"],
            row["delta_gap_count"],
            row["accession"],
        )

    improved_rows = sorted(improved_rows, key=improved_sort_key)
    regressed_rows = sorted(regressed_rows, key=regressed_sort_key)
    unchanged_rows = sorted(unchanged_rows, key=remaining_sort_key)
    remaining_rows = sorted(remaining_rows, key=remaining_sort_key)

    latest_gap_packet_count = int(
        (packet_deficit.get("summary") or {}).get("packet_deficit_count") or 0
    )
    freshest_gap_packet_count = len(remaining_rows)
    packet_level_change_count = len(improved_rows) + len(regressed_rows)
    packet_level_unchanged_count = len(unchanged_rows)
    evidence_level_change_count = (
        len(evidence_improved_rows)
        + len(evidence_regressed_rows)
        + len(evidence_mixed_rows)
    )

    return {
        "schema_id": "proteosphere-packet-state-delta-report-2026-03-31",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "comparison_boundary": boundary,
        "comparison_source_path": str(comparison_path),
        "packet_deficit_source_path": str(packet_deficit_path),
        "summary": {
            "latest_gap_packet_count": latest_gap_packet_count,
            "freshest_gap_packet_count": freshest_gap_packet_count,
            "packet_level_improved_count": len(improved_rows),
            "packet_level_regressed_count": len(regressed_rows),
            "packet_level_unchanged_count": packet_level_unchanged_count,
            "packet_level_change_count": packet_level_change_count,
            "evidence_layer_improved_count": len(evidence_improved_rows),
            "evidence_layer_regressed_count": len(evidence_regressed_rows),
            "evidence_layer_mixed_count": len(evidence_mixed_rows),
            "evidence_layer_unchanged_count": len(evidence_unchanged_rows),
            "evidence_layer_change_count": evidence_level_change_count,
            "remaining_gap_packet_count": freshest_gap_packet_count,
            "improved_accessions": [row["accession"] for row in improved_rows],
            "regressed_accessions": [row["accession"] for row in regressed_rows],
            "unchanged_accessions": [row["accession"] for row in unchanged_rows],
            "evidence_improved_accessions": [
                row["accession"] for row in evidence_improved_rows
            ],
            "evidence_regressed_accessions": [
                row["accession"] for row in evidence_regressed_rows
            ],
            "evidence_mixed_accessions": [
                row["accession"] for row in evidence_mixed_rows
            ],
        },
        "truth_boundary": {
            "packet_level_improvement_rule": (
                "A packet is counted as improved only when the freshest run reduces its "
                "packet-level missing modality count relative to the preserved baseline. "
                "Lower-layer evidence changes are not counted as improvements."
            ),
            "evidence_layer_rule": (
                "Lower-layer evidence is tracked separately using manifest artifact and "
                "note counts; a packet may improve, regress, or stay mixed at the "
                "evidence layer independently of packet-level missing modality counts."
            ),
        },
        "packet_level_improvements": improved_rows,
        "packet_level_regressions": regressed_rows,
        "unchanged_remaining_gaps": unchanged_rows,
        "lower_layer_evidence_improvements": evidence_improved_rows,
        "lower_layer_evidence_regressions": evidence_regressed_rows,
        "lower_layer_evidence_mixed": evidence_mixed_rows,
        "lower_layer_evidence_unchanged": evidence_unchanged_rows,
        "remaining_gaps": remaining_rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    boundary = payload["comparison_boundary"]
    lines = [
        "# Packet Delta Report",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        (
            "- Comparison boundary: "
            f"{boundary['latest_label']} (`{boundary['latest_path']}`) vs "
            f"{boundary['freshest_label']} (`{boundary['freshest_path']}`)"
        ),
        f"- Latest preserved gap packets: `{summary['latest_gap_packet_count']}`",
        f"- Freshest run packets with gaps: `{summary['freshest_gap_packet_count']}`",
        f"- Packet-level improvements: `{summary['packet_level_improved_count']}`",
        f"- Packet-level regressions: `{summary['packet_level_regressed_count']}`",
        f"- Packet-level unchanged gaps: `{summary['packet_level_unchanged_count']}`",
        f"- Lower-layer evidence improvements: `{summary['evidence_layer_improved_count']}`",
        f"- Lower-layer evidence regressions: `{summary['evidence_layer_regressed_count']}`",
        f"- Lower-layer evidence mixed: `{summary['evidence_layer_mixed_count']}`",
        f"- Lower-layer evidence unchanged: `{summary['evidence_layer_unchanged_count']}`",
        "",
        "Packet-level improvements are counted only when the freshest run reduces the",
        "packet-level missing modality count. Lower-layer evidence changes are not",
        "counted as improvements.",
        "",
        "## Packet-Level Improvements",
        "",
    ]

    if payload["packet_level_improvements"]:
        for row in payload["packet_level_improvements"]:
            lines.append(
                "- "
                + f"`{row['accession']}` "
                + f"latest_missing=`{','.join(row['latest_missing_modalities']) or 'none'}` "
                + f"freshest_missing=`{','.join(row['freshest_missing_modalities']) or 'none'}` "
                + f"delta=`{row['delta_gap_count']}` "
                + f"refs=`{','.join(row['latest_deficit_source_refs']) or 'none'}`"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Lower-Layer Evidence Improvements", ""])
    if payload["lower_layer_evidence_improvements"]:
        for row in payload["lower_layer_evidence_improvements"]:
            lines.append(
                "- "
                + f"`{row['accession']}` "
                + f"latest_artifacts=`{row['latest_artifact_count']}` "
                + f"freshest_artifacts=`{row['freshest_artifact_count']}` "
                + f"latest_notes=`{row['latest_note_count']}` "
                + f"freshest_notes=`{row['freshest_note_count']}` "
                + f"truth=`{row['evidence_level_truth']}`"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Packet-Level Regressions", ""])
    if payload["packet_level_regressions"]:
        for row in payload["packet_level_regressions"]:
            lines.append(
                "- "
                + f"`{row['accession']}` "
                + f"latest_missing=`{','.join(row['latest_missing_modalities']) or 'none'}` "
                + f"freshest_missing=`{','.join(row['freshest_missing_modalities']) or 'none'}` "
                + f"delta=`{row['delta_gap_count']}` "
                + f"refs=`{','.join(row['latest_deficit_source_refs']) or 'none'}`"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Lower-Layer Evidence Regressions", ""])
    if payload["lower_layer_evidence_regressions"]:
        for row in payload["lower_layer_evidence_regressions"]:
            lines.append(
                "- "
                + f"`{row['accession']}` "
                + f"latest_artifacts=`{row['latest_artifact_count']}` "
                + f"freshest_artifacts=`{row['freshest_artifact_count']}` "
                + f"latest_notes=`{row['latest_note_count']}` "
                + f"freshest_notes=`{row['freshest_note_count']}` "
                + f"truth=`{row['evidence_level_truth']}`"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Unchanged Remaining Gaps", ""])
    if payload["unchanged_remaining_gaps"]:
        for row in payload["unchanged_remaining_gaps"]:
            lines.append(
                "- "
                + f"`{row['accession']}` "
                + f"latest_missing=`{','.join(row['latest_missing_modalities']) or 'none'}` "
                + f"freshest_missing=`{','.join(row['freshest_missing_modalities']) or 'none'}` "
                + f"delta=`{row['delta_gap_count']}` "
                + f"refs=`{','.join(row['latest_deficit_source_refs']) or 'none'}`"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Lower-Layer Evidence Mixed", ""])
    if payload["lower_layer_evidence_mixed"]:
        for row in payload["lower_layer_evidence_mixed"]:
            lines.append(
                "- "
                + f"`{row['accession']}` "
                + f"latest_artifacts=`{row['latest_artifact_count']}` "
                + f"freshest_artifacts=`{row['freshest_artifact_count']}` "
                + f"latest_notes=`{row['latest_note_count']}` "
                + f"freshest_notes=`{row['freshest_note_count']}` "
                + f"truth=`{row['evidence_level_truth']}`"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Remaining Freshest Gaps", ""])
    if payload["remaining_gaps"]:
        lines.append(
            "| Accession | Packet delta | Evidence delta | Latest missing | Freshest missing | Latest refs |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in payload["remaining_gaps"]:
            lines.append(
                "| "
                + f"`{row['accession']}` | "
                + f"`{row['packet_level_truth']}` | "
                + f"`{row['evidence_level_truth']}` | "
                + f"`{','.join(row['latest_missing_modalities']) or 'none'}` | "
                + f"`{','.join(row['freshest_missing_modalities']) or 'none'}` | "
                + f"`{','.join(row['latest_deficit_source_refs']) or 'none'}` |"
            )
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a current-vs-latest packet delta report."
    )
    parser.add_argument("--comparison", type=Path, default=DEFAULT_COMPARISON_PATH)
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_packet_state_delta_report(
        comparison_path=args.comparison,
        packet_deficit_path=args.packet_deficit,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))
    print(
        "Packet delta report exported: "
        f"improved={payload['summary']['packet_level_improved_count']} "
        f"regressed={payload['summary']['packet_level_regressed_count']} "
        f"remaining={payload['summary']['remaining_gap_packet_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
