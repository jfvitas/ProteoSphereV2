from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

ReleaseRecordType = Literal["protein", "protein_protein", "protein_ligand", "packet"]
ReleaseInclusionStatus = Literal["included", "excluded", "candidate", "deferred"]
ReleaseFreezeState = Literal["draft", "frozen", "superseded"]

_RECORD_TYPES: frozenset[str] = frozenset(
    {"protein", "protein_protein", "protein_ligand", "packet"}
)
_INCLUSION_STATUSES: frozenset[str] = frozenset(
    {"included", "excluded", "candidate", "deferred"}
)
_FREEZE_STATES: frozenset[str] = frozenset({"draft", "frozen", "superseded"})


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


def _normalize_text_tuple(values: Iterable[Any] | None) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values or ():
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_bool_or_none(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool or None")
    return value


def _normalize_int_or_none(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or None")
    return value


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


def _json_ready(value: JSONValue) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _normalize_record_type(value: Any) -> ReleaseRecordType:
    normalized = _required_text(value, "record_type").replace("-", "_").replace(" ", "_")
    lowered = normalized.casefold()
    if lowered not in _RECORD_TYPES:
        raise ValueError(f"unsupported record_type: {value!r}")
    return lowered  # type: ignore[return-value]


def _normalize_inclusion_status(value: Any) -> ReleaseInclusionStatus:
    normalized = _required_text(value, "inclusion_status").replace("-", "_").replace(" ", "_")
    lowered = normalized.casefold()
    if lowered not in _INCLUSION_STATUSES:
        raise ValueError(f"unsupported inclusion_status: {value!r}")
    return lowered  # type: ignore[return-value]


def _normalize_freeze_state(value: Any) -> ReleaseFreezeState:
    normalized = _required_text(value, "freeze_state").replace("-", "_").replace(" ", "_")
    lowered = normalized.casefold()
    if lowered not in _FREEZE_STATES:
        raise ValueError(f"unsupported freeze_state: {value!r}")
    return lowered  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ReleaseCohortEntry:
    canonical_id: str
    record_type: ReleaseRecordType
    inclusion_status: ReleaseInclusionStatus = "candidate"
    freeze_state: ReleaseFreezeState = "draft"
    inclusion_reason: str = ""
    exclusion_reason: str | None = None
    blocker_ids: tuple[str, ...] = ()
    evidence_lanes: tuple[str, ...] = ()
    source_manifest_ids: tuple[str, ...] = ()
    packet_ready: bool | None = None
    benchmark_priority: int | None = None
    leakage_key: str | None = None
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        object.__setattr__(self, "record_type", _normalize_record_type(self.record_type))
        object.__setattr__(
            self,
            "inclusion_status",
            _normalize_inclusion_status(self.inclusion_status),
        )
        object.__setattr__(self, "freeze_state", _normalize_freeze_state(self.freeze_state))
        object.__setattr__(self, "inclusion_reason", _clean_text(self.inclusion_reason))
        object.__setattr__(self, "exclusion_reason", _optional_text(self.exclusion_reason))
        object.__setattr__(self, "blocker_ids", _normalize_text_tuple(self.blocker_ids))
        object.__setattr__(self, "evidence_lanes", _normalize_text_tuple(self.evidence_lanes))
        object.__setattr__(
            self,
            "source_manifest_ids",
            _normalize_text_tuple(self.source_manifest_ids),
        )
        object.__setattr__(
            self,
            "packet_ready",
            _normalize_bool_or_none(self.packet_ready, "packet_ready"),
        )
        object.__setattr__(
            self,
            "benchmark_priority",
            _normalize_int_or_none(self.benchmark_priority, "benchmark_priority"),
        )
        object.__setattr__(self, "leakage_key", _optional_text(self.leakage_key))
        object.__setattr__(self, "tags", _normalize_text_tuple(self.tags))
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))

        if self.inclusion_status == "included" and not self.inclusion_reason:
            raise ValueError("included release cohort entries require an inclusion_reason")
        if self.inclusion_status == "excluded" and not self.exclusion_reason:
            raise ValueError("excluded release cohort entries require an exclusion_reason")

    @property
    def is_included(self) -> bool:
        return self.inclusion_status == "included"

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocker_ids)

    @property
    def release_ready(self) -> bool:
        return self.is_included and self.freeze_state == "frozen" and not self.is_blocked

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_id": self.canonical_id,
            "record_type": self.record_type,
            "inclusion_status": self.inclusion_status,
            "freeze_state": self.freeze_state,
            "inclusion_reason": self.inclusion_reason,
            "exclusion_reason": self.exclusion_reason,
            "blocker_ids": list(self.blocker_ids),
            "evidence_lanes": list(self.evidence_lanes),
            "source_manifest_ids": list(self.source_manifest_ids),
            "packet_ready": self.packet_ready,
            "benchmark_priority": self.benchmark_priority,
            "leakage_key": self.leakage_key,
            "tags": list(self.tags),
            "metadata": _json_ready(dict(self.metadata)),
            "release_ready": self.release_ready,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReleaseCohortEntry:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            canonical_id=payload.get("canonical_id") or payload.get("id") or "",
            record_type=payload.get("record_type") or payload.get("type") or "protein",
            inclusion_status=(
                payload.get("inclusion_status") or payload.get("status") or "candidate"
            ),
            freeze_state=payload.get("freeze_state") or "draft",
            inclusion_reason=payload.get("inclusion_reason") or payload.get("reason") or "",
            exclusion_reason=payload.get("exclusion_reason"),
            blocker_ids=payload.get("blocker_ids") or payload.get("blockers") or (),
            evidence_lanes=payload.get("evidence_lanes") or (),
            source_manifest_ids=payload.get("source_manifest_ids") or (),
            packet_ready=payload.get("packet_ready"),
            benchmark_priority=payload.get("benchmark_priority"),
            leakage_key=payload.get("leakage_key"),
            tags=payload.get("tags") or (),
            metadata=payload.get("metadata"),
        )


@dataclass(frozen=True, slots=True)
class ReleaseCohortRegistry:
    registry_id: str
    release_version: str
    freeze_state: ReleaseFreezeState = "draft"
    entries: tuple[ReleaseCohortEntry, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_id", _required_text(self.registry_id, "registry_id"))
        object.__setattr__(
            self,
            "release_version",
            _required_text(self.release_version, "release_version"),
        )
        object.__setattr__(self, "freeze_state", _normalize_freeze_state(self.freeze_state))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        normalized_entries = [
            entry if isinstance(entry, ReleaseCohortEntry) else ReleaseCohortEntry.from_dict(entry)
            for entry in self.entries
        ]
        normalized_entries.sort(key=lambda entry: entry.canonical_id.casefold())
        seen_ids: set[str] = set()
        for entry in normalized_entries:
            if entry.canonical_id.casefold() in seen_ids:
                raise ValueError(f"duplicate release cohort entry: {entry.canonical_id}")
            seen_ids.add(entry.canonical_id.casefold())
        object.__setattr__(self, "entries", tuple(normalized_entries))

    @property
    def included_entries(self) -> tuple[ReleaseCohortEntry, ...]:
        return tuple(entry for entry in self.entries if entry.is_included)

    @property
    def excluded_entries(self) -> tuple[ReleaseCohortEntry, ...]:
        return tuple(entry for entry in self.entries if entry.inclusion_status == "excluded")

    @property
    def pending_entries(self) -> tuple[ReleaseCohortEntry, ...]:
        return tuple(
            entry
            for entry in self.entries
            if entry.inclusion_status in {"candidate", "deferred"}
        )

    @property
    def blocked_entries(self) -> tuple[ReleaseCohortEntry, ...]:
        return tuple(entry for entry in self.entries if entry.is_blocked)

    @property
    def release_ready_entries(self) -> tuple[ReleaseCohortEntry, ...]:
        return tuple(entry for entry in self.entries if entry.release_ready)

    @property
    def included_canonical_ids(self) -> tuple[str, ...]:
        return tuple(entry.canonical_id for entry in self.included_entries)

    def get(self, canonical_id: str) -> ReleaseCohortEntry | None:
        normalized = _clean_text(canonical_id).casefold()
        if not normalized:
            return None
        for entry in self.entries:
            if entry.canonical_id.casefold() == normalized:
                return entry
        return None

    def require(self, canonical_id: str) -> ReleaseCohortEntry:
        entry = self.get(canonical_id)
        if entry is None:
            raise KeyError(f"unknown release cohort entry: {canonical_id!r}")
        return entry

    def to_dict(self) -> dict[str, object]:
        return {
            "registry_id": self.registry_id,
            "release_version": self.release_version,
            "freeze_state": self.freeze_state,
            "notes": list(self.notes),
            "entry_count": len(self.entries),
            "included_count": len(self.included_entries),
            "excluded_count": len(self.excluded_entries),
            "pending_count": len(self.pending_entries),
            "blocked_count": len(self.blocked_entries),
            "release_ready_count": len(self.release_ready_entries),
            "included_canonical_ids": list(self.included_canonical_ids),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReleaseCohortRegistry:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            registry_id=payload.get("registry_id") or payload.get("id") or "",
            release_version=payload.get("release_version") or payload.get("version") or "",
            freeze_state=payload.get("freeze_state") or "draft",
            entries=tuple(payload.get("entries") or ()),
            notes=payload.get("notes") or (),
        )


__all__ = [
    "ReleaseCohortEntry",
    "ReleaseCohortRegistry",
    "ReleaseFreezeState",
    "ReleaseInclusionStatus",
    "ReleaseRecordType",
]
