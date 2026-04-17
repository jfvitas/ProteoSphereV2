from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

LicenseScope = Literal[
    "public_metadata",
    "public_derived",
    "internal_only",
    "restricted",
    "unknown",
]
WarehouseValidationState = Literal["passed", "warning", "failed", "unknown"]

_LICENSE_SCOPE_ALIASES: dict[str, LicenseScope] = {
    "public_metadata": "public_metadata",
    "metadata_only": "public_metadata",
    "public_derived": "public_derived",
    "derived": "public_derived",
    "internal_only": "internal_only",
    "internal": "internal_only",
    "restricted": "restricted",
    "unknown": "unknown",
}
_VALIDATION_STATE_ALIASES: dict[str, WarehouseValidationState] = {
    "passed": "passed",
    "warning": "warning",
    "warn": "warning",
    "failed": "failed",
    "error": "failed",
    "unknown": "unknown",
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


def _normalize_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in {0, 1}:
        return bool(value)
    raise TypeError(f"{field_name} must be a bool")


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


def _normalize_date(value: Any) -> str | None:
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
        raise ValueError("date value must be ISO-8601 formatted") from exc


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


def _normalize_license_scope(value: Any) -> LicenseScope:
    text = _required_text(value, "license_scope").replace("-", "_").replace(" ", "_").casefold()
    scope = _LICENSE_SCOPE_ALIASES.get(text)
    if scope is None:
        raise ValueError(f"unsupported license_scope: {value!r}")
    return scope


def _normalize_validation_state(value: Any) -> WarehouseValidationState:
    text = (
        _required_text(value, "validation_state")
        .replace("-", "_")
        .replace(" ", "_")
        .casefold()
    )
    state = _VALIDATION_STATE_ALIASES.get(text)
    if state is None:
        raise ValueError(f"unsupported validation_state: {value!r}")
    return state


@dataclass(frozen=True, slots=True)
class ReferenceWarehouseSourceDescriptor:
    source_key: str
    source_name: str
    category: str
    snapshot_id: str
    retrieval_mode: str
    release_version: str | None = None
    release_date: str | date | datetime | None = None
    source_locator: str | None = None
    license_scope: LicenseScope = "unknown"
    redistributable: bool = False
    public_export_allowed: bool = False
    checksum_inventory_ref: str | None = None
    partition_strategy: str = "source/snapshot"
    refresh_cadence: str = "manual"
    availability_status: str = "unknown"
    location_verified: bool = False
    canonical_root: str | None = None
    duplicate_roots: tuple[str, ...] = field(default_factory=tuple)
    derived_roots: tuple[str, ...] = field(default_factory=tuple)
    scraped_roots: tuple[str, ...] = field(default_factory=tuple)
    consolidation_target: str | None = None
    consolidation_status: str = "not_required"
    scope_tier: str = "authoritative"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_key", _required_text(self.source_key, "source_key"))
        object.__setattr__(self, "source_name", _required_text(self.source_name, "source_name"))
        object.__setattr__(self, "category", _required_text(self.category, "category"))
        object.__setattr__(self, "snapshot_id", _required_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(
            self,
            "retrieval_mode",
            _required_text(self.retrieval_mode, "retrieval_mode"),
        )
        object.__setattr__(self, "release_version", _optional_text(self.release_version))
        object.__setattr__(self, "release_date", _normalize_date(self.release_date))
        object.__setattr__(self, "source_locator", _optional_text(self.source_locator))
        object.__setattr__(self, "license_scope", _normalize_license_scope(self.license_scope))
        object.__setattr__(
            self,
            "redistributable",
            _normalize_bool(self.redistributable, "redistributable"),
        )
        object.__setattr__(
            self,
            "public_export_allowed",
            _normalize_bool(self.public_export_allowed, "public_export_allowed"),
        )
        object.__setattr__(
            self,
            "checksum_inventory_ref",
            _optional_text(self.checksum_inventory_ref),
        )
        object.__setattr__(
            self,
            "partition_strategy",
            _required_text(self.partition_strategy, "partition_strategy"),
        )
        object.__setattr__(
            self,
            "refresh_cadence",
            _required_text(self.refresh_cadence, "refresh_cadence"),
        )
        object.__setattr__(
            self,
            "availability_status",
            _required_text(self.availability_status, "availability_status"),
        )
        object.__setattr__(
            self,
            "location_verified",
            _normalize_bool(self.location_verified, "location_verified"),
        )
        object.__setattr__(self, "canonical_root", _optional_text(self.canonical_root))
        object.__setattr__(self, "duplicate_roots", _normalize_text_tuple(self.duplicate_roots))
        object.__setattr__(self, "derived_roots", _normalize_text_tuple(self.derived_roots))
        object.__setattr__(self, "scraped_roots", _normalize_text_tuple(self.scraped_roots))
        object.__setattr__(self, "consolidation_target", _optional_text(self.consolidation_target))
        object.__setattr__(
            self,
            "consolidation_status",
            _required_text(self.consolidation_status, "consolidation_status"),
        )
        object.__setattr__(self, "scope_tier", _required_text(self.scope_tier, "scope_tier"))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "source_name": self.source_name,
            "category": self.category,
            "snapshot_id": self.snapshot_id,
            "retrieval_mode": self.retrieval_mode,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "source_locator": self.source_locator,
            "license_scope": self.license_scope,
            "redistributable": self.redistributable,
            "public_export_allowed": self.public_export_allowed,
            "checksum_inventory_ref": self.checksum_inventory_ref,
            "partition_strategy": self.partition_strategy,
            "refresh_cadence": self.refresh_cadence,
            "availability_status": self.availability_status,
            "location_verified": self.location_verified,
            "canonical_root": self.canonical_root,
            "duplicate_roots": list(self.duplicate_roots),
            "derived_roots": list(self.derived_roots),
            "scraped_roots": list(self.scraped_roots),
            "consolidation_target": self.consolidation_target,
            "consolidation_status": self.consolidation_status,
            "scope_tier": self.scope_tier,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReferenceWarehouseSourceDescriptor:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_key=payload.get("source_key") or payload.get("source_id") or "",
            source_name=payload.get("source_name") or payload.get("source") or "",
            category=payload.get("category") or "unknown",
            snapshot_id=payload.get("snapshot_id")
            or payload.get("manifest_id")
            or payload.get("release_stamp")
            or "",
            retrieval_mode=payload.get("retrieval_mode") or payload.get("mode") or "download",
            release_version=payload.get("release_version")
            or payload.get("version")
            or payload.get("release"),
            release_date=payload.get("release_date") or payload.get("date"),
            source_locator=payload.get("source_locator") or payload.get("url"),
            license_scope=payload.get("license_scope") or "unknown",
            redistributable=bool(payload.get("redistributable", False)),
            public_export_allowed=bool(payload.get("public_export_allowed", False)),
            checksum_inventory_ref=payload.get("checksum_inventory_ref")
            or payload.get("checksum_ref"),
            partition_strategy=payload.get("partition_strategy") or "source/snapshot",
            refresh_cadence=payload.get("refresh_cadence") or "manual",
            availability_status=payload.get("availability_status")
            or payload.get("status")
            or "unknown",
            location_verified=bool(payload.get("location_verified", False)),
            canonical_root=payload.get("canonical_root"),
            duplicate_roots=payload.get("duplicate_roots") or (),
            derived_roots=payload.get("derived_roots") or (),
            scraped_roots=payload.get("scraped_roots") or (),
            consolidation_target=payload.get("consolidation_target"),
            consolidation_status=payload.get("consolidation_status") or "not_required",
            scope_tier=payload.get("scope_tier") or "authoritative",
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class ReferenceWarehouseEntityFamily:
    family_name: str
    storage_format: str
    row_count: int
    partition_glob: str
    partition_keys: tuple[str, ...] = field(default_factory=tuple)
    public_export_allowed: bool = False
    export_policy: str = "metadata_only"
    truth_surface_fields: tuple[str, ...] = field(default_factory=tuple)
    default_view: str = "best_evidence"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "family_name", _required_text(self.family_name, "family_name"))
        object.__setattr__(
            self,
            "storage_format",
            _required_text(self.storage_format, "storage_format"),
        )
        row_count = _normalize_int(self.row_count, "row_count")
        if row_count is None or row_count < 0:
            raise ValueError("row_count must be >= 0")
        object.__setattr__(self, "row_count", row_count)
        object.__setattr__(
            self,
            "partition_glob",
            _required_text(self.partition_glob, "partition_glob"),
        )
        object.__setattr__(self, "partition_keys", _normalize_text_tuple(self.partition_keys))
        object.__setattr__(
            self,
            "public_export_allowed",
            _normalize_bool(self.public_export_allowed, "public_export_allowed"),
        )
        object.__setattr__(
            self,
            "export_policy",
            _required_text(self.export_policy, "export_policy"),
        )
        object.__setattr__(self, "truth_surface_fields", _normalize_text_tuple(self.truth_surface_fields))
        object.__setattr__(self, "default_view", _required_text(self.default_view, "default_view"))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_name": self.family_name,
            "storage_format": self.storage_format,
            "row_count": self.row_count,
            "partition_glob": self.partition_glob,
            "partition_keys": list(self.partition_keys),
            "public_export_allowed": self.public_export_allowed,
            "export_policy": self.export_policy,
            "truth_surface_fields": list(self.truth_surface_fields),
            "default_view": self.default_view,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReferenceWarehouseEntityFamily:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            family_name=payload.get("family_name") or payload.get("name") or "",
            storage_format=payload.get("storage_format") or payload.get("format") or "",
            row_count=payload.get("row_count") or 0,
            partition_glob=payload.get("partition_glob") or payload.get("path_glob") or "",
            partition_keys=payload.get("partition_keys") or (),
            public_export_allowed=bool(payload.get("public_export_allowed", False)),
            export_policy=payload.get("export_policy") or "metadata_only",
            truth_surface_fields=payload.get("truth_surface_fields") or (),
            default_view=payload.get("default_view") or "best_evidence",
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class ReferenceWarehouseValidation:
    state: WarehouseValidationState
    validated_at: str | date | datetime | None = None
    validator_id: str | None = None
    checks: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", _normalize_validation_state(self.state))
        object.__setattr__(self, "validated_at", _normalize_timestamp(self.validated_at))
        object.__setattr__(self, "validator_id", _optional_text(self.validator_id))
        object.__setattr__(self, "checks", _normalize_json_mapping(self.checks, "checks"))
        object.__setattr__(self, "warnings", _normalize_text_tuple(self.warnings))
        object.__setattr__(self, "errors", _normalize_text_tuple(self.errors))

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "validated_at": self.validated_at,
            "validator_id": self.validator_id,
            "checks": _json_ready(dict(self.checks)),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReferenceWarehouseValidation:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            state=payload.get("state") or "unknown",
            validated_at=payload.get("validated_at"),
            validator_id=payload.get("validator_id"),
            checks=payload.get("checks") or {},
            warnings=payload.get("warnings") or (),
            errors=payload.get("errors") or (),
        )


@dataclass(frozen=True, slots=True)
class ReferenceWarehouseManifest:
    warehouse_id: str
    warehouse_root: str
    catalog_path: str
    catalog_engine: str
    catalog_status: str
    generated_at: str | date | datetime | None = None
    source_descriptors: tuple[ReferenceWarehouseSourceDescriptor, ...] = field(
        default_factory=tuple
    )
    entity_families: tuple[ReferenceWarehouseEntityFamily, ...] = field(default_factory=tuple)
    validation: ReferenceWarehouseValidation = field(
        default_factory=lambda: ReferenceWarehouseValidation("unknown")
    )
    export_policy: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "warehouse_id", _required_text(self.warehouse_id, "warehouse_id"))
        object.__setattr__(
            self,
            "warehouse_root",
            _required_text(self.warehouse_root, "warehouse_root"),
        )
        object.__setattr__(self, "catalog_path", _required_text(self.catalog_path, "catalog_path"))
        object.__setattr__(
            self,
            "catalog_engine",
            _required_text(self.catalog_engine, "catalog_engine"),
        )
        object.__setattr__(
            self,
            "catalog_status",
            _required_text(self.catalog_status, "catalog_status"),
        )
        object.__setattr__(self, "generated_at", _normalize_timestamp(self.generated_at))
        descriptors: list[ReferenceWarehouseSourceDescriptor] = []
        seen_sources: set[str] = set()
        for item in self.source_descriptors:
            if not isinstance(item, ReferenceWarehouseSourceDescriptor):
                raise TypeError(
                    "source_descriptors must contain ReferenceWarehouseSourceDescriptor objects"
                )
            if item.source_key in seen_sources:
                raise ValueError(f"duplicate source_key: {item.source_key}")
            seen_sources.add(item.source_key)
            descriptors.append(item)
        object.__setattr__(self, "source_descriptors", tuple(descriptors))
        families: list[ReferenceWarehouseEntityFamily] = []
        seen_families: set[str] = set()
        for item in self.entity_families:
            if not isinstance(item, ReferenceWarehouseEntityFamily):
                raise TypeError(
                    "entity_families must contain ReferenceWarehouseEntityFamily objects"
                )
            if item.family_name in seen_families:
                raise ValueError(f"duplicate family_name: {item.family_name}")
            seen_families.add(item.family_name)
            families.append(item)
        object.__setattr__(self, "entity_families", tuple(families))
        if not isinstance(self.validation, ReferenceWarehouseValidation):
            object.__setattr__(
                self,
                "validation",
                ReferenceWarehouseValidation.from_dict(self.validation),
            )
        object.__setattr__(
            self,
            "export_policy",
            _normalize_json_mapping(self.export_policy, "export_policy"),
        )
        object.__setattr__(self, "warnings", _normalize_text_tuple(self.warnings))

    @property
    def family_count(self) -> int:
        return len(self.entity_families)

    @property
    def source_count(self) -> int:
        return len(self.source_descriptors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "warehouse_id": self.warehouse_id,
            "warehouse_root": self.warehouse_root,
            "catalog_path": self.catalog_path,
            "catalog_engine": self.catalog_engine,
            "catalog_status": self.catalog_status,
            "generated_at": self.generated_at,
            "source_count": self.source_count,
            "family_count": self.family_count,
            "source_descriptors": [item.to_dict() for item in self.source_descriptors],
            "entity_families": [item.to_dict() for item in self.entity_families],
            "validation": self.validation.to_dict(),
            "export_policy": _json_ready(dict(self.export_policy)),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReferenceWarehouseManifest:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            warehouse_id=payload.get("warehouse_id") or payload.get("id") or "",
            warehouse_root=payload.get("warehouse_root") or payload.get("root") or "",
            catalog_path=payload.get("catalog_path") or "",
            catalog_engine=payload.get("catalog_engine") or "duckdb",
            catalog_status=payload.get("catalog_status") or "unknown",
            generated_at=payload.get("generated_at"),
            source_descriptors=tuple(
                item
                if isinstance(item, ReferenceWarehouseSourceDescriptor)
                else ReferenceWarehouseSourceDescriptor.from_dict(item)
                for item in _iter_values(payload.get("source_descriptors") or ())
            ),
            entity_families=tuple(
                item
                if isinstance(item, ReferenceWarehouseEntityFamily)
                else ReferenceWarehouseEntityFamily.from_dict(item)
                for item in _iter_values(payload.get("entity_families") or ())
            ),
            validation=(
                payload.get("validation")
                if isinstance(payload.get("validation"), ReferenceWarehouseValidation)
                else ReferenceWarehouseValidation.from_dict(payload.get("validation") or {})
            ),
            export_policy=payload.get("export_policy") or {},
            warnings=payload.get("warnings") or (),
        )


def validate_reference_warehouse_manifest_payload(
    payload: Mapping[str, Any],
) -> ReferenceWarehouseManifest:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return ReferenceWarehouseManifest.from_dict(payload)


__all__ = [
    "LicenseScope",
    "ReferenceWarehouseEntityFamily",
    "ReferenceWarehouseManifest",
    "ReferenceWarehouseSourceDescriptor",
    "ReferenceWarehouseValidation",
    "WarehouseValidationState",
    "validate_reference_warehouse_manifest_payload",
]
