from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGES_ROOT = REPO_ROOT / "data" / "packages"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "packet_deficit_dashboard.md"
DEFAULT_MODALITY_ORDER = ("sequence", "structure", "ligand", "ppi")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Path)):
        return (values,)
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    if isinstance(values, dict):
        return tuple(values.values())
    try:
        return tuple(values)
    except TypeError:
        return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _packet_manifest_paths(packages_root: Path) -> tuple[Path, ...]:
    if not packages_root.exists():
        return ()
    return tuple(
        sorted(
            path
            for path in packages_root.rglob("packet_manifest.json")
            if path.is_file()
        )
    )


def _latest_summary_path(packages_root: Path) -> Path:
    return packages_root / "LATEST.json"


def _coerce_path(value: Any) -> Path | None:
    text = _clean_text(value)
    if not text:
        return None
    return Path(text)


def _merge_latest_packet_with_manifest(
    packet: dict[str, Any],
) -> dict[str, Any]:
    manifest_path = _coerce_path(packet.get("manifest_path"))
    if manifest_path is None or not manifest_path.is_file():
        return dict(packet)

    payload = _read_json(manifest_path)
    if not isinstance(payload, dict):
        return dict(packet)

    merged = dict(payload)
    merged.update(packet)
    merged["_source_path"] = str(manifest_path)

    # Recover richer manifest-only detail when the latest summary omits it.
    packet_modality_sources = packet.get("modality_sources")
    if (
        (
            "modality_sources" not in packet
            or not isinstance(packet_modality_sources, dict)
            or not packet_modality_sources
        )
        and isinstance(payload.get("modality_sources"), dict)
        and payload.get("modality_sources")
    ):
        merged["modality_sources"] = payload["modality_sources"]
    if "raw_manifest_ids" not in packet and payload.get("raw_manifest_ids") is not None:
        merged["raw_manifest_ids"] = payload.get("raw_manifest_ids")
    if "provenance_refs" not in packet and payload.get("provenance_refs") is not None:
        merged["provenance_refs"] = payload.get("provenance_refs")
    if "notes" not in packet and payload.get("notes") is not None:
        merged["notes"] = payload.get("notes")
    if "artifacts" not in packet and payload.get("artifacts") is not None:
        merged["artifacts"] = payload.get("artifacts")
    return merged


def _status_from_packet(payload: dict[str, Any]) -> str:
    status = _clean_text(payload.get("status"))
    if status in {"complete", "partial", "unresolved"}:
        return status
    requested = _dedupe_text(payload.get("requested_modalities") or ())
    present = _dedupe_text(payload.get("present_modalities") or ())
    missing = _dedupe_text(payload.get("missing_modalities") or ())
    if requested and present and not missing and len(present) == len(requested):
        return "complete"
    if present:
        return "partial"
    return "unresolved"


def _modality_sources(payload: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    raw_sources = payload.get("modality_sources") or {}
    if not isinstance(raw_sources, dict):
        return {}
    return {
        _clean_text(modality): _dedupe_text(refs)
        for modality, refs in raw_sources.items()
        if _clean_text(modality)
    }


def _packet_row(payload: dict[str, Any], *, source_path: Path | None = None) -> dict[str, Any]:
    requested_modalities = _dedupe_text(payload.get("requested_modalities") or ())
    present_modalities = _dedupe_text(payload.get("present_modalities") or ())
    missing_modalities = _dedupe_text(payload.get("missing_modalities") or ())
    present_lookup = {modality.casefold() for modality in present_modalities}
    if not missing_modalities and requested_modalities:
        missing_modalities = tuple(
            modality
            for modality in requested_modalities
            if modality.casefold() not in present_lookup
        )
    if not present_modalities and requested_modalities and not missing_modalities:
        present_modalities = requested_modalities
    modality_sources = _modality_sources(payload)
    missing_source_refs: dict[str, list[str]] = {}
    for modality in missing_modalities:
        refs = list(modality_sources.get(modality, ()))
        missing_source_refs[modality] = refs

    deficit_source_refs = tuple(
        _dedupe_text(
            ref
            for refs in missing_source_refs.values()
            for ref in refs
        )
    )
    artifact_count = len(_iter_values(payload.get("artifacts") or ()))
    requested_count = len(requested_modalities)
    present_count = len(present_modalities)
    missing_count = len(missing_modalities)
    coverage_ratio = (present_count / requested_count) if requested_count else 0.0
    deficit_ratio = (missing_count / requested_count) if requested_count else 0.0

    row = {
        "packet_id": _clean_text(payload.get("packet_id") or payload.get("id")),
        "accession": _clean_text(payload.get("accession")),
        "canonical_id": _clean_text(payload.get("canonical_id")),
        "status": _status_from_packet(payload),
        "packet_dir": _clean_text(payload.get("packet_dir")),
        "manifest_path": _clean_text(payload.get("manifest_path"))
        or (str(source_path) if source_path is not None else ""),
        "requested_modalities": list(requested_modalities),
        "present_modalities": list(present_modalities),
        "missing_modalities": list(missing_modalities),
        "requested_modality_count": requested_count,
        "present_modality_count": present_count,
        "missing_modality_count": missing_count,
        "artifact_count": artifact_count,
        "coverage_ratio": round(coverage_ratio, 6),
        "deficit_ratio": round(deficit_ratio, 6),
        "modality_sources": {
            modality: list(refs) for modality, refs in modality_sources.items()
        },
        "missing_source_refs": missing_source_refs,
        "deficit_source_refs": list(deficit_source_refs),
        "raw_manifest_ids": list(_dedupe_text(payload.get("raw_manifest_ids") or ())),
        "provenance_refs": list(_dedupe_text(payload.get("provenance_refs") or ())),
        "notes": list(_dedupe_text(payload.get("notes") or ())),
    }
    return row


def _load_packet_payloads(
    packages_root: Path,
    *,
    latest_only: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_paths = _packet_manifest_paths(packages_root)
    latest_path = _latest_summary_path(packages_root)
    latest_summary: dict[str, Any] = {}
    if latest_path.exists():
        payload = _read_json(latest_path)
        if isinstance(payload, dict):
            latest_summary = dict(payload)

    packet_payloads: list[dict[str, Any]] = []
    if latest_only and latest_summary:
        for packet in _iter_values(latest_summary.get("packets") or ()):
            if isinstance(packet, dict):
                packet_payloads.append(_merge_latest_packet_with_manifest(dict(packet)))
    elif manifest_paths:
        for path in manifest_paths:
            payload = _read_json(path)
            if isinstance(payload, dict):
                packet_payloads.append({**payload, "_source_path": str(path)})
    else:
        for packet in _iter_values(latest_summary.get("packets") or ()):
            if isinstance(packet, dict):
                packet_payloads.append(dict(packet))

    return packet_payloads, {
        "latest_summary_path": str(latest_path) if latest_path.exists() else "",
        "manifest_count": len(manifest_paths),
        "packet_source_count": len(packet_payloads),
        "latest_only": latest_only,
        "latest_summary": latest_summary,
    }


def _aggregate_source_fixes(packet_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_index: dict[str, dict[str, Any]] = {}
    for row in packet_rows:
        packet_id = row["packet_id"]
        accession = row["accession"]
        for modality, refs in row["missing_source_refs"].items():
            modality_refs = refs or [f"unmapped:{modality}"]
            for ref in modality_refs:
                source_ref = _clean_text(ref) or f"unmapped:{modality}"
                candidate = candidate_index.setdefault(
                    source_ref,
                    {
                        "source_ref": source_ref,
                        "missing_modality_count": 0,
                        "affected_packet_count": 0,
                        "missing_modalities": [],
                        "modality_counts": Counter(),
                        "packet_ids": [],
                        "packet_accessions": [],
                    },
                )
                candidate["missing_modality_count"] += 1
                candidate["modality_counts"][modality] += 1
                if modality not in candidate["missing_modalities"]:
                    candidate["missing_modalities"].append(modality)
                if packet_id not in candidate["packet_ids"]:
                    candidate["packet_ids"].append(packet_id)
                    candidate["affected_packet_count"] += 1
                if accession and accession not in candidate["packet_accessions"]:
                    candidate["packet_accessions"].append(accession)

    return [
        {
            "source_ref": item["source_ref"],
            "missing_modality_count": item["missing_modality_count"],
            "affected_packet_count": item["affected_packet_count"],
            "missing_modalities": sorted(item["missing_modalities"]),
            "modality_counts": dict(sorted(item["modality_counts"].items())),
            "packet_ids": sorted(item["packet_ids"]),
            "packet_accessions": sorted(item["packet_accessions"]),
        }
        for item in sorted(
            candidate_index.values(),
            key=lambda item: (
                -int(item["missing_modality_count"]),
                -int(item["affected_packet_count"]),
                item["source_ref"].casefold(),
            ),
        )
    ]


def _aggregate_modality_deficits(
    packet_rows: list[dict[str, Any]],
    source_fix_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    requested_modalities: list[str] = []
    seen_requested: set[str] = set()
    for row in packet_rows:
        for modality in row["requested_modalities"]:
            key = modality.casefold()
            if key in seen_requested:
                continue
            seen_requested.add(key)
            requested_modalities.append(modality)
    ordered_modalities = [
        modality
        for modality in DEFAULT_MODALITY_ORDER
        if modality.casefold() in seen_requested
    ]
    ordered_modalities.extend(
        modality for modality in requested_modalities if modality.casefold() not in {
            item.casefold() for item in ordered_modalities
        }
    )

    candidate_lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in source_fix_candidates:
        for modality in candidate["missing_modalities"]:
            candidate_lookup[modality.casefold()].append(candidate)

    modality_rows: list[dict[str, Any]] = []
    for modality in ordered_modalities:
        packet_ids = [
            row["packet_id"]
            for row in packet_rows
            if modality.casefold() in {item.casefold() for item in row["missing_modalities"]}
        ]
        packet_accessions = [
            row["accession"]
            for row in packet_rows
            if modality.casefold() in {item.casefold() for item in row["missing_modalities"]}
        ]
        top_fix_candidates = sorted(
            candidate_lookup.get(modality.casefold(), ()),
            key=lambda item: (
                -int(item["missing_modality_count"]),
                -int(item["affected_packet_count"]),
                item["source_ref"].casefold(),
            ),
        )[:5]
        modality_rows.append(
            {
                "modality": modality,
                "requested_packet_count": sum(
                    1
                    for row in packet_rows
                    if modality.casefold()
                    in {item.casefold() for item in row["requested_modalities"]}
                ),
                "present_packet_count": sum(
                    1
                    for row in packet_rows
                    if modality.casefold()
                    in {item.casefold() for item in row["present_modalities"]}
                ),
                "missing_packet_count": len(packet_ids),
                "packet_ids": sorted(packet_ids),
                "packet_accessions": sorted(packet_accessions),
                "top_source_fix_refs": [
                    candidate["source_ref"] for candidate in top_fix_candidates
                ],
                "top_source_fix_candidates": top_fix_candidates,
            }
        )

    return modality_rows


def build_packet_deficit_dashboard(
    *,
    packages_root: Path = DEFAULT_PACKAGES_ROOT,
    latest_only: bool = False,
) -> dict[str, Any]:
    packet_payloads, discovery = _load_packet_payloads(
        packages_root,
        latest_only=latest_only,
    )
    packet_rows = [
        _packet_row(
            packet,
            source_path=(
                Path(packet.get("_source_path")) if packet.get("_source_path") else None
            ),
        )
        for packet in packet_payloads
    ]
    source_fix_candidates = _aggregate_source_fixes(packet_rows)
    modality_deficits = _aggregate_modality_deficits(packet_rows, source_fix_candidates)
    packet_status_counts = Counter(row["status"] for row in packet_rows)
    packet_deficit_count = sum(1 for row in packet_rows if row["missing_modality_count"] > 0)
    total_missing_modality_count = sum(row["missing_modality_count"] for row in packet_rows)

    return {
        "schema_id": "proteosphere-packet-deficit-dashboard-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "complete",
        "inputs": {
            "packages_root": str(packages_root).replace("\\", "/"),
            "latest_summary_path": discovery["latest_summary_path"],
            "manifest_count": discovery["manifest_count"],
            "packet_source_count": discovery["packet_source_count"],
            "latest_only": discovery["latest_only"],
        },
        "summary": {
            "packet_count": len(packet_rows),
            "packet_status_counts": dict(sorted(packet_status_counts.items())),
            "complete_packet_count": int(packet_status_counts.get("complete", 0)),
            "partial_packet_count": int(packet_status_counts.get("partial", 0)),
            "unresolved_packet_count": int(packet_status_counts.get("unresolved", 0)),
            "packet_deficit_count": packet_deficit_count,
            "total_missing_modality_count": total_missing_modality_count,
            "modality_deficit_counts": {
                row["modality"]: row["missing_packet_count"] for row in modality_deficits
            },
            "highest_leverage_source_fixes": source_fix_candidates[:10],
            "source_fix_candidate_count": len(source_fix_candidates),
        },
        "modality_deficits": modality_deficits,
        "source_fix_candidates": source_fix_candidates,
        "packets": sorted(
            packet_rows,
            key=lambda row: (
                -int(row["missing_modality_count"]),
                row["packet_id"].casefold(),
                row["accession"].casefold(),
            ),
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Packet Deficit Dashboard",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Packet count: `{summary['packet_count']}`",
        f"- Packet status counts: `{summary['packet_status_counts']}`",
        f"- Packet deficit count: `{summary['packet_deficit_count']}`",
        f"- Total missing modality count: `{summary['total_missing_modality_count']}`",
        "",
        "## Modality Deficits",
        "",
    ]
    for row in payload["modality_deficits"]:
        lines.append(
            "- "
            + f"`{row['modality']}` "
            + f"missing_packets=`{row['missing_packet_count']}` "
            + f"requested_packets=`{row['requested_packet_count']}` "
            + f"present_packets=`{row['present_packet_count']}`"
        )
    lines.extend(["", "## Highest-Leverage Source Fixes", ""])
    top_fix_refs = summary["highest_leverage_source_fixes"]
    if top_fix_refs:
        for row in top_fix_refs:
            lines.append(
                "- "
                + f"`{row['source_ref']}` "
                + f"missing_modalities=`{row['missing_modality_count']}` "
                + f"affected_packets=`{row['affected_packet_count']}` "
                + f"modalities=`{','.join(row['missing_modalities']) or 'none'}`"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Packet Rows", ""])
    for row in payload["packets"]:
        lines.append(
            "- "
            + f"`{row['packet_id'] or row['accession']}` "
            + f"status=`{row['status']}` "
            + f"coverage=`{row['coverage_ratio']}` "
            + f"deficit=`{row['deficit_ratio']}` "
            + f"missing=`{','.join(row['missing_modalities']) or 'none'}`"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the packet deficit dashboard.")
    parser.add_argument("--packages-root", type=Path, default=DEFAULT_PACKAGES_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    parser.add_argument("--latest-only", action="store_true")
    args = parser.parse_args(argv)

    payload = build_packet_deficit_dashboard(
        packages_root=args.packages_root,
        latest_only=args.latest_only,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Packet deficit dashboard exported: "
            f"packets={payload['summary']['packet_count']} "
            f"deficits={payload['summary']['packet_deficit_count']} "
            f"source_fixes={payload['summary']['source_fix_candidate_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
