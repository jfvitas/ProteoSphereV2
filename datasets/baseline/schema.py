from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

BaselineEntityKind = Literal["protein", "structure", "ligand", "observation", "chain"]
BaselineLabelKind = Literal["continuous", "binary", "categorical", "ordinal", "missing"]

_ENTITY_KIND_ALIASES: dict[str, BaselineEntityKind] = {
    "protein": "protein",
    "target": "protein",
    "structure": "structure",
    "pdb": "structure",
    "ligand": "ligand",
    "compound": "ligand",
    "observation": "observation",
    "measurement": "observation",
    "chain": "chain",
}
_LABEL_KIND_ALIASES: dict[str, BaselineLabelKind] = {
    "continuous": "continuous",
    "regression": "continuous",
    "numeric": "continuous",
    "binary": "binary",
    "boolean": "binary",
    "categorical": "categorical",
    "class": "categorical",
    "ordinal": "ordinal",
    "missing": "missing",
}
_MODALITY_ALIASES: dict[str, str] = {
    "sequence": "sequence",
    "protein": "sequence",
    "structure": "structure",
    "pdb": "structure",
    "ligand": "ligand",
    "compound": "ligand",
    "affinity": "affinity",
    "assay": "affinity",
    "observation": "affinity",
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


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer or None")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer or None") from exc


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


def _normalize_json_value(value: Any, field_name: str) -> JSONValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
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


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _normalize_entity_kind(value: Any) -> BaselineEntityKind:
    text = _required_text(value, "entity_kind").replace("-", "_").replace(" ", "_").casefold()
    kind = _ENTITY_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported entity_kind: {value!r}")
    return kind


def _normalize_label_kind(value: Any) -> BaselineLabelKind:
    text = _required_text(value, "label_kind").replace("-", "_").replace(" ", "_").casefold()
    kind = _LABEL_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported label_kind: {value!r}")
    return kind


def _normalize_modality(value: Any) -> str:
    text = _required_text(value, "modality").replace("-", "_").replace(" ", "_").casefold()
    return _MODALITY_ALIASES.get(text, text)


@dataclass(frozen=True, slots=True)
class BaselineEntityRef:
    entity_kind: BaselineEntityKind
    canonical_id: str
    source_record_id: str | None = None
    join_status: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_kind", _normalize_entity_kind(self.entity_kind))
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "join_status", _optional_text(self.join_status))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_kind": self.entity_kind,
            "canonical_id": self.canonical_id,
            "source_record_id": self.source_record_id,
            "join_status": self.join_status,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BaselineEntityRef:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            entity_kind=payload.get("entity_kind") or payload.get("kind") or "",
            canonical_id=(
                payload.get("canonical_id")
                or payload.get("ref")
                or payload.get("id")
                or ""
            ),
            source_record_id=payload.get("source_record_id") or payload.get("record_id"),
            join_status=payload.get("join_status") or payload.get("status"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class BaselineFeaturePointer:
    modality: str
    pointer: str
    feature_family: str | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "modality", _normalize_modality(self.modality))
        object.__setattr__(self, "pointer", _required_text(self.pointer, "pointer"))
        object.__setattr__(self, "feature_family", _optional_text(self.feature_family))
        object.__setattr__(self, "source_name", _optional_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "modality": self.modality,
            "pointer": self.pointer,
            "feature_family": self.feature_family,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BaselineFeaturePointer:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            modality=(
                payload.get("modality")
                or payload.get("selector")
                or payload.get("feature_family")
                or ""
            ),
            pointer=payload.get("pointer") or payload.get("ref") or payload.get("path") or "",
            feature_family=payload.get("feature_family") or payload.get("family"),
            source_name=payload.get("source_name") or payload.get("source"),
            source_record_id=payload.get("source_record_id") or payload.get("record_id"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class BaselineLabel:
    label_name: str
    label_kind: BaselineLabelKind
    value: JSONValue = None
    unit: str | None = None
    qualifier: str | None = None
    source_record_id: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_name", _required_text(self.label_name, "label_name"))
        object.__setattr__(self, "label_kind", _normalize_label_kind(self.label_kind))
        object.__setattr__(self, "value", _normalize_json_value(self.value, "value"))
        object.__setattr__(self, "unit", _optional_text(self.unit))
        object.__setattr__(self, "qualifier", _optional_text(self.qualifier))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        if self.label_kind == "missing" and self.value is not None:
            raise ValueError("missing labels must not carry a value")

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_name": self.label_name,
            "label_kind": self.label_kind,
            "value": _json_ready(self.value),
            "unit": self.unit,
            "qualifier": self.qualifier,
            "source_record_id": self.source_record_id,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BaselineLabel:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            label_name=payload.get("label_name") or payload.get("name") or "",
            label_kind=payload.get("label_kind") or payload.get("kind") or "continuous",
            value=payload.get("value"),
            unit=payload.get("unit"),
            qualifier=payload.get("qualifier") or payload.get("relation"),
            source_record_id=payload.get("source_record_id") or payload.get("record_id"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class BaselineDatasetExample:
    example_id: str
    protein_ref: BaselineEntityRef
    feature_pointers: tuple[BaselineFeaturePointer, ...]
    structure_ref: BaselineEntityRef | None = None
    ligand_ref: BaselineEntityRef | None = None
    observation_ref: BaselineEntityRef | None = None
    labels: tuple[BaselineLabel, ...] = field(default_factory=tuple)
    source_lineage_refs: tuple[str, ...] = field(default_factory=tuple)
    split: str | None = None
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        if not isinstance(self.protein_ref, BaselineEntityRef):
            raise TypeError("protein_ref must be a BaselineEntityRef")
        if self.protein_ref.entity_kind != "protein":
            raise ValueError("protein_ref must have entity_kind='protein'")
        feature_pointers = tuple(self.feature_pointers)
        if not feature_pointers:
            raise ValueError("feature_pointers must contain at least one pointer")
        normalized_features: list[BaselineFeaturePointer] = []
        seen_feature_keys: set[tuple[str, str]] = set()
        for pointer in feature_pointers:
            if not isinstance(pointer, BaselineFeaturePointer):
                raise TypeError("feature_pointers must contain BaselineFeaturePointer objects")
            feature_key = (pointer.modality, pointer.pointer.casefold())
            if feature_key in seen_feature_keys:
                raise ValueError(f"duplicate feature pointer: {pointer.modality}:{pointer.pointer}")
            seen_feature_keys.add(feature_key)
            normalized_features.append(pointer)
        object.__setattr__(self, "feature_pointers", tuple(normalized_features))
        for field_name in ("structure_ref", "ligand_ref", "observation_ref"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, BaselineEntityRef):
                raise TypeError(f"{field_name} must be a BaselineEntityRef or None")
        labels = tuple(self.labels)
        for label in labels:
            if not isinstance(label, BaselineLabel):
                raise TypeError("labels must contain BaselineLabel objects")
        object.__setattr__(self, "labels", labels)
        object.__setattr__(
            self,
            "source_lineage_refs",
            _normalize_text_tuple(self.source_lineage_refs),
        )
        object.__setattr__(self, "split", _optional_text(self.split))
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    @property
    def feature_modalities(self) -> tuple[str, ...]:
        return _normalize_text_tuple(pointer.modality for pointer in self.feature_pointers)

    @property
    def lineage_complete(self) -> bool:
        return bool(self.source_lineage_refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "protein_ref": self.protein_ref.to_dict(),
            "structure_ref": self.structure_ref.to_dict() if self.structure_ref else None,
            "ligand_ref": self.ligand_ref.to_dict() if self.ligand_ref else None,
            "observation_ref": self.observation_ref.to_dict() if self.observation_ref else None,
            "feature_pointers": [pointer.to_dict() for pointer in self.feature_pointers],
            "labels": [label.to_dict() for label in self.labels],
            "source_lineage_refs": list(self.source_lineage_refs),
            "split": self.split,
            "metadata": _json_ready(dict(self.metadata)),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BaselineDatasetExample:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            example_id=payload.get("example_id") or payload.get("id") or "",
            protein_ref=BaselineEntityRef.from_dict(payload.get("protein_ref") or {}),
            structure_ref=(
                BaselineEntityRef.from_dict(payload["structure_ref"])
                if isinstance(payload.get("structure_ref"), Mapping)
                else None
            ),
            ligand_ref=(
                BaselineEntityRef.from_dict(payload["ligand_ref"])
                if isinstance(payload.get("ligand_ref"), Mapping)
                else None
            ),
            observation_ref=(
                BaselineEntityRef.from_dict(payload["observation_ref"])
                if isinstance(payload.get("observation_ref"), Mapping)
                else None
            ),
            feature_pointers=tuple(
                BaselineFeaturePointer.from_dict(item)
                for item in _iter_values(payload.get("feature_pointers") or payload.get("features"))
            ),
            labels=tuple(
                BaselineLabel.from_dict(item)
                for item in _iter_values(payload.get("labels") or payload.get("targets"))
            ),
            source_lineage_refs=(
                payload.get("source_lineage_refs")
                or payload.get("lineage_refs")
                or ()
            ),
            split=payload.get("split"),
            metadata=payload.get("metadata") or {},
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class BaselineDatasetSchema:
    dataset_id: str
    schema_version: int = 1
    examples: tuple[BaselineDatasetExample, ...] = field(default_factory=tuple)
    requested_modalities: tuple[str, ...] = field(default_factory=tuple)
    package_id: str | None = None
    package_state: str | None = None
    created_at: str | None = None
    source_packages: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_id", _required_text(self.dataset_id, "dataset_id"))
        schema_version = _normalize_int(self.schema_version, "schema_version")
        if schema_version is None or schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        object.__setattr__(self, "schema_version", schema_version)
        normalized_examples: list[BaselineDatasetExample] = []
        seen_example_ids: set[str] = set()
        for example in self.examples:
            if not isinstance(example, BaselineDatasetExample):
                raise TypeError("examples must contain BaselineDatasetExample objects")
            example_key = example.example_id.casefold()
            if example_key in seen_example_ids:
                raise ValueError(f"duplicate example_id: {example.example_id}")
            seen_example_ids.add(example_key)
            normalized_examples.append(example)
        object.__setattr__(self, "examples", tuple(normalized_examples))
        requested_modalities = tuple(
            _normalize_modality(item) for item in _iter_values(self.requested_modalities)
        )
        object.__setattr__(
            self,
            "requested_modalities",
            _normalize_text_tuple(requested_modalities),
        )
        object.__setattr__(self, "package_id", _optional_text(self.package_id))
        object.__setattr__(self, "package_state", _optional_text(self.package_state))
        object.__setattr__(self, "created_at", _normalize_timestamp(self.created_at))
        object.__setattr__(self, "source_packages", _normalize_text_tuple(self.source_packages))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))

    @property
    def example_count(self) -> int:
        return len(self.examples)

    @property
    def lineage_complete_example_count(self) -> int:
        return sum(1 for example in self.examples if example.lineage_complete)

    @property
    def available_modalities(self) -> tuple[str, ...]:
        return _normalize_text_tuple(
            modality
            for example in self.examples
            for modality in example.feature_modalities
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "schema_version": self.schema_version,
            "examples": [example.to_dict() for example in self.examples],
            "requested_modalities": list(self.requested_modalities),
            "package_id": self.package_id,
            "package_state": self.package_state,
            "created_at": self.created_at,
            "source_packages": list(self.source_packages),
            "notes": list(self.notes),
            "metadata": _json_ready(dict(self.metadata)),
            "example_count": self.example_count,
            "lineage_complete_example_count": self.lineage_complete_example_count,
            "available_modalities": list(self.available_modalities),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BaselineDatasetSchema:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            dataset_id=(
                payload.get("dataset_id")
                or payload.get("package_id")
                or payload.get("id")
                or ""
            ),
            schema_version=payload.get("schema_version", 1),
            examples=tuple(
                BaselineDatasetExample.from_dict(item)
                for item in _iter_values(payload.get("examples"))
            ),
            requested_modalities=(
                payload.get("requested_modalities")
                or payload.get("modalities")
                or ()
            ),
            package_id=payload.get("package_id"),
            package_state=payload.get("package_state") or payload.get("state"),
            created_at=payload.get("created_at"),
            source_packages=payload.get("source_packages") or payload.get("package_refs") or (),
            notes=payload.get("notes") or payload.get("note") or (),
            metadata=payload.get("metadata") or {},
        )


__all__ = [
    "BaselineDatasetExample",
    "BaselineDatasetSchema",
    "BaselineEntityRef",
    "BaselineFeaturePointer",
    "BaselineLabel",
]
