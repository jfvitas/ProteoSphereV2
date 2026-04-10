from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datasets.recipes.balanced_cohort_scorer import (  # noqa: E402
    BalancedCohortCandidate,
    rank_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_COVERAGE_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)
DEFAULT_COHORT_SLICE_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "p15_upgraded_cohort_slice.json"
)
DEFAULT_PACKET_SUMMARY_PATH = ROOT / "data" / "packages" / "LATEST.json"
DEFAULT_OUTPUT_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "balanced_dataset_plan.json"
)
DEFAULT_REQUESTED_MODALITIES = ("sequence", "structure", "ligand", "ppi")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable: Sequence[Any] = (values,)
    elif isinstance(values, Sequence):
        iterable = values
    else:
        iterable = (values,)
    ordered: dict[str, str] = {}
    for value in iterable:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _source_coverage_rows(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = payload.get("coverage_matrix") or payload.get("rows") or payload.get("entries") or ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ()
    return tuple(dict(row) for row in rows if isinstance(row, Mapping))


def _cohort_rows(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = payload.get("rows") or payload.get("cohort") or ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ()
    return tuple(dict(row) for row in rows if isinstance(row, Mapping))


def _packet_rows(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = payload.get("packets") or payload.get("rows") or ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ()
    return tuple(dict(row) for row in rows if isinstance(row, Mapping))


def _lookup_by_accession(
    rows: Sequence[Mapping[str, Any]],
    *,
    accession_key: str = "accession",
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = _optional_text(row.get(accession_key))
        if accession:
            lookup[accession.casefold()] = dict(row)
    return lookup


def _packet_lookup(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = _optional_text(row.get("accession"))
        if accession:
            lookup[accession.casefold()] = dict(row)
    return lookup


def _merge_modalities(
    coverage_row: Mapping[str, Any],
    cohort_row: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    present_modalities = _clean_text_tuple(coverage_row.get("present_modalities"))
    missing_modalities = _clean_text_tuple(coverage_row.get("missing_modalities"))
    source_lanes = _clean_text_tuple(
        coverage_row.get("source_lanes") or coverage_row.get("evidence_lanes")
    )
    if cohort_row and isinstance(cohort_row.get("protein_depth"), Mapping):
        protein_depth = dict(cohort_row["protein_depth"])
        if not present_modalities:
            present_modalities = _clean_text_tuple(protein_depth.get("present_modalities"))
        if not missing_modalities:
            missing_modalities = _clean_text_tuple(protein_depth.get("missing_modalities"))
        if not source_lanes:
            source_lanes = _clean_text_tuple(protein_depth.get("source_lanes"))
    return present_modalities, missing_modalities, source_lanes


def _inferred_packet_expectation(
    *,
    accession: str,
    canonical_id: str,
    requested_modalities: Sequence[str],
    present_modalities: Sequence[str],
    missing_modalities: Sequence[str],
) -> dict[str, Any]:
    normalized_requested = _clean_text_tuple(requested_modalities)
    normalized_present = _clean_text_tuple(present_modalities)
    normalized_missing = _clean_text_tuple(missing_modalities)
    present_lookup = {item.casefold() for item in normalized_present}
    if not normalized_missing:
        normalized_missing = tuple(
            item
            for item in normalized_requested
            if item.casefold() not in present_lookup
        )
    status = "unresolved"
    if normalized_requested and all(
        item.casefold() in present_lookup for item in normalized_requested
    ):
        status = "complete"
    elif normalized_present:
        status = "partial"
    return {
        "accession": accession,
        "canonical_id": canonical_id,
        "source": "inferred_from_coverage",
        "status": status,
        "packet_ready": status == "complete",
        "present_modalities": list(normalized_present),
        "missing_modalities": list(normalized_missing),
        "manifest_path": None,
        "notes": [
            "no materialized packet summary was available for this accession",
            "packet expectation is inferred conservatively from real coverage artifacts",
        ],
    }


def _materialized_packet_expectation(
    packet_row: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "accession": _optional_text(packet_row.get("accession")),
        "canonical_id": _optional_text(packet_row.get("canonical_id")),
        "source": "materialized_packet",
        "status": _optional_text(packet_row.get("status")) or "unresolved",
        "packet_ready": _clean_text(packet_row.get("status")).casefold() == "complete",
        "present_modalities": list(_clean_text_tuple(packet_row.get("present_modalities"))),
        "missing_modalities": list(_clean_text_tuple(packet_row.get("missing_modalities"))),
        "manifest_path": _optional_text(packet_row.get("manifest_path")),
        "notes": list(_clean_text_tuple(packet_row.get("notes"))),
    }


def _plan_row(
    coverage_row: Mapping[str, Any],
    *,
    cohort_row: Mapping[str, Any] | None,
    packet_row: Mapping[str, Any] | None,
    requested_modalities: Sequence[str],
    score_lookup: Mapping[str, Any],
) -> dict[str, Any]:
    accession = _optional_text(coverage_row.get("accession")) or ""
    canonical_id = _optional_text(coverage_row.get("canonical_id")) or f"protein:{accession}"
    present_modalities, missing_modalities, source_lanes = _merge_modalities(
        coverage_row,
        cohort_row,
    )
    packet_expectation = (
        _materialized_packet_expectation(packet_row)
        if packet_row is not None
        else _inferred_packet_expectation(
            accession=accession,
            canonical_id=canonical_id,
            requested_modalities=requested_modalities,
            present_modalities=present_modalities,
            missing_modalities=missing_modalities,
        )
    )
    return {
        "accession": accession,
        "canonical_id": canonical_id,
        "split": _optional_text(coverage_row.get("split")) or "train",
        "leakage_key": _optional_text(coverage_row.get("leakage_key")) or accession,
        "bucket": _optional_text(coverage_row.get("bucket")) or "unknown",
        "evidence_mode": _optional_text(coverage_row.get("evidence_mode")) or "unknown",
        "validation_class": _optional_text(coverage_row.get("validation_class")) or "unknown",
        "lane_depth": int(coverage_row.get("lane_depth") or 0),
        "thin_coverage": bool(coverage_row.get("thin_coverage", False)),
        "mixed_evidence": bool(coverage_row.get("mixed_evidence", False)),
        "source_lanes": list(source_lanes),
        "present_modalities": list(present_modalities),
        "missing_modalities": list(missing_modalities),
        "coverage_notes": list(_clean_text_tuple(coverage_row.get("coverage_notes"))),
        "score_trace": {
            "accepted": bool(score_lookup["accepted"]),
            "total_score": score_lookup["total_score"],
            "component_scores": dict(score_lookup["component_scores"]),
            "reasons": list(score_lookup["reasons"]),
        },
        "packet_expectation": packet_expectation,
    }


def build_balanced_dataset_plan(
    *,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE_PATH,
    cohort_slice_path: Path = DEFAULT_COHORT_SLICE_PATH,
    packet_summary_path: Path = DEFAULT_PACKET_SUMMARY_PATH,
    requested_modalities: Sequence[str] = DEFAULT_REQUESTED_MODALITIES,
    limit: int | None = None,
) -> dict[str, Any]:
    source_coverage_payload = _load_json(source_coverage_path)
    cohort_slice_payload = _load_json(cohort_slice_path)
    packet_summary_payload = (
        _load_json(packet_summary_path) if packet_summary_path.exists() else None
    )

    coverage_rows = _source_coverage_rows(source_coverage_payload)
    cohort_lookup = _lookup_by_accession(_cohort_rows(cohort_slice_payload))
    packet_lookup = (
        _packet_lookup(_packet_rows(packet_summary_payload))
        if isinstance(packet_summary_payload, Mapping)
        else {}
    )

    candidates: list[BalancedCohortCandidate] = []
    for row in coverage_rows:
        accession = _optional_text(row.get("accession"))
        if not accession:
            continue
        canonical_id = _optional_text(row.get("canonical_id")) or f"protein:{accession}"
        cohort_row = cohort_lookup.get(accession.casefold())
        present_modalities, missing_modalities, source_lanes = _merge_modalities(row, cohort_row)
        packet_row = packet_lookup.get(accession.casefold())
        packet_status = _clean_text(packet_row.get("status")) if packet_row else ""
        packet_ready = packet_status.lower() == "complete"
        candidate_payload = {
            "canonical_id": canonical_id,
            "leakage_key": _optional_text(row.get("leakage_key")) or accession,
            "present_modalities": present_modalities,
            "missing_modalities": missing_modalities,
            "source_lanes": source_lanes,
            "lane_depth": int(row.get("lane_depth") or 0),
            "evidence_mode": _optional_text(row.get("evidence_mode")) or "unknown",
            "validation_class": _optional_text(row.get("validation_class")) or "unknown",
            "bucket": _optional_text(row.get("bucket")) or "unknown",
            "record_type": _optional_text(row.get("record_type")) or "protein",
            "packet_ready": packet_ready,
            "thin_coverage": bool(row.get("thin_coverage", False)),
            "mixed_evidence": bool(row.get("mixed_evidence", False)),
            "payload": dict(row),
        }
        candidates.append(
            BalancedCohortCandidate.from_dict(
                candidate_payload,
                requested_modalities=requested_modalities,
            )
        )

    ranking = rank_candidates(
        candidates,
        requested_modalities=requested_modalities,
        limit=limit,
    )
    accepted_lookup = {item.canonical_id: item.to_dict() for item in ranking.accepted}
    rejected_lookup = {item.canonical_id: item.to_dict() for item in ranking.rejected}

    selected_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    for row in coverage_rows:
        accession = _optional_text(row.get("accession"))
        if not accession:
            continue
        canonical_id = _optional_text(row.get("canonical_id")) or f"protein:{accession}"
        cohort_row = cohort_lookup.get(accession.casefold())
        packet_row = packet_lookup.get(accession.casefold())
        if canonical_id in accepted_lookup:
            selected_rows.append(
                _plan_row(
                    row,
                    cohort_row=cohort_row,
                    packet_row=packet_row,
                    requested_modalities=requested_modalities,
                    score_lookup=accepted_lookup[canonical_id],
                )
            )
        elif canonical_id in rejected_lookup:
            rejected_rows.append(
                _plan_row(
                    row,
                    cohort_row=cohort_row,
                    packet_row=packet_row,
                    requested_modalities=requested_modalities,
                    score_lookup=rejected_lookup[canonical_id],
                )
            )

    packet_status_counts = Counter(
        row["packet_expectation"]["status"] for row in selected_rows
    )
    split_counts = Counter(row["split"] for row in selected_rows)
    leakage_keys = [row["leakage_key"] for row in selected_rows]
    modality_coverage = Counter()
    for row in selected_rows:
        for modality in row["present_modalities"]:
            modality_coverage[modality] += 1

    packet_materialization_mode = (
        "materialized_packets_present"
        if packet_lookup
        else "inferred_packet_expectations_only"
    )
    return {
        "generated_at": _utc_now(),
        "requested_modalities": list(_clean_text_tuple(requested_modalities)),
        "source_artifacts": {
            "source_coverage_path": str(source_coverage_path),
            "cohort_slice_path": str(cohort_slice_path),
            "packet_summary_path": str(packet_summary_path),
        },
        "packet_materialization_mode": packet_materialization_mode,
        "selected_count": len(selected_rows),
        "rejected_count": len(rejected_rows),
        "selected_rows": selected_rows,
        "rejected_rows": rejected_rows,
        "summary": {
            "selected_split_counts": dict(sorted(split_counts.items())),
            "selected_packet_status_counts": dict(sorted(packet_status_counts.items())),
            "selected_modality_coverage": dict(sorted(modality_coverage.items())),
            "leakage_safe": len(leakage_keys) == len(set(item.casefold() for item in leakage_keys)),
            "conservative_boundary": (
                "plan stays conservative by preserving incomplete packet expectations "
                "instead of upgrading missing modalities into complete packets"
            ),
        },
    }


def _parse_modalities(value: str | None) -> tuple[str, ...]:
    if not value:
        return DEFAULT_REQUESTED_MODALITIES
    return _clean_text_tuple(tuple(part.strip() for part in value.split(",")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a leakage-safe balanced dataset plan from source coverage, "
            "cohort uplift artifacts, and optional materialized packet outputs."
        )
    )
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE_PATH)
    parser.add_argument("--cohort-slice", type=Path, default=DEFAULT_COHORT_SLICE_PATH)
    parser.add_argument("--packet-summary", type=Path, default=DEFAULT_PACKET_SUMMARY_PATH)
    parser.add_argument(
        "--requested-modalities",
        type=str,
        default=",".join(DEFAULT_REQUESTED_MODALITIES),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_balanced_dataset_plan(
        source_coverage_path=args.source_coverage,
        cohort_slice_path=args.cohort_slice,
        packet_summary_path=args.packet_summary,
        requested_modalities=_parse_modalities(args.requested_modalities),
        limit=args.limit,
    )
    if args.output:
        _write_json(args.output, payload)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "Balanced dataset plan: "
            f"selected={payload['selected_count']} "
            f"rejected={payload['rejected_count']} "
            f"packet_mode={payload['packet_materialization_mode']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
