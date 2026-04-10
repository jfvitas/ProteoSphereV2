from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _listify(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, list):
        return list(values)
    if isinstance(values, tuple):
        return list(values)
    return [values]


def _dedupe_text(values: Sequence[Any]) -> list[str]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return list(ordered.values())


def _packet_lookup(training_packet_audit_payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    packets = training_packet_audit_payload.get("packets") or ()
    lookup: dict[str, dict[str, Any]] = {}
    for packet in packets:
        if not isinstance(packet, Mapping):
            continue
        accession = _text(packet.get("accession")).upper()
        if accession:
            lookup[accession] = dict(packet)
    return lookup


def _benchmark_rows(
    usefulness_review_payload: Mapping[str, Any],
    training_packet_audit_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    packet_lookup = _packet_lookup(training_packet_audit_payload)
    rows: list[dict[str, Any]] = []
    for review in usefulness_review_payload.get("example_reviews") or ():
        if not isinstance(review, Mapping):
            continue
        accession = _text(review.get("accession")).upper()
        if not accession:
            continue
        packet = packet_lookup.get(accession, {})
        row = {
            "accession": accession,
            "canonical_id": _text(review.get("canonical_id")) or f"protein:{accession}",
            "split": _text(review.get("split")),
            "bucket": _text(review.get("bucket")),
            "judgment": _text(review.get("judgment")),
            "evidence_mode": _text(review.get("evidence_mode")),
            "validation_class": _text(review.get("validation_class")),
            "lane_depth": int(review.get("lane_depth") or 0),
            "mixed_evidence": bool(review.get("mixed_evidence", False)),
            "thin_coverage": bool(review.get("thin_coverage", False)),
            "source_lanes": _listify(review.get("source_lanes")),
            "coverage_notes": _listify(review.get("coverage_notes")),
            "evidence_refs": _listify(review.get("evidence_refs")),
            "planning_index_ref": _text(packet.get("planning_index_ref")),
            "present_modalities": _listify(packet.get("present_modalities")),
            "missing_modalities": _listify(packet.get("missing_modalities")),
        }
        rows.append(row)
    return rows


def _canonical_pair_lineage_complete(pair_records: Sequence[Mapping[str, Any]]) -> bool:
    for pair in pair_records:
        if not isinstance(pair, Mapping):
            continue
        source_record_ids = [
            _text(item) for item in pair.get("source_record_ids") or () if _text(item)
        ]
        if source_record_ids:
            return True
    return False


def build_curated_ppi_candidate_slice(
    usefulness_review_payload: Mapping[str, Any],
    training_packet_audit_payload: Mapping[str, Any],
    intact_slices_by_accession: Mapping[str, Mapping[str, Any]],
    biogrid_probe_entry: Mapping[str, Any],
) -> dict[str, Any]:
    direct_evidence: list[dict[str, Any]] = []
    breadth_only_evidence: list[dict[str, Any]] = []
    empty_hits: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []

    for benchmark_row in _benchmark_rows(
        usefulness_review_payload,
        training_packet_audit_payload,
    ):
        accession = benchmark_row["accession"]
        intact_slice = dict(intact_slices_by_accession.get(accession) or {})
        state = _text(intact_slice.get("state")) or "unavailable"
        pair_records = intact_slice.get("pair_records") or ()
        pair_count = int(intact_slice.get("pair_count") or len(pair_records))
        shared = {
            "accession": accession,
            "canonical_id": benchmark_row["canonical_id"],
            "split": benchmark_row["split"],
            "bucket": benchmark_row["bucket"],
            "judgment": benchmark_row["judgment"],
            "evidence_mode": benchmark_row["evidence_mode"],
            "validation_class": benchmark_row["validation_class"],
            "source_lanes": list(benchmark_row["source_lanes"]),
            "pair_count": pair_count,
            "pair_records": pair_records,
            "probe_reason": _text(intact_slice.get("probe_reason")),
            "provenance_pointers": _listify(intact_slice.get("provenance_pointers")),
            "canonical_pair_lineage_complete": _canonical_pair_lineage_complete(pair_records),
        }
        if state == "direct_hit":
            direct_evidence.append(
                {
                    **shared,
                    "evidence_kind": "curated_direct",
                    "source_name": "IntAct",
                }
            )
        elif state == "reachable_empty":
            empty_hits.append(
                {
                    **shared,
                    "source_name": "IntAct",
                    "empty_state": "reachable_empty",
                }
            )
        else:
            blocked_rows.append(
                {
                    **shared,
                    "source_name": "IntAct",
                    "blocked_state": state or "unavailable",
                }
            )

        breadth_only_evidence.append(
            {
                "accession": accession,
                "canonical_id": benchmark_row["canonical_id"],
                "source_name": _text(biogrid_probe_entry.get("source_name")) or "BioGRID",
                "probe_state": _text(biogrid_probe_entry.get("probe_state")) or "surface_reachable",
                "evidence_kind": "breadth_surface_only",
                "row_acquired": False,
                "next_step": _text(biogrid_probe_entry.get("next_step")),
                "notes": _listify(biogrid_probe_entry.get("notes")),
            }
        )

    return {
        "task_id": "P14-I006",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "cohort_accession_count": len(direct_evidence)
        + len(empty_hits)
        + len(blocked_rows),
        "direct_evidence": direct_evidence,
        "breadth_only_evidence": breadth_only_evidence,
        "empty_hits": empty_hits,
        "blocked_rows": blocked_rows,
        "summary": {
            "direct_evidence_count": len(direct_evidence),
            "breadth_only_count": len(breadth_only_evidence),
            "empty_hit_count": len(empty_hits),
            "blocked_count": len(blocked_rows),
            "canonical_pair_lineage_complete_count": sum(
                1 for row in direct_evidence if row["canonical_pair_lineage_complete"]
            ),
        },
    }


def build_protein_depth_candidate_slice(
    usefulness_review_payload: Mapping[str, Any],
    training_packet_audit_payload: Mapping[str, Any],
    disprot_probe_payload: Mapping[str, Any],
    structure_bridge_payload: Mapping[str, Any],
    sabiork_probe_entry: Mapping[str, Any],
) -> dict[str, Any]:
    direct_evidence: list[dict[str, Any]] = []
    breadth_only_evidence: list[dict[str, Any]] = []
    bridge_glue: list[dict[str, Any]] = []
    empty_hits: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []

    benchmark_by_accession = {
        row["accession"]: row
        for row in _benchmark_rows(usefulness_review_payload, training_packet_audit_payload)
    }
    for row in benchmark_by_accession.values():
        direct_evidence.append(
            {
                "accession": row["accession"],
                "canonical_id": row["canonical_id"],
                "split": row["split"],
                "bucket": row["bucket"],
                "judgment": row["judgment"],
                "evidence_mode": row["evidence_mode"],
                "validation_class": row["validation_class"],
                "lane_depth": row["lane_depth"],
                "source_lanes": list(row["source_lanes"]),
                "present_modalities": list(row["present_modalities"]),
                "missing_modalities": list(row["missing_modalities"]),
                "coverage_notes": list(row["coverage_notes"]),
            }
        )

    for record in disprot_probe_payload.get("records") or ():
        if not isinstance(record, Mapping):
            continue
        status = _text(record.get("status"))
        row = {
            "accession": _text(record.get("accession")).upper(),
            "source_name": "DisProt",
            "probe_url": _text(record.get("probe_url")),
            "status": status,
            "matched_record_count": int(record.get("matched_record_count") or 0),
            "matched_disprot_ids": _listify(record.get("matched_disprot_ids")),
            "returned_record_count": int(record.get("returned_record_count") or 0),
        }
        if status == "positive_hit":
            breadth_only_evidence.append(
                {
                    **row,
                    "evidence_kind": "protein_depth_breadth",
                }
            )
        elif status == "reachable_empty":
            empty_hits.append(
                {
                    **row,
                    "empty_state": "reachable_empty",
                }
            )
        else:
            blocked_rows.append(
                {
                    **row,
                    "blocked_reason": _text(record.get("blocker_reason")),
                }
            )

    for record in structure_bridge_payload.get("records") or ():
        if not isinstance(record, Mapping):
            continue
        bridge_state = _text(record.get("bridge_state"))
        row = {
            "accession": _text(record.get("accession")).upper(),
            "canonical_id": _text(record.get("canonical_id")),
            "source_name": _text(record.get("source_name")) or "RCSB/PDBe bridge",
            "pdb_id": _text(record.get("pdb_id")),
            "bridge_state": bridge_state,
            "bridge_kind": _text(record.get("bridge_kind")),
            "matched_uniprot_ids": _listify(record.get("matched_uniprot_ids")),
            "chain_ids": _listify(record.get("chain_ids")),
            "evidence_refs": _listify(record.get("evidence_refs")),
            "notes": _listify(record.get("notes")),
        }
        if bridge_state == "positive_hit":
            bridge_glue.append(row)
        else:
            empty_hits.append(
                {
                    **row,
                    "empty_state": "reachable_empty",
                }
            )

    sabiork_accessions = _dedupe_text(
        sabiork_probe_entry.get("expected_join_anchors") or ("P31749",)
    )
    for accession in sabiork_accessions:
        empty_hits.append(
            {
                "accession": accession,
                "source_name": _text(sabiork_probe_entry.get("source_name")) or "SABIO-RK",
                "empty_state": _text(sabiork_probe_entry.get("probe_state"))
                or "reachable_no_target_data",
                "next_step": _text(sabiork_probe_entry.get("next_step")),
                "notes": _listify(sabiork_probe_entry.get("notes")),
            }
        )

    return {
        "task_id": "P14-I007",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "cohort_accession_count": len(direct_evidence),
        "direct_evidence": direct_evidence,
        "breadth_only_evidence": breadth_only_evidence,
        "bridge_glue": bridge_glue,
        "empty_hits": empty_hits,
        "blocked_rows": blocked_rows,
        "summary": {
            "direct_evidence_count": len(direct_evidence),
            "disprot_positive_count": len(breadth_only_evidence),
            "bridge_glue_count": len(bridge_glue),
            "empty_hit_count": len(empty_hits),
            "blocked_count": len(blocked_rows),
        },
    }


def render_curated_ppi_candidate_slice_report(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary") or {}
    direct_rows = payload.get("direct_evidence") or ()
    empty_rows = payload.get("empty_hits") or ()
    blocked_rows = payload.get("blocked_rows") or ()
    lines = [
        "# Curated PPI Cohort Slice",
        "",
        f"Generated: `{_text(payload.get('generated_at'))}`",
        "",
        "## Summary",
        "",
        f"- Direct curated rows: `{summary.get('direct_evidence_count', 0)}`",
        f"- Breadth-only rows: `{summary.get('breadth_only_count', 0)}`",
        f"- Reachable-empty rows: `{summary.get('empty_hit_count', 0)}`",
        f"- Blocked rows: `{summary.get('blocked_count', 0)}`",
        "",
        "## Direct Evidence",
        "",
        "| Accession | Pair Count | Canonical Lineage | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in direct_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['accession']}`",
                    str(row.get("pair_count", 0)),
                    "yes" if row.get("canonical_pair_lineage_complete") else "partial",
                    _text(row.get("probe_reason")) or "direct curated IntAct slice",
                ]
            )
            + " |"
        )
    if not direct_rows:
        lines.append("| none | 0 | n/a | no direct curated IntAct pair rows were materialized |")
        lines.extend(
        [
            "",
            "## Breadth-Only Context",
            "",
            (
                "- BioGRID remains breadth-only in this slice unless a "
                "release-pinned row export is acquired."
            ),
            "",
            "## Empty And Blocked",
            "",
        ]
    )
    for row in empty_rows:
        lines.append(
            f"- `{row['accession']}`: IntAct reachable but empty for this accession slice"
        )
    for row in blocked_rows:
        lines.append(
            f"- `{row['accession']}`: IntAct unavailable or unresolved for the current live slice"
        )
    return "\n".join(lines) + "\n"


def render_protein_depth_candidate_slice_report(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Protein-Depth Candidate Slice",
        "",
        f"Generated: `{_text(payload.get('generated_at'))}`",
        "",
        "## Summary",
        "",
        f"- Direct benchmark depth rows: `{summary.get('direct_evidence_count', 0)}`",
        f"- DisProt breadth positives: `{summary.get('disprot_positive_count', 0)}`",
        f"- Structure bridge hits: `{summary.get('bridge_glue_count', 0)}`",
        f"- Empty hits: `{summary.get('empty_hit_count', 0)}`",
        f"- Blocked rows: `{summary.get('blocked_count', 0)}`",
        "",
        "## Direct Protein-Depth Evidence",
        "",
        "| Accession | Lanes | Evidence | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload.get("direct_evidence") or ():
        notes = (
            "; ".join(_dedupe_text(row.get("coverage_notes") or ()))
            or "benchmark-backed depth"
        )
        lines.append(
            "| "
            f"`{row['accession']}` | {row.get('lane_depth', 0)} | "
            f"`{row.get('evidence_mode', '')}` | {notes} |"
        )
    lines.extend(
        [
            "",
            "## Breadth And Bridge Lanes",
            "",
        ]
    )
    for row in payload.get("breadth_only_evidence") or ():
        disprot_ids = ",".join(row.get("matched_disprot_ids") or [])
        lines.append(
            f"- `{row['accession']}`: DisProt positive hit `{disprot_ids}`"
        )
    for row in payload.get("bridge_glue") or ():
        lines.append(
            f"- `{row['accession']}`: bridge-only structure glue via `{row.get('pdb_id', '')}`"
        )
    lines.extend(["", "## Empty And Blocked", ""])
    for row in payload.get("empty_hits") or ():
        lines.append(
            f"- `{row['accession']}`: `{row.get('source_name', '')}` reported "
            f"`{row.get('empty_state', '')}`"
        )
    for row in payload.get("blocked_rows") or ():
        lines.append(
            f"- `{row['accession']}`: `{row.get('source_name', '')}` blocked for this probe wave"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "build_curated_ppi_candidate_slice",
    "build_protein_depth_candidate_slice",
    "render_curated_ppi_candidate_slice_report",
    "render_protein_depth_candidate_slice_report",
]
