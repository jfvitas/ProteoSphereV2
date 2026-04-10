from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from core.storage.canonical_store import (
    CanonicalStore,
    validate_canonical_store_payload,
)
from core.storage.embedding_cache import (
    EmbeddingCacheCatalog,
    validate_embedding_cache_payload,
)
from core.storage.feature_cache import (
    FeatureCacheCatalog,
    validate_feature_cache_payload,
)
from core.storage.package_manifest import PackageManifest
from core.storage.planning_index_schema import (
    PlanningIndexSchema,
    validate_planning_index_payload,
)
from execution.materialization.package_builder import (
    TrainingPackageBuildResult,
    build_training_package,
)
from execution.materialization.selective_materializer import (
    SelectiveMaterializationResult,
    materialize_selected_examples,
)

StorageRuntimeStatus = Literal["integrated", "partial", "unresolved"]
StorageRuntimeIssueKind = Literal[
    "missing_planning_index_entry",
    "missing_feature_cache_entry",
    "missing_embedding_cache_entry",
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
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


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


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


@dataclass(frozen=True, slots=True)
class StorageRuntimeIssue:
    kind: StorageRuntimeIssueKind
    message: str
    example_id: str | None = None
    planning_index_ref: str | None = None
    artifact_pointer: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "example_id", _optional_text(self.example_id))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "artifact_pointer", _optional_text(self.artifact_pointer))
        if not isinstance(self.details, Mapping):
            raise TypeError("details must be a mapping")
        object.__setattr__(self, "details", dict(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "example_id": self.example_id,
            "planning_index_ref": self.planning_index_ref,
            "artifact_pointer": self.artifact_pointer,
            "details": _json_ready(dict(self.details)),
        }


def _feature_artifact_pointers(feature_cache: FeatureCacheCatalog | None) -> set[str]:
    pointers: set[str] = set()
    if feature_cache is None:
        return pointers
    for record in feature_cache.records:
        for pointer in record.artifact_pointers:
            pointers.add(pointer.pointer)
    return pointers


def _embedding_artifact_pointers(embedding_cache: EmbeddingCacheCatalog | None) -> set[str]:
    pointers: set[str] = set()
    if embedding_cache is None:
        return pointers
    for record in embedding_cache.records:
        for pointer in record.artifact_pointers:
            pointers.add(pointer.pointer)
    return pointers


def _planning_index_ids(planning_index: PlanningIndexSchema | None) -> set[str]:
    if planning_index is None:
        return set()
    return {record.planning_id for record in planning_index.records}


@dataclass(frozen=True, slots=True)
class StorageRuntimeResult:
    package_manifest: PackageManifest
    planning_index: PlanningIndexSchema
    canonical_store: CanonicalStore
    feature_cache: FeatureCacheCatalog | None
    embedding_cache: EmbeddingCacheCatalog | None
    selective_materialization: SelectiveMaterializationResult
    package_build: TrainingPackageBuildResult
    status: StorageRuntimeStatus
    issues: tuple[StorageRuntimeIssue, ...] = field(default_factory=tuple)
    materialized_at: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.package_manifest, PackageManifest):
            raise TypeError("package_manifest must be a PackageManifest")
        if not isinstance(self.planning_index, PlanningIndexSchema):
            raise TypeError("planning_index must be a PlanningIndexSchema")
        if not isinstance(self.canonical_store, CanonicalStore):
            raise TypeError("canonical_store must be a CanonicalStore")
        if self.feature_cache is not None and not isinstance(
            self.feature_cache,
            FeatureCacheCatalog,
        ):
            raise TypeError("feature_cache must be a FeatureCacheCatalog or None")
        if self.embedding_cache is not None and not isinstance(
            self.embedding_cache,
            EmbeddingCacheCatalog,
        ):
            raise TypeError("embedding_cache must be an EmbeddingCacheCatalog or None")
        if not isinstance(self.selective_materialization, SelectiveMaterializationResult):
            raise TypeError("selective_materialization must be a SelectiveMaterializationResult")
        if not isinstance(self.package_build, TrainingPackageBuildResult):
            raise TypeError("package_build must be a TrainingPackageBuildResult")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        if self.status not in {"integrated", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        object.__setattr__(self, "materialized_at", _normalize_timestamp(self.materialized_at))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def selected_example_ids(self) -> tuple[str, ...]:
        return self.package_manifest.selected_example_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "package_manifest": self.package_manifest.to_dict(),
            "planning_index": self.planning_index.to_dict(),
            "canonical_store": self.canonical_store.to_dict(),
            "feature_cache": None if self.feature_cache is None else self.feature_cache.to_dict(),
            "embedding_cache": None
            if self.embedding_cache is None
            else self.embedding_cache.to_dict(),
            "selective_materialization": self.selective_materialization.to_dict(),
            "package_build": self.package_build.to_dict(),
            "selected_example_ids": list(self.selected_example_ids),
            "issues": [issue.to_dict() for issue in self.issues],
            "materialized_at": self.materialized_at,
            "notes": list(self.notes),
        }


def integrate_storage_runtime(
    package_manifest: PackageManifest,
    *,
    planning_index: PlanningIndexSchema | Mapping[str, Any],
    canonical_store: CanonicalStore | Mapping[str, Any],
    feature_cache: FeatureCacheCatalog | Mapping[str, Any] | None = None,
    embedding_cache: EmbeddingCacheCatalog | Mapping[str, Any] | None = None,
    available_artifacts: Mapping[str, Any] | None = None,
    materialization_run_id: str | None = None,
    materialized_at: str | date | datetime | None = None,
    package_version: str | None = None,
    package_state: str = "frozen",
    split_name: str | None = None,
    split_artifact_id: str | None = None,
    published_at: str | date | datetime | None = None,
    provenance_refs: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> StorageRuntimeResult:
    if not isinstance(package_manifest, PackageManifest):
        raise TypeError("package_manifest must be a PackageManifest")
    if available_artifacts is not None and not isinstance(available_artifacts, Mapping):
        raise TypeError("available_artifacts must be a mapping or None")

    planning_index_obj = (
        planning_index
        if isinstance(planning_index, PlanningIndexSchema)
        else validate_planning_index_payload(planning_index)
    )
    canonical_store_obj = (
        canonical_store
        if isinstance(canonical_store, CanonicalStore)
        else validate_canonical_store_payload(canonical_store)
    )
    feature_cache_obj = (
        None
        if feature_cache is None
        else feature_cache
        if isinstance(feature_cache, FeatureCacheCatalog)
        else validate_feature_cache_payload(feature_cache)
    )
    embedding_cache_obj = (
        None
        if embedding_cache is None
        else embedding_cache
        if isinstance(embedding_cache, EmbeddingCacheCatalog)
        else validate_embedding_cache_payload(embedding_cache)
    )

    issues: list[StorageRuntimeIssue] = []
    planning_ids = _planning_index_ids(planning_index_obj)
    feature_artifacts = _feature_artifact_pointers(feature_cache_obj)
    embedding_artifacts = _embedding_artifact_pointers(embedding_cache_obj)

    for example in package_manifest.selected_examples:
        if example.planning_index_ref and example.planning_index_ref not in planning_ids:
            issues.append(
                StorageRuntimeIssue(
                    kind="missing_planning_index_entry",
                    message="selected example references a planning index row that is not present",
                    example_id=example.example_id,
                    planning_index_ref=example.planning_index_ref,
                    details={
                        "package_id": package_manifest.package_id,
                        "package_manifest_id": package_manifest.manifest_id,
                    },
                )
            )
        for pointer in example.artifact_pointers:
            if pointer.artifact_kind == "feature" and pointer.pointer not in feature_artifacts:
                issues.append(
                    StorageRuntimeIssue(
                        kind="missing_feature_cache_entry",
                        message="selected feature artifact is not present in the feature cache",
                        example_id=example.example_id,
                        artifact_pointer=pointer.pointer,
                        details={
                            "package_id": package_manifest.package_id,
                            "package_manifest_id": package_manifest.manifest_id,
                        },
                    )
                )
            if pointer.artifact_kind == "embedding" and pointer.pointer not in embedding_artifacts:
                issues.append(
                    StorageRuntimeIssue(
                        kind="missing_embedding_cache_entry",
                        message="selected embedding artifact is not present in the embedding cache",
                        example_id=example.example_id,
                        artifact_pointer=pointer.pointer,
                        details={
                            "package_id": package_manifest.package_id,
                            "package_manifest_id": package_manifest.manifest_id,
                        },
                    )
                )

    selective_result = materialize_selected_examples(
        package_manifest,
        available_artifacts=available_artifacts,
        canonical_store=canonical_store_obj,
        materialization_run_id=materialization_run_id,
        materialized_at=materialized_at,
    )

    build_result = build_training_package(
        selective_result,
        package_version=package_version,
        package_state=package_state,
        split_name=split_name,
        split_artifact_id=split_artifact_id,
        materialization_run_id=materialization_run_id,
        materialized_at=materialized_at,
        published_at=published_at,
        provenance_refs=provenance_refs,
        notes=notes,
    )

    status: StorageRuntimeStatus
    if issues or selective_result.status != "materialized" or build_result.status != "built":
        if selective_result.status == "unresolved" or build_result.status == "unresolved":
            status = "unresolved"
        else:
            status = "partial"
    else:
        status = "integrated"

    return StorageRuntimeResult(
        package_manifest=build_result.package_manifest,
        planning_index=planning_index_obj,
        canonical_store=canonical_store_obj,
        feature_cache=feature_cache_obj,
        embedding_cache=embedding_cache_obj,
        selective_materialization=selective_result,
        package_build=build_result,
        status=status,
        issues=tuple(issues),
        materialized_at=_normalize_timestamp(materialized_at),
        notes=tuple(notes),
    )


__all__ = [
    "StorageRuntimeIssue",
    "StorageRuntimeResult",
    "StorageRuntimeStatus",
    "integrate_storage_runtime",
]
