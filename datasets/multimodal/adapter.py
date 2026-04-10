from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from core.storage.package_manifest import PackageManifestArtifactPointer, PackageManifestExample
from execution.materialization.selective_materializer import (
    SelectiveMaterializationArtifact,
    SelectiveMaterializationExample,
)
from execution.storage_runtime import StorageRuntimeResult
from features.ppi_representation import PPIRepresentation, PPIRepresentationRecord

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

MultimodalDatasetStatus = Literal["ready", "partial", "unresolved"]
MultimodalDatasetIssueKind = Literal[
    "missing_selected_example",
    "missing_requested_modality",
    "missing_ppi_representation_record",
    "ambiguous_ppi_representation_record",
]

DEFAULT_MULTIMODAL_MODALITIES = ("sequence", "structure", "ligand", "ppi")

_MODALITY_ALIASES: dict[str, str] = {
    "sequence": "sequence",
    "protein": "sequence",
    "protein_sequence": "sequence",
    "protein_embedding": "sequence",
    "esm": "sequence",
    "esm2": "sequence",
    "structure": "structure",
    "structural": "structure",
    "pdb": "structure",
    "mmcif": "structure",
    "cif": "structure",
    "coordinates": "structure",
    "coordinate": "structure",
    "ligand": "ligand",
    "compound": "ligand",
    "molecule": "ligand",
    "smiles": "ligand",
    "rdkit": "ligand",
    "ppi": "ppi",
    "pair": "ppi",
    "protein_protein": "ppi",
    "interaction": "ppi",
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


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


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


def _normalize_text_tuple_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, tuple[str, ...]] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized[normalized_key] = _dedupe_text(item)
    return normalized


def _normalize_modality(value: Any) -> str:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    return _MODALITY_ALIASES.get(text, text)


def _artifact_kind_modality(pointer: PackageManifestArtifactPointer) -> str:
    selector = _optional_text(pointer.selector)
    source_name = _optional_text(pointer.source_name)
    for candidate in (source_name, selector):
        if candidate is None:
            continue
        modality = _MODALITY_ALIASES.get(candidate.replace("-", "_").replace(" ", "_").casefold())
        if modality is not None:
            return modality
    return f"artifact_kind:{pointer.artifact_kind}"


def _dedupe_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


@dataclass(frozen=True, slots=True)
class MultimodalDatasetIssue:
    example_id: str
    kind: MultimodalDatasetIssueKind
    message: str
    modality: str | None = None
    artifact_pointer: str | None = None
    ppi_summary_id: str | None = None
    details: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "modality", _optional_text(self.modality))
        object.__setattr__(self, "artifact_pointer", _optional_text(self.artifact_pointer))
        object.__setattr__(self, "ppi_summary_id", _optional_text(self.ppi_summary_id))
        object.__setattr__(self, "details", _normalize_json_mapping(self.details, "details"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "kind": self.kind,
            "message": self.message,
            "modality": self.modality,
            "artifact_pointer": self.artifact_pointer,
            "ppi_summary_id": self.ppi_summary_id,
            "details": _json_ready(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MultimodalDatasetIssue:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            example_id=payload.get("example_id") or payload.get("id") or "",
            kind=payload.get("kind") or "missing_requested_modality",
            message=payload.get("message") or "",
            modality=payload.get("modality") or payload.get("feature"),
            artifact_pointer=payload.get("artifact_pointer") or payload.get("pointer"),
            ppi_summary_id=payload.get("ppi_summary_id") or payload.get("summary_id"),
            details=payload.get("details") or payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class MultimodalDatasetExample:
    selected_example: PackageManifestExample
    materialized_artifacts: tuple[SelectiveMaterializationArtifact, ...] = field(
        default_factory=tuple
    )
    ppi_records: tuple[PPIRepresentationRecord, ...] = field(default_factory=tuple)
    resolved_modalities: tuple[str, ...] = field(default_factory=tuple)
    available_modalities: tuple[str, ...] = field(default_factory=tuple)
    missing_modalities: tuple[str, ...] = field(default_factory=tuple)
    modality_refs: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[MultimodalDatasetIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    status: MultimodalDatasetStatus = "unresolved"

    def __post_init__(self) -> None:
        if not isinstance(self.selected_example, PackageManifestExample):
            raise TypeError("selected_example must be a PackageManifestExample")
        artifact_refs: list[SelectiveMaterializationArtifact] = []
        seen_artifact_refs: set[str] = set()
        for item in self.materialized_artifacts:
            if not isinstance(item, SelectiveMaterializationArtifact):
                raise TypeError(
                    "materialized_artifacts must contain SelectiveMaterializationArtifact objects"
                )
            if item.materialized_ref in seen_artifact_refs:
                continue
            seen_artifact_refs.add(item.materialized_ref)
            artifact_refs.append(item)
        object.__setattr__(self, "materialized_artifacts", tuple(artifact_refs))

        ppi_records: list[PPIRepresentationRecord] = []
        seen_ppi_ids: set[str] = set()
        for item in self.ppi_records:
            if not isinstance(item, PPIRepresentationRecord):
                raise TypeError("ppi_records must contain PPIRepresentationRecord objects")
            if item.summary_id in seen_ppi_ids:
                continue
            seen_ppi_ids.add(item.summary_id)
            ppi_records.append(item)
        object.__setattr__(self, "ppi_records", tuple(ppi_records))

        object.__setattr__(self, "resolved_modalities", _dedupe_text(self.resolved_modalities))
        object.__setattr__(self, "available_modalities", _dedupe_text(self.available_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        object.__setattr__(
            self,
            "modality_refs",
            _normalize_text_tuple_mapping(self.modality_refs, "modality_refs"),
        )
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if self.status not in {"ready", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")

    @property
    def example_id(self) -> str:
        return self.selected_example.example_id

    @property
    def selected_example_id(self) -> str:
        return self.selected_example.example_id

    @property
    def pair_id(self) -> str | None:
        if not self.ppi_records:
            return None
        return self.ppi_records[0].pair_id

    @property
    def ppi_summary_ids(self) -> tuple[str, ...]:
        return tuple(record.summary_id for record in self.ppi_records)

    @property
    def ppi_feature_vectors(self) -> tuple[tuple[Any, ...], ...]:
        return tuple(record.feature_vector for record in self.ppi_records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "selected_example": self.selected_example.to_dict(),
            "materialized_artifacts": [item.to_dict() for item in self.materialized_artifacts],
            "ppi_records": [record.to_dict() for record in self.ppi_records],
            "resolved_modalities": list(self.resolved_modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "modality_refs": {
                key: list(values) for key, values in self.modality_refs.items()
            },
            "provenance_refs": list(self.provenance_refs),
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
            "status": self.status,
            "pair_id": self.pair_id,
            "ppi_summary_ids": list(self.ppi_summary_ids),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MultimodalDatasetExample:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        selected_example = payload.get("selected_example") or payload.get("example") or {}
        return cls(
            selected_example=(
                selected_example
                if isinstance(selected_example, PackageManifestExample)
                else PackageManifestExample.from_dict(selected_example)
            ),
            materialized_artifacts=tuple(
                item
                if isinstance(item, SelectiveMaterializationArtifact)
                else SelectiveMaterializationArtifact.from_dict(item)
                for item in _iter_values(
                    payload.get("materialized_artifacts") or payload.get("artifacts") or ()
                )
            ),
            ppi_records=tuple(
                item
                if isinstance(item, PPIRepresentationRecord)
                else PPIRepresentationRecord.from_dict(item)
                for item in _iter_values(payload.get("ppi_records") or payload.get("ppi") or ())
            ),
            resolved_modalities=payload.get("resolved_modalities") or (),
            available_modalities=payload.get("available_modalities") or (),
            missing_modalities=payload.get("missing_modalities") or (),
            modality_refs=payload.get("modality_refs") or {},
            provenance_refs=payload.get("provenance_refs") or payload.get("provenance") or (),
            issues=tuple(
                item
                if isinstance(item, MultimodalDatasetIssue)
                else MultimodalDatasetIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
            status=payload.get("status") or "unresolved",
        )


@dataclass(frozen=True, slots=True)
class MultimodalDataset:
    dataset_id: str
    package_id: str
    package_manifest_id: str
    requested_modalities: tuple[str, ...]
    storage_runtime_status: str
    examples: tuple[MultimodalDatasetExample, ...]
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[MultimodalDatasetIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1
    status: MultimodalDatasetStatus = "unresolved"

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_id", _required_text(self.dataset_id, "dataset_id"))
        object.__setattr__(self, "package_id", _required_text(self.package_id, "package_id"))
        object.__setattr__(
            self,
            "package_manifest_id",
            _required_text(self.package_manifest_id, "package_manifest_id"),
        )
        object.__setattr__(
            self,
            "requested_modalities",
            _dedupe_preserve_order(
                _normalize_modality(modality) for modality in self.requested_modalities
            ),
        )
        object.__setattr__(
            self,
            "storage_runtime_status",
            _required_text(self.storage_runtime_status, "storage_runtime_status"),
        )
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

        examples: list[MultimodalDatasetExample] = []
        seen_example_ids: set[str] = set()
        for example in self.examples:
            if not isinstance(example, MultimodalDatasetExample):
                raise TypeError("examples must contain MultimodalDatasetExample objects")
            if example.example_id in seen_example_ids:
                raise ValueError(f"duplicate example_id: {example.example_id}")
            seen_example_ids.add(example.example_id)
            examples.append(example)
        if not examples:
            raise ValueError("examples must not be empty")
        object.__setattr__(self, "examples", tuple(examples))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if self.status not in {"ready", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")

    @property
    def example_count(self) -> int:
        return len(self.examples)

    @property
    def selected_example_ids(self) -> tuple[str, ...]:
        return tuple(example.example_id for example in self.examples)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "requested_modalities": list(self.requested_modalities),
            "storage_runtime_status": self.storage_runtime_status,
            "status": self.status,
            "example_count": self.example_count,
            "selected_example_ids": list(self.selected_example_ids),
            "examples": [example.to_dict() for example in self.examples],
            "provenance_refs": list(self.provenance_refs),
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MultimodalDataset:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            dataset_id=payload.get("dataset_id") or payload.get("id") or "",
            package_id=payload.get("package_id") or payload.get("package") or "",
            package_manifest_id=payload.get("package_manifest_id")
            or payload.get("manifest_id")
            or "",
            requested_modalities=payload.get("requested_modalities")
            or payload.get("modalities")
            or (),
            storage_runtime_status=payload.get("storage_runtime_status")
            or payload.get("status")
            or "unresolved",
            examples=tuple(
                item
                if isinstance(item, MultimodalDatasetExample)
                else MultimodalDatasetExample.from_dict(item)
                for item in _iter_values(payload.get("examples") or payload.get("records") or ())
            ),
            provenance_refs=payload.get("provenance_refs") or payload.get("provenance") or (),
            issues=tuple(
                item
                if isinstance(item, MultimodalDatasetIssue)
                else MultimodalDatasetIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
            schema_version=int(payload.get("schema_version") or 1),
            status=payload.get("status") or "unresolved",
        )


def _ppi_records_for_example(
    example: PackageManifestExample,
    ppi_index: Mapping[str, list[PPIRepresentationRecord]] | None,
) -> tuple[PPIRepresentationRecord, ...]:
    if not ppi_index:
        return ()
    matched: list[PPIRepresentationRecord] = []
    seen_summary_ids: set[str] = set()
    for reference in _dedupe_preserve_order(example.source_record_refs):
        for record in ppi_index.get(reference, ()):
            if record.summary_id in seen_summary_ids:
                continue
            seen_summary_ids.add(record.summary_id)
            matched.append(record)
    return tuple(matched)


def _requested_modalities_with_refs(
    requested_modalities: tuple[str, ...],
    modality_refs: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    available: list[str] = []
    resolved_lookup = {modality.casefold(): modality for modality in modality_refs}
    for requested_modality in requested_modalities:
        if requested_modality.casefold() in resolved_lookup:
            available.append(requested_modality)
    return tuple(available)


def _dataset_status(examples: Iterable[MultimodalDatasetExample]) -> MultimodalDatasetStatus:
    example_list = tuple(examples)
    if all(example.status == "ready" for example in example_list):
        return "ready"
    if any(example.available_modalities for example in example_list):
        return "partial"
    return "unresolved"


def _collect_dataset_provenance(
    storage_runtime: StorageRuntimeResult,
    ppi_representation: PPIRepresentation | None,
    provenance: Iterable[str],
) -> tuple[str, ...]:
    refs: list[str] = [
        storage_runtime.package_manifest.manifest_id,
        storage_runtime.selective_materialization.manifest_id,
        storage_runtime.package_build.package_manifest.manifest_id,
        *storage_runtime.package_manifest.provenance,
        *storage_runtime.selective_materialization.provenance_refs,
        *storage_runtime.notes,
        *provenance,
    ]
    if ppi_representation is not None:
        refs.extend(ppi_representation.provenance)
        if ppi_representation.source_manifest_id is not None:
            refs.append(ppi_representation.source_manifest_id)
    return _dedupe_text(refs)


def _match_ppi_records(
    ppi_representation: PPIRepresentation | None,
) -> dict[str, list[PPIRepresentationRecord]]:
    if ppi_representation is None:
        return {}
    index: dict[str, list[PPIRepresentationRecord]] = {}
    for record in ppi_representation.records:
        for key in _dedupe_preserve_order(
            (record.summary_id, record.pair_id, *record.source_record_ids),
        ):
            index.setdefault(key, []).append(record)
    return index


def _select_example_materialization(
    example: PackageManifestExample,
    runtime_index: Mapping[str, SelectiveMaterializationExample],
) -> tuple[SelectiveMaterializationExample | None, MultimodalDatasetIssue | None]:
    materialized = runtime_index.get(example.example_id)
    if materialized is not None:
        return materialized, None
    issue = MultimodalDatasetIssue(
        example_id=example.example_id,
        kind="missing_selected_example",
        message="selected example is not present in the selective materialization result",
        details={
            "package_example_id": example.example_id,
            "package_planning_index_ref": example.planning_index_ref,
        },
    )
    return None, issue


def build_multimodal_dataset(
    storage_runtime: StorageRuntimeResult,
    *,
    ppi_representation: PPIRepresentation | Mapping[str, Any] | None = None,
    dataset_id: str | None = None,
    requested_modalities: Iterable[str] = DEFAULT_MULTIMODAL_MODALITIES,
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> MultimodalDataset:
    if not isinstance(storage_runtime, StorageRuntimeResult):
        raise TypeError("storage_runtime must be a StorageRuntimeResult")
    if ppi_representation is not None and not isinstance(
        ppi_representation,
        (PPIRepresentation, Mapping),
    ):
        raise TypeError("ppi_representation must be a PPIRepresentation, mapping, or None")

    ppi_representation_obj = (
        None
        if ppi_representation is None
        else ppi_representation
        if isinstance(ppi_representation, PPIRepresentation)
        else PPIRepresentation.from_dict(ppi_representation)
    )
    requested_modalities_tuple = _dedupe_preserve_order(
        _normalize_modality(modality) for modality in requested_modalities
    )
    if not requested_modalities_tuple:
        requested_modalities_tuple = DEFAULT_MULTIMODAL_MODALITIES

    runtime_examples = {
        example.example_id: example
        for example in storage_runtime.selective_materialization.selected_examples
    }
    ppi_index = _match_ppi_records(ppi_representation_obj)
    dataset_examples: list[MultimodalDatasetExample] = []
    dataset_issues: list[MultimodalDatasetIssue] = []

    for package_example in storage_runtime.package_manifest.selected_examples:
        materialized_example, missing_example_issue = _select_example_materialization(
            package_example,
            runtime_examples,
        )
        example_issues: list[MultimodalDatasetIssue] = []
        if missing_example_issue is not None:
            example_issues.append(missing_example_issue)
            dataset_issues.append(missing_example_issue)

        materialized_artifacts: tuple[SelectiveMaterializationArtifact, ...] = ()
        provenance_refs: list[str] = [
            storage_runtime.package_manifest.manifest_id,
            storage_runtime.selective_materialization.manifest_id,
            *storage_runtime.package_manifest.provenance,
            *package_example.source_record_refs,
            *package_example.notes,
        ]
        if materialized_example is not None:
            materialized_artifacts = materialized_example.materialized_artifacts
            provenance_refs.extend(materialized_example.provenance_refs)
            provenance_refs.extend(materialized_example.notes)
            for issue in materialized_example.issues:
                example_issue = MultimodalDatasetIssue(
                    example_id=package_example.example_id,
                    kind="missing_requested_modality",
                    message=issue.message,
                    modality=issue.artifact_pointer,
                    artifact_pointer=issue.artifact_pointer,
                    details=issue.details,
                )
                example_issues.append(example_issue)
                dataset_issues.append(example_issue)

        modality_refs: dict[str, list[str]] = {}
        resolved_modalities: list[str] = []

        for artifact in materialized_artifacts:
            modality = _artifact_kind_modality(artifact.artifact_pointer)
            modality_refs.setdefault(modality, []).append(artifact.materialized_ref)
            resolved_modalities.append(modality)
            provenance_refs.extend(artifact.provenance_refs)
            provenance_refs.extend(artifact.notes)

        matched_ppi_records = _ppi_records_for_example(package_example, ppi_index)
        if matched_ppi_records:
            modality_refs.setdefault("ppi", []).extend(
                record.summary_id for record in matched_ppi_records
            )
            resolved_modalities.append("ppi")
            for record in matched_ppi_records:
                provenance_refs.extend(
                    pointer.provenance_id
                    for pointer in record.provenance_pointers
                    if pointer.provenance_id is not None
                )
                provenance_refs.extend(
                    pointer.source_record_id
                    for pointer in record.provenance_pointers
                    if pointer.source_record_id is not None
                )
        elif "ppi" in requested_modalities_tuple:
            issue = MultimodalDatasetIssue(
                example_id=package_example.example_id,
                kind="missing_ppi_representation_record",
                message="selected example did not resolve a matching PPI representation record",
                modality="ppi",
                details={
                    "source_record_refs": list(package_example.source_record_refs),
                    "package_manifest_id": storage_runtime.package_manifest.manifest_id,
                },
            )
            example_issues.append(issue)
            dataset_issues.append(issue)

        normalized_modality_refs = {
            modality: _dedupe_preserve_order(values)
            for modality, values in modality_refs.items()
        }
        available_modalities = _requested_modalities_with_refs(
            requested_modalities_tuple,
            normalized_modality_refs,
        )
        missing_modalities = tuple(
            modality
            for modality in requested_modalities_tuple
            if modality.casefold()
            not in {item.casefold() for item in available_modalities}
        )
        for modality in missing_modalities:
            issue = MultimodalDatasetIssue(
                example_id=package_example.example_id,
                kind="missing_requested_modality",
                message="requested modality was not available for the selected example",
                modality=modality,
                details={
                    "package_manifest_id": storage_runtime.package_manifest.manifest_id,
                    "selected_example_id": package_example.example_id,
                },
            )
            example_issues.append(issue)
            dataset_issues.append(issue)

        example_status: MultimodalDatasetStatus
        if not available_modalities:
            example_status = "unresolved"
        elif example_issues:
            example_status = "partial"
        else:
            example_status = "ready"

        dataset_examples.append(
            MultimodalDatasetExample(
                selected_example=package_example,
                materialized_artifacts=materialized_artifacts,
                ppi_records=matched_ppi_records,
                resolved_modalities=tuple(resolved_modalities),
                available_modalities=available_modalities,
                missing_modalities=missing_modalities,
                modality_refs={
                    key: tuple(values)
                    for key, values in normalized_modality_refs.items()
                },
                provenance_refs=_dedupe_text(provenance_refs),
                issues=tuple(example_issues),
                notes=package_example.notes,
                status=example_status,
            )
        )

    return MultimodalDataset(
        dataset_id=dataset_id or f"multimodal:{storage_runtime.package_manifest.manifest_id}",
        package_id=storage_runtime.package_manifest.package_id,
        package_manifest_id=storage_runtime.package_manifest.manifest_id,
        requested_modalities=requested_modalities_tuple,
        storage_runtime_status=storage_runtime.status,
        examples=tuple(dataset_examples),
        provenance_refs=_collect_dataset_provenance(
            storage_runtime,
            ppi_representation_obj,
            provenance,
        ),
        issues=tuple(dataset_issues),
        notes=_dedupe_text((*storage_runtime.notes, *notes)),
        status=_dataset_status(dataset_examples),
    )


@dataclass(frozen=True, slots=True)
class MultimodalDatasetAdapter:
    requested_modalities: tuple[str, ...] = DEFAULT_MULTIMODAL_MODALITIES
    dataset_id: str | None = None

    def adapt(
        self,
        storage_runtime: StorageRuntimeResult,
        *,
        ppi_representation: PPIRepresentation | Mapping[str, Any] | None = None,
        provenance: Iterable[str] = (),
        notes: Iterable[str] = (),
    ) -> MultimodalDataset:
        return build_multimodal_dataset(
            storage_runtime,
            ppi_representation=ppi_representation,
            dataset_id=self.dataset_id,
            requested_modalities=self.requested_modalities,
            provenance=provenance,
            notes=notes,
        )

    def adapt_many(
        self,
        values: Iterable[StorageRuntimeResult],
        *,
        ppi_representation: PPIRepresentation | Mapping[str, Any] | None = None,
        provenance: Iterable[str] = (),
        notes: Iterable[str] = (),
    ) -> tuple[MultimodalDataset, ...]:
        return tuple(
            self.adapt(
                value,
                ppi_representation=ppi_representation,
                provenance=provenance,
                notes=notes,
            )
            for value in values
        )


def validate_multimodal_dataset_payload(payload: Mapping[str, Any]) -> MultimodalDataset:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return MultimodalDataset.from_dict(payload)


__all__ = [
    "DEFAULT_MULTIMODAL_MODALITIES",
    "MultimodalDataset",
    "MultimodalDatasetAdapter",
    "MultimodalDatasetExample",
    "MultimodalDatasetIssue",
    "MultimodalDatasetIssueKind",
    "MultimodalDatasetStatus",
    "build_multimodal_dataset",
    "validate_multimodal_dataset_payload",
]
