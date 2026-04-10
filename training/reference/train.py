from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from datasets.baseline.schema import BaselineDatasetSchema
from models.reference.model import (
    ReferenceModelResult,
    summarize_reference_dataset,
)

Scalar = str | int | float | bool


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        values = (values,)
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _relative_path(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


def _coerce_dataset_schema(
    dataset: BaselineDatasetSchema | Mapping[str, Any],
) -> BaselineDatasetSchema:
    if isinstance(dataset, BaselineDatasetSchema):
        return dataset
    if isinstance(dataset, Mapping):
        return BaselineDatasetSchema.from_dict(dataset)
    raise TypeError("dataset must be a BaselineDatasetSchema or mapping")


@dataclass(frozen=True, slots=True)
class ReferenceTrainingSpec:
    model_contract: str
    training_contract: str
    source_path: str
    config: dict[str, Scalar]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_contract": self.model_contract,
            "training_contract": self.training_contract,
            "source_path": self.source_path,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class ReferenceTrainingBlocker:
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
class ReferenceTrainingEpochSummary:
    epoch_index: int
    example_count: int
    lineage_complete_example_count: int
    requested_modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    label_count: int
    backend_mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "epoch_index": self.epoch_index,
            "example_count": self.example_count,
            "lineage_complete_example_count": self.lineage_complete_example_count,
            "requested_modalities": list(self.requested_modalities),
            "available_modalities": list(self.available_modalities),
            "label_count": self.label_count,
            "backend_mode": self.backend_mode,
        }


@dataclass(frozen=True, slots=True)
class ReferenceTrainingStatus:
    stage: str
    requested_backend: str
    resolved_backend: str
    backend_ready: bool
    contract_fidelity: str
    provenance: dict[str, object] = field(default_factory=dict)
    blocker: ReferenceTrainingBlocker | None = None

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
class ReferenceTrainingResult:
    spec: ReferenceTrainingSpec
    dataset_summary: ReferenceModelResult
    dataset_id: str
    schema_version: int
    example_count: int
    requested_modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_requested_modalities: tuple[str, ...]
    planned_epoch_count: int
    executed_epoch_count: int
    epoch_summaries: tuple[ReferenceTrainingEpochSummary, ...]
    status: ReferenceTrainingStatus
    blockers: tuple[ReferenceTrainingBlocker, ...]

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_dict(),
            "dataset_summary": self.dataset_summary.to_dict(),
            "dataset_id": self.dataset_id,
            "schema_version": self.schema_version,
            "example_count": self.example_count,
            "requested_modalities": list(self.requested_modalities),
            "available_modalities": list(self.available_modalities),
            "missing_requested_modalities": list(self.missing_requested_modalities),
            "planned_epoch_count": self.planned_epoch_count,
            "executed_epoch_count": self.executed_epoch_count,
            "epoch_summaries": [summary.to_dict() for summary in self.epoch_summaries],
            "status": self.status.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def load_reference_training_spec(repo_root: str | Path | None = None) -> ReferenceTrainingSpec:
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    source_path = root / "training" / "reference" / "train.py"
    config: dict[str, Scalar] = {
        "contract": "reference_training_loop",
        "training_mode": "summary_only",
        "model_module": "models.reference.model",
        "dataset_contract": "BaselineDatasetSchema",
    }
    return ReferenceTrainingSpec(
        model_contract="baseline-reference-model-skeleton",
        training_contract="reference-training-loop-skeleton",
        source_path=_relative_path(root, source_path),
        config=config,
    )


class ReferenceTrainingLoop:
    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        spec: ReferenceTrainingSpec | None = None,
    ) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.spec = spec or load_reference_training_spec(self.repo_root)

    def run(
        self,
        dataset: BaselineDatasetSchema | Mapping[str, Any],
    ) -> ReferenceTrainingResult:
        return self.train(dataset)

    def train(
        self,
        dataset: BaselineDatasetSchema | Mapping[str, Any],
    ) -> ReferenceTrainingResult:
        schema = _coerce_dataset_schema(dataset)
        dataset_summary = summarize_reference_dataset(schema, repo_root=self.repo_root)

        blockers: list[ReferenceTrainingBlocker] = [
            ReferenceTrainingBlocker(
                stage=blocker.stage,
                requested_backend=blocker.requested_backend,
                reason=blocker.reason,
            )
            for blocker in dataset_summary.blockers
        ]
        blockers.append(
            ReferenceTrainingBlocker(
                stage="trainer_runtime",
                requested_backend=self.spec.training_contract,
                reason=(
                    "The repository exposes a conservative reference training loop only; "
                    "no real trainer backend is wired under training/reference."
                ),
            )
        )

        requested_modalities = dataset_summary.requested_modalities
        available_modalities = dataset_summary.available_modalities
        missing_requested_modalities = dataset_summary.missing_requested_modalities

        planned_epoch_count = 1 if schema.example_count else 0
        epoch_summaries = (
            ReferenceTrainingEpochSummary(
                epoch_index=1,
                example_count=schema.example_count,
                lineage_complete_example_count=schema.lineage_complete_example_count,
                requested_modalities=requested_modalities,
                available_modalities=available_modalities,
                label_count=sum(len(example.labels) for example in schema.examples),
                backend_mode="contract-plan-only",
            ),
        ) if planned_epoch_count else ()
        executed_epoch_count = 0

        status = ReferenceTrainingStatus(
            stage="training_preview",
            requested_backend=self.spec.training_contract,
            resolved_backend="contract-plan-only",
            backend_ready=False,
            contract_fidelity="summary-only",
            provenance={
                "training_contract": self.spec.training_contract,
                "model_contract": self.spec.model_contract,
                "dataset_contract": dataset_summary.status.provenance.get(
                    "dataset_contract",
                    "BaselineDatasetSchema",
                ),
                "source_path": self.spec.source_path,
                "planned_epoch_count": planned_epoch_count,
                "executed_epoch_count": executed_epoch_count,
                "dataset_example_count": schema.example_count,
                "lineage_complete_example_count": schema.lineage_complete_example_count,
            },
            blocker=blockers[0] if blockers else None,
        )

        return ReferenceTrainingResult(
            spec=self.spec,
            dataset_summary=dataset_summary,
            dataset_id=schema.dataset_id,
            schema_version=schema.schema_version,
            example_count=schema.example_count,
            requested_modalities=requested_modalities,
            available_modalities=available_modalities,
            missing_requested_modalities=missing_requested_modalities,
            planned_epoch_count=planned_epoch_count,
            executed_epoch_count=executed_epoch_count,
            epoch_summaries=epoch_summaries,
            status=status,
            blockers=tuple(blockers),
        )

    __call__ = run


def train_reference_dataset(
    dataset: BaselineDatasetSchema | Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> ReferenceTrainingResult:
    return ReferenceTrainingLoop(repo_root=repo_root).train(dataset)


__all__ = [
    "ReferenceTrainingBlocker",
    "ReferenceTrainingEpochSummary",
    "ReferenceTrainingLoop",
    "ReferenceTrainingResult",
    "ReferenceTrainingSpec",
    "ReferenceTrainingStatus",
    "load_reference_training_spec",
    "train_reference_dataset",
]
