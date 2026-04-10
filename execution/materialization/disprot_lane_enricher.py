from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from execution.acquire.disprot_candidate_probe import (
    DisProtCandidateProbeResult,
)

DisProtLaneState = Literal["positive_hit", "reachable_empty", "blocked", "unresolved"]

DEFAULT_DISPROT_POSITIVE_ACCESSIONS = ("P04637", "P31749", "Q9NZD4")
DEFAULT_DISPROT_POSITIVE_IDS: dict[str, tuple[str, ...]] = {
    "P04637": ("DP00086",),
    "P31749": ("DP03300",),
    "Q9NZD4": ("DP03619",),
}


class DisProtLaneEnricherError(ValueError):
    """Raised when a DisProt lane enrichment payload cannot be normalized."""


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise DisProtLaneEnricherError(f"{field_name} must be a non-empty string")
    return text


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Sequence):
        return tuple(values)
    return (values,)


def _normalize_accession(value: Any) -> str:
    accession = _clean_text(value).upper()
    if not accession:
        return ""
    if not 6 <= len(accession) <= 10 or not accession.isalnum():
        return ""
    return accession


def _coerce_accessions(values: Any) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        accession = _normalize_accession(value)
        if not accession or accession in seen:
            continue
        seen.add(accession)
        normalized.append(accession)
    return tuple(normalized)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _record_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _record_status(record: Any) -> str:
    return _clean_text(_record_value(record, "status")).casefold()


def _record_probe_url(record: Any) -> str | None:
    text = _clean_text(_record_value(record, "probe_url"))
    return text or None


def _record_blocker_reason(record: Any) -> str | None:
    text = _clean_text(_record_value(record, "blocker_reason"))
    return text or None


def _record_response_size(record: Any) -> int | None:
    value = _record_value(record, "response_size")
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _record_counts(record: Any) -> tuple[int, int]:
    returned = _record_value(record, "returned_record_count", 0)
    matched = _record_value(record, "matched_record_count", 0)
    try:
        return int(returned or 0), int(matched or 0)
    except (TypeError, ValueError) as exc:
        raise DisProtLaneEnricherError("record counts must be integers") from exc


def _record_disprot_ids(record: Any) -> tuple[str, ...]:
    values = _record_value(record, "matched_disprot_ids")
    if not values:
        values = _record_value(record, "returned_disprot_ids")
    return _dedupe_text(values)


def _record_accession(record: Any) -> str:
    accession = _normalize_accession(_record_value(record, "accession"))
    if not accession:
        raise DisProtLaneEnricherError("probe record is missing a valid accession")
    return accession


def _probe_records(probe_result: Any) -> dict[str, Any]:
    if probe_result is None:
        return {}
    if isinstance(probe_result, DisProtCandidateProbeResult):
        records = probe_result.records
    elif isinstance(probe_result, Mapping):
        records = probe_result.get("records") or ()
    else:
        records = getattr(probe_result, "records", ())

    lookup: dict[str, Any] = {}
    for record in _iter_values(records):
        accession = _record_accession(record)
        lookup[accession] = record
    return lookup


def _positive_id_lookup(
    positive_accessions: Sequence[str] | str,
    positive_disprot_ids: Mapping[str, Sequence[str]] | None,
) -> dict[str, tuple[str, ...]]:
    lookup: dict[str, tuple[str, ...]] = {
        accession: ids for accession, ids in DEFAULT_DISPROT_POSITIVE_IDS.items()
    }
    if positive_disprot_ids is not None:
        if not isinstance(positive_disprot_ids, Mapping):
            raise DisProtLaneEnricherError("positive_disprot_ids must be a mapping")
        for key, value in positive_disprot_ids.items():
            accession = _normalize_accession(key)
            if not accession:
                continue
            lookup[accession] = _dedupe_text(value)
    for accession in _coerce_accessions(positive_accessions):
        lookup.setdefault(accession, DEFAULT_DISPROT_POSITIVE_IDS.get(accession, ()))
    return lookup


@dataclass(frozen=True, slots=True)
class DisProtPacketLane:
    accession: str
    lane_state: DisProtLaneState
    lane_depth: int
    disprot_ids: tuple[str, ...] = ()
    probe_url: str | None = None
    blocker_reason: str | None = None
    returned_record_count: int = 0
    matched_record_count: int = 0
    response_size: int | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        accession = _normalize_accession(self.accession)
        if not accession:
            raise DisProtLaneEnricherError("accession must be a valid UniProt accession")
        lane_state = _clean_text(self.lane_state).casefold()
        if lane_state not in {"positive_hit", "reachable_empty", "blocked", "unresolved"}:
            raise DisProtLaneEnricherError("lane_state must describe a DisProt lane outcome")
        if self.lane_depth < 0:
            raise DisProtLaneEnricherError("lane_depth must be non-negative")
        if self.returned_record_count < 0 or self.matched_record_count < 0:
            raise DisProtLaneEnricherError("record counts must be non-negative")
        if self.response_size is not None and self.response_size < 0:
            raise DisProtLaneEnricherError("response_size must be non-negative")

        object.__setattr__(self, "accession", accession)
        object.__setattr__(self, "lane_state", lane_state)
        object.__setattr__(self, "disprot_ids", _dedupe_text(self.disprot_ids))
        object.__setattr__(self, "probe_url", _clean_text(self.probe_url) or None)
        object.__setattr__(self, "blocker_reason", _clean_text(self.blocker_reason) or None)
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "lane_state": self.lane_state,
            "lane_depth": self.lane_depth,
            "disprot_ids": list(self.disprot_ids),
            "probe_url": self.probe_url,
            "blocker_reason": self.blocker_reason,
            "returned_record_count": self.returned_record_count,
            "matched_record_count": self.matched_record_count,
            "response_size": self.response_size,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class DisProtLaneEnrichment:
    cohort_accessions: tuple[str, ...]
    packet_lanes: tuple[DisProtPacketLane, ...]
    positive_accessions: tuple[str, ...]
    reachable_empty_accessions: tuple[str, ...]
    blocked_accessions: tuple[str, ...]
    unresolved_accessions: tuple[str, ...]
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_accessions": list(self.cohort_accessions),
            "packet_lanes": [lane.to_dict() for lane in self.packet_lanes],
            "positive_accessions": list(self.positive_accessions),
            "reachable_empty_accessions": list(self.reachable_empty_accessions),
            "blocked_accessions": list(self.blocked_accessions),
            "unresolved_accessions": list(self.unresolved_accessions),
            "summary": dict(self.summary),
        }


def build_disprot_lane_enrichment(
    cohort_accessions: Sequence[str] | str,
    *,
    probe_result: DisProtCandidateProbeResult | Mapping[str, Any] | None = None,
    positive_accessions: Sequence[str] | str = DEFAULT_DISPROT_POSITIVE_ACCESSIONS,
    positive_disprot_ids: Mapping[str, Sequence[str]] | None = None,
) -> DisProtLaneEnrichment:
    normalized_accessions = _coerce_accessions(cohort_accessions)
    probe_lookup = _probe_records(probe_result)
    positive_lookup = _positive_id_lookup(positive_accessions, positive_disprot_ids)

    packet_lanes: list[DisProtPacketLane] = []
    positive_ordered: list[str] = []
    empty_ordered: list[str] = []
    blocked_ordered: list[str] = []
    unresolved_ordered: list[str] = []

    for accession in normalized_accessions:
        record = probe_lookup.get(accession)
        if record is not None:
            status = _record_status(record)
            probe_url = _record_probe_url(record)
            blocker_reason = _record_blocker_reason(record)
            returned_count, matched_count = _record_counts(record)
            response_size = _record_response_size(record)
            disprot_ids = _record_disprot_ids(record)
            notes = ()
            if status == "positive_hit":
                if not disprot_ids:
                    disprot_ids = positive_lookup.get(accession, ())
                positive_ordered.append(accession)
                lane_depth = 1
            elif status == "reachable_empty":
                empty_ordered.append(accession)
                unresolved_ordered.append(accession)
                lane_depth = 0
                notes = ("reachable but empty accession probe",)
            elif status == "blocked":
                blocked_ordered.append(accession)
                lane_depth = 0
            else:
                unresolved_ordered.append(accession)
                lane_depth = 0
                notes = ("unrecognized probe state",)
            packet_lanes.append(
                DisProtPacketLane(
                    accession=accession,
                    lane_state=(
                        "unresolved"
                        if status == "reachable_empty"
                        else status
                        if status in {"positive_hit", "blocked"}
                        else "unresolved"
                    ),
                    lane_depth=lane_depth,
                    disprot_ids=disprot_ids,
                    probe_url=probe_url,
                    blocker_reason=blocker_reason,
                    returned_record_count=returned_count,
                    matched_record_count=matched_count,
                    response_size=response_size,
                    notes=notes,
                )
            )
            continue

        if accession in positive_lookup:
            positive_ordered.append(accession)
            packet_lanes.append(
                DisProtPacketLane(
                    accession=accession,
                    lane_state="positive_hit",
                    lane_depth=1,
                    disprot_ids=positive_lookup.get(accession, ()),
                    notes=("integrated from the current DisProt-positive cohort set",),
                )
            )
        else:
            unresolved_ordered.append(accession)
            packet_lanes.append(
                DisProtPacketLane(
                    accession=accession,
                    lane_state="unresolved",
                    lane_depth=0,
                    notes=("no positive DisProt lane materialized for this accession",),
                )
            )

    summary = {
        "cohort_accession_count": len(normalized_accessions),
        "lane_count": len(packet_lanes),
        "positive_count": len(positive_ordered),
        "reachable_empty_count": len(empty_ordered),
        "blocked_count": len(blocked_ordered),
        "unresolved_count": len(unresolved_ordered),
    }
    return DisProtLaneEnrichment(
        cohort_accessions=normalized_accessions,
        packet_lanes=tuple(packet_lanes),
        positive_accessions=tuple(positive_ordered),
        reachable_empty_accessions=tuple(empty_ordered),
        blocked_accessions=tuple(blocked_ordered),
        unresolved_accessions=tuple(unresolved_ordered),
        summary=summary,
    )


__all__ = [
    "DEFAULT_DISPROT_POSITIVE_ACCESSIONS",
    "DEFAULT_DISPROT_POSITIVE_IDS",
    "DisProtLaneEnricherError",
    "DisProtLaneEnrichment",
    "DisProtLaneState",
    "DisProtPacketLane",
    "build_disprot_lane_enrichment",
]
