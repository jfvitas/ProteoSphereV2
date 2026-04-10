from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from datasets.baseline.builder import build_baseline_dataset
from datasets.baseline.schema import BaselineDatasetExample, BaselineDatasetSchema
from evaluation.reference.metrics import ReferenceMetrics, summarize_reference_metrics
from models.reference.model import ReferenceModel, ReferenceModelResult
from training.reference.train import ReferenceTrainingLoop, ReferenceTrainingResult

ReferencePipelineStatus = Literal["ready", "partial", "failed"]


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


@dataclass(frozen=True, slots=True)
class ReferencePipelineSpec:
    pipeline_name: str
    source_path: str
    config: dict[str, str | int | float | bool]

    def to_dict(self) -> dict[str, object]:
        return {
            "pipeline_name": self.pipeline_name,
            "source_path": self.source_path,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class ReferencePipelineBlocker:
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
class ReferencePipelineResult:
    spec: ReferencePipelineSpec
    run_id: str
    dataset: BaselineDatasetSchema
    model_result: ReferenceModelResult
    training_result: ReferenceTrainingResult
    metrics: ReferenceMetrics
    status: ReferencePipelineStatus
    reason: str
    blockers: tuple[ReferencePipelineBlocker, ...]
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_dict(),
            "run_id": self.run_id,
            "dataset": self.dataset.to_dict(),
            "model_result": self.model_result.to_dict(),
            "training_result": self.training_result.to_dict(),
            "metrics": self.metrics.to_dict(),
            "status": self.status,
            "reason": self.reason,
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "summary": _json_ready(self.summary),
        }


@dataclass(frozen=True, slots=True)
class ReferencePipelineConfig:
    run_id: str
    dataset_id: str
    examples: tuple[BaselineDatasetExample | Mapping[str, Any], ...]
    requested_modalities: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1
    package_id: str | None = None
    package_state: str | None = None
    created_at: str | None = None
    source_packages: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    metrics_id: str = "reference-pipeline-metrics"
    repo_root: str | Path | None = None

    def __post_init__(self) -> None:
        run_id = _clean_text(self.run_id)
        dataset_id = _clean_text(self.dataset_id)
        if not run_id:
            raise ValueError("run_id must be a non-empty string")
        if not dataset_id:
            raise ValueError("dataset_id must be a non-empty string")
        examples = tuple(self.examples)
        if not examples:
            raise ValueError("examples must not be empty")
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "dataset_id", dataset_id)
        object.__setattr__(self, "examples", examples)
        object.__setattr__(
            self,
            "requested_modalities",
            _normalize_text_tuple(self.requested_modalities),
        )
        object.__setattr__(
            self,
            "source_packages",
            _normalize_text_tuple(self.source_packages),
        )
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(
            self,
            "metrics_id",
            _clean_text(self.metrics_id) or "reference-pipeline-metrics",
        )

    @property
    def resolved_repo_root(self) -> Path:
        return Path(self.repo_root or Path(__file__).resolve().parents[1]).resolve()


def load_reference_pipeline_spec(repo_root: str | Path | None = None) -> ReferencePipelineSpec:
    root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
    source_path = root / "execution" / "reference_pipeline.py"
    return ReferencePipelineSpec(
        pipeline_name="reference-execution-pipeline",
        source_path=_relative_path(root, source_path),
        config={
            "contract": (
                "baseline_builder_plus_reference_model_plus_reference_training_plus_reference_metrics"
            ),
            "status": "summary_only",
            "truth_boundary": "fail_closed",
        },
    )


class ReferencePipeline:
    def __init__(
        self,
        config: ReferencePipelineConfig,
        *,
        spec: ReferencePipelineSpec | None = None,
    ) -> None:
        self.config = config
        self.spec = spec or load_reference_pipeline_spec(config.resolved_repo_root)

    def build_dataset(self) -> BaselineDatasetSchema:
        return build_baseline_dataset(
            self.config.examples,
            dataset_id=self.config.dataset_id,
            schema_version=self.config.schema_version,
            requested_modalities=self.config.requested_modalities,
            package_id=self.config.package_id,
            package_state=self.config.package_state,
            created_at=self.config.created_at,
            source_packages=self.config.source_packages,
            notes=self.config.notes,
            metadata=self.config.metadata,
        )

    def run(self) -> ReferencePipelineResult:
        dataset = self.build_dataset()
        model_result = ReferenceModel(repo_root=self.config.resolved_repo_root).run(dataset)
        training_result = ReferenceTrainingLoop(repo_root=self.config.resolved_repo_root).train(
            dataset
        )
        metrics = summarize_reference_metrics(
            training_result.dataset_summary,
            metrics_id=self.config.metrics_id,
            provenance={
                "run_id": self.config.run_id,
                "pipeline_name": self.spec.pipeline_name,
                "dataset_id": dataset.dataset_id,
                "schema_version": dataset.schema_version,
            },
        )

        blockers = _dedupe_blockers((*model_result.blockers, *training_result.blockers))
        status = "ready" if not blockers else "partial"
        reason = (
            "reference_pipeline_ready"
            if not blockers
            else blockers[0].reason
        )
        summary = {
            "dataset": {
                "dataset_id": dataset.dataset_id,
                "example_count": dataset.example_count,
                "requested_modalities": list(dataset.requested_modalities),
                "available_modalities": list(dataset.available_modalities),
                "lineage_complete_example_count": dataset.lineage_complete_example_count,
            },
            "model": {
                "backend_ready": model_result.status.backend_ready,
                "resolved_backend": model_result.status.resolved_backend,
                "blocked_stages": list(model_result.blocked_stages),
            },
            "training": {
                "backend_ready": training_result.status.backend_ready,
                "resolved_backend": training_result.status.resolved_backend,
                "planned_epoch_count": training_result.planned_epoch_count,
                "executed_epoch_count": training_result.executed_epoch_count,
                "blocked_stages": list(training_result.blocked_stages),
            },
            "metrics": {
                "example_count": metrics.example_count,
                "requested_coverage_mean": metrics.requested_coverage_mean,
                "complete_requested_rate": metrics.complete_requested_rate,
                "lineage_complete_rate": metrics.lineage_complete_rate,
            },
            "blocked_stage_count": len(blockers),
        }
        return ReferencePipelineResult(
            spec=self.spec,
            run_id=self.config.run_id,
            dataset=dataset,
            model_result=model_result,
            training_result=training_result,
            metrics=metrics,
            status=status,
            reason=reason,
            blockers=blockers,
            summary=summary,
        )

    __call__ = run


def _dedupe_blockers(
    blockers: Iterable[ReferencePipelineBlocker | Any],
) -> tuple[ReferencePipelineBlocker, ...]:
    ordered: dict[tuple[str, str, str], ReferencePipelineBlocker] = {}
    for blocker in blockers:
        if blocker is None:
            continue
        candidate = ReferencePipelineBlocker(
            stage=_clean_text(blocker.stage),
            requested_backend=_clean_text(blocker.requested_backend),
            reason=_clean_text(blocker.reason),
        )
        key = (candidate.stage, candidate.reason)
        ordered.setdefault(key, candidate)
    return tuple(ordered.values())


def run_reference_pipeline(
    *,
    run_id: str,
    dataset_id: str,
    examples: Iterable[BaselineDatasetExample | Mapping[str, Any]],
    requested_modalities: Iterable[str] = (),
    schema_version: int = 1,
    package_id: str | None = None,
    package_state: str | None = None,
    created_at: str | None = None,
    source_packages: Iterable[str] = (),
    notes: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
    metrics_id: str = "reference-pipeline-metrics",
    repo_root: str | Path | None = None,
) -> ReferencePipelineResult:
    return ReferencePipeline(
        ReferencePipelineConfig(
            run_id=run_id,
            dataset_id=dataset_id,
            examples=tuple(examples),
            requested_modalities=tuple(requested_modalities),
            schema_version=schema_version,
            package_id=package_id,
            package_state=package_state,
            created_at=created_at,
            source_packages=tuple(source_packages),
            notes=tuple(notes),
            metadata=metadata or {},
            metrics_id=metrics_id,
            repo_root=repo_root,
        )
    ).run()


__all__ = [
    "ReferencePipeline",
    "ReferencePipelineBlocker",
    "ReferencePipelineConfig",
    "ReferencePipelineResult",
    "ReferencePipelineSpec",
    "ReferencePipelineStatus",
    "load_reference_pipeline_spec",
    "run_reference_pipeline",
]
