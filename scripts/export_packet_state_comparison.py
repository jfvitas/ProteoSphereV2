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

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LATEST_PATH = REPO_ROOT / "data" / "packages" / "LATEST.json"
DEFAULT_FRESHEST_PATH = REPO_ROOT / "data" / "packages" / "training-packets-20260331T193611Z"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "packet_state_comparison.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "packet_state_comparison.md"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return dict(payload)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _packet_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packets = payload.get("packets") or ()
    if not isinstance(packets, list):
        materialization = payload.get("materialization")
        if isinstance(materialization, dict):
            packets = materialization.get("packets") or ()
    if not isinstance(packets, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        accession = _clean_text(packet.get("accession")).upper()
        if accession:
            indexed[accession] = dict(packet)
    return indexed


def _packet_index_from_directory(path: Path) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for manifest_path in sorted(path.rglob("packet_manifest.json")):
        payload = _read_json(manifest_path)
        accession = _clean_text(payload.get("accession")).upper()
        if accession:
            payload["manifest_path"] = (
                _clean_text(payload.get("manifest_path")) or str(manifest_path)
            )
            indexed[accession] = payload
    return indexed


def _status_counts(indexed: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = Counter(_clean_text(packet.get("status")) or "unknown" for packet in indexed.values())
    return {key: counts[key] for key in sorted(counts)}


def _packet_row(
    accession: str,
    *,
    latest_packet: dict[str, Any] | None,
    freshest_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    latest_status = _clean_text((latest_packet or {}).get("status")) or "missing"
    freshest_status = _clean_text((freshest_packet or {}).get("status")) or "missing"
    latest_missing = sorted(
        _clean_text(value)
        for value in ((latest_packet or {}).get("missing_modalities") or ())
        if _clean_text(value)
    )
    freshest_missing = sorted(
        _clean_text(value)
        for value in ((freshest_packet or {}).get("missing_modalities") or ())
        if _clean_text(value)
    )
    changed = (
        latest_status != freshest_status
        or latest_missing != freshest_missing
    )
    improvement = len(freshest_missing) < len(latest_missing)
    regression = len(freshest_missing) > len(latest_missing)
    return {
        "accession": accession,
        "latest_status": latest_status,
        "freshest_status": freshest_status,
        "latest_missing_modalities": latest_missing,
        "freshest_missing_modalities": freshest_missing,
        "changed": changed,
        "improvement": improvement,
        "regression": regression,
        "latest_manifest_path": _clean_text((latest_packet or {}).get("manifest_path")),
        "freshest_manifest_path": _clean_text((freshest_packet or {}).get("manifest_path")),
    }


def build_packet_state_comparison(
    *,
    latest_path: Path = DEFAULT_LATEST_PATH,
    freshest_path: Path = DEFAULT_FRESHEST_PATH,
) -> dict[str, Any]:
    latest_payload = _read_json(latest_path)
    freshest_payload = _read_json(freshest_path) if freshest_path.is_file() else {}
    latest_index = _packet_index(latest_payload)
    freshest_index = (
        _packet_index(freshest_payload)
        if freshest_path.is_file()
        else _packet_index_from_directory(freshest_path)
    )
    accessions = sorted(set(latest_index) | set(freshest_index))
    rows = [
        _packet_row(
            accession,
            latest_packet=latest_index.get(accession),
            freshest_packet=freshest_index.get(accession),
        )
        for accession in accessions
    ]
    improved = [row for row in rows if row["improvement"]]
    regressed = [row for row in rows if row["regression"]]
    changed = [row for row in rows if row["changed"]]
    comparison_boundary = {
        "latest_label": "preserved packet baseline",
        "freshest_label": "freshest run-scoped packet state",
        "latest_path": str(latest_path),
        "freshest_path": str(freshest_path),
    }
    freshest_complete_count = sum(
        1
        for packet in freshest_index.values()
        if _clean_text(packet.get("status")) == "complete"
    )
    freshest_partial_count = sum(
        1
        for packet in freshest_index.values()
        if _clean_text(packet.get("status")) == "partial"
    )
    freshest_unresolved_count = sum(
        1
        for packet in freshest_index.values()
        if _clean_text(packet.get("status")) == "unresolved"
    )
    return {
        "schema_id": "proteosphere-packet-state-comparison-2026-03-31",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "latest_path": str(latest_path),
        "freshest_path": str(freshest_path),
        "comparison_boundary": comparison_boundary,
        "latest_summary": {
            "packet_count": len(latest_index),
            "status_counts": _status_counts(latest_index),
            "complete_count": int(latest_payload.get("complete_count") or 0),
            "partial_count": int(latest_payload.get("partial_count") or 0),
            "unresolved_count": int(latest_payload.get("unresolved_count") or 0),
            "latest_promotion_state": _clean_text(latest_payload.get("latest_promotion_state")),
        },
        "freshest_summary": {
            "packet_count": len(freshest_index),
            "status_counts": _status_counts(freshest_index),
            "complete_count": int(
                freshest_payload.get("complete_count")
                or (freshest_payload.get("materialization") or {}).get("complete_count")
                or freshest_complete_count
                or 0
            ),
            "partial_count": int(
                freshest_payload.get("partial_count")
                or (freshest_payload.get("materialization") or {}).get("partial_count")
                or freshest_partial_count
                or 0
            ),
            "unresolved_count": int(
                freshest_payload.get("unresolved_count")
                or (freshest_payload.get("materialization") or {}).get("unresolved_count")
                or freshest_unresolved_count
                or 0
            ),
            "latest_promotion_state": _clean_text(
                freshest_payload.get("latest_promotion_state")
                or (freshest_payload.get("materialization") or {}).get("latest_promotion_state")
            ),
        },
        "summary": {
            "packet_count": len(rows),
            "changed_packet_count": len(changed),
            "improved_packet_count": len(improved),
            "regressed_packet_count": len(regressed),
            "improved_accessions": [row["accession"] for row in improved],
            "regressed_accessions": [row["accession"] for row in regressed],
        },
        "packets": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    boundary = payload["comparison_boundary"]
    lines = [
        "# Packet State Comparison",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        (
            "- Comparison boundary: "
            f"{boundary['latest_label']} (`{boundary['latest_path']}`) vs "
            f"{boundary['freshest_label']} (`{boundary['freshest_path']}`)"
        ),
        f"- Latest summary: `{payload['latest_summary']['status_counts']}`",
        f"- Freshest summary: `{payload['freshest_summary']['status_counts']}`",
        f"- Changed packets: `{payload['summary']['changed_packet_count']}`",
        f"- Improved packets: `{payload['summary']['improved_packet_count']}`",
        f"- Regressed packets: `{payload['summary']['regressed_packet_count']}`",
        "",
        "## Packet Rows",
        "",
    ]
    for row in payload["packets"]:
        change_bits: list[str] = []
        if row["improvement"]:
            change_bits.append("improved")
        if row["regression"]:
            change_bits.append("regressed")
        if row["changed"] and not change_bits:
            change_bits.append("changed")
        if not change_bits:
            change_bits.append("unchanged")
        lines.append(
            "- "
            + f"`{row['accession']}` "
            + f"latest=`{row['latest_status']}` "
            + f"freshest=`{row['freshest_status']}` "
            + f"latest_missing=`{','.join(row['latest_missing_modalities']) or 'none'}` "
            + f"freshest_missing=`{','.join(row['freshest_missing_modalities']) or 'none'}` "
            + f"change=`{','.join(change_bits)}`"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export latest-vs-freshest packet state comparison."
    )
    parser.add_argument("--latest", type=Path, default=DEFAULT_LATEST_PATH)
    parser.add_argument("--freshest", type=Path, default=DEFAULT_FRESHEST_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_packet_state_comparison(
        latest_path=args.latest,
        freshest_path=args.freshest,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))
    print(
        "Packet state comparison exported: "
        f"changed={payload['summary']['changed_packet_count']} "
        f"improved={payload['summary']['improved_packet_count']} "
        f"regressed={payload['summary']['regressed_packet_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
