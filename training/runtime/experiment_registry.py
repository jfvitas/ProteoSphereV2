from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from datasets.multimodal.adapter import DEFAULT_MULTIMODAL_MODALITIES
from execution.storage_runtime import StorageRuntimeResult
from features.ppi_representation import PPIRepresentation
from training.multimodal.train import train_multimodal_model

DEFAULT_EXPERIMENT_REGISTRY_ID = "multimodal-experiment-registry:v1"
DEFAULT_TRAINING_ENTRYPOINT = "training/multimodal/train.py"


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
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _relative_path(path: Path) -> str:
    root = Path(__file__).resolve().parents[2]
    return str(path.resolve().relative_to(root)).replace("\\", "/")


def _experiment_id(
    registry_id: str,
    training_result: Any,
) -> str:
    payload = {
        "registry_id": registry_id,
        "dataset_signature": training_result.state.dataset_signature,
        "plan_signature": training_result.plan.plan_signature,
        "state_signature": training_result.state.state_signature,
        "checkpoint_tag": training_result.state.checkpoint_tag,
    }
    return f"experiment:{_fingerprint(payload)}"


def _checkpoint_ref(checkpoint_tag: str) -> str:
    return f"checkpoint://{_clean_text(checkpoint_tag)}"


def _supported_modalities(requested_modalities: tuple[str, ...]) -> tuple[str, ...]:
    modalities = tuple(
        modality for modality in requested_modalities if modality in DEFAULT_MULTIMODAL_MODALITIES
    )
    if not modalities:
        return DEFAULT_MULTIMODAL_MODALITIES
    return modalities


def _runtime_status(training_result: Any) -> dict[str, Any]:
    status = getattr(getattr(training_result, "plan", None), "status", None)
    runtime_status = _json_ready(status)
    if isinstance(runtime_status, Mapping):
        return dict(runtime_status)
    return {}


def _blocker_from_status(status: Mapping[str, Any]) -> ExperimentRegistryBlocker | None:
    blocker = status.get("blocker")
    if isinstance(blocker, Mapping):
        return ExperimentRegistryBlocker(
            stage=_clean_text(blocker.get("stage")) or "trainer_runtime",
            requested_backend=_clean_text(blocker.get("requested_backend"))
            or "multimodal-fusion-baseline-v1+multimodal-dataset-adapter",
            reason=_clean_text(blocker.get("reason"))
            or (
                "The repository can execute the multimodal runtime locally, but no real "
                "multimodal trainer runtime is wired under training/multimodal yet."
            ),
        )
    return None


@dataclass(frozen=True, slots=True)
class ExperimentRegistryBlocker:
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
class ExperimentRegistryRecord:
    experiment_id: str
    training_entrypoint: str
    dataset_id: str
    package_id: str
    package_manifest_id: str
    checkpoint_tag: str
    checkpoint_ref: str
    model_name: str
    fusion_dim: int
    requested_modalities: tuple[str, ...]
    fusion_modalities: tuple[str, ...]
    observed_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    plan_signature: str
    state_signature: str
    storage_runtime_status: str
    backend_ready: bool
    contract_fidelity: str
    runtime_status: Mapping[str, Any] = field(default_factory=dict)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    blocker: ExperimentRegistryBlocker | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "experiment_id", _clean_text(self.experiment_id))
        object.__setattr__(self, "training_entrypoint", _clean_text(self.training_entrypoint))
        object.__setattr__(self, "dataset_id", _clean_text(self.dataset_id))
        object.__setattr__(self, "package_id", _clean_text(self.package_id))
        object.__setattr__(self, "package_manifest_id", _clean_text(self.package_manifest_id))
        object.__setattr__(self, "checkpoint_tag", _clean_text(self.checkpoint_tag))
        object.__setattr__(self, "checkpoint_ref", _clean_text(self.checkpoint_ref))
        object.__setattr__(self, "model_name", _clean_text(self.model_name))
        object.__setattr__(self, "requested_modalities", _dedupe_text(self.requested_modalities))
        object.__setattr__(self, "fusion_modalities", _dedupe_text(self.fusion_modalities))
        object.__setattr__(self, "observed_modalities", _dedupe_text(self.observed_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        if not isinstance(self.runtime_status, Mapping):
            raise TypeError("runtime_status must be a mapping")
        runtime_status = dict(self.runtime_status)
        object.__setattr__(self, "runtime_status", runtime_status)
        if "backend_ready" in runtime_status:
            object.__setattr__(self, "backend_ready", bool(runtime_status.get("backend_ready")))
        if "contract_fidelity" in runtime_status:
            object.__setattr__(
                self,
                "contract_fidelity",
                _clean_text(runtime_status.get("contract_fidelity")) or self.contract_fidelity,
            )
        runtime_blocker = _blocker_from_status(runtime_status)
        if runtime_blocker is not None and self.blocker is None:
            object.__setattr__(self, "blocker", runtime_blocker)
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not self.experiment_id:
            raise ValueError("experiment_id must not be empty")
        if not self.training_entrypoint:
            raise ValueError("training_entrypoint must not be empty")
        if not self.checkpoint_tag:
            raise ValueError("checkpoint_tag must not be empty")
        if not self.checkpoint_ref:
            raise ValueError("checkpoint_ref must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "training_entrypoint": self.training_entrypoint,
            "dataset_id": self.dataset_id,
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "checkpoint_tag": self.checkpoint_tag,
            "checkpoint_ref": self.checkpoint_ref,
            "model_name": self.model_name,
            "fusion_dim": self.fusion_dim,
            "requested_modalities": list(self.requested_modalities),
            "fusion_modalities": list(self.fusion_modalities),
            "observed_modalities": list(self.observed_modalities),
            "missing_modalities": list(self.missing_modalities),
            "plan_signature": self.plan_signature,
            "state_signature": self.state_signature,
            "storage_runtime_status": self.storage_runtime_status,
            "backend_ready": self.backend_ready,
            "contract_fidelity": self.contract_fidelity,
            "runtime_status": dict(self.runtime_status),
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
            "blocker": self.blocker.to_dict() if self.blocker is not None else None,
        }


@dataclass(frozen=True, slots=True)
class ExperimentRegistry:
    registry_id: str
    records: tuple[ExperimentRegistryRecord, ...]
    source_path: str
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_id", _clean_text(self.registry_id))
        object.__setattr__(self, "source_path", _clean_text(self.source_path))
        if not self.registry_id:
            raise ValueError("registry_id must not be empty")
        if not self.source_path:
            raise ValueError("source_path must not be empty")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        records: list[ExperimentRegistryRecord] = []
        seen_ids: set[str] = set()
        for record in self.records:
            if not isinstance(record, ExperimentRegistryRecord):
                raise TypeError("records must contain ExperimentRegistryRecord objects")
            if record.experiment_id in seen_ids:
                raise ValueError(f"duplicate experiment_id: {record.experiment_id}")
            seen_ids.add(record.experiment_id)
            records.append(record)
        object.__setattr__(self, "records", tuple(records))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def registry_signature(self) -> str:
        return _fingerprint(
            {
                "registry_id": self.registry_id,
                "source_path": self.source_path,
                "records": [record.to_dict() for record in self.records],
                "provenance_refs": list(self.provenance_refs),
                "notes": list(self.notes),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "source_path": self.source_path,
            "record_count": self.record_count,
            "registry_signature": self.registry_signature,
            "records": [record.to_dict() for record in self.records],
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
        }


def build_experiment_registry(
    storage_runtime: StorageRuntimeResult,
    *,
    ppi_representation: PPIRepresentation | Mapping[str, Any] | None = None,
    registry_id: str | None = None,
    requested_modalities: Iterable[str] = DEFAULT_MULTIMODAL_MODALITIES,
    model_name: str = "multimodal-fusion-baseline-v1",
    fusion_dim: int = 8,
    deterministic_seed: int = 0,
    training_result: Any | None = None,
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> ExperimentRegistry:
    if not isinstance(storage_runtime, StorageRuntimeResult):
        raise TypeError("storage_runtime must be a StorageRuntimeResult")
    if deterministic_seed < 0:
        raise ValueError("deterministic_seed must be non-negative")
    if training_result is None:
        training_result = train_multimodal_model(
            storage_runtime,
            ppi_representation=ppi_representation,
            requested_modalities=requested_modalities,
            model_name=model_name,
            fusion_dim=fusion_dim,
            deterministic_seed=deterministic_seed,
            provenance=provenance,
            notes=notes,
        )
    registry_id_value = _clean_text(registry_id) or DEFAULT_EXPERIMENT_REGISTRY_ID
    runtime_status = _runtime_status(training_result)
    record = ExperimentRegistryRecord(
        experiment_id=_experiment_id(registry_id_value, training_result),
        training_entrypoint=DEFAULT_TRAINING_ENTRYPOINT,
        dataset_id=training_result.dataset.dataset_id,
        package_id=training_result.dataset.package_id,
        package_manifest_id=training_result.dataset.package_manifest_id,
        checkpoint_tag=training_result.state.checkpoint_tag,
        checkpoint_ref=_checkpoint_ref(training_result.state.checkpoint_tag),
        model_name=training_result.spec.model_name,
        fusion_dim=training_result.spec.fusion_dim,
        requested_modalities=training_result.spec.requested_modalities,
        fusion_modalities=training_result.spec.fusion_modalities,
        observed_modalities=training_result.plan.observed_modalities,
        missing_modalities=training_result.plan.missing_modalities,
        plan_signature=training_result.plan.plan_signature,
        state_signature=training_result.state.state_signature,
        storage_runtime_status=training_result.dataset.storage_runtime_status,
        backend_ready=bool(runtime_status.get("backend_ready", False)),
        contract_fidelity=_clean_text(runtime_status.get("contract_fidelity"))
        or "dataset-and-fusion-plan-only",
        runtime_status=runtime_status,
        provenance_refs=(
            *training_result.dataset.provenance_refs,
        ),
        notes=(
            *training_result.dataset.notes,
            *notes,
        ),
        blocker=_blocker_from_status(runtime_status),
    )
    return ExperimentRegistry(
        registry_id=registry_id_value,
        records=(record,),
        source_path=_relative_path(Path(__file__)),
        provenance_refs=_dedupe_text(
            (
                storage_runtime.package_manifest.manifest_id,
                storage_runtime.selective_materialization.manifest_id,
                storage_runtime.package_build.package_manifest.manifest_id,
                *training_result.dataset.provenance_refs,
                *storage_runtime.package_manifest.provenance,
                *storage_runtime.selective_materialization.provenance_refs,
                *storage_runtime.package_build.package_manifest.provenance,
                *provenance,
            )
        ),
        notes=_dedupe_text((*storage_runtime.notes, *notes)),
    )


def register_experiment(
    storage_runtime: StorageRuntimeResult,
    **kwargs: Any,
) -> ExperimentRegistry:
    return build_experiment_registry(storage_runtime, **kwargs)


__all__ = [
    "DEFAULT_EXPERIMENT_REGISTRY_ID",
    "DEFAULT_TRAINING_ENTRYPOINT",
    "ExperimentRegistry",
    "ExperimentRegistryBlocker",
    "ExperimentRegistryRecord",
    "build_experiment_registry",
    "register_experiment",
]
