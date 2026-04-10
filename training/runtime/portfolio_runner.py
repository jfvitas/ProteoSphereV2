from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from datasets.multimodal.adapter import DEFAULT_MULTIMODAL_MODALITIES
from execution.storage_runtime import StorageRuntimeResult
from training.runtime.experiment_registry import (
    DEFAULT_EXPERIMENT_REGISTRY_ID,
    ExperimentRegistry,
    ExperimentRegistryBlocker,
    ExperimentRegistryRecord,
    build_experiment_registry,
)

DEFAULT_PORTFOLIO_RUNNER_ID = "multimodal-portfolio-runner:v1"
DEFAULT_PORTFOLIO_MATRIX_ID = "multimodal-portfolio-matrix:v1"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


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
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _fingerprint(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _relative_path(path: Path) -> str:
    root = Path(__file__).resolve().parents[2]
    return str(path.resolve().relative_to(root)).replace("\\", "/")


def _normalize_modalities(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(
        modality
        for modality in _dedupe_text(values)
        if modality in DEFAULT_MULTIMODAL_MODALITIES
    )
    if not normalized:
        raise ValueError("requested_modalities must include at least one supported modality")
    return normalized


def _normalize_opt_modalities(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        modality
        for modality in _dedupe_text(values)
        if modality in DEFAULT_MULTIMODAL_MODALITIES
    )


def _coerce_candidate(value: PortfolioCandidateSpec | Mapping[str, Any]) -> PortfolioCandidateSpec:
    if isinstance(value, PortfolioCandidateSpec):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("candidate values must be PortfolioCandidateSpec objects or mappings")
    return PortfolioCandidateSpec(
        candidate_id=value.get("candidate_id") or value.get("id") or "",
        rank=int(value.get("rank") or 0),
        model_name=value.get("model_name") or value.get("model") or "",
        requested_modalities=value.get("requested_modalities")
        or value.get("modalities")
        or (),
        fusion_dim=int(value.get("fusion_dim") or 8),
        notes=value.get("notes") or value.get("note") or (),
        tags=value.get("tags") or (),
    )


def _coerce_ablation(value: PortfolioAblationSpec | Mapping[str, Any]) -> PortfolioAblationSpec:
    if isinstance(value, PortfolioAblationSpec):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("ablation values must be PortfolioAblationSpec objects or mappings")
    return PortfolioAblationSpec(
        ablation_id=value.get("ablation_id") or value.get("id") or "",
        rank_offset=int(value.get("rank_offset") or 0),
        drop_modalities=value.get("drop_modalities") or value.get("drop") or (),
        keep_only_modalities=value.get("keep_only_modalities")
        or value.get("keep_only")
        or (),
        notes=value.get("notes") or value.get("note") or (),
        tags=value.get("tags") or (),
    )


def _apply_ablation(
    requested_modalities: tuple[str, ...],
    ablation: PortfolioAblationSpec,
) -> tuple[str, ...]:
    result = list(requested_modalities)
    if ablation.keep_only_modalities:
        keep = set(ablation.keep_only_modalities)
        result = [modality for modality in result if modality in keep]
    if ablation.drop_modalities:
        drop = set(ablation.drop_modalities)
        result = [modality for modality in result if modality not in drop]
    normalized = _normalize_opt_modalities(result)
    if not normalized:
        raise ValueError(f"ablation {ablation.ablation_id!r} removes all supported modalities")
    return normalized


@dataclass(frozen=True, slots=True)
class PortfolioCandidateSpec:
    candidate_id: str
    rank: int
    model_name: str
    requested_modalities: tuple[str, ...]
    fusion_dim: int = 8
    notes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _clean_text(self.candidate_id))
        object.__setattr__(self, "model_name", _clean_text(self.model_name))
        object.__setattr__(self, "rank", int(self.rank))
        object.__setattr__(
            self,
            "requested_modalities",
            _normalize_modalities(self.requested_modalities),
        )
        object.__setattr__(self, "fusion_dim", int(self.fusion_dim))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "tags", _dedupe_text(self.tags))
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty")
        if not self.model_name:
            raise ValueError("model_name must not be empty")
        if self.fusion_dim < 1:
            raise ValueError("fusion_dim must be >= 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "rank": self.rank,
            "model_name": self.model_name,
            "requested_modalities": list(self.requested_modalities),
            "fusion_dim": self.fusion_dim,
            "notes": list(self.notes),
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class PortfolioAblationSpec:
    ablation_id: str
    rank_offset: int = 0
    drop_modalities: tuple[str, ...] = ()
    keep_only_modalities: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ablation_id", _clean_text(self.ablation_id))
        object.__setattr__(self, "rank_offset", int(self.rank_offset))
        object.__setattr__(
            self,
            "drop_modalities",
            _normalize_opt_modalities(self.drop_modalities),
        )
        object.__setattr__(
            self,
            "keep_only_modalities",
            _normalize_opt_modalities(self.keep_only_modalities),
        )
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "tags", _dedupe_text(self.tags))
        if not self.ablation_id:
            raise ValueError("ablation_id must not be empty")
        if not self.drop_modalities and not self.keep_only_modalities:
            raise ValueError("ablation must define drop_modalities or keep_only_modalities")

    def to_dict(self) -> dict[str, object]:
        return {
            "ablation_id": self.ablation_id,
            "rank_offset": self.rank_offset,
            "drop_modalities": list(self.drop_modalities),
            "keep_only_modalities": list(self.keep_only_modalities),
            "notes": list(self.notes),
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class PortfolioSliceSpec:
    slice_id: str
    candidate_id: str
    rank: int
    model_name: str
    requested_modalities: tuple[str, ...]
    fusion_dim: int = 8
    ablation_id: str | None = None
    parent_slice_id: str | None = None
    notes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "slice_id", _clean_text(self.slice_id))
        object.__setattr__(self, "candidate_id", _clean_text(self.candidate_id))
        object.__setattr__(self, "rank", int(self.rank))
        object.__setattr__(self, "model_name", _clean_text(self.model_name))
        object.__setattr__(
            self,
            "requested_modalities",
            _normalize_modalities(self.requested_modalities),
        )
        object.__setattr__(self, "fusion_dim", int(self.fusion_dim))
        object.__setattr__(self, "ablation_id", _clean_text(self.ablation_id) or None)
        object.__setattr__(
            self,
            "parent_slice_id",
            _clean_text(self.parent_slice_id) or None,
        )
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "tags", _dedupe_text(self.tags))
        if not self.slice_id:
            raise ValueError("slice_id must not be empty")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty")
        if not self.model_name:
            raise ValueError("model_name must not be empty")
        if self.fusion_dim < 1:
            raise ValueError("fusion_dim must be >= 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "slice_id": self.slice_id,
            "candidate_id": self.candidate_id,
            "rank": self.rank,
            "model_name": self.model_name,
            "requested_modalities": list(self.requested_modalities),
            "fusion_dim": self.fusion_dim,
            "ablation_id": self.ablation_id,
            "parent_slice_id": self.parent_slice_id,
            "notes": list(self.notes),
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class PortfolioSliceRecord:
    slice_id: str
    experiment_id: str
    registry_id: str
    registry_signature: str
    checkpoint_ref: str
    model_name: str
    requested_modalities: tuple[str, ...]
    fusion_modalities: tuple[str, ...]
    observed_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    storage_runtime_status: str
    backend_ready: bool
    contract_fidelity: str
    deterministic_seed: int
    blocker: ExperimentRegistryBlocker | None = None
    runtime_status: Mapping[str, Any] = field(default_factory=dict)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "slice_id", _clean_text(self.slice_id))
        object.__setattr__(self, "experiment_id", _clean_text(self.experiment_id))
        object.__setattr__(self, "registry_id", _clean_text(self.registry_id))
        object.__setattr__(self, "registry_signature", _clean_text(self.registry_signature))
        object.__setattr__(self, "checkpoint_ref", _clean_text(self.checkpoint_ref))
        object.__setattr__(self, "model_name", _clean_text(self.model_name))
        object.__setattr__(
            self,
            "requested_modalities",
            _normalize_modalities(self.requested_modalities),
        )
        object.__setattr__(
            self,
            "fusion_modalities",
            _normalize_opt_modalities(self.fusion_modalities),
        )
        object.__setattr__(
            self,
            "observed_modalities",
            _normalize_opt_modalities(self.observed_modalities),
        )
        object.__setattr__(
            self,
            "missing_modalities",
            _normalize_opt_modalities(self.missing_modalities),
        )
        object.__setattr__(
            self,
            "storage_runtime_status",
            _clean_text(self.storage_runtime_status),
        )
        object.__setattr__(self, "backend_ready", bool(self.backend_ready))
        object.__setattr__(self, "contract_fidelity", _clean_text(self.contract_fidelity))
        if not isinstance(self.runtime_status, Mapping):
            raise TypeError("runtime_status must be a mapping")
        object.__setattr__(self, "runtime_status", dict(self.runtime_status))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not self.slice_id:
            raise ValueError("slice_id must not be empty")
        if not self.experiment_id:
            raise ValueError("experiment_id must not be empty")
        if not self.registry_id:
            raise ValueError("registry_id must not be empty")
        if not self.registry_signature:
            raise ValueError("registry_signature must not be empty")
        if not self.checkpoint_ref:
            raise ValueError("checkpoint_ref must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "slice_id": self.slice_id,
            "experiment_id": self.experiment_id,
            "registry_id": self.registry_id,
            "registry_signature": self.registry_signature,
            "checkpoint_ref": self.checkpoint_ref,
            "model_name": self.model_name,
            "requested_modalities": list(self.requested_modalities),
            "fusion_modalities": list(self.fusion_modalities),
            "observed_modalities": list(self.observed_modalities),
            "missing_modalities": list(self.missing_modalities),
            "storage_runtime_status": self.storage_runtime_status,
            "backend_ready": self.backend_ready,
            "contract_fidelity": self.contract_fidelity,
            "deterministic_seed": self.deterministic_seed,
            "blocker": self.blocker.to_dict() if self.blocker is not None else None,
            "runtime_status": dict(self.runtime_status),
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class PortfolioMatrixRun:
    runner_id: str
    matrix_id: str
    slices: tuple[PortfolioSliceSpec, ...]
    records: tuple[PortfolioSliceRecord, ...]
    source_path: str
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "runner_id", _clean_text(self.runner_id))
        object.__setattr__(self, "matrix_id", _clean_text(self.matrix_id))
        object.__setattr__(self, "source_path", _clean_text(self.source_path))
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        if not self.runner_id:
            raise ValueError("runner_id must not be empty")
        if not self.matrix_id:
            raise ValueError("matrix_id must not be empty")
        if not self.source_path:
            raise ValueError("source_path must not be empty")
        slice_ids: set[str] = set()
        for slice_spec in self.slices:
            if not isinstance(slice_spec, PortfolioSliceSpec):
                raise TypeError("slices must contain PortfolioSliceSpec objects")
            if slice_spec.slice_id in slice_ids:
                raise ValueError(f"duplicate slice_id: {slice_spec.slice_id}")
            slice_ids.add(slice_spec.slice_id)
        record_slice_ids: set[str] = set()
        for record in self.records:
            if not isinstance(record, PortfolioSliceRecord):
                raise TypeError("records must contain PortfolioSliceRecord objects")
            if record.slice_id in record_slice_ids:
                raise ValueError(f"duplicate record slice_id: {record.slice_id}")
            record_slice_ids.add(record.slice_id)
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def slice_count(self) -> int:
        return len(self.slices)

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def run_signature(self) -> str:
        return _fingerprint(
            {
                "runner_id": self.runner_id,
                "matrix_id": self.matrix_id,
                "slices": [slice_spec.to_dict() for slice_spec in self.slices],
                "records": [record.to_dict() for record in self.records],
                "provenance_refs": list(self.provenance_refs),
                "notes": list(self.notes),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "runner_id": self.runner_id,
            "matrix_id": self.matrix_id,
            "slice_count": self.slice_count,
            "record_count": self.record_count,
            "run_signature": self.run_signature,
            "source_path": self.source_path,
            "slices": [slice_spec.to_dict() for slice_spec in self.slices],
            "records": [record.to_dict() for record in self.records],
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
        }


def expand_portfolio_matrix(
    candidates: Sequence[PortfolioCandidateSpec | Mapping[str, Any]],
    *,
    ablations: Sequence[PortfolioAblationSpec | Mapping[str, Any]] = (),
) -> tuple[PortfolioSliceSpec, ...]:
    normalized_candidates = tuple(_coerce_candidate(candidate) for candidate in candidates)
    normalized_ablations = tuple(_coerce_ablation(ablation) for ablation in ablations)
    slices: list[PortfolioSliceSpec] = []
    seen_slice_ids: set[str] = set()
    for candidate in sorted(
        normalized_candidates,
        key=lambda item: (item.rank, item.candidate_id),
    ):
        base_slice_id = f"{candidate.candidate_id}:base"
        if base_slice_id in seen_slice_ids:
            raise ValueError(f"duplicate slice_id: {base_slice_id}")
        seen_slice_ids.add(base_slice_id)
        base_slice = PortfolioSliceSpec(
            slice_id=base_slice_id,
            candidate_id=candidate.candidate_id,
            rank=candidate.rank,
            model_name=candidate.model_name,
            requested_modalities=candidate.requested_modalities,
            fusion_dim=candidate.fusion_dim,
            notes=candidate.notes,
            tags=(*candidate.tags, "base"),
        )
        slices.append(base_slice)
        for ablation in normalized_ablations:
            slice_id = f"{candidate.candidate_id}:{ablation.ablation_id}"
            if slice_id in seen_slice_ids:
                raise ValueError(f"duplicate slice_id: {slice_id}")
            seen_slice_ids.add(slice_id)
            slices.append(
                PortfolioSliceSpec(
                    slice_id=slice_id,
                    candidate_id=candidate.candidate_id,
                    rank=candidate.rank + ablation.rank_offset,
                    model_name=candidate.model_name,
                    requested_modalities=_apply_ablation(candidate.requested_modalities, ablation),
                    fusion_dim=candidate.fusion_dim,
                    ablation_id=ablation.ablation_id,
                    parent_slice_id=base_slice.slice_id,
                    notes=(*candidate.notes, *ablation.notes),
                    tags=(*candidate.tags, *ablation.tags),
                )
            )
    return tuple(slices)


def _record_from_registry(
    slice_spec: PortfolioSliceSpec,
    registry: ExperimentRegistry,
    *,
    deterministic_seed: int,
) -> PortfolioSliceRecord:
    if registry.record_count != 1:
        raise ValueError(
            "portfolio runner expects each registry build to yield exactly one record"
        )
    record: ExperimentRegistryRecord = registry.records[0]
    return PortfolioSliceRecord(
        slice_id=slice_spec.slice_id,
        experiment_id=record.experiment_id,
        registry_id=registry.registry_id,
        registry_signature=registry.registry_signature,
        checkpoint_ref=record.checkpoint_ref,
        model_name=record.model_name,
        requested_modalities=record.requested_modalities,
        fusion_modalities=record.fusion_modalities,
        observed_modalities=record.observed_modalities,
        missing_modalities=record.missing_modalities,
        storage_runtime_status=record.storage_runtime_status,
        backend_ready=record.backend_ready,
        contract_fidelity=record.contract_fidelity,
        deterministic_seed=deterministic_seed,
        blocker=record.blocker,
        runtime_status=record.runtime_status,
        provenance_refs=(*registry.provenance_refs, *record.provenance_refs),
        notes=(*slice_spec.notes, *registry.notes, *record.notes),
    )


def run_portfolio_matrix(
    storage_runtime: StorageRuntimeResult,
    slices: Sequence[PortfolioSliceSpec | Mapping[str, Any]],
    *,
    ppi_representation: Mapping[str, Any] | Any | None = None,
    registry_builder: Callable[..., ExperimentRegistry] = build_experiment_registry,
    runner_id: str = DEFAULT_PORTFOLIO_RUNNER_ID,
    matrix_id: str = DEFAULT_PORTFOLIO_MATRIX_ID,
    registry_id: str = DEFAULT_EXPERIMENT_REGISTRY_ID,
    deterministic_seed_base: int = 0,
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> PortfolioMatrixRun:
    if not isinstance(storage_runtime, StorageRuntimeResult):
        raise TypeError("storage_runtime must be a StorageRuntimeResult")
    if deterministic_seed_base < 0:
        raise ValueError("deterministic_seed_base must be non-negative")
    normalized_slices = tuple(
        slice_spec
        if isinstance(slice_spec, PortfolioSliceSpec)
        else PortfolioSliceSpec(
            slice_id=slice_spec.get("slice_id") or slice_spec.get("id") or "",
            candidate_id=slice_spec.get("candidate_id") or "",
            rank=int(slice_spec.get("rank") or 0),
            model_name=slice_spec.get("model_name") or slice_spec.get("model") or "",
            requested_modalities=slice_spec.get("requested_modalities")
            or slice_spec.get("modalities")
            or (),
            fusion_dim=int(slice_spec.get("fusion_dim") or 8),
            ablation_id=slice_spec.get("ablation_id"),
            parent_slice_id=slice_spec.get("parent_slice_id"),
            notes=slice_spec.get("notes") or (),
            tags=slice_spec.get("tags") or (),
        )
        for slice_spec in slices
    )
    records: list[PortfolioSliceRecord] = []
    provenance_refs = _dedupe_text(
        (
            storage_runtime.package_manifest.manifest_id,
            storage_runtime.selective_materialization.manifest_id,
            *storage_runtime.package_manifest.provenance,
            *storage_runtime.selective_materialization.provenance_refs,
            *provenance,
        )
    )
    run_notes = _dedupe_text((*storage_runtime.notes, *notes))
    for index, slice_spec in enumerate(normalized_slices):
        slice_seed = deterministic_seed_base + index
        registry = registry_builder(
            storage_runtime,
            ppi_representation=ppi_representation,
            registry_id=registry_id,
            requested_modalities=slice_spec.requested_modalities,
            model_name=slice_spec.model_name,
            fusion_dim=slice_spec.fusion_dim,
            deterministic_seed=slice_seed,
            provenance=(
                *provenance_refs,
                f"portfolio_slice:{slice_spec.slice_id}",
            ),
            notes=(
                *slice_spec.notes,
                f"portfolio_seed:{slice_seed}",
            ),
        )
        records.append(_record_from_registry(slice_spec, registry, deterministic_seed=slice_seed))
    return PortfolioMatrixRun(
        runner_id=runner_id,
        matrix_id=matrix_id,
        slices=normalized_slices,
        records=tuple(records),
        source_path=_relative_path(Path(__file__)),
        provenance_refs=provenance_refs,
        notes=run_notes,
    )


__all__ = [
    "DEFAULT_PORTFOLIO_MATRIX_ID",
    "DEFAULT_PORTFOLIO_RUNNER_ID",
    "PortfolioAblationSpec",
    "PortfolioCandidateSpec",
    "PortfolioMatrixRun",
    "PortfolioSliceRecord",
    "PortfolioSliceSpec",
    "expand_portfolio_matrix",
    "run_portfolio_matrix",
]
