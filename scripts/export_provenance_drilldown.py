from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
DEFAULT_OUTPUT = DEFAULT_RESULTS_DIR / "provenance_drilldown.json"
DEFAULT_PROVENANCE_TABLE = DEFAULT_RESULTS_DIR / "provenance_table.json"
DEFAULT_SOURCE_COVERAGE = DEFAULT_RESULTS_DIR / "source_coverage.json"
DEFAULT_PACKET_AUDIT = DEFAULT_RESULTS_DIR / "training_packet_audit.json"
DEFAULT_CURATED_PPI = DEFAULT_RESULTS_DIR / "curated_ppi_candidate_slice.json"

EXPORTER_ID = "provenance-drilldown:v1"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _norm_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _index_rows(rows: list[dict[str, Any]], *, key: str = "accession") -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if isinstance(value, str) and value not in indexed:
            indexed[value] = row
    return indexed


def _ordered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _sort_key(row: dict[str, Any]) -> tuple[int, str]:
        row_index = row.get("row_index")
        if isinstance(row_index, int):
            return (row_index, str(row.get("accession", "")))
        return (10**9, str(row.get("accession", "")))

    return sorted(rows, key=_sort_key)


def _lane_entry(
    *,
    lane_id: str,
    lane_kind: str,
    parent_kind: str,
    parent_id: str,
    accession: str,
    reason: str,
    state: str = "unresolved",
    evidence_refs: list[str] | None = None,
    provenance_pointers: list[str] | None = None,
    source_name: str | None = None,
    modality: str | None = None,
) -> dict[str, Any]:
    lane: dict[str, Any] = {
        "lane_id": lane_id,
        "lane_kind": lane_kind,
        "parent_kind": parent_kind,
        "parent_id": parent_id,
        "accession": accession,
        "state": state,
        "reason": reason,
    }
    if evidence_refs:
        lane["evidence_refs"] = sorted(dict.fromkeys(evidence_refs))
    if provenance_pointers:
        lane["provenance_pointers"] = sorted(dict.fromkeys(provenance_pointers))
    if source_name is not None:
        lane["source_name"] = source_name
    if modality is not None:
        lane["modality"] = modality
    return lane


def _build_entity_trace(
    *,
    provenance_row: dict[str, Any],
    coverage_row: dict[str, Any] | None,
    packet_row: dict[str, Any] | None,
) -> dict[str, Any]:
    accession = str(provenance_row["accession"])
    canonical_id = str(provenance_row.get("canonical_id", f"protein:{accession}"))
    evidence_refs = list(provenance_row.get("evidence_refs", []))
    source_lanes = list(provenance_row.get("source_lanes", []))
    missing_modalities = list(
        (packet_row or coverage_row or {}).get("missing_modalities", [])
    )
    present_modalities = list(
        (packet_row or coverage_row or {}).get("present_modalities", [])
    )
    coverage_notes = list((packet_row or {}).get("coverage_notes", []))
    coverage_notes = sorted(
        dict.fromkeys(
            [
                *coverage_notes,
                *list((coverage_row or {}).get("coverage_notes", [])),
            ]
        )
    )
    unresolved_lanes = [
        _lane_entry(
            lane_id=f"entity:{accession}:{modality}",
            lane_kind="entity_modality",
            parent_kind="entity",
            parent_id=canonical_id,
            accession=accession,
            modality=modality,
            reason="missing modality in source coverage",
            evidence_refs=evidence_refs,
            provenance_pointers=[
                f"planning/{accession}",
                f"source_lanes={','.join(source_lanes)}" if source_lanes else "source_lanes=",
            ],
        )
        for modality in missing_modalities
    ]
    checkpoint_coverage = provenance_row.get("checkpoint_coverage", {})
    trace = {
        "trace_kind": "entity",
        "trace_state": provenance_row.get("status", "resolved"),
        "accession": accession,
        "canonical_id": canonical_id,
        "split": provenance_row.get("split"),
        "bucket": provenance_row.get("bucket"),
        "row_index": provenance_row.get("row_index"),
        "leakage_key": provenance_row.get("leakage_key"),
        "planning_index_ref": provenance_row.get("planning_index_ref"),
        "evidence_mode": provenance_row.get("evidence_mode"),
        "evidence_refs": evidence_refs,
        "source_lanes": source_lanes,
        "checkpoint_coverage": checkpoint_coverage,
        "provenance_notes": provenance_row.get("provenance_notes", ""),
        "coverage_snapshot": {
            "lane_depth": (coverage_row or {}).get("lane_depth"),
            "conservative_evidence_tier": (coverage_row or {}).get(
                "conservative_evidence_tier"
            ),
            "mixed_evidence": (coverage_row or {}).get("mixed_evidence"),
            "thin_coverage": (coverage_row or {}).get("thin_coverage"),
            "validation_class": (coverage_row or {}).get("validation_class"),
            "present_modalities": present_modalities,
            "missing_modalities": missing_modalities,
            "coverage_notes": coverage_notes,
        },
        "unresolved_lanes": unresolved_lanes,
    }
    return trace


def _normalize_pair_record(record: dict[str, Any]) -> dict[str, Any]:
    pair_key = str(record.get("pair_key", ""))
    accession_pair = list(record.get("accession_pair", []))
    evidence_refs = list(record.get("evidence_refs", []))
    provenance_pointers = list(record.get("provenance_pointers", []))
    normalized = {
        "pair_key": pair_key,
        "accession_pair": accession_pair,
        "source_record_ids": list(record.get("source_record_ids", [])),
        "evidence_refs": sorted(dict.fromkeys(evidence_refs)),
        "provenance_pointers": sorted(dict.fromkeys(provenance_pointers)),
    }
    return normalized


def _build_pair_trace_from_direct_evidence(entry: dict[str, Any]) -> dict[str, Any]:
    accession = str(entry["accession"])
    source_name = str(entry.get("source_name", ""))
    canonical_pair_lineage_complete = bool(entry.get("canonical_pair_lineage_complete", False))
    pair_records = sorted(
        (_normalize_pair_record(record) for record in entry.get("pair_records", [])),
        key=lambda item: item["pair_key"],
    )
    empty_state = entry.get("empty_state")
    unresolved_lanes: list[dict[str, Any]] = []
    if empty_state == "reachable_empty":
        unresolved_lanes.append(
            _lane_entry(
                lane_id=f"pair:{source_name}:{accession}",
                lane_kind="pair_empty_hit",
                parent_kind="pair",
                parent_id=f"protein:{accession}",
                accession=accession,
                source_name=source_name,
                state="unresolved",
                reason="source probe returned a reachable empty hit",
                evidence_refs=list(entry.get("provenance_pointers", [])),
                provenance_pointers=list(entry.get("provenance_pointers", [])),
            )
        )
    elif not canonical_pair_lineage_complete:
        unresolved_lanes.append(
            _lane_entry(
                lane_id=f"pair:{source_name}:{accession}:lineage",
                lane_kind="pair_lineage",
                parent_kind="pair",
                parent_id=f"protein:{accession}",
                accession=accession,
                source_name=source_name,
                state="unresolved",
                reason="canonical pair lineage is incomplete",
                evidence_refs=list(entry.get("provenance_pointers", [])),
                provenance_pointers=list(entry.get("provenance_pointers", [])),
            )
        )

    status = "resolved"
    if empty_state == "reachable_empty":
        status = "unresolved"
    elif not canonical_pair_lineage_complete:
        status = "partial"

    return {
        "trace_kind": "pair",
        "trace_state": status,
        "accession": accession,
        "canonical_id": str(entry.get("canonical_id", f"protein:{accession}")),
        "split": entry.get("split"),
        "bucket": entry.get("bucket"),
        "evidence_mode": entry.get("evidence_mode"),
        "validation_class": entry.get("validation_class"),
        "evidence_kind": entry.get("evidence_kind"),
        "source_name": source_name,
        "pair_count": entry.get("pair_count", 0),
        "pair_records": pair_records,
        "canonical_pair_lineage_complete": canonical_pair_lineage_complete,
        "probe_reason": entry.get("probe_reason"),
        "empty_state": empty_state,
        "provenance_pointers": sorted(dict.fromkeys(entry.get("provenance_pointers", []))),
        "unresolved_lanes": unresolved_lanes,
    }


def _build_pair_trace_from_empty_hit(entry: dict[str, Any]) -> dict[str, Any]:
    accession = str(entry["accession"])
    source_name = str(entry.get("source_name", ""))
    probe_url = str(entry.get("probe_url", ""))
    record_count = int(entry.get("returned_record_count", 0))
    lane = _lane_entry(
        lane_id=f"pair:{source_name}:{accession}:empty",
        lane_kind="pair_empty_hit",
        parent_kind="pair",
        parent_id=f"protein:{accession}",
        accession=accession,
        source_name=source_name,
        state="unresolved",
        reason="probe returned no records",
        evidence_refs=[probe_url] if probe_url else [],
        provenance_pointers=[probe_url] if probe_url else [],
    )
    return {
        "trace_kind": "pair",
        "trace_state": "unresolved",
        "accession": accession,
        "canonical_id": f"protein:{accession}",
        "split": entry.get("split"),
        "bucket": entry.get("bucket"),
        "evidence_mode": "reachable_empty",
        "validation_class": "reachable_empty",
        "evidence_kind": "empty_hit",
        "source_name": source_name,
        "pair_count": 0,
        "pair_records": [],
        "canonical_pair_lineage_complete": False,
        "probe_reason": "reachable empty hit",
        "empty_state": entry.get("empty_state", "reachable_empty"),
        "probe_url": probe_url,
        "matched_record_count": entry.get("matched_record_count", 0),
        "returned_record_count": record_count,
        "provenance_pointers": [probe_url] if probe_url else [],
        "unresolved_lanes": [lane],
    }


def _build_pair_trace_from_blocked_row(row: dict[str, Any]) -> dict[str, Any]:
    accession = str(row.get("accession", ""))
    source_name = str(row.get("source_name", ""))
    reason = str(row.get("reason", row.get("notes", "blocked provenance lane")))
    pointers = list(row.get("provenance_pointers", []))
    lane = _lane_entry(
        lane_id=f"pair:{source_name}:{accession}:blocked",
        lane_kind="pair_blocked",
        parent_kind="pair",
        parent_id=f"protein:{accession}",
        accession=accession,
        source_name=source_name,
        state="blocked",
        reason=reason,
        evidence_refs=list(row.get("evidence_refs", [])),
        provenance_pointers=pointers,
    )
    return {
        "trace_kind": "pair",
        "trace_state": "blocked",
        "accession": accession,
        "canonical_id": str(row.get("canonical_id", f"protein:{accession}")),
        "split": row.get("split"),
        "bucket": row.get("bucket"),
        "evidence_mode": row.get("evidence_mode", "blocked"),
        "validation_class": row.get("validation_class", "blocked"),
        "evidence_kind": "blocked_row",
        "source_name": source_name,
        "pair_count": int(row.get("pair_count", 0)),
        "pair_records": [],
        "canonical_pair_lineage_complete": False,
        "probe_reason": reason,
        "empty_state": row.get("empty_state"),
        "provenance_pointers": pointers,
        "unresolved_lanes": [lane],
    }


def _build_packet_trace(
    packet: dict[str, Any],
    *,
    coverage_row: dict[str, Any] | None,
) -> dict[str, Any]:
    accession = str(packet["accession"])
    missing_modalities = list(packet.get("missing_modalities", []))
    evidence_refs = list(packet.get("evidence_refs", []))
    provenance_pointers = list(packet.get("provenance_pointers", []))
    unresolved_lanes = [
        _lane_entry(
            lane_id=f"packet:{accession}:{modality}",
            lane_kind="packet_modality",
            parent_kind="packet",
            parent_id=f"packet:{accession}",
            accession=accession,
            modality=modality,
            reason="missing modality in packet audit",
            evidence_refs=evidence_refs,
            provenance_pointers=provenance_pointers,
        )
        for modality in missing_modalities
    ]
    coverage_notes = list(packet.get("coverage_notes", []))
    if coverage_row and coverage_row.get("coverage_notes"):
        coverage_notes = sorted(dict.fromkeys([*coverage_notes, *coverage_row["coverage_notes"]]))
    return {
        "trace_kind": "packet",
        "trace_state": "complete" if packet.get("completeness") == "complete" else "partial",
        "accession": accession,
        "canonical_id": str(packet.get("canonical_id", f"protein:{accession}")),
        "split": packet.get("split"),
        "bucket": packet.get("bucket"),
        "judgment": packet.get("judgment"),
        "validation_class": packet.get("validation_class"),
        "evidence_mode": packet.get("evidence_mode"),
        "evidence_refs": evidence_refs,
        "lane_depth": packet.get("lane_depth"),
        "completeness": packet.get("completeness"),
        "present_modalities": list(packet.get("present_modalities", [])),
        "missing_modalities": missing_modalities,
        "mixed_evidence": packet.get("mixed_evidence"),
        "thin_coverage": packet.get("thin_coverage"),
        "coverage_notes": coverage_notes,
        "supporting_modalities": list(packet.get("supporting_modalities", [])),
        "runtime_surface": packet.get("runtime_surface"),
        "provenance_pointers": provenance_pointers,
        "unresolved_lanes": unresolved_lanes,
    }


def _collect_unresolved_lanes(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    lanes: list[dict[str, Any]] = []
    for trace in traces:
        for lane in trace.get("unresolved_lanes", []):
            lane_id = str(lane.get("lane_id", ""))
            if lane_id in seen:
                continue
            seen.add(lane_id)
            lanes.append(lane)
    return sorted(
        lanes,
        key=lambda lane: (
            str(lane.get("lane_kind", "")),
            str(lane.get("parent_id", "")),
            str(lane.get("lane_id", "")),
        ),
    )


def build_provenance_drilldown(
    *,
    provenance_table_path: Path = DEFAULT_PROVENANCE_TABLE,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE,
    packet_audit_path: Path = DEFAULT_PACKET_AUDIT,
    curated_ppi_path: Path = DEFAULT_CURATED_PPI,
) -> dict[str, Any]:
    provenance_table = _read_json(provenance_table_path)
    source_coverage = _read_json(source_coverage_path)
    packet_audit = _read_json(packet_audit_path)
    curated_ppi = _read_json(curated_ppi_path)

    provenance_rows = list(provenance_table["cohort_summary"]["rows"])
    coverage_rows = list(source_coverage["coverage_matrix"])
    packet_rows = list(packet_audit["packets"])
    direct_pairs = list(curated_ppi.get("direct_evidence", []))
    empty_hits = list(curated_ppi.get("empty_hits", []))
    blocked_rows = list(curated_ppi.get("blocked_rows", []))

    coverage_by_accession = _index_rows(coverage_rows)
    packet_by_accession = _index_rows(packet_rows)
    entity_traces = [
        _build_entity_trace(
            provenance_row=row,
            coverage_row=coverage_by_accession.get(str(row["accession"])),
            packet_row=packet_by_accession.get(str(row["accession"])),
        )
        for row in _ordered_rows(provenance_rows)
    ]

    pair_traces = [_build_pair_trace_from_direct_evidence(entry) for entry in direct_pairs]
    pair_traces.extend(_build_pair_trace_from_empty_hit(entry) for entry in empty_hits)
    pair_traces.extend(_build_pair_trace_from_blocked_row(row) for row in blocked_rows)
    pair_traces = sorted(
        pair_traces,
        key=lambda item: (
            str(item.get("accession", "")),
            str(item.get("source_name", "")),
            str(item.get("trace_state", "")),
        ),
    )

    packet_traces = [
        _build_packet_trace(
            packet,
            coverage_row=coverage_by_accession.get(str(packet["accession"])),
        )
        for packet in sorted(
            packet_rows,
            key=lambda row: (
                int(row.get("row_index", 10**9)),
                str(row.get("accession", "")),
            ),
        )
    ]

    all_traces = [*entity_traces, *pair_traces, *packet_traces]
    unresolved_lanes = _collect_unresolved_lanes(all_traces)

    entity_status_counts = Counter(trace["trace_state"] for trace in entity_traces)
    pair_status_counts = Counter(trace["trace_state"] for trace in pair_traces)
    packet_status_counts = Counter(trace["trace_state"] for trace in packet_traces)

    return {
        "exporter_id": EXPORTER_ID,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "summary": {
            "entity_trace_count": len(entity_traces),
            "pair_trace_count": len(pair_traces),
            "packet_trace_count": len(packet_traces),
            "unresolved_lane_count": len(unresolved_lanes),
            "entity_status_counts": dict(sorted(entity_status_counts.items())),
            "pair_status_counts": dict(sorted(pair_status_counts.items())),
            "packet_status_counts": dict(sorted(packet_status_counts.items())),
        },
        "truth_boundary": [
            "prototype provenance only; no release-grade or corpus-scale overclaim",
            "partial and unreachable lanes remain explicit in the drilldown output",
            "packet completeness does not imply corpus completeness",
        ],
        "entities": entity_traces,
        "pairs": pair_traces,
        "packets": packet_traces,
        "unresolved_lanes": unresolved_lanes,
        "source_files": {
            "provenance_table": _norm_path(provenance_table_path),
            "source_coverage": _norm_path(source_coverage_path),
            "training_packet_audit": _norm_path(packet_audit_path),
            "curated_ppi_candidate_slice": _norm_path(curated_ppi_path),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a provenance drilldown for operator workflows.",
    )
    parser.add_argument("--provenance-table", type=Path, default=DEFAULT_PROVENANCE_TABLE)
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE)
    parser.add_argument("--packet-audit", type=Path, default=DEFAULT_PACKET_AUDIT)
    parser.add_argument("--curated-ppi", type=Path, default=DEFAULT_CURATED_PPI)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    payload = build_provenance_drilldown(
        provenance_table_path=args.provenance_table,
        source_coverage_path=args.source_coverage,
        packet_audit_path=args.packet_audit,
        curated_ppi_path=args.curated_ppi,
    )
    _write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
