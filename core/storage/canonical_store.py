from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import quote

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

CanonicalEntityKind = Literal[
    "protein",
    "ligand",
    "assay",
    "sequence",
    "structure",
    "interaction",
    "feature",
    "embedding",
    "other",
]
ArtifactKind = Literal[
    "structure",
    "coordinates",
    "map",
    "sequence",
    "feature",
    "embedding",
    "table",
    "bundle",
    "other",
]

_ENTITY_KIND_ALIASES: dict[str, CanonicalEntityKind] = {
    "protein": "protein",
    "proteins": "protein",
    "ligand": "ligand",
    "ligands": "ligand",
    "assay": "assay",
    "assays": "assay",
    "sequence": "sequence",
    "sequences": "sequence",
    "structure": "structure",
    "structures": "structure",
    "interaction": "interaction",
    "interactions": "interaction",
    "feature": "feature",
    "features": "feature",
    "embedding": "embedding",
    "embeddings": "embedding",
    "other": "other",
}
_ARTIFACT_KIND_ALIASES: dict[str, ArtifactKind] = {
    "structure": "structure",
    "structures": "structure",
    "pdb": "structure",
    "mmcif": "structure",
    "cif": "structure",
    "bcif": "structure",
    "coordinates": "coordinates",
    "coordinate": "coordinates",
    "map": "map",
    "sequence": "sequence",
    "feature": "feature",
    "features": "feature",
    "embedding": "embedding",
    "embeddings": "embedding",
    "table": "table",
    "rows": "table",
    "bundle": "bundle",
    "package": "bundle",
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


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _coerce_nested_items(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, (str, bytes)):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)
    return (value,)


def _payload_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


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


def _normalize_entity_kind(value: Any) -> CanonicalEntityKind:
    text = _required_text(value, "entity_kind").replace("-", "_").replace(" ", "_").casefold()
    kind = _ENTITY_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported entity_kind: {value!r}")
    return kind


def _normalize_artifact_kind(value: Any) -> ArtifactKind:
    text = _required_text(value, "artifact_kind").replace("-", "_").replace(" ", "_").casefold()
    kind = _ARTIFACT_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported artifact_kind: {value!r}")
    return kind


def _encode_storage_segment(value: str) -> str:
    return quote(_required_text(value, "storage_segment"), safe="-_.~/")


def _normalize_key_tuple(values: Any) -> tuple[str, ...]:
    return _dedupe_text(values)


@dataclass(frozen=True, slots=True)
class CanonicalStoreSourceRef:
    source_name: str
    source_record_id: str
    source_manifest_id: str | None = None
    planning_index_ref: str | None = None
    package_id: str | None = None
    source_locator: str | None = None
    source_keys: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _required_text(self.source_name, "source_name"))
        object.__setattr__(
            self,
            "source_record_id",
            _required_text(self.source_record_id, "source_record_id"),
        )
        object.__setattr__(self, "source_manifest_id", _optional_text(self.source_manifest_id))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "package_id", _optional_text(self.package_id))
        object.__setattr__(self, "source_locator", _optional_text(self.source_locator))
        object.__setattr__(
            self,
            "source_keys",
            _normalize_json_mapping(self.source_keys, "source_keys"),
        )

    @property
    def storage_key(self) -> str:
        return (
            f"sources/{_encode_storage_segment(self.source_name)}/"
            f"{_encode_storage_segment(self.source_record_id)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "source_manifest_id": self.source_manifest_id,
            "planning_index_ref": self.planning_index_ref,
            "package_id": self.package_id,
            "source_locator": self.source_locator,
            "source_keys": _json_ready(dict(self.source_keys)),
            "storage_key": self.storage_key,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CanonicalStoreSourceRef:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=payload.get("source_name") or payload.get("source") or "",
            source_record_id=payload.get("source_record_id")
            or payload.get("record_id")
            or payload.get("identifier")
            or payload.get("accession")
            or "",
            source_manifest_id=payload.get("source_manifest_id")
            or payload.get("manifest_id")
            or payload.get("release_manifest_id"),
            planning_index_ref=payload.get("planning_index_ref")
            or payload.get("planning_ref")
            or payload.get("planning_id"),
            package_id=payload.get("package_id") or payload.get("package"),
            source_locator=payload.get("source_locator")
            or payload.get("source_url")
            or payload.get("url"),
            source_keys=payload.get("source_keys") or payload.get("keys") or {},
        )


@dataclass(frozen=True, slots=True)
class CanonicalStoreArtifactPointer:
    artifact_kind: ArtifactKind
    pointer: str
    selector: str | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    canonical_id: str | None = None
    planning_index_ref: str | None = None
    package_id: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_kind", _normalize_artifact_kind(self.artifact_kind))
        object.__setattr__(self, "pointer", _required_text(self.pointer, "pointer"))
        object.__setattr__(self, "selector", _optional_text(self.selector))
        object.__setattr__(self, "source_name", _optional_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "canonical_id", _optional_text(self.canonical_id))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "package_id", _optional_text(self.package_id))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def storage_key(self) -> str:
        return (
            f"artifacts/{self.artifact_kind}/"
            f"{quote(self.pointer, safe='-_.~/')}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "pointer": self.pointer,
            "selector": self.selector,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "canonical_id": self.canonical_id,
            "planning_index_ref": self.planning_index_ref,
            "package_id": self.package_id,
            "notes": list(self.notes),
            "storage_key": self.storage_key,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CanonicalStoreArtifactPointer:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            artifact_kind=payload.get("artifact_kind")
            or payload.get("kind")
            or payload.get("asset_kind")
            or "other",
            pointer=payload.get("pointer") or payload.get("uri") or payload.get("path") or "",
            selector=payload.get("selector") or payload.get("selection"),
            source_name=payload.get("source_name") or payload.get("source"),
            source_record_id=payload.get("source_record_id")
            or payload.get("record_id")
            or payload.get("identifier"),
            canonical_id=payload.get("canonical_id") or payload.get("id"),
            planning_index_ref=payload.get("planning_index_ref")
            or payload.get("planning_ref")
            or payload.get("planning_id"),
            package_id=payload.get("package_id") or payload.get("package"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class CanonicalStoreRecord:
    canonical_id: str
    entity_kind: CanonicalEntityKind
    canonical_payload: Mapping[str, JSONValue] = field(default_factory=dict)
    source_refs: tuple[CanonicalStoreSourceRef, ...] = field(default_factory=tuple)
    planning_index_refs: tuple[str, ...] = field(default_factory=tuple)
    package_ids: tuple[str, ...] = field(default_factory=tuple)
    artifact_pointers: tuple[CanonicalStoreArtifactPointer, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        object.__setattr__(self, "entity_kind", _normalize_entity_kind(self.entity_kind))
        object.__setattr__(
            self,
            "canonical_payload",
            _normalize_json_mapping(self.canonical_payload, "canonical_payload"),
        )

        source_refs: list[CanonicalStoreSourceRef] = []
        seen_source_refs: set[tuple[str, str, str | None, str | None, str | None]] = set()
        for item in self.source_refs:
            if not isinstance(item, CanonicalStoreSourceRef):
                raise TypeError("source_refs must contain CanonicalStoreSourceRef objects")
            signature = (
                item.source_name,
                item.source_record_id,
                item.source_manifest_id,
                item.planning_index_ref,
                item.package_id,
            )
            if signature in seen_source_refs:
                continue
            seen_source_refs.add(signature)
            source_refs.append(item)
        object.__setattr__(self, "source_refs", tuple(source_refs))

        object.__setattr__(
            self,
            "planning_index_refs",
            _normalize_key_tuple(self.planning_index_refs),
        )
        object.__setattr__(self, "package_ids", _normalize_key_tuple(self.package_ids))
        object.__setattr__(self, "aliases", _normalize_key_tuple(self.aliases))
        object.__setattr__(self, "provenance_refs", _normalize_key_tuple(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

        pointers: list[CanonicalStoreArtifactPointer] = []
        seen_pointers: set[tuple[str, str, str | None, str | None, str | None, str | None]] = set()
        for item in self.artifact_pointers:
            if not isinstance(item, CanonicalStoreArtifactPointer):
                raise TypeError(
                    "artifact_pointers must contain CanonicalStoreArtifactPointer objects"
                )
            signature = (
                item.artifact_kind,
                item.pointer,
                item.selector,
                item.source_name,
                item.source_record_id,
                item.package_id,
            )
            if signature in seen_pointers:
                continue
            seen_pointers.add(signature)
            pointers.append(item)
        object.__setattr__(self, "artifact_pointers", tuple(pointers))

    @property
    def storage_key(self) -> str:
        return f"canonical/{self.entity_kind}/{quote(self.canonical_id, safe='-_.~')}"

    @property
    def source_manifest_ids(self) -> tuple[str, ...]:
        return tuple(
            ref.source_manifest_id
            for ref in self.source_refs
            if ref.source_manifest_id is not None
        )

    @property
    def source_names(self) -> tuple[str, ...]:
        return tuple(ref.source_name for ref in self.source_refs)

    @property
    def source_record_ids(self) -> tuple[str, ...]:
        return tuple(ref.source_record_id for ref in self.source_refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "entity_kind": self.entity_kind,
            "storage_key": self.storage_key,
            "canonical_payload": _json_ready(dict(self.canonical_payload)),
            "source_refs": [ref.to_dict() for ref in self.source_refs],
            "source_manifest_ids": list(self.source_manifest_ids),
            "source_names": list(self.source_names),
            "source_record_ids": list(self.source_record_ids),
            "planning_index_refs": list(self.planning_index_refs),
            "package_ids": list(self.package_ids),
            "artifact_pointers": [item.to_dict() for item in self.artifact_pointers],
            "aliases": list(self.aliases),
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CanonicalStoreRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        canonical_payload = _payload_value(
            payload,
            "canonical_payload",
            "payload",
            "record",
        )
        if canonical_payload is None:
            canonical_payload = {}
        return cls(
            canonical_id=_payload_value(payload, "canonical_id", "canonical_record_id", "id")
            or "",
            entity_kind=_payload_value(payload, "entity_kind", "kind", "record_kind")
            or "other",
            canonical_payload=canonical_payload,
            source_refs=tuple(
                item
                if isinstance(item, CanonicalStoreSourceRef)
                else CanonicalStoreSourceRef.from_dict(item)
                for item in _coerce_nested_items(
                    _payload_value(payload, "source_refs", "sources", "source_records")
                )
            ),
            planning_index_refs=_payload_value(
                payload,
                "planning_index_refs",
                "planning_refs",
                "planning_ids",
            )
            or (),
            package_ids=_payload_value(payload, "package_ids", "packages", "package_refs")
            or (),
            artifact_pointers=tuple(
                item
                if isinstance(item, CanonicalStoreArtifactPointer)
                else CanonicalStoreArtifactPointer.from_dict(item)
                for item in _coerce_nested_items(
                    _payload_value(
                        payload,
                        "artifact_pointers",
                        "artifacts",
                        "materialization_pointers",
                    )
                )
            ),
            aliases=_payload_value(payload, "aliases", "alternative_ids") or (),
            provenance_refs=_payload_value(payload, "provenance_refs", "provenance", "lineage_refs")
            or (),
            notes=_payload_value(payload, "notes", "note") or (),
        )


@dataclass(frozen=True, slots=True)
class CanonicalStore:
    records: tuple[CanonicalStoreRecord, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        records: list[CanonicalStoreRecord] = []
        seen_ids: set[str] = set()
        for record in self.records:
            if not isinstance(record, CanonicalStoreRecord):
                raise TypeError("records must contain CanonicalStoreRecord objects")
            if record.canonical_id in seen_ids:
                raise ValueError(f"duplicate canonical_id: {record.canonical_id}")
            seen_ids.add(record.canonical_id)
            records.append(record)
        if not records:
            raise ValueError("records must not be empty")
        object.__setattr__(self, "records", tuple(records))

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def canonical_ids(self) -> tuple[str, ...]:
        return tuple(record.canonical_id for record in self.records)

    def get(self, canonical_id: str) -> CanonicalStoreRecord | None:
        target = _required_text(canonical_id, "canonical_id")
        for record in self.records:
            if record.canonical_id == target:
                return record
        return None

    def get_by_storage_key(self, storage_key: str) -> CanonicalStoreRecord | None:
        target = _required_text(storage_key, "storage_key")
        for record in self.records:
            if record.storage_key == target:
                return record
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_count": self.record_count,
            "canonical_ids": list(self.canonical_ids),
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CanonicalStore:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        records_value = _payload_value(payload, "records", "entries")
        if records_value is None:
            records_value = ()
        return cls(
            records=tuple(
                item
                if isinstance(item, CanonicalStoreRecord)
                else CanonicalStoreRecord.from_dict(item)
                for item in _coerce_nested_items(records_value)
            ),
            schema_version=int(_payload_value(payload, "schema_version") or 1),
        )


def validate_canonical_store_payload(payload: Mapping[str, Any]) -> CanonicalStore:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return CanonicalStore.from_dict(payload)


__all__ = [
    "ArtifactKind",
    "CanonicalEntityKind",
    "CanonicalStore",
    "CanonicalStoreArtifactPointer",
    "CanonicalStoreRecord",
    "CanonicalStoreSourceRef",
    "validate_canonical_store_payload",
]
