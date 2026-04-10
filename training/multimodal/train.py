from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from datasets.multimodal.adapter import (
    DEFAULT_MULTIMODAL_MODALITIES,
    MultimodalDataset,
    MultimodalDatasetAdapter,
)
from execution.storage_runtime import StorageRuntimeResult
from features.ppi_representation import PPIRepresentation
from models.multimodal.fusion_model import (
    DEFAULT_FUSION_DIM,
    DEFAULT_FUSION_MODEL,
    DEFAULT_MODALITY_ORDER,
    FusionModel,
)

if TYPE_CHECKING:
    from training.multimodal.runtime import ExecutableMultimodalTrainingResult

type Scalar = str | int | float | bool

MultimodalTrainingStatus = Literal["blocked", "completed", "paused"]


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


def _slug_segment(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return "unknown"
    return (
        text.replace("\\", "-")
        .replace("/", "-")
        .replace(":", "-")
        .replace(" ", "-")
        .replace("_", "-")
    )


def _dataset_modalities(dataset: MultimodalDataset) -> tuple[str, ...]:
    observed: list[str] = []
    seen: set[str] = set()
    for modality in dataset.requested_modalities:
        if any(modality in example.available_modalities for example in dataset.examples):
            key = modality.casefold()
            if key not in seen:
                seen.add(key)
                observed.append(modality)
    return tuple(observed)


def _example_status_counts(dataset: MultimodalDataset) -> dict[str, int]:
    counts = {"ready": 0, "partial": 0, "unresolved": 0}
    for example in dataset.examples:
        counts[example.status] += 1
    return counts


def _fusion_modalities(requested_modalities: tuple[str, ...]) -> tuple[str, ...]:
    supported = tuple(
        modality for modality in requested_modalities if modality in DEFAULT_MODALITY_ORDER
    )
    if not supported:
        raise ValueError("requested_modalities must include at least one fusion-supported modality")
    return supported


def _fusion_model_payload(model: FusionModel) -> dict[str, object]:
    return {
        "model_name": model.model_name,
        "fusion_dim": model.fusion_dim,
        "source_kind": model.source_kind,
        "modalities": list(model.modalities),
    }


def _dataset_signature(dataset: MultimodalDataset) -> str:
    payload = {
        "dataset_id": dataset.dataset_id,
        "package_id": dataset.package_id,
        "package_manifest_id": dataset.package_manifest_id,
        "requested_modalities": list(dataset.requested_modalities),
        "selected_example_ids": list(dataset.selected_example_ids),
        "example_statuses": [example.status for example in dataset.examples],
        "provenance_refs": list(dataset.provenance_refs),
        "notes": list(dataset.notes),
        "storage_runtime_status": dataset.storage_runtime_status,
    }
    return _fingerprint(payload)


@dataclass(frozen=True, slots=True)
class MultimodalTrainingBlocker:
    stage: str
    requested_backend: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage,
            "requested_backend": self.requested_backend,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class MultimodalTrainingSpec:
    model_name: str
    fusion_dim: int
    requested_modalities: tuple[str, ...]
    fusion_modalities: tuple[str, ...]
    dataset_id: str
    source_path: str
    config: dict[str, Scalar]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "fusion_dim": self.fusion_dim,
            "requested_modalities": list(self.requested_modalities),
            "fusion_modalities": list(self.fusion_modalities),
            "dataset_id": self.dataset_id,
            "source_path": self.source_path,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class MultimodalTrainingRuntimeStatus:
    stage: str
    requested_backend: str
    resolved_backend: str
    backend_ready: bool
    contract_fidelity: str
    provenance: dict[str, object] = field(default_factory=dict)
    blocker: MultimodalTrainingBlocker | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "requested_backend": self.requested_backend,
            "resolved_backend": self.resolved_backend,
            "backend_ready": self.backend_ready,
            "contract_fidelity": self.contract_fidelity,
            "provenance": dict(self.provenance),
            "blocker": self.blocker.to_dict() if self.blocker is not None else None,
        }


@dataclass(frozen=True, slots=True)
class MultimodalTrainingPlan:
    model_name: str
    fusion_dim: int
    dataset_id: str
    package_id: str
    package_manifest_id: str
    requested_modalities: tuple[str, ...]
    fusion_modalities: tuple[str, ...]
    observed_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    unsupported_requested_modalities: tuple[str, ...]
    example_count: int
    ready_example_count: int
    partial_example_count: int
    unresolved_example_count: int
    checkpoint_tag: str
    deterministic_seed: int
    plan_signature: str
    status: MultimodalTrainingRuntimeStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "fusion_dim": self.fusion_dim,
            "dataset_id": self.dataset_id,
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "requested_modalities": list(self.requested_modalities),
            "fusion_modalities": list(self.fusion_modalities),
            "observed_modalities": list(self.observed_modalities),
            "missing_modalities": list(self.missing_modalities),
            "unsupported_requested_modalities": list(self.unsupported_requested_modalities),
            "example_count": self.example_count,
            "ready_example_count": self.ready_example_count,
            "partial_example_count": self.partial_example_count,
            "unresolved_example_count": self.unresolved_example_count,
            "checkpoint_tag": self.checkpoint_tag,
            "deterministic_seed": self.deterministic_seed,
            "plan_signature": self.plan_signature,
            "status": self.status.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class MultimodalTrainingState:
    phase: str
    processed_examples: int
    checkpoint_tag: str
    deterministic_seed: int
    dataset_signature: str
    state_signature: str

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "processed_examples": self.processed_examples,
            "checkpoint_tag": self.checkpoint_tag,
            "deterministic_seed": self.deterministic_seed,
            "dataset_signature": self.dataset_signature,
            "state_signature": self.state_signature,
        }


@dataclass(frozen=True, slots=True)
class MultimodalTrainingBackendResult:
    spec: MultimodalTrainingSpec
    dataset: MultimodalDataset
    fusion_model: FusionModel
    plan: MultimodalTrainingPlan
    state: MultimodalTrainingState
    blockers: tuple[MultimodalTrainingBlocker, ...]

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_dict(),
            "dataset": self.dataset.to_dict(),
            "fusion_model": _fusion_model_payload(self.fusion_model),
            "plan": self.plan.to_dict(),
            "state": self.state.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def prepare_multimodal_training(
    storage_runtime: StorageRuntimeResult,
    *,
    ppi_representation: PPIRepresentation | Mapping[str, Any] | None = None,
    dataset_id: str | None = None,
    requested_modalities: Iterable[str] = DEFAULT_MULTIMODAL_MODALITIES,
    model_name: str = DEFAULT_FUSION_MODEL,
    fusion_dim: int = DEFAULT_FUSION_DIM,
    deterministic_seed: int = 0,
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> MultimodalTrainingBackendResult:
    if not isinstance(storage_runtime, StorageRuntimeResult):
        raise TypeError("storage_runtime must be a StorageRuntimeResult")
    if deterministic_seed < 0:
        raise ValueError("deterministic_seed must be non-negative")
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

    adapter = MultimodalDatasetAdapter(
        requested_modalities=tuple(requested_modalities),
        dataset_id=dataset_id,
    )
    dataset = adapter.adapt(
        storage_runtime,
        ppi_representation=ppi_representation_obj,
        provenance=provenance,
        notes=notes,
    )

    fusion_modalities = _fusion_modalities(dataset.requested_modalities)
    fusion_model = FusionModel(
        model_name=model_name,
        fusion_dim=fusion_dim,
        modalities=fusion_modalities,
    )

    observed_modalities = _dataset_modalities(dataset)
    missing_modalities = tuple(
        modality
        for modality in dataset.requested_modalities
        if modality.casefold() not in {item.casefold() for item in observed_modalities}
    )
    unsupported_requested_modalities = tuple(
        modality
        for modality in dataset.requested_modalities
        if modality not in fusion_model.modalities
    )
    counts = _example_status_counts(dataset)
    checkpoint_tag = f"{_slug_segment(dataset.package_manifest_id)}-seed-{deterministic_seed:04d}"
    dataset_signature = _dataset_signature(dataset)
    spec = MultimodalTrainingSpec(
        model_name=fusion_model.model_name,
        fusion_dim=fusion_model.fusion_dim,
        requested_modalities=dataset.requested_modalities,
        fusion_modalities=fusion_model.modalities,
        dataset_id=dataset.dataset_id,
        source_path=str(
            Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[2])
        ).replace("\\", "/"),
        config={
            "trainer_backend": "contract-plan-only",
            "checkpoint_policy": "deterministic",
            "dataset_adapter": "multimodal",
            "storage_runtime_status": storage_runtime.status,
            "fusion_modalities": ",".join(fusion_model.modalities),
            "requested_modalities": ",".join(dataset.requested_modalities),
        },
    )
    plan_signature = _fingerprint(
        {
            "spec": spec.to_dict(),
            "dataset_signature": dataset_signature,
            "observed_modalities": list(observed_modalities),
            "missing_modalities": list(missing_modalities),
            "unsupported_requested_modalities": list(unsupported_requested_modalities),
            "counts": counts,
            "checkpoint_tag": checkpoint_tag,
            "deterministic_seed": deterministic_seed,
        }
    )
    blocker = MultimodalTrainingBlocker(
        stage="trainer_runtime",
        requested_backend=f"{fusion_model.model_name}+multimodal-dataset-adapter",
        reason=(
            "The repository can materialize the multimodal dataset and capture a deterministic "
            "fusion contract, but no real multimodal trainer runtime is wired under "
            "training/multimodal yet."
        ),
    )
    status = MultimodalTrainingRuntimeStatus(
        stage="trainer_runtime",
        requested_backend=f"{fusion_model.model_name}+multimodal-dataset-adapter",
        resolved_backend="contract-plan-only",
        backend_ready=False,
        contract_fidelity="dataset-and-fusion-plan-only",
        provenance={
            "storage_runtime_status": storage_runtime.status,
            "dataset_id": dataset.dataset_id,
            "package_id": dataset.package_id,
            "package_manifest_id": dataset.package_manifest_id,
            "selected_example_ids": list(dataset.selected_example_ids),
            "requested_modalities": list(dataset.requested_modalities),
            "fusion_modalities": list(fusion_model.modalities),
            "observed_modalities": list(observed_modalities),
            "missing_modalities": list(missing_modalities),
            "unsupported_requested_modalities": list(unsupported_requested_modalities),
            "example_status_counts": counts,
            "provenance_refs": list(dataset.provenance_refs),
            "notes": list(dataset.notes),
            "real_components": [
                "multimodal dataset adapter",
                "fusion model contract",
                "storage/runtime provenance threading",
                "deterministic checkpoint tagging",
            ],
            "abstracted_components": [
                "optimizer step execution",
                "gradient accumulation",
                "distributed/GPU orchestration",
                "checkpoint serialization loop",
            ],
        },
        blocker=blocker,
    )
    plan = MultimodalTrainingPlan(
        model_name=fusion_model.model_name,
        fusion_dim=fusion_model.fusion_dim,
        dataset_id=dataset.dataset_id,
        package_id=dataset.package_id,
        package_manifest_id=dataset.package_manifest_id,
        requested_modalities=dataset.requested_modalities,
        fusion_modalities=fusion_model.modalities,
        observed_modalities=observed_modalities,
        missing_modalities=missing_modalities,
        unsupported_requested_modalities=unsupported_requested_modalities,
        example_count=dataset.example_count,
        ready_example_count=counts["ready"],
        partial_example_count=counts["partial"],
        unresolved_example_count=counts["unresolved"],
        checkpoint_tag=checkpoint_tag,
        deterministic_seed=deterministic_seed,
        plan_signature=plan_signature,
        status=status,
    )
    state_signature = _fingerprint(
        {
            "plan_signature": plan_signature,
            "phase": "blocked",
            "processed_examples": 0,
            "checkpoint_tag": checkpoint_tag,
            "deterministic_seed": deterministic_seed,
        }
    )
    state = MultimodalTrainingState(
        phase="blocked",
        processed_examples=0,
        checkpoint_tag=checkpoint_tag,
        deterministic_seed=deterministic_seed,
        dataset_signature=dataset_signature,
        state_signature=state_signature,
    )
    return MultimodalTrainingBackendResult(
        spec=spec,
        dataset=dataset,
        fusion_model=fusion_model,
        plan=plan,
        state=state,
        blockers=(blocker,),
    )


def train_multimodal_model(
    storage_runtime: StorageRuntimeResult,
    **kwargs: Any,
) -> ExecutableMultimodalTrainingResult:
    from training.multimodal.runtime import execute_multimodal_training

    return execute_multimodal_training(storage_runtime, **kwargs)


__all__ = [
    "MultimodalTrainingBackendResult",
    "MultimodalTrainingBlocker",
    "MultimodalTrainingPlan",
    "MultimodalTrainingRuntimeStatus",
    "MultimodalTrainingSpec",
    "MultimodalTrainingState",
    "prepare_multimodal_training",
    "train_multimodal_model",
]
