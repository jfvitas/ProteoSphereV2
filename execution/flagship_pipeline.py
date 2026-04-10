from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from hashlib import sha256
from typing import Any, Literal

from datasets.multimodal.adapter import DEFAULT_MULTIMODAL_MODALITIES
from evaluation.multimodal.metrics import MultimodalMetrics, summarize_multimodal_metrics
from execution.storage_runtime import StorageRuntimeResult
from features.esm2_embeddings import ProteinEmbeddingResult
from features.ppi_representation import PPIRepresentation
from models.multimodal.fusion_model import (
    DEFAULT_FUSION_DIM,
    DEFAULT_FUSION_MODEL,
    DEFAULT_MODALITY_ORDER,
    FusionModel,
    FusionModelResult,
)
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult
from models.multimodal.uncertainty import UncertaintyHead, UncertaintyHeadResult
from training.multimodal.train import MultimodalTrainingBackendResult, train_multimodal_model
from training.runtime.experiment_registry import ExperimentRegistry, build_experiment_registry
from training.runtime.gpu_policy import (
    DEFAULT_GPU_WORKER_LIMIT,
    GPUJobRequest,
    GPUSchedulingDecision,
    GPUSchedulingPolicy,
)

FlagshipPipelineStatus = Literal["ready", "partial", "blocked"]


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
    if is_dataclass(value):
        return {str(key): _json_ready(item) for key, item in asdict(value).items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = _json_ready(dict(payload))
    return sha256(str(encoded).encode("utf-8")).hexdigest()[:16]


def _pipeline_limitations(
    training_result: MultimodalTrainingBackendResult,
    dataset_status: str,
    fusion_result: FusionModelResult,
    uncertainty_result: UncertaintyHeadResult,
    gpu_decision: GPUSchedulingDecision,
) -> tuple[str, ...]:
    limitations: list[str] = []
    if training_result.plan.status.blocker is not None:
        limitations.append(training_result.plan.status.blocker.reason)
    if dataset_status != "ready":
        limitations.append(
            f"multimodal dataset status is {dataset_status}; the PPI lane may be partial"
        )
    if fusion_result.missing_modalities:
        limitations.append(
            "fusion result is missing modalities: " + ", ".join(fusion_result.missing_modalities)
        )
    if uncertainty_result.missing_modalities:
        limitations.append(
            "uncertainty result reports missing modalities: "
            + ", ".join(uncertainty_result.missing_modalities)
        )
    if not gpu_decision.allowed:
        limitations.append(gpu_decision.reason)
    return _dedupe_text(limitations)


def _pipeline_blockers(
    training_result: MultimodalTrainingBackendResult,
    gpu_decision: GPUSchedulingDecision,
) -> tuple[FlagshipPipelineBlocker, ...]:
    blockers: list[FlagshipPipelineBlocker] = []
    if training_result.plan.status.blocker is not None:
        blockers.append(
            FlagshipPipelineBlocker(
                stage=training_result.plan.status.blocker.stage,
                requested_backend=training_result.plan.status.blocker.requested_backend,
                reason=training_result.plan.status.blocker.reason,
            )
        )
    if not gpu_decision.allowed:
        blockers.append(
            FlagshipPipelineBlocker(
                stage="gpu_policy",
                requested_backend=_clean_text(gpu_decision.request.get("requested_device"))
                or "unknown",
                reason=gpu_decision.reason,
            )
        )
    return tuple(blockers)


def _prototype_training_view(
    training_result: Any,
) -> Any:
    blocker = training_result.plan.status.blocker
    if blocker is not None:
        return training_result
    conservative_blocker = FlagshipPipelineBlocker(
        stage="trainer_runtime",
        requested_backend=training_result.plan.status.requested_backend,
        reason=(
            "The repository can execute the multimodal runtime locally, but no real "
            "multimodal trainer runtime is wired under training/multimodal yet."
        ),
    )
    conservative_status = replace(
        training_result.plan.status,
        resolved_backend="contract-plan-only",
        backend_ready=False,
        contract_fidelity="dataset-and-fusion-plan-only",
        blocker=conservative_blocker,
        provenance={
            **training_result.plan.status.provenance,
            "runtime_resolved_backend": training_result.plan.status.resolved_backend,
            "runtime_state_signature": training_result.state.state_signature,
            "runtime_checkpoint_ref": training_result.checkpoint.checkpoint_ref,
        },
    )
    return replace(
        training_result,
        plan=replace(training_result.plan, status=conservative_status),
    )


@dataclass(frozen=True, slots=True)
class FlagshipPipelineBlocker:
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
class FlagshipPipelineResult:
    pipeline_id: str
    storage_runtime_status: str
    training: MultimodalTrainingBackendResult
    gpu_decision: GPUSchedulingDecision
    fusion_result: FusionModelResult
    uncertainty_result: UncertaintyHeadResult
    metrics: MultimodalMetrics
    experiment_registry: ExperimentRegistry
    blockers: tuple[FlagshipPipelineBlocker, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    status: FlagshipPipelineStatus = "partial"
    pipeline_signature: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "pipeline_id", _clean_text(self.pipeline_id))
        object.__setattr__(self, "storage_runtime_status", _clean_text(self.storage_runtime_status))
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(self, "limitations", _dedupe_text(self.limitations))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not self.pipeline_id:
            raise ValueError("pipeline_id must not be empty")
        if self.status not in {"ready", "partial", "blocked"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        if not self.pipeline_signature:
            object.__setattr__(
                self,
                "pipeline_signature",
                _fingerprint(
                    {
                        "pipeline_id": self.pipeline_id,
                        "status": self.status,
                        "storage_runtime_status": self.storage_runtime_status,
                        "training": self.training.plan.plan_signature,
                        "fusion": self.fusion_result.feature_vector,
                        "uncertainty": self.uncertainty_result.feature_vector,
                        "metrics": self.metrics.metrics_id,
                        "experiment_registry": self.experiment_registry.registry_signature,
                        "gpu_decision": self.gpu_decision.to_dict(),
                    }
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "status": self.status,
            "pipeline_signature": self.pipeline_signature,
            "storage_runtime_status": self.storage_runtime_status,
            "training": _json_ready(self.training.to_dict()),
            "gpu_decision": self.gpu_decision.to_dict(),
            "fusion_result": self.fusion_result.to_dict(),
            "uncertainty_result": self.uncertainty_result.to_dict(),
            "metrics": self.metrics.to_dict(),
            "experiment_registry": self.experiment_registry.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "limitations": list(self.limitations),
            "notes": list(self.notes),
        }


def run_flagship_pipeline(
    storage_runtime: StorageRuntimeResult,
    *,
    ppi_representation: PPIRepresentation | Mapping[str, Any] | None = None,
    sequence_embedding: ProteinEmbeddingResult | Mapping[str, Any] | Any | None = None,
    structure_embedding: StructureEmbeddingResult | Mapping[str, Any] | Any | None = None,
    ligand_embedding: LigandEmbeddingResult | Mapping[str, Any] | Any | None = None,
    requested_modalities: Iterable[str] = DEFAULT_MULTIMODAL_MODALITIES,
    model_name: str = DEFAULT_FUSION_MODEL,
    fusion_dim: int = DEFAULT_FUSION_DIM,
    deterministic_seed: int = 0,
    gpu_worker_limit: int = DEFAULT_GPU_WORKER_LIMIT,
    gpu_active_workers: Iterable[Any] = (),
    gpu_requested_device: str = "single_cuda_gpu",
    gpu_requires_gpu: bool = True,
    registry_id: str | None = None,
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
    pipeline_id: str = "P5-I012",
) -> FlagshipPipelineResult:
    if not isinstance(storage_runtime, StorageRuntimeResult):
        raise TypeError("storage_runtime must be a StorageRuntimeResult")

    runtime_training_result = train_multimodal_model(
        storage_runtime,
        ppi_representation=ppi_representation,
        requested_modalities=requested_modalities,
        model_name=model_name,
        fusion_dim=fusion_dim,
        deterministic_seed=deterministic_seed,
        provenance=provenance,
        notes=notes,
    )
    training_result = _prototype_training_view(runtime_training_result)
    fusion_model = FusionModel(
        model_name=training_result.plan.model_name,
        fusion_dim=training_result.plan.fusion_dim,
        modalities=training_result.plan.fusion_modalities or DEFAULT_MODALITY_ORDER,
    )
    fusion_result = fusion_model.fuse(
        sequence_embedding=sequence_embedding,
        structure_embedding=structure_embedding,
        ligand_embedding=ligand_embedding,
        provenance={
            "pipeline_id": pipeline_id,
            "training_plan_signature": training_result.plan.plan_signature,
            "training_state_signature": training_result.state.state_signature,
            "storage_runtime_status": storage_runtime.status,
        },
    )
    uncertainty_result = UncertaintyHead().evaluate(
        fusion_result,
        provenance={
            "pipeline_id": pipeline_id,
            "fusion_pipeline": "flagship",
        },
    )
    metrics = summarize_multimodal_metrics(
        (fusion_result,),
        provenance={
            "pipeline_id": pipeline_id,
            "training_plan_signature": training_result.plan.plan_signature,
        },
    )
    gpu_decision = GPUSchedulingPolicy(gpu_worker_limit=gpu_worker_limit).evaluate(
        GPUJobRequest(
            task_id=pipeline_id,
            title="Flagship multimodal training",
            requested_device=gpu_requested_device,
            requires_gpu=gpu_requires_gpu,
            provenance={
                "pipeline_id": pipeline_id,
                "storage_runtime_status": storage_runtime.status,
            },
        ),
        active_workers=gpu_active_workers,
    )
    experiment_registry = build_experiment_registry(
        storage_runtime,
        ppi_representation=ppi_representation,
        registry_id=registry_id,
        requested_modalities=training_result.spec.requested_modalities,
        model_name=training_result.spec.model_name,
        fusion_dim=training_result.spec.fusion_dim,
        deterministic_seed=deterministic_seed,
        training_result=runtime_training_result,
        provenance=provenance,
        notes=notes,
    )

    blockers = _pipeline_blockers(training_result, gpu_decision)
    limitations = _pipeline_limitations(
        training_result,
        training_result.dataset.status,
        fusion_result,
        uncertainty_result,
        gpu_decision,
    )
    if blockers:
        status: FlagshipPipelineStatus = "blocked" if not gpu_decision.allowed else "partial"
    elif limitations:
        status = "partial"
    else:
        status = "ready"

    return FlagshipPipelineResult(
        pipeline_id=pipeline_id,
        storage_runtime_status=storage_runtime.status,
        training=training_result,
        gpu_decision=gpu_decision,
        fusion_result=fusion_result,
        uncertainty_result=uncertainty_result,
        metrics=metrics,
        experiment_registry=experiment_registry,
        blockers=blockers,
        limitations=limitations,
        notes=tuple(notes),
        status=status,
    )


def build_flagship_pipeline(
    storage_runtime: StorageRuntimeResult,
    **kwargs: Any,
) -> FlagshipPipelineResult:
    return run_flagship_pipeline(storage_runtime, **kwargs)


__all__ = [
    "FlagshipPipelineBlocker",
    "FlagshipPipelineResult",
    "FlagshipPipelineStatus",
    "build_flagship_pipeline",
    "run_flagship_pipeline",
]
