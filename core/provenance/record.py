from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]
AcquisitionMode = Literal["api", "bulk_download", "manual_curated", "derived"]

_ACQUISITION_MODES: frozenset[str] = frozenset(
    {"api", "bulk_download", "manual_curated", "derived"}
)


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


def _normalize_string_mapping(value: Mapping[str, Any] | None, field_name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized_item = _required_text(item, f"{field_name}[{normalized_key!r}]")
        normalized[normalized_key] = normalized_item
    return normalized


def _normalize_int_mapping(value: Mapping[str, Any] | None, field_name: str) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, int] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        if isinstance(item, bool) or not isinstance(item, int):
            raise TypeError(f"{field_name}[{normalized_key!r}] must be an integer")
        normalized[normalized_key] = item
    return normalized


def _normalize_acquisition_mode(value: Any) -> AcquisitionMode:
    text = _required_text(value, "acquisition_mode").replace("-", "_").replace(" ", "_")
    normalized = text.casefold()
    if normalized not in _ACQUISITION_MODES:
        raise ValueError(f"unsupported acquisition_mode: {value!r}")
    return normalized  # type: ignore[return-value]


def _normalize_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("confidence must be numeric or None")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
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


def _json_ready(value: JSONValue) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class ProvenanceSource:
    source_name: str
    acquisition_mode: AcquisitionMode
    original_identifier: str | None = None
    release_version: str | None = None
    snapshot_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _required_text(self.source_name, "source_name"))
        object.__setattr__(
            self,
            "acquisition_mode",
            _normalize_acquisition_mode(self.acquisition_mode),
        )
        object.__setattr__(self, "original_identifier", _optional_text(self.original_identifier))
        object.__setattr__(self, "release_version", _optional_text(self.release_version))
        object.__setattr__(self, "snapshot_id", _optional_text(self.snapshot_id))

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "acquisition_mode": self.acquisition_mode,
            "original_identifier": self.original_identifier,
            "release_version": self.release_version,
            "snapshot_id": self.snapshot_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProvenanceSource:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=payload.get("source_name") or payload.get("source") or "",
            acquisition_mode=payload.get("acquisition_mode") or "derived",
            original_identifier=payload.get("original_identifier"),
            release_version=payload.get("release_version")
            or payload.get("source_version"),
            snapshot_id=payload.get("snapshot_id"),
        )


@dataclass(frozen=True, slots=True)
class ReproducibilityMetadata:
    config_snapshot_id: str | None = None
    code_version: str | None = None
    source_bundle_hash: str | None = None
    environment_summary: Mapping[str, JSONValue] = field(default_factory=dict)
    library_versions: Mapping[str, str] = field(default_factory=dict)
    hardware_summary: Mapping[str, JSONValue] = field(default_factory=dict)
    rng_seeds: Mapping[str, int] = field(default_factory=dict)
    dataset_version_ids: tuple[str, ...] = field(default_factory=tuple)
    split_artifact_id: str | None = None
    feature_schema_version: str | None = None
    model_schema_version: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "config_snapshot_id", _optional_text(self.config_snapshot_id))
        object.__setattr__(self, "code_version", _optional_text(self.code_version))
        object.__setattr__(self, "source_bundle_hash", _optional_text(self.source_bundle_hash))
        object.__setattr__(
            self,
            "environment_summary",
            _normalize_json_mapping(self.environment_summary, "environment_summary"),
        )
        object.__setattr__(
            self,
            "library_versions",
            _normalize_string_mapping(self.library_versions, "library_versions"),
        )
        object.__setattr__(
            self,
            "hardware_summary",
            _normalize_json_mapping(self.hardware_summary, "hardware_summary"),
        )
        object.__setattr__(self, "rng_seeds", _normalize_int_mapping(self.rng_seeds, "rng_seeds"))
        object.__setattr__(
            self,
            "dataset_version_ids",
            _normalize_text_tuple(self.dataset_version_ids),
        )
        object.__setattr__(self, "split_artifact_id", _optional_text(self.split_artifact_id))
        object.__setattr__(
            self,
            "feature_schema_version",
            _optional_text(self.feature_schema_version),
        )
        object.__setattr__(self, "model_schema_version", _optional_text(self.model_schema_version))

    def to_dict(self) -> dict[str, object]:
        return {
            "config_snapshot_id": self.config_snapshot_id,
            "code_version": self.code_version,
            "source_bundle_hash": self.source_bundle_hash,
            "environment_summary": _json_ready(dict(self.environment_summary)),
            "library_versions": deepcopy(dict(self.library_versions)),
            "hardware_summary": _json_ready(dict(self.hardware_summary)),
            "rng_seeds": deepcopy(dict(self.rng_seeds)),
            "dataset_version_ids": list(self.dataset_version_ids),
            "split_artifact_id": self.split_artifact_id,
            "feature_schema_version": self.feature_schema_version,
            "model_schema_version": self.model_schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> ReproducibilityMetadata:
        if payload is None:
            return cls()
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            config_snapshot_id=payload.get("config_snapshot_id"),
            code_version=payload.get("code_version"),
            source_bundle_hash=payload.get("source_bundle_hash"),
            environment_summary=payload.get("environment_summary"),
            library_versions=payload.get("library_versions"),
            hardware_summary=payload.get("hardware_summary"),
            rng_seeds=payload.get("rng_seeds"),
            dataset_version_ids=tuple(payload.get("dataset_version_ids") or ()),
            split_artifact_id=payload.get("split_artifact_id"),
            feature_schema_version=payload.get("feature_schema_version"),
            model_schema_version=payload.get("model_schema_version"),
        )


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    provenance_id: str
    source: ProvenanceSource
    transformation_step: str
    acquired_at: str | None = None
    parser_version: str | None = None
    transformation_history: tuple[str, ...] = field(default_factory=tuple)
    parent_ids: tuple[str, ...] = field(default_factory=tuple)
    child_ids: tuple[str, ...] = field(default_factory=tuple)
    run_id: str | None = None
    confidence: float | None = None
    checksum: str | None = None
    raw_payload_pointer: str | None = None
    reproducibility: ReproducibilityMetadata = field(default_factory=ReproducibilityMetadata)
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provenance_id",
            _required_text(self.provenance_id, "provenance_id"),
        )
        if not isinstance(self.source, ProvenanceSource):
            raise TypeError("source must be a ProvenanceSource")
        object.__setattr__(
            self,
            "transformation_step",
            _required_text(self.transformation_step, "transformation_step"),
        )
        object.__setattr__(self, "acquired_at", _optional_text(self.acquired_at))
        object.__setattr__(self, "parser_version", _optional_text(self.parser_version))
        object.__setattr__(
            self,
            "transformation_history",
            _normalize_text_tuple(self.transformation_history),
        )
        object.__setattr__(self, "parent_ids", _normalize_text_tuple(self.parent_ids))
        object.__setattr__(self, "child_ids", _normalize_text_tuple(self.child_ids))
        object.__setattr__(self, "run_id", _optional_text(self.run_id))
        object.__setattr__(self, "confidence", _normalize_confidence(self.confidence))
        object.__setattr__(self, "checksum", _optional_text(self.checksum))
        object.__setattr__(self, "raw_payload_pointer", _optional_text(self.raw_payload_pointer))
        if not isinstance(self.reproducibility, ReproducibilityMetadata):
            raise TypeError("reproducibility must be ReproducibilityMetadata")
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "provenance_id": self.provenance_id,
            "source": self.source.to_dict(),
            "transformation_step": self.transformation_step,
            "acquired_at": self.acquired_at,
            "parser_version": self.parser_version,
            "transformation_history": list(self.transformation_history),
            "parent_ids": list(self.parent_ids),
            "child_ids": list(self.child_ids),
            "run_id": self.run_id,
            "confidence": self.confidence,
            "checksum": self.checksum,
            "raw_payload_pointer": self.raw_payload_pointer,
            "reproducibility": self.reproducibility.to_dict(),
            "metadata": _json_ready(dict(self.metadata)),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProvenanceRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            provenance_id=payload.get("provenance_id") or "",
            source=ProvenanceSource.from_dict(payload.get("source") or {}),
            transformation_step=payload.get("transformation_step") or "",
            acquired_at=payload.get("acquired_at"),
            parser_version=payload.get("parser_version"),
            transformation_history=tuple(payload.get("transformation_history") or ()),
            parent_ids=tuple(payload.get("parent_ids") or ()),
            child_ids=tuple(payload.get("child_ids") or ()),
            run_id=payload.get("run_id"),
            confidence=payload.get("confidence"),
            checksum=payload.get("checksum"),
            raw_payload_pointer=payload.get("raw_payload_pointer"),
            reproducibility=ReproducibilityMetadata.from_dict(payload.get("reproducibility")),
            metadata=payload.get("metadata"),
            schema_version=int(payload.get("schema_version") or 1),
        )

    def with_child(self, child_provenance_id: str) -> ProvenanceRecord:
        normalized_child_id = _required_text(child_provenance_id, "child_provenance_id")
        return replace(
            self,
            child_ids=_normalize_text_tuple((*self.child_ids, normalized_child_id)),
        )

    def spawn_child(
        self,
        *,
        provenance_id: str,
        transformation_step: str,
        acquired_at: str | None = None,
        parser_version: str | None = None,
        run_id: str | None = None,
        confidence: float | None = None,
        checksum: str | None = None,
        raw_payload_pointer: str | None = None,
        reproducibility: ReproducibilityMetadata | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProvenanceRecord:
        return ProvenanceRecord(
            provenance_id=provenance_id,
            source=self.source,
            transformation_step=transformation_step,
            acquired_at=acquired_at if acquired_at is not None else self.acquired_at,
            parser_version=parser_version if parser_version is not None else self.parser_version,
            transformation_history=(*self.transformation_history, self.transformation_step),
            parent_ids=(self.provenance_id,),
            run_id=run_id if run_id is not None else self.run_id,
            confidence=confidence,
            checksum=checksum,
            raw_payload_pointer=raw_payload_pointer,
            reproducibility=reproducibility or self.reproducibility,
            metadata=metadata or {},
            schema_version=self.schema_version,
        )


__all__ = [
    "AcquisitionMode",
    "ProvenanceRecord",
    "ProvenanceSource",
    "ReproducibilityMetadata",
]
