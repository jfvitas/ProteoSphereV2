from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestExample,
    PackageManifestMaterialization,
)
from execution.materialization.selective_materializer import (
    SelectiveMaterializationExample,
    SelectiveMaterializationResult,
)

TrainingPackageBuildStatus = Literal["built", "partial", "unresolved"]
TrainingPackageBuildIssueKind = Literal[
    "missing_materialization",
    "published_incomplete_package",
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


@dataclass(frozen=True, slots=True)
class TrainingPackageBuildIssue:
    package_id: str
    kind: TrainingPackageBuildIssueKind
    message: str
    example_id: str | None = None
    canonical_id: str | None = None
    artifact_pointer: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_id", _required_text(self.package_id, "package_id"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "example_id", _optional_text(self.example_id))
        object.__setattr__(self, "canonical_id", _optional_text(self.canonical_id))
        object.__setattr__(self, "artifact_pointer", _optional_text(self.artifact_pointer))
        if not isinstance(self.details, Mapping):
            raise TypeError("details must be a mapping")
        object.__setattr__(self, "details", dict(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "kind": self.kind,
            "message": self.message,
            "example_id": self.example_id,
            "canonical_id": self.canonical_id,
            "artifact_pointer": self.artifact_pointer,
            "details": _json_ready(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TrainingPackageBuildIssue:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            package_id=payload.get("package_id") or payload.get("package") or "",
            kind=payload.get("kind") or "missing_materialization",
            message=payload.get("message") or "",
            example_id=payload.get("example_id") or payload.get("id"),
            canonical_id=payload.get("canonical_id") or payload.get("canonical"),
            artifact_pointer=payload.get("artifact_pointer") or payload.get("pointer"),
            details=payload.get("details") or payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class TrainingPackageBuildResult:
    package_manifest: PackageManifest
    status: TrainingPackageBuildStatus
    issues: tuple[TrainingPackageBuildIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.package_manifest, PackageManifest):
            raise TypeError("package_manifest must be a PackageManifest")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        if self.status not in {"built", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def package_id(self) -> str:
        return self.package_manifest.package_id

    @property
    def package_manifest_id(self) -> str:
        return self.package_manifest.manifest_id

    @property
    def selected_example_ids(self) -> tuple[str, ...]:
        return self.package_manifest.selected_example_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "package_manifest": self.package_manifest.to_dict(),
            "selected_example_ids": list(self.selected_example_ids),
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TrainingPackageBuildResult:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        manifest_payload = payload.get("package_manifest") or {}
        package_manifest = (
            manifest_payload
            if isinstance(manifest_payload, PackageManifest)
            else PackageManifest.from_dict(manifest_payload)
        )
        return cls(
            package_manifest=package_manifest,
            status=payload.get("status") or "unresolved",
            issues=tuple(
                item
                if isinstance(item, TrainingPackageBuildIssue)
                else TrainingPackageBuildIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
            schema_version=int(payload.get("schema_version") or 1),
        )


def _example_from_selective(example: SelectiveMaterializationExample) -> PackageManifestExample:
    return PackageManifestExample(
        example_id=example.example_id,
        planning_index_ref=example.planning_index_ref,
        source_record_refs=example.source_record_refs,
        canonical_ids=example.canonical_ids,
        artifact_pointers=example.artifact_pointers,
        notes=example.notes,
    )


def _package_manifest_status(result: SelectiveMaterializationResult) -> TrainingPackageBuildStatus:
    if result.status == "materialized":
        return "built"
    if result.materialized_example_count:
        return "partial"
    return "unresolved"


def build_training_package(
    selective_result: SelectiveMaterializationResult,
    *,
    package_version: str | None = None,
    package_state: str = "frozen",
    split_name: str | None = None,
    split_artifact_id: str | None = None,
    materialization_run_id: str | None = None,
    materialized_at: str | date | datetime | None = None,
    published_at: str | date | datetime | None = None,
    provenance_refs: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> TrainingPackageBuildResult:
    if not isinstance(selective_result, SelectiveMaterializationResult):
        raise TypeError("selective_result must be a SelectiveMaterializationResult")

    build_status = _package_manifest_status(selective_result)
    if (
        package_state.replace("-", "_").replace(" ", "_").casefold() == "published"
        and build_status != "built"
    ):
        raise ValueError("published training packages require a fully materialized selection")

    selected_examples = tuple(
        _example_from_selective(example) for example in selective_result.selected_examples
    )
    package_provenance = _dedupe_text(
        (
            selective_result.package_manifest_id,
            *selective_result.provenance_refs,
            *provenance_refs,
        )
    )
    package_notes = _dedupe_text((*selective_result.notes, *notes))

    materialization = PackageManifestMaterialization(
        split_name=split_name,
        split_artifact_id=split_artifact_id,
        materialization_run_id=materialization_run_id or selective_result.materialization_run_id,
        materialization_mode="selective",
        materialized_at=materialized_at or selective_result.materialized_at,
        package_version=package_version,
        package_state=package_state,
        published_at=published_at,
        notes=package_notes,
    )

    package_manifest = PackageManifest(
        package_id=selective_result.package_id,
        selected_examples=selected_examples,
        raw_manifests=selective_result.raw_manifests,
        planning_index_refs=selective_result.planning_index_refs,
        materialization=materialization,
        provenance=package_provenance,
        notes=package_notes,
    )

    issues: list[TrainingPackageBuildIssue] = []
    for issue in selective_result.issues:
        kind: TrainingPackageBuildIssueKind = "missing_materialization"
        if issue.kind == "missing_canonical_record":
            kind = "missing_materialization"
        elif issue.kind in {"missing_artifact_payload", "invalid_artifact_payload"}:
            kind = "missing_materialization"
        issues.append(
            TrainingPackageBuildIssue(
                package_id=selective_result.package_id,
                kind=kind,
                message=issue.message,
                example_id=issue.example_id,
                canonical_id=issue.canonical_id,
                artifact_pointer=issue.artifact_pointer,
                details=issue.details,
            )
        )

    return TrainingPackageBuildResult(
        package_manifest=package_manifest,
        status=build_status,
        issues=tuple(issues),
        notes=package_notes,
    )


def validate_training_package_payload(payload: Mapping[str, Any]) -> TrainingPackageBuildResult:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return TrainingPackageBuildResult.from_dict(payload)


__all__ = [
    "TrainingPackageBuildIssue",
    "TrainingPackageBuildResult",
    "TrainingPackageBuildStatus",
    "build_training_package",
    "validate_training_package_payload",
]
