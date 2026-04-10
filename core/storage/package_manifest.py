from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

PackageState = Literal["draft", "frozen", "published"]
ArtifactKind = Literal[
    "feature",
    "embedding",
    "structure",
    "coordinates",
    "map",
    "alignment",
    "table",
    "evidence_text",
    "diagram",
    "other",
]

_PACKAGE_STATE_ALIASES: dict[str, PackageState] = {
    "draft": "draft",
    "working": "draft",
    "frozen": "frozen",
    "locked": "frozen",
    "published": "published",
    "release": "published",
}
_ARTIFACT_KIND_ALIASES: dict[str, ArtifactKind] = {
    "feature": "feature",
    "features": "feature",
    "feature_vector": "feature",
    "embedding": "embedding",
    "embeddings": "embedding",
    "embedding_vector": "embedding",
    "structure": "structure",
    "structures": "structure",
    "pdb": "structure",
    "mmcif": "structure",
    "cif": "structure",
    "bcif": "structure",
    "coordinates": "coordinates",
    "coordinate": "coordinates",
    "map": "map",
    "alignment": "alignment",
    "msa": "alignment",
    "table": "table",
    "rows": "table",
    "evidence_text": "evidence_text",
    "text": "evidence_text",
    "diagram": "diagram",
    "other": "other",
}
_RETRIEVAL_MODE_ALIASES: dict[str, str] = {
    "download": "download",
    "bulk_download": "download",
    "bulkdownload": "download",
    "file_download": "download",
    "ftp": "download",
    "scrape": "scrape",
    "web_scrape": "scrape",
    "webscrape": "scrape",
    "html_scrape": "scrape",
    "api": "api",
    "endpoint": "api",
    "query": "api",
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


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


def _normalize_package_state(value: Any) -> PackageState:
    text = _required_text(value, "package_state").replace("-", "_").replace(" ", "_").casefold()
    state = _PACKAGE_STATE_ALIASES.get(text)
    if state is None:
        raise ValueError(f"unsupported package_state: {value!r}")
    return state


def _normalize_artifact_kind(value: Any) -> ArtifactKind:
    text = _required_text(value, "artifact_kind").replace("-", "_").replace(" ", "_").casefold()
    kind = _ARTIFACT_KIND_ALIASES.get(text)
    if kind is None:
        raise ValueError(f"unsupported artifact_kind: {value!r}")
    return kind


def _normalize_retrieval_mode(value: Any) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    normalized = text.replace("-", "_").replace(" ", "_").casefold()
    retrieval_mode = _RETRIEVAL_MODE_ALIASES.get(normalized)
    if retrieval_mode is None:
        raise ValueError(f"unsupported retrieval_mode: {value!r}")
    return retrieval_mode


def _dedupe_refs(values: Iterable[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


@dataclass(frozen=True, slots=True)
class PackageManifestArtifactPointer:
    artifact_kind: ArtifactKind
    pointer: str
    selector: str | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_kind", _normalize_artifact_kind(self.artifact_kind))
        object.__setattr__(self, "pointer", _required_text(self.pointer, "pointer"))
        object.__setattr__(self, "selector", _optional_text(self.selector))
        object.__setattr__(self, "source_name", _optional_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "pointer": self.pointer,
            "selector": self.selector,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PackageManifestArtifactPointer:
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
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class PackageManifestExample:
    example_id: str
    planning_index_ref: str | None = None
    source_record_refs: tuple[str, ...] = field(default_factory=tuple)
    canonical_ids: tuple[str, ...] = field(default_factory=tuple)
    artifact_pointers: tuple[PackageManifestArtifactPointer, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(
            self,
            "source_record_refs",
            _normalize_text_tuple(self.source_record_refs),
        )
        object.__setattr__(self, "canonical_ids", _normalize_text_tuple(self.canonical_ids))
        pointers: list[PackageManifestArtifactPointer] = []
        for item in self.artifact_pointers:
            if not isinstance(item, PackageManifestArtifactPointer):
                raise TypeError(
                    "artifact_pointers must contain PackageManifestArtifactPointer objects"
                )
            pointers.append(item)
        object.__setattr__(self, "artifact_pointers", tuple(pointers))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "planning_index_ref": self.planning_index_ref,
            "source_record_refs": list(self.source_record_refs),
            "canonical_ids": list(self.canonical_ids),
            "artifact_pointers": [item.to_dict() for item in self.artifact_pointers],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PackageManifestExample:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            example_id=payload.get("example_id")
            or payload.get("id")
            or payload.get("record_id")
            or payload.get("selection_id")
            or "",
            planning_index_ref=payload.get("planning_index_ref")
            or payload.get("planning_ref")
            or payload.get("planning_index_id"),
            source_record_refs=payload.get("source_record_refs")
            or payload.get("source_records")
            or payload.get("record_refs")
            or (),
            canonical_ids=payload.get("canonical_ids") or payload.get("canonical_id") or (),
            artifact_pointers=tuple(
                item
                if isinstance(item, PackageManifestArtifactPointer)
                else PackageManifestArtifactPointer.from_dict(item)
                for item in _iter_values(
                    payload.get("artifact_pointers")
                    or payload.get("artifacts")
                    or payload.get("materialization_artifacts")
                    or payload.get("assets")
                    or ()
                )
            ),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class PackageManifestRawManifest:
    source_name: str
    raw_manifest_id: str
    raw_manifest_ref: str
    release_version: str | None = None
    release_date: str | date | datetime | None = None
    retrieval_mode: str | None = None
    source_locator: str | None = None
    planning_index_ref: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _required_text(self.source_name, "source_name"))
        object.__setattr__(
            self,
            "raw_manifest_id",
            _required_text(self.raw_manifest_id, "raw_manifest_id"),
        )
        object.__setattr__(
            self,
            "raw_manifest_ref",
            _required_text(self.raw_manifest_ref, "raw_manifest_ref"),
        )
        object.__setattr__(self, "release_version", _optional_text(self.release_version))
        object.__setattr__(self, "release_date", _normalize_date(self.release_date))
        object.__setattr__(self, "retrieval_mode", _normalize_retrieval_mode(self.retrieval_mode))
        object.__setattr__(self, "source_locator", _optional_text(self.source_locator))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        if self.release_version is None and self.release_date is None:
            raise ValueError("release_version or release_date is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "raw_manifest_id": self.raw_manifest_id,
            "raw_manifest_ref": self.raw_manifest_ref,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "planning_index_ref": self.planning_index_ref,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PackageManifestRawManifest:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=payload.get("source_name") or payload.get("source") or "",
            raw_manifest_id=payload.get("raw_manifest_id")
            or payload.get("manifest_id")
            or payload.get("source_manifest_id")
            or "",
            raw_manifest_ref=payload.get("raw_manifest_ref")
            or payload.get("manifest_ref")
            or payload.get("pointer")
            or payload.get("path")
            or payload.get("uri")
            or "",
            release_version=payload.get("release_version")
            or payload.get("version")
            or payload.get("release"),
            release_date=payload.get("release_date") or payload.get("date"),
            retrieval_mode=payload.get("retrieval_mode") or payload.get("mode"),
            source_locator=payload.get("source_locator")
            or payload.get("source_url")
            or payload.get("url"),
            planning_index_ref=payload.get("planning_index_ref")
            or payload.get("planning_ref")
            or payload.get("planning_index_id"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class PackageManifestMaterialization:
    split_name: str | None = None
    split_artifact_id: str | None = None
    materialization_run_id: str | None = None
    materialization_mode: str = "selective"
    materialized_at: str | date | datetime | None = None
    package_version: str | None = None
    package_state: PackageState = "draft"
    published_at: str | date | datetime | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "split_name", _optional_text(self.split_name))
        object.__setattr__(self, "split_artifact_id", _optional_text(self.split_artifact_id))
        object.__setattr__(
            self,
            "materialization_run_id",
            _optional_text(self.materialization_run_id),
        )
        object.__setattr__(
            self,
            "materialization_mode",
            _required_text(self.materialization_mode, "materialization_mode")
            .replace("-", "_")
            .replace(" ", "_")
            .casefold(),
        )
        object.__setattr__(self, "materialized_at", _normalize_timestamp(self.materialized_at))
        object.__setattr__(self, "package_version", _optional_text(self.package_version))
        object.__setattr__(self, "package_state", _normalize_package_state(self.package_state))
        object.__setattr__(self, "published_at", _normalize_timestamp(self.published_at))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        if self.package_state == "published":
            if not self.package_version:
                raise ValueError("published package materializations require package_version")
            if not self.materialized_at:
                raise ValueError("published package materializations require materialized_at")
            if not self.published_at:
                raise ValueError("published package materializations require published_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_name": self.split_name,
            "split_artifact_id": self.split_artifact_id,
            "materialization_run_id": self.materialization_run_id,
            "materialization_mode": self.materialization_mode,
            "materialized_at": self.materialized_at,
            "package_version": self.package_version,
            "package_state": self.package_state,
            "published_at": self.published_at,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PackageManifestMaterialization:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            split_name=payload.get("split_name") or payload.get("split"),
            split_artifact_id=payload.get("split_artifact_id")
            or payload.get("split_id")
            or payload.get("split_manifest_id"),
            materialization_run_id=payload.get("materialization_run_id")
            or payload.get("run_id")
            or payload.get("materialization_id"),
            materialization_mode=payload.get("materialization_mode")
            or payload.get("mode")
            or payload.get("strategy")
            or "selective",
            materialized_at=payload.get("materialized_at") or payload.get("materialized"),
            package_version=payload.get("package_version")
            or payload.get("version")
            or payload.get("release"),
            package_state=payload.get("package_state") or payload.get("state") or "draft",
            published_at=payload.get("published_at") or payload.get("published"),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class PackageManifest:
    package_id: str
    selected_examples: tuple[PackageManifestExample, ...]
    raw_manifests: tuple[PackageManifestRawManifest, ...] = field(default_factory=tuple)
    planning_index_refs: tuple[str, ...] = field(default_factory=tuple)
    materialization: PackageManifestMaterialization | None = None
    provenance: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_id", _required_text(self.package_id, "package_id"))
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

        selected_examples: list[PackageManifestExample] = []
        seen_example_ids: set[str] = set()
        for example in self.selected_examples:
            if not isinstance(example, PackageManifestExample):
                raise TypeError("selected_examples must contain PackageManifestExample objects")
            if example.example_id in seen_example_ids:
                raise ValueError(f"duplicate example_id: {example.example_id}")
            seen_example_ids.add(example.example_id)
            selected_examples.append(example)
        if not selected_examples:
            raise ValueError("selected_examples must not be empty")
        object.__setattr__(self, "selected_examples", tuple(selected_examples))

        raw_manifests: list[PackageManifestRawManifest] = []
        seen_raw_manifest_ids: set[str] = set()
        for manifest in self.raw_manifests:
            if not isinstance(manifest, PackageManifestRawManifest):
                raise TypeError("raw_manifests must contain PackageManifestRawManifest objects")
            if manifest.raw_manifest_id in seen_raw_manifest_ids:
                raise ValueError(f"duplicate raw_manifest_id: {manifest.raw_manifest_id}")
            seen_raw_manifest_ids.add(manifest.raw_manifest_id)
            raw_manifests.append(manifest)
        if not raw_manifests:
            raise ValueError("raw_manifests must not be empty")
        object.__setattr__(self, "raw_manifests", tuple(raw_manifests))

        planning_refs = _dedupe_refs(_iter_values(self.planning_index_refs))
        if not planning_refs:
            planning_ref_candidates = [
                manifest.planning_index_ref
                for manifest in self.raw_manifests
                if manifest.planning_index_ref is not None
            ]
            planning_ref_candidates.extend(
                example.planning_index_ref
                for example in self.selected_examples
                if example.planning_index_ref is not None
            )
            planning_refs = _dedupe_refs(planning_ref_candidates)
        if not planning_refs:
            raise ValueError("planning_index_refs must not be empty")
        object.__setattr__(self, "planning_index_refs", planning_refs)

        if self.materialization is not None and not isinstance(
            self.materialization,
            PackageManifestMaterialization,
        ):
            raise TypeError("materialization must be a PackageManifestMaterialization or None")

        object.__setattr__(self, "provenance", _normalize_text_tuple(self.provenance))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    @property
    def selected_example_ids(self) -> tuple[str, ...]:
        return tuple(example.example_id for example in self.selected_examples)

    @property
    def package_state(self) -> PackageState:
        if self.materialization is None:
            return "draft"
        return self.materialization.package_state

    @property
    def package_version(self) -> str | None:
        if self.materialization is None:
            return None
        return self.materialization.package_version

    @property
    def published_at(self) -> str | None:
        if self.materialization is None:
            return None
        return self.materialization.published_at

    @property
    def manifest_id(self) -> str:
        suffix = self.package_version or self.package_state
        return f"package:{self.package_id}:{suffix}"

    @property
    def selected_example_count(self) -> int:
        return len(self.selected_examples)

    @property
    def raw_manifest_count(self) -> int:
        return len(self.raw_manifests)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "package_id": self.package_id,
            "package_state": self.package_state,
            "package_version": self.package_version,
            "published_at": self.published_at,
            "selected_example_count": self.selected_example_count,
            "selected_example_ids": list(self.selected_example_ids),
            "selected_examples": [example.to_dict() for example in self.selected_examples],
            "raw_manifest_count": self.raw_manifest_count,
            "raw_manifests": [manifest.to_dict() for manifest in self.raw_manifests],
            "planning_index_refs": list(self.planning_index_refs),
            "materialization": (
                None if self.materialization is None else self.materialization.to_dict()
            ),
            "provenance": list(self.provenance),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PackageManifest:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        materialization_payload = payload.get("materialization")
        if materialization_payload is None:
            materialization_payload = payload.get("split_metadata")
        if materialization_payload is None:
            materialization_payload = payload.get("materialization_metadata")
        return cls(
            package_id=payload.get("package_id")
            or payload.get("package")
            or payload.get("id")
            or "",
            selected_examples=tuple(
                item
                if isinstance(item, PackageManifestExample)
                else PackageManifestExample.from_dict(item)
                for item in _iter_values(
                    payload.get("selected_examples")
                    or payload.get("examples")
                    or payload.get("example_records")
                    or ()
                )
            ),
            raw_manifests=tuple(
                item
                if isinstance(item, PackageManifestRawManifest)
                else PackageManifestRawManifest.from_dict(item)
                for item in _iter_values(
                    payload.get("raw_manifests")
                    or payload.get("source_manifests")
                    or payload.get("manifests")
                    or ()
                )
            ),
            planning_index_refs=(
                payload.get("planning_index_refs")
                or payload.get("planning_refs")
                or payload.get("index_refs")
                or ()
            ),
            materialization=(
                materialization_payload
                if isinstance(materialization_payload, PackageManifestMaterialization)
                else PackageManifestMaterialization.from_dict(materialization_payload)
                if materialization_payload is not None
                else None
            ),
            provenance=payload.get("provenance") or payload.get("lineage") or (),
            notes=payload.get("notes") or payload.get("note") or (),
            schema_version=int(payload.get("schema_version") or 1),
        )


def validate_package_manifest_payload(payload: Mapping[str, Any]) -> PackageManifest:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return PackageManifest.from_dict(payload)


__all__ = [
    "ArtifactKind",
    "PackageManifest",
    "PackageManifestArtifactPointer",
    "PackageManifestExample",
    "PackageManifestMaterialization",
    "PackageManifestRawManifest",
    "PackageState",
    "validate_package_manifest_payload",
]
