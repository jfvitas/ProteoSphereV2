from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import quote

from core.storage.canonical_store import CanonicalStore
from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestRawManifest,
)

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

SelectiveMaterializationStatus = Literal["materialized", "partial", "unresolved"]
SelectiveMaterializationIssueKind = Literal[
    "missing_artifact_payload",
    "missing_canonical_record",
    "invalid_artifact_payload",
]


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


def _json_ready(value: JSONValue) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _stable_digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def _quote_key(value: str) -> str:
    return quote(_required_text(value, "storage_key"), safe="-_.~")


def _coerce_artifact_payload(
    pointer: PackageManifestArtifactPointer,
    payload: Any,
) -> tuple[str, str | None, tuple[str, ...], tuple[str, ...]]:
    if isinstance(payload, str):
        materialized_ref = _required_text(payload, "materialized_ref")
        return materialized_ref, None, (), ()
    if not isinstance(payload, Mapping):
        raise TypeError("artifact payloads must be strings or mappings")
    materialized_ref = _optional_text(
        payload.get("materialized_ref")
        or payload.get("storage_key")
        or payload.get("path")
        or payload.get("uri")
        or payload.get("pointer")
    )
    if materialized_ref is None:
        raise ValueError(f"missing materialized_ref for artifact pointer: {pointer.pointer}")
    checksum = _optional_text(payload.get("checksum") or payload.get("digest"))
    provenance_refs = _dedupe_text(
        payload.get("provenance_refs") or payload.get("provenance") or payload.get("lineage")
    )
    notes = _dedupe_text(payload.get("notes") or payload.get("note") or ())
    return materialized_ref, checksum, provenance_refs, notes


@dataclass(frozen=True, slots=True)
class SelectiveMaterializationIssue:
    example_id: str
    kind: SelectiveMaterializationIssueKind
    message: str
    artifact_pointer: str | None = None
    canonical_id: str | None = None
    details: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "artifact_pointer", _optional_text(self.artifact_pointer))
        object.__setattr__(self, "canonical_id", _optional_text(self.canonical_id))
        object.__setattr__(
            self,
            "details",
            _normalize_json_mapping(self.details, "details"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "kind": self.kind,
            "message": self.message,
            "artifact_pointer": self.artifact_pointer,
            "canonical_id": self.canonical_id,
            "details": _json_ready(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SelectiveMaterializationIssue:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            example_id=payload.get("example_id") or payload.get("id") or "",
            kind=payload.get("kind") or "missing_artifact_payload",
            message=payload.get("message") or "",
            artifact_pointer=payload.get("artifact_pointer") or payload.get("pointer"),
            canonical_id=payload.get("canonical_id") or payload.get("canonical"),
            details=payload.get("details") or payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class SelectiveMaterializationArtifact:
    artifact_pointer: PackageManifestArtifactPointer
    materialized_ref: str
    checksum: str | None = None
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_pointer, PackageManifestArtifactPointer):
            raise TypeError("artifact_pointer must be a PackageManifestArtifactPointer")
        object.__setattr__(
            self,
            "materialized_ref",
            _required_text(self.materialized_ref, "materialized_ref"),
        )
        object.__setattr__(self, "checksum", _optional_text(self.checksum))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def storage_key(self) -> str:
        return (
            f"materialized/{self.artifact_pointer.artifact_kind}/"
            f"{_quote_key(self.materialized_ref)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_pointer": self.artifact_pointer.to_dict(),
            "materialized_ref": self.materialized_ref,
            "checksum": self.checksum,
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
            "storage_key": self.storage_key,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SelectiveMaterializationArtifact:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        artifact_pointer = payload.get("artifact_pointer") or payload.get("pointer") or {}
        return cls(
            artifact_pointer=(
                artifact_pointer
                if isinstance(artifact_pointer, PackageManifestArtifactPointer)
                else PackageManifestArtifactPointer.from_dict(artifact_pointer)
            ),
            materialized_ref=payload.get("materialized_ref")
            or payload.get("storage_key")
            or payload.get("path")
            or payload.get("uri")
            or "",
            checksum=payload.get("checksum") or payload.get("digest"),
            provenance_refs=payload.get("provenance_refs")
            or payload.get("provenance")
            or payload.get("lineage")
            or (),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class SelectiveMaterializationExample:
    example_id: str
    status: SelectiveMaterializationStatus
    artifact_pointers: tuple[PackageManifestArtifactPointer, ...]
    materialized_artifacts: tuple[SelectiveMaterializationArtifact, ...]
    source_record_refs: tuple[str, ...] = field(default_factory=tuple)
    canonical_ids: tuple[str, ...] = field(default_factory=tuple)
    planning_index_ref: str | None = None
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[SelectiveMaterializationIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "source_record_refs", _dedupe_text(self.source_record_refs))
        object.__setattr__(self, "canonical_ids", _dedupe_text(self.canonical_ids))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        artifact_pointers: list[PackageManifestArtifactPointer] = []
        seen_artifact_pointers: set[str] = set()
        for item in self.artifact_pointers:
            if not isinstance(item, PackageManifestArtifactPointer):
                raise TypeError(
                    "artifact_pointers must contain PackageManifestArtifactPointer objects"
                )
            if item.pointer in seen_artifact_pointers:
                continue
            seen_artifact_pointers.add(item.pointer)
            artifact_pointers.append(item)
        object.__setattr__(self, "artifact_pointers", tuple(artifact_pointers))
        materialized_artifacts: list[SelectiveMaterializationArtifact] = []
        seen_materialized: set[str] = set()
        for item in self.materialized_artifacts:
            if not isinstance(item, SelectiveMaterializationArtifact):
                raise TypeError(
                    "materialized_artifacts must contain SelectiveMaterializationArtifact objects"
                )
            if item.artifact_pointer.pointer in seen_materialized:
                continue
            seen_materialized.add(item.artifact_pointer.pointer)
            materialized_artifacts.append(item)
        object.__setattr__(self, "materialized_artifacts", tuple(materialized_artifacts))
        object.__setattr__(self, "issues", tuple(self.issues))

    @property
    def selected_artifact_pointers(self) -> tuple[str, ...]:
        return tuple(pointer.pointer for pointer in self.artifact_pointers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "status": self.status,
            "artifact_pointers": [pointer.to_dict() for pointer in self.artifact_pointers],
            "selected_artifact_pointers": list(self.selected_artifact_pointers),
            "materialized_artifacts": [item.to_dict() for item in self.materialized_artifacts],
            "source_record_refs": list(self.source_record_refs),
            "canonical_ids": list(self.canonical_ids),
            "planning_index_ref": self.planning_index_ref,
            "provenance_refs": list(self.provenance_refs),
            "issues": [item.to_dict() for item in self.issues],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SelectiveMaterializationExample:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            example_id=payload.get("example_id") or payload.get("id") or "",
            status=payload.get("status") or "unresolved",
            artifact_pointers=tuple(
                item
                if isinstance(item, PackageManifestArtifactPointer)
                else PackageManifestArtifactPointer.from_dict(item)
                for item in _iter_values(
                    payload.get("artifact_pointers")
                    or payload.get("selected_artifact_pointers")
                    or payload.get("artifacts")
                    or ()
                )
            ),
            materialized_artifacts=tuple(
                item
                if isinstance(item, SelectiveMaterializationArtifact)
                else SelectiveMaterializationArtifact.from_dict(item)
                for item in _iter_values(
                    payload.get("materialized_artifacts")
                    or payload.get("resolved_artifacts")
                    or ()
                )
            ),
            source_record_refs=payload.get("source_record_refs")
            or payload.get("source_records")
            or (),
            canonical_ids=payload.get("canonical_ids") or payload.get("canonical_id") or (),
            planning_index_ref=payload.get("planning_index_ref")
            or payload.get("planning_ref")
            or payload.get("planning_index_id"),
            provenance_refs=payload.get("provenance_refs")
            or payload.get("provenance")
            or payload.get("lineage_refs")
            or (),
            issues=tuple(
                item
                if isinstance(item, SelectiveMaterializationIssue)
                else SelectiveMaterializationIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or payload.get("missing") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class SelectiveMaterializationResult:
    package_id: str
    package_manifest_id: str
    selected_examples: tuple[SelectiveMaterializationExample, ...]
    raw_manifests: tuple[PackageManifestRawManifest, ...] = field(default_factory=tuple)
    planning_index_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    materialization_run_id: str | None = None
    materialized_at: str | date | datetime | None = None
    status: SelectiveMaterializationStatus = "unresolved"
    issues: tuple[SelectiveMaterializationIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_id", _required_text(self.package_id, "package_id"))
        object.__setattr__(
            self,
            "package_manifest_id",
            _required_text(self.package_manifest_id, "package_manifest_id"),
        )
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        object.__setattr__(
            self,
            "materialization_run_id",
            _optional_text(self.materialization_run_id),
        )
        object.__setattr__(self, "materialized_at", _normalize_timestamp(self.materialized_at))
        object.__setattr__(self, "planning_index_refs", _dedupe_text(self.planning_index_refs))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        raw_manifests: list[PackageManifestRawManifest] = []
        seen_raw_manifest_ids: set[str] = set()
        for item in self.raw_manifests:
            if not isinstance(item, PackageManifestRawManifest):
                raise TypeError("raw_manifests must contain PackageManifestRawManifest objects")
            if item.raw_manifest_id in seen_raw_manifest_ids:
                continue
            seen_raw_manifest_ids.add(item.raw_manifest_id)
            raw_manifests.append(item)
        object.__setattr__(self, "raw_manifests", tuple(raw_manifests))
        selected_examples: list[SelectiveMaterializationExample] = []
        seen_example_ids: set[str] = set()
        for item in self.selected_examples:
            if not isinstance(item, SelectiveMaterializationExample):
                raise TypeError(
                    "selected_examples must contain SelectiveMaterializationExample objects"
                )
            if item.example_id in seen_example_ids:
                raise ValueError(f"duplicate example_id: {item.example_id}")
            seen_example_ids.add(item.example_id)
            selected_examples.append(item)
        if not selected_examples:
            raise ValueError("selected_examples must not be empty")
        object.__setattr__(self, "selected_examples", tuple(selected_examples))
        object.__setattr__(self, "issues", tuple(self.issues))
        if self.status not in {"materialized", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")

    @property
    def selected_example_ids(self) -> tuple[str, ...]:
        return tuple(example.example_id for example in self.selected_examples)

    @property
    def manifest_id(self) -> str:
        return f"{self.package_manifest_id}:{self._selection_fingerprint()}:selective"

    @property
    def storage_key(self) -> str:
        return f"materialization/{_quote_key(self.package_id)}/{_quote_key(self.manifest_id)}"

    @property
    def selection_count(self) -> int:
        return len(self.selected_examples)

    @property
    def materialized_example_count(self) -> int:
        return sum(1 for example in self.selected_examples if example.materialized_artifacts)

    def _selection_fingerprint(self) -> str:
        payload = {
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "selected_examples": [
                {
                    "example_id": example.example_id,
                    "planning_index_ref": example.planning_index_ref,
                    "source_record_refs": list(example.source_record_refs),
                    "canonical_ids": list(example.canonical_ids),
                    "artifact_pointers": [
                        pointer.to_dict() for pointer in example.artifact_pointers
                    ],
                }
                for example in self.selected_examples
            ],
            "raw_manifests": [manifest.to_dict() for manifest in self.raw_manifests],
            "planning_index_refs": list(self.planning_index_refs),
        }
        return _stable_digest(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "storage_key": self.storage_key,
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "selected_example_ids": list(self.selected_example_ids),
            "selection_count": self.selection_count,
            "materialized_example_count": self.materialized_example_count,
            "selected_examples": [example.to_dict() for example in self.selected_examples],
            "raw_manifests": [manifest.to_dict() for manifest in self.raw_manifests],
            "planning_index_refs": list(self.planning_index_refs),
            "provenance_refs": list(self.provenance_refs),
            "materialization_run_id": self.materialization_run_id,
            "materialized_at": self.materialized_at,
            "status": self.status,
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SelectiveMaterializationResult:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            package_id=payload.get("package_id") or payload.get("package") or "",
            package_manifest_id=payload.get("package_manifest_id")
            or payload.get("manifest_id")
            or payload.get("package_manifest")
            or "",
            selected_examples=tuple(
                item
                if isinstance(item, SelectiveMaterializationExample)
                else SelectiveMaterializationExample.from_dict(item)
                for item in _iter_values(
                    payload.get("selected_examples") or payload.get("examples") or ()
                )
            ),
            raw_manifests=tuple(
                item
                if isinstance(item, PackageManifestRawManifest)
                else PackageManifestRawManifest.from_dict(item)
                for item in _iter_values(
                    payload.get("raw_manifests") or payload.get("manifests") or ()
                )
            ),
            planning_index_refs=payload.get("planning_index_refs")
            or payload.get("planning_refs")
            or payload.get("index_refs")
            or (),
            provenance_refs=payload.get("provenance_refs")
            or payload.get("provenance")
            or payload.get("lineage_refs")
            or (),
            materialization_run_id=payload.get("materialization_run_id")
            or payload.get("run_id")
            or payload.get("materialization_id"),
            materialized_at=payload.get("materialized_at") or payload.get("materialized"),
            status=payload.get("status") or "unresolved",
            issues=tuple(
                item
                if isinstance(item, SelectiveMaterializationIssue)
                else SelectiveMaterializationIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or payload.get("missing") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
            schema_version=int(payload.get("schema_version") or 1),
        )


def _canonical_lookup(canonical_store: CanonicalStore | None, canonical_id: str) -> bool:
    if canonical_store is None:
        return True
    return canonical_store.get(canonical_id) is not None


def materialize_selected_examples(
    package_manifest: PackageManifest,
    *,
    available_artifacts: Mapping[str, Any] | None = None,
    canonical_store: CanonicalStore | None = None,
    materialization_run_id: str | None = None,
    materialized_at: str | date | datetime | None = None,
) -> SelectiveMaterializationResult:
    if not isinstance(package_manifest, PackageManifest):
        raise TypeError("package_manifest must be a PackageManifest")
    if available_artifacts is not None and not isinstance(available_artifacts, Mapping):
        raise TypeError("available_artifacts must be a mapping or None")

    artifact_index = dict(available_artifacts or {})
    example_results: list[SelectiveMaterializationExample] = []
    issues: list[SelectiveMaterializationIssue] = []
    provenance_refs = _dedupe_text(
        (
            package_manifest.manifest_id,
            *package_manifest.provenance,
            *(manifest.raw_manifest_ref for manifest in package_manifest.raw_manifests),
            *package_manifest.planning_index_refs,
        )
    )

    for example in package_manifest.selected_examples:
        resolved_artifacts: list[SelectiveMaterializationArtifact] = []
        missing_artifact_pointers: list[PackageManifestArtifactPointer] = []
        example_issues: list[SelectiveMaterializationIssue] = []

        for canonical_id in example.canonical_ids:
            if not _canonical_lookup(canonical_store, canonical_id):
                issue = SelectiveMaterializationIssue(
                    example_id=example.example_id,
                    kind="missing_canonical_record",
                    message="canonical record required for selected example is missing",
                    canonical_id=canonical_id,
                    details={
                        "package_id": package_manifest.package_id,
                        "package_manifest_id": package_manifest.manifest_id,
                    },
                )
                example_issues.append(issue)
                issues.append(issue)

        for pointer in example.artifact_pointers:
            payload = artifact_index.get(pointer.pointer)
            if payload is None:
                missing_artifact_pointers.append(pointer)
                issue = SelectiveMaterializationIssue(
                    example_id=example.example_id,
                    kind="missing_artifact_payload",
                    message="selected artifact payload is missing",
                    artifact_pointer=pointer.pointer,
                    details={
                        "artifact_kind": pointer.artifact_kind,
                        "package_id": package_manifest.package_id,
                        "package_manifest_id": package_manifest.manifest_id,
                    },
                )
                example_issues.append(issue)
                issues.append(issue)
                continue
            try:
                materialized_ref, checksum, provenance, notes = _coerce_artifact_payload(
                    pointer,
                    payload,
                )
            except (TypeError, ValueError) as exc:
                issue = SelectiveMaterializationIssue(
                    example_id=example.example_id,
                    kind="invalid_artifact_payload",
                    message=str(exc),
                    artifact_pointer=pointer.pointer,
                    details={
                        "artifact_kind": pointer.artifact_kind,
                        "package_id": package_manifest.package_id,
                        "package_manifest_id": package_manifest.manifest_id,
                    },
                )
                example_issues.append(issue)
                issues.append(issue)
                continue
            resolved_artifacts.append(
                SelectiveMaterializationArtifact(
                    artifact_pointer=pointer,
                    materialized_ref=materialized_ref,
                    checksum=checksum,
                    provenance_refs=provenance,
                    notes=notes,
                )
            )

        if example_issues and resolved_artifacts:
            example_status: SelectiveMaterializationStatus = "partial"
        elif example_issues:
            example_status = "unresolved"
        else:
            example_status = "materialized"

        example_results.append(
            SelectiveMaterializationExample(
                example_id=example.example_id,
                status=example_status,
                artifact_pointers=example.artifact_pointers,
                materialized_artifacts=tuple(resolved_artifacts),
                source_record_refs=example.source_record_refs,
                canonical_ids=example.canonical_ids,
                planning_index_ref=example.planning_index_ref,
                provenance_refs=(
                    package_manifest.manifest_id,
                    *package_manifest.provenance,
                    *example.source_record_refs,
                ),
                issues=tuple(example_issues),
                notes=example.notes,
            )
        )

        if missing_artifact_pointers:
            # Keep selection strict by only surfacing the selected pointers that were requested.
            missing_artifact_pointers = list(dict.fromkeys(missing_artifact_pointers))

    if issues and any(example.materialized_artifacts for example in example_results):
        status: SelectiveMaterializationStatus = "partial"
    elif issues:
        status = "unresolved"
    else:
        status = "materialized"

    return SelectiveMaterializationResult(
        package_id=package_manifest.package_id,
        package_manifest_id=package_manifest.manifest_id,
        selected_examples=tuple(example_results),
        raw_manifests=package_manifest.raw_manifests,
        planning_index_refs=package_manifest.planning_index_refs,
        provenance_refs=provenance_refs,
        materialization_run_id=materialization_run_id,
        materialized_at=materialized_at,
        status=status,
        issues=tuple(issues),
        notes=package_manifest.notes,
    )


def validate_selective_materialization_payload(
    payload: Mapping[str, Any],
) -> SelectiveMaterializationResult:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return SelectiveMaterializationResult.from_dict(payload)


__all__ = [
    "SelectiveMaterializationArtifact",
    "SelectiveMaterializationExample",
    "SelectiveMaterializationIssue",
    "SelectiveMaterializationIssueKind",
    "SelectiveMaterializationResult",
    "SelectiveMaterializationStatus",
    "materialize_selected_examples",
    "validate_selective_materialization_payload",
]
