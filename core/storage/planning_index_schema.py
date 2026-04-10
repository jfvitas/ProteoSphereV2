from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

JoinStatus = Literal[
    "unjoined",
    "candidate",
    "joined",
    "partial",
    "ambiguous",
    "conflict",
    "deferred",
]
CoverageKind = Literal["source", "modality"]
CoverageState = Literal["unknown", "absent", "partial", "present"]
MaterializationKind = Literal[
    "coordinates",
    "map",
    "alignment",
    "table",
    "evidence_text",
    "diagram",
    "portal_payload",
    "other",
]

_JOIN_STATUS_ALIASES: dict[str, JoinStatus] = {
    "unjoined": "unjoined",
    "unmapped": "unjoined",
    "candidate": "candidate",
    "pending": "candidate",
    "joined": "joined",
    "linked": "joined",
    "mapped": "joined",
    "partial": "partial",
    "ambiguous": "ambiguous",
    "conflict": "conflict",
    "deferred": "deferred",
    "lazy": "deferred",
}
_COVERAGE_KIND_ALIASES: dict[str, CoverageKind] = {
    "source": "source",
    "source_coverage": "source",
    "modality": "modality",
    "modality_coverage": "modality",
}
_COVERAGE_STATE_ALIASES: dict[str, CoverageState] = {
    "unknown": "unknown",
    "unset": "unknown",
    "absent": "absent",
    "missing": "absent",
    "none": "absent",
    "partial": "partial",
    "limited": "partial",
    "present": "present",
    "full": "present",
    "covered": "present",
    "indexed": "present",
    "preloaded": "present",
}
_MATERIALIZATION_KIND_ALIASES: dict[str, MaterializationKind] = {
    "coordinates": "coordinates",
    "coordinate": "coordinates",
    "structure": "coordinates",
    "map": "map",
    "alignment": "alignment",
    "msa": "alignment",
    "table": "table",
    "evidence_table": "table",
    "rows": "table",
    "evidence_text": "evidence_text",
    "text": "evidence_text",
    "diagram": "diagram",
    "portal_payload": "portal_payload",
    "payload": "portal_payload",
    "other": "other",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _normalize_release_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _optional_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError("release_date must be ISO-8601 formatted") from exc


def _normalize_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric or None")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")
    return normalized


def _normalize_json_value(value: Any, field_name: str) -> JSONValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, JSONValue] = {}
        for key, item in value.items():
            normalized_key = _required_text(key, f"{field_name} key")
            normalized[normalized_key] = _normalize_json_value(
                item,
                f"{field_name}[{normalized_key!r}]",
            )
        return normalized
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return tuple(_normalize_json_value(item, field_name) for item in value)
    raise TypeError(f"{field_name} must contain only JSON-serializable values")


def _normalize_json_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, JSONValue]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, JSONValue] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized[normalized_key] = _normalize_json_value(
            item,
            f"{field_name}[{normalized_key!r}]",
        )
    return normalized


def _normalize_string_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized[normalized_key] = _required_text(item, f"{field_name}[{normalized_key!r}]")
    return normalized


def _json_ready(value: JSONValue) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _normalize_join_status(value: Any) -> JoinStatus:
    text = _required_text(value, "join_status").replace("-", "_").replace(" ", "_").casefold()
    status = _JOIN_STATUS_ALIASES.get(text)
    if status is None:
        raise ValueError(f"unsupported join_status: {value!r}")
    return status


def _normalize_coverage_kind(value: Any) -> CoverageKind:
    text = _required_text(value, "coverage_kind").replace("-", "_").replace(" ", "_").casefold()
    kind = _COVERAGE_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported coverage_kind: {value!r}")
    return kind


def _normalize_coverage_state(value: Any) -> CoverageState:
    text = _required_text(value, "coverage_state").replace("-", "_").replace(" ", "_").casefold()
    state = _COVERAGE_STATE_ALIASES.get(text)
    if state is None:
        raise ValueError(f"unsupported coverage_state: {value!r}")
    return state


def _normalize_materialization_kind(value: Any) -> MaterializationKind:
    text = (
        _required_text(value, "materialization_kind")
        .replace("-", "_")
        .replace(" ", "_")
        .casefold()
    )
    kind = _MATERIALIZATION_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported materialization_kind: {value!r}")
    return kind


def _canonicalize_ids(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


@dataclass(frozen=True, slots=True)
class PlanningIndexSourceRecord:
    """Pinned source-backed identity slice used by the planning index."""

    source_name: str
    source_record_id: str
    release_version: str | None = None
    release_date: str | date | datetime | None = None
    source_locator: str | None = None
    manifest_id: str | None = None
    source_keys: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _required_text(self.source_name, "source_name"))
        object.__setattr__(
            self,
            "source_record_id",
            _required_text(self.source_record_id, "source_record_id"),
        )
        release_version = _optional_text(self.release_version)
        release_date = _normalize_release_date(self.release_date)
        manifest_id = _optional_text(self.manifest_id)
        source_locator = _optional_text(self.source_locator)
        if release_version is None and release_date is None and manifest_id is None:
            raise ValueError("release_version, release_date, or manifest_id is required")
        object.__setattr__(self, "release_version", release_version)
        object.__setattr__(self, "release_date", release_date)
        object.__setattr__(self, "source_locator", source_locator)
        object.__setattr__(self, "manifest_id", manifest_id)
        object.__setattr__(
            self,
            "source_keys",
            _normalize_string_mapping(self.source_keys, "source_keys"),
        )

    @property
    def release_stamp(self) -> str:
        return self.release_version or self.release_date or self.manifest_id or "unreleased"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "source_locator": self.source_locator,
            "manifest_id": self.manifest_id,
            "source_keys": dict(self.source_keys),
            "release_stamp": self.release_stamp,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanningIndexSourceRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=payload.get("source_name") or payload.get("source") or "",
            source_record_id=payload.get("source_record_id")
            or payload.get("record_id")
            or payload.get("identifier")
            or payload.get("accession")
            or "",
            release_version=payload.get("release_version")
            or payload.get("version")
            or payload.get("release"),
            release_date=payload.get("release_date") or payload.get("date"),
            source_locator=payload.get("source_locator")
            or payload.get("source_url")
            or payload.get("url"),
            manifest_id=payload.get("manifest_id") or payload.get("snapshot_id"),
            source_keys=payload.get("source_keys") or payload.get("keys") or {},
        )


@dataclass(frozen=True, slots=True)
class PlanningIndexCoverage:
    """Coarse source or modality coverage signal for planning."""

    coverage_kind: CoverageKind
    label: str
    coverage_state: CoverageState = "unknown"
    source_names: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    confidence: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "coverage_kind", _normalize_coverage_kind(self.coverage_kind))
        object.__setattr__(self, "label", _required_text(self.label, "label"))
        object.__setattr__(self, "coverage_state", _normalize_coverage_state(self.coverage_state))
        object.__setattr__(self, "source_names", _normalize_text_tuple(self.source_names))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        object.__setattr__(self, "confidence", _normalize_float(self.confidence, "confidence"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "coverage_kind": self.coverage_kind,
            "label": self.label,
            "coverage_state": self.coverage_state,
            "source_names": list(self.source_names),
            "notes": list(self.notes),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanningIndexCoverage:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            coverage_kind=payload.get("coverage_kind") or payload.get("axis") or "modality",
            label=payload.get("label") or payload.get("name") or "",
            coverage_state=payload.get("coverage_state") or payload.get("state") or "unknown",
            source_names=payload.get("source_names") or payload.get("sources") or (),
            notes=payload.get("notes") or payload.get("note") or (),
            confidence=payload.get("confidence"),
        )


@dataclass(frozen=True, slots=True)
class PlanningIndexMaterializationPointer:
    """Deferred hydration pointer for heavy or selection-specific payloads."""

    materialization_kind: MaterializationKind
    pointer: str
    selector: str | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "materialization_kind",
            _normalize_materialization_kind(self.materialization_kind),
        )
        object.__setattr__(self, "pointer", _required_text(self.pointer, "pointer"))
        object.__setattr__(self, "selector", _optional_text(self.selector))
        object.__setattr__(self, "source_name", _optional_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "materialization_kind": self.materialization_kind,
            "pointer": self.pointer,
            "selector": self.selector,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> PlanningIndexMaterializationPointer:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            materialization_kind=payload.get("materialization_kind")
            or payload.get("kind")
            or payload.get("asset_kind")
            or "other",
            pointer=payload.get("pointer") or payload.get("uri") or payload.get("path") or "",
            selector=payload.get("selector") or payload.get("selection"),
            source_name=payload.get("source_name") or payload.get("source"),
            source_record_id=payload.get("source_record_id")
            or payload.get("record_id")
            or payload.get("identifier"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class PlanningIndexEntry:
    """Single planning-index row with source pins and join-state metadata."""

    planning_id: str
    source_records: tuple[PlanningIndexSourceRecord, ...]
    canonical_ids: tuple[str, ...] = field(default_factory=tuple)
    join_status: JoinStatus = "unjoined"
    join_confidence: float | None = None
    coverage: tuple[PlanningIndexCoverage, ...] = field(default_factory=tuple)
    lazy_materialization_pointers: tuple[PlanningIndexMaterializationPointer, ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "planning_id", _required_text(self.planning_id, "planning_id"))
        source_records = tuple(self.source_records)
        if not source_records:
            raise ValueError("source_records must not be empty")
        normalized_sources: list[PlanningIndexSourceRecord] = []
        for source_record in source_records:
            if not isinstance(source_record, PlanningIndexSourceRecord):
                raise TypeError("source_records must contain PlanningIndexSourceRecord objects")
            normalized_sources.append(source_record)
        object.__setattr__(self, "source_records", tuple(normalized_sources))
        canonical_ids = _canonicalize_ids(self.canonical_ids)
        object.__setattr__(self, "canonical_ids", canonical_ids)
        join_status = _normalize_join_status(self.join_status)
        object.__setattr__(self, "join_status", join_status)
        object.__setattr__(
            self,
            "join_confidence",
            _normalize_float(self.join_confidence, "join_confidence"),
        )
        coverage: list[PlanningIndexCoverage] = []
        for item in self.coverage:
            if not isinstance(item, PlanningIndexCoverage):
                raise TypeError("coverage must contain PlanningIndexCoverage objects")
            coverage.append(item)
        object.__setattr__(self, "coverage", tuple(coverage))
        pointers: list[PlanningIndexMaterializationPointer] = []
        for item in self.lazy_materialization_pointers:
            if not isinstance(item, PlanningIndexMaterializationPointer):
                raise TypeError(
                    "lazy_materialization_pointers must contain "
                    "PlanningIndexMaterializationPointer objects"
                )
            pointers.append(item)
        object.__setattr__(self, "lazy_materialization_pointers", tuple(pointers))
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))
        if join_status == "joined" and not canonical_ids:
            raise ValueError("joined entries require canonical_ids")

    @property
    def primary_canonical_id(self) -> str | None:
        return self.canonical_ids[0] if self.canonical_ids else None

    @property
    def source_names(self) -> tuple[str, ...]:
        return tuple(source_record.source_name for source_record in self.source_records)

    @property
    def is_pinned_source_backed(self) -> bool:
        return bool(self.source_records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "planning_id": self.planning_id,
            "source_records": [source_record.to_dict() for source_record in self.source_records],
            "canonical_ids": list(self.canonical_ids),
            "canonical_id": self.primary_canonical_id,
            "join_status": self.join_status,
            "join_confidence": self.join_confidence,
            "coverage": [item.to_dict() for item in self.coverage],
            "lazy_materialization_pointers": [
                item.to_dict() for item in self.lazy_materialization_pointers
            ],
            "metadata": _json_ready(dict(self.metadata)),
            "is_pinned_source_backed": self.is_pinned_source_backed,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanningIndexEntry:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        source_payloads = payload.get("source_records") or payload.get("sources") or ()
        return cls(
            planning_id=(
                payload.get("planning_id")
                or payload.get("id")
                or payload.get("record_id")
                or ""
            ),
            source_records=tuple(
                item
                if isinstance(item, PlanningIndexSourceRecord)
                else PlanningIndexSourceRecord.from_dict(item)
                for item in _iter_values(source_payloads)
            ),
            canonical_ids=_canonicalize_ids(
                _first_non_none(payload.get("canonical_ids"), payload.get("canonical_id"), ())
            ),
            join_status=payload.get("join_status") or payload.get("status") or "unjoined",
            join_confidence=_first_non_none(
                payload.get("join_confidence"),
                payload.get("confidence"),
            ),
            coverage=tuple(
                item
                if isinstance(item, PlanningIndexCoverage)
                else PlanningIndexCoverage.from_dict(item)
                for item in _iter_values(
                    payload.get("coverage") or payload.get("coverage_slices") or ()
                )
            ),
            lazy_materialization_pointers=tuple(
                item
                if isinstance(item, PlanningIndexMaterializationPointer)
                else PlanningIndexMaterializationPointer.from_dict(item)
                for item in _iter_values(
                    payload.get("lazy_materialization_pointers")
                    or payload.get("lazy_materialization")
                    or payload.get("materialization_pointers")
                    or ()
                )
            ),
            metadata=payload.get("metadata") or payload.get("annotations") or {},
        )


@dataclass(frozen=True, slots=True)
class PlanningIndexSchema:
    """Root container for a rebuildable planning index."""

    records: tuple[PlanningIndexEntry, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        records: list[PlanningIndexEntry] = []
        seen_ids: set[str] = set()
        for record in self.records:
            if not isinstance(record, PlanningIndexEntry):
                raise TypeError("records must contain PlanningIndexEntry objects")
            if record.planning_id in seen_ids:
                raise ValueError(f"duplicate planning_id: {record.planning_id}")
            seen_ids.add(record.planning_id)
            records.append(record)
        object.__setattr__(self, "records", tuple(records))

    @property
    def record_count(self) -> int:
        return len(self.records)

    def get(self, planning_id: str) -> PlanningIndexEntry | None:
        target = _required_text(planning_id, "planning_id")
        for record in self.records:
            if record.planning_id == target:
                return record
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_count": self.record_count,
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanningIndexSchema:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            records=tuple(
                item if isinstance(item, PlanningIndexEntry) else PlanningIndexEntry.from_dict(item)
                for item in _iter_values(payload.get("records") or payload.get("entries") or ())
            ),
            schema_version=int(payload.get("schema_version") or 1),
        )


def validate_planning_index_payload(payload: Mapping[str, Any]) -> PlanningIndexSchema:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return PlanningIndexSchema.from_dict(payload)


__all__ = [
    "CoverageKind",
    "CoverageState",
    "JoinStatus",
    "MaterializationKind",
    "PlanningIndexCoverage",
    "PlanningIndexEntry",
    "PlanningIndexMaterializationPointer",
    "PlanningIndexSchema",
    "PlanningIndexSourceRecord",
    "validate_planning_index_payload",
]
