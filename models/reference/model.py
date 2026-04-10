from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from datasets.baseline.schema import (
    BaselineDatasetExample,
    BaselineDatasetSchema,
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
class ReferenceModelBlocker:
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
class ReferenceModelSpec:
    model_name: str
    dataset_contract: str
    source_path: str
    config: dict[str, Scalar]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "dataset_contract": self.dataset_contract,
            "source_path": self.source_path,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class ReferenceExampleSummary:
    example_id: str
    protein_accession: str
    feature_modalities: tuple[str, ...]
    label_names: tuple[str, ...]
    split: str | None
    lineage_complete: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "example_id": self.example_id,
            "protein_accession": self.protein_accession,
            "feature_modalities": list(self.feature_modalities),
            "label_names": list(self.label_names),
            "split": self.split,
            "lineage_complete": self.lineage_complete,
        }


@dataclass(frozen=True, slots=True)
class ReferenceModelStatus:
    stage: str
    requested_backend: str
    resolved_backend: str
    backend_ready: bool
    contract_fidelity: str
    provenance: dict[str, object] = field(default_factory=dict)
    blocker: ReferenceModelBlocker | None = None

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
class ReferenceModelResult:
    spec: ReferenceModelSpec
    dataset_id: str
    schema_version: int
    example_count: int
    requested_modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_requested_modalities: tuple[str, ...]
    example_summaries: tuple[ReferenceExampleSummary, ...]
    lineage_complete_example_count: int
    status: ReferenceModelStatus
    blockers: tuple[ReferenceModelBlocker, ...]

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_dict(),
            "dataset_id": self.dataset_id,
            "schema_version": self.schema_version,
            "example_count": self.example_count,
            "requested_modalities": list(self.requested_modalities),
            "available_modalities": list(self.available_modalities),
            "missing_requested_modalities": list(self.missing_requested_modalities),
            "example_summaries": [summary.to_dict() for summary in self.example_summaries],
            "lineage_complete_example_count": self.lineage_complete_example_count,
            "status": self.status.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def load_reference_model_spec(repo_root: str | Path | None = None) -> ReferenceModelSpec:
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    schema_path = root / "datasets" / "baseline" / "schema.py"
    builder_path = root / "datasets" / "baseline" / "builder.py"
    config: dict[str, Scalar] = {
        "contract": "baseline_dataset_schema",
        "interface": "summary_only",
        "schema_module": "datasets.baseline.schema",
        "builder_module": "datasets.baseline.builder",
    }
    if builder_path.is_file():
        config["builder_source"] = _relative_path(root, builder_path)
    if schema_path.is_file():
        config["schema_source"] = _relative_path(root, schema_path)
    return ReferenceModelSpec(
        model_name="baseline-reference-model-skeleton",
        dataset_contract="BaselineDatasetSchema",
        source_path=_relative_path(root, schema_path),
        config=config,
    )


class ReferenceModel:
    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        spec: ReferenceModelSpec | None = None,
    ) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.spec = spec or load_reference_model_spec(self.repo_root)

    def run(
        self,
        dataset: BaselineDatasetSchema | Mapping[str, Any],
    ) -> ReferenceModelResult:
        return self.summarize(dataset)

    def summarize(
        self,
        dataset: BaselineDatasetSchema | Mapping[str, Any],
    ) -> ReferenceModelResult:
        schema = _coerce_dataset_schema(dataset)
        blockers: list[ReferenceModelBlocker] = []

        example_summaries = tuple(_summarize_example(example) for example in schema.examples)
        if not example_summaries:
            blockers.append(
                ReferenceModelBlocker(
                    stage="dataset",
                    requested_backend=self.spec.model_name,
                    reason="Baseline dataset schemas must contain at least one example.",
                )
            )

        requested_modalities = _normalize_text_tuple(schema.requested_modalities)
        available_modalities = _normalize_text_tuple(
            modality
            for example in schema.examples
            for modality in example.feature_modalities
        )
        missing_requested_modalities = tuple(
            modality
            for modality in requested_modalities
            if modality.casefold() not in {item.casefold() for item in available_modalities}
        )
        if missing_requested_modalities:
            blockers.append(
                ReferenceModelBlocker(
                    stage="modality_coverage",
                    requested_backend=self.spec.model_name,
                    reason=(
                        "Requested modalities are not fully represented in the baseline dataset: "
                        + ", ".join(missing_requested_modalities)
                    ),
                )
            )

        backend_ready = not blockers
        status = ReferenceModelStatus(
            stage="dataset_summary",
            requested_backend=self.spec.model_name,
            resolved_backend="baseline-dataset-summary",
            backend_ready=backend_ready,
            contract_fidelity=(
                "schema-summary-ready" if backend_ready else "schema-summary-blocked"
            ),
            provenance={
                "dataset_contract": self.spec.dataset_contract,
                "schema_source": self.spec.source_path,
                "example_count": schema.example_count,
                "lineage_complete_example_count": schema.lineage_complete_example_count,
                "requested_modalities": list(requested_modalities),
                "available_modalities": list(available_modalities),
            },
            blocker=blockers[0] if blockers else None,
        )

        return ReferenceModelResult(
            spec=self.spec,
            dataset_id=schema.dataset_id,
            schema_version=schema.schema_version,
            example_count=schema.example_count,
            requested_modalities=requested_modalities,
            available_modalities=available_modalities,
            missing_requested_modalities=missing_requested_modalities,
            example_summaries=example_summaries,
            lineage_complete_example_count=schema.lineage_complete_example_count,
            status=status,
            blockers=tuple(blockers),
        )

    __call__ = run


def summarize_reference_dataset(
    dataset: BaselineDatasetSchema | Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> ReferenceModelResult:
    return ReferenceModel(repo_root=repo_root).summarize(dataset)


def _summarize_example(example: BaselineDatasetExample) -> ReferenceExampleSummary:
    return ReferenceExampleSummary(
        example_id=example.example_id,
        protein_accession=example.protein_ref.canonical_id,
        feature_modalities=example.feature_modalities,
        label_names=tuple(label.label_name for label in example.labels),
        split=example.split,
        lineage_complete=example.lineage_complete,
    )


__all__ = [
    "ReferenceExampleSummary",
    "ReferenceModel",
    "ReferenceModelBlocker",
    "ReferenceModelResult",
    "ReferenceModelSpec",
    "ReferenceModelStatus",
    "load_reference_model_spec",
    "summarize_reference_dataset",
]
