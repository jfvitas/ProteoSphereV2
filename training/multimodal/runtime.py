from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from datasets.multimodal.adapter import MultimodalDatasetExample
from execution.checkpoints.store import CheckpointRecord
from execution.storage_runtime import StorageRuntimeResult
from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.fusion_model import FusionModelResult
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult
from training.multimodal.train import (
    MultimodalTrainingBackendResult,
    MultimodalTrainingPlan,
    MultimodalTrainingRuntimeStatus,
    MultimodalTrainingState,
    prepare_multimodal_training,
)

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
DEFAULT_RUNTIME_BACKEND = "local-prototype-runtime"
DEFAULT_RUNTIME_OBJECTIVE = "modality-coverage-regression"
DEFAULT_CHECKPOINT_ROOT = Path("artifacts/runtime_checkpoints")


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


def _mean_rows(rows: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if not rows:
        return ()
    width = len(rows[0])
    totals = [0.0] * width
    for row in rows:
        for index, value in enumerate(row):
            totals[index] += float(value)
    return tuple(total / len(rows) for total in totals)


def _hash_bytes(*parts: object) -> bytes:
    payload = "|".join(_clean_text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).digest()


def _vector_from_key(*parts: object, width: int) -> tuple[float, ...]:
    if width < 1:
        raise ValueError("width must be >= 1")
    numbers: list[float] = []
    block = _hash_bytes(*parts)
    index = 0
    while len(numbers) < width:
        if index >= len(block):
            block = _hash_bytes(*parts, len(numbers))
            index = 0
        value = block[index]
        numbers.append((float(value) / 255.0) * 2.0 - 1.0)
        index += 1
    return tuple(numbers)


def _pseudo_sequence(example: MultimodalDatasetExample, *, deterministic_seed: int) -> str:
    refs = example.modality_refs.get("sequence") or example.provenance_refs or (
        example.example_id,
    )
    basis = "|".join(refs)
    length = max(8, min(24, len(basis) % 17 + 8))
    digest = _hash_bytes("sequence", basis, deterministic_seed)
    chars = [
        AMINO_ACIDS[digest[index % len(digest)] % len(AMINO_ACIDS)]
        for index in range(length)
    ]
    return "".join(chars)


def _sequence_embedding(
    example: MultimodalDatasetExample,
    *,
    fusion_dim: int,
    deterministic_seed: int,
) -> ProteinEmbeddingResult | None:
    refs = example.modality_refs.get("sequence")
    if not refs:
        return None
    sequence = _pseudo_sequence(example, deterministic_seed=deterministic_seed)
    residue_embeddings = tuple(
        _vector_from_key(
            "sequence",
            example.example_id,
            residue_index,
            residue,
            deterministic_seed,
            width=fusion_dim,
        )
        for residue_index, residue in enumerate(sequence, start=1)
    )
    pooled_embedding = _mean_rows(residue_embeddings)
    return ProteinEmbeddingResult(
        sequence=sequence,
        model_name="sequence-surrogate-runtime-v1",
        embedding_dim=fusion_dim,
        residue_embeddings=residue_embeddings,
        pooled_embedding=pooled_embedding,
        cls_embedding=None,
        source="multimodal_runtime_surrogate",
        frozen=True,
        provenance={
            "backend": DEFAULT_RUNTIME_BACKEND,
            "input_kind": "materialized_ref_surrogate",
            "artifact_refs": list(refs),
            "deterministic_seed": deterministic_seed,
            "example_id": example.example_id,
        },
    )


def _structure_embedding(
    example: MultimodalDatasetExample,
    *,
    fusion_dim: int,
    deterministic_seed: int,
) -> StructureEmbeddingResult | None:
    refs = example.modality_refs.get("structure")
    if not refs:
        return None
    token_ids = tuple(f"structure:{index}" for index, _ in enumerate(refs, start=1))
    token_embeddings = tuple(
        _vector_from_key(
            "structure",
            example.example_id,
            ref,
            deterministic_seed,
            width=fusion_dim,
        )
        for ref in refs
    )
    return StructureEmbeddingResult(
        pdb_id=_clean_text(refs[0]) or "unknown",
        model_name="structure-surrogate-runtime-v1",
        embedding_dim=fusion_dim,
        token_ids=token_ids,
        token_embeddings=token_embeddings,
        pooled_embedding=_mean_rows(token_embeddings),
        graph_kinds=tuple("artifact_ref_surrogate" for _ in refs),
        source="multimodal_runtime_surrogate",
        frozen=True,
        provenance={
            "backend": DEFAULT_RUNTIME_BACKEND,
            "input_kind": "materialized_ref_surrogate",
            "artifact_refs": list(refs),
            "deterministic_seed": deterministic_seed,
            "example_id": example.example_id,
        },
    )


def _ligand_embedding(
    example: MultimodalDatasetExample,
    *,
    fusion_dim: int,
    deterministic_seed: int,
) -> LigandEmbeddingResult | None:
    refs = example.modality_refs.get("ligand")
    if not refs:
        return None
    token_ids = tuple(f"ligand:{index}" for index, _ in enumerate(refs, start=1))
    token_embeddings = tuple(
        _vector_from_key(
            "ligand",
            example.example_id,
            ref,
            deterministic_seed,
            width=fusion_dim,
        )
        for ref in refs
    )
    canonical_id = f"ligand:{_fingerprint({'example_id': example.example_id, 'refs': list(refs)})}"
    return LigandEmbeddingResult(
        canonical_id=canonical_id,
        ligand_id=_clean_text(refs[0]) or None,
        name=_clean_text(refs[0]) or canonical_id,
        source="multimodal_runtime_surrogate",
        source_id=_clean_text(refs[0]) or canonical_id,
        smiles=None,
        inchi=None,
        inchikey=None,
        formula=None,
        charge=None,
        model_name="ligand-surrogate-runtime-v1",
        embedding_dim=fusion_dim,
        token_ids=token_ids,
        token_embeddings=token_embeddings,
        pooled_embedding=_mean_rows(token_embeddings),
        source_kind="ligand_runtime_surrogate",
        frozen=True,
        provenance={
            "backend": DEFAULT_RUNTIME_BACKEND,
            "input_kind": "materialized_ref_surrogate",
            "artifact_refs": list(refs),
            "deterministic_seed": deterministic_seed,
            "example_id": example.example_id,
        },
    )


def _coverage_target(
    example: MultimodalDatasetExample,
    *,
    requested_modalities: tuple[str, ...],
) -> float:
    if not requested_modalities:
        return 0.0
    return len(example.available_modalities) / float(len(requested_modalities))


def _default_checkpoint_path(checkpoint_tag: str) -> Path:
    return DEFAULT_CHECKPOINT_ROOT / f"{checkpoint_tag}.json"


def _run_id(
    contract_result: MultimodalTrainingBackendResult,
    *,
    deterministic_seed: int,
    feature_bundle_signature: str,
) -> str:
    payload = {
        "dataset_id": contract_result.dataset.dataset_id,
        "package_id": contract_result.dataset.package_id,
        "package_manifest_id": contract_result.dataset.package_manifest_id,
        "requested_modalities": list(contract_result.dataset.requested_modalities),
        "fusion_modalities": list(contract_result.plan.fusion_modalities),
        "model_name": contract_result.spec.model_name,
        "fusion_dim": contract_result.spec.fusion_dim,
        "deterministic_seed": deterministic_seed,
        "feature_bundle_signature": feature_bundle_signature,
    }
    return f"multimodal-run:{_fingerprint(payload)}"


def _initial_weights(fusion_dim: int, *, deterministic_seed: int) -> tuple[float, ...]:
    return _vector_from_key("head", deterministic_seed, width=fusion_dim)


def _bundle_value(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            return getattr(value, key)
    return None


def _bundle_provenance(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        if "provenance" in value:
            provenance = value["provenance"]
            if provenance is None:
                return {}
            if not isinstance(provenance, Mapping):
                raise TypeError("bundle provenance must be a mapping")
            return _json_ready(dict(provenance))
        return _json_ready(dict(value))
    provenance = _bundle_value(value, "provenance")
    if provenance is None:
        return {}
    if not isinstance(provenance, Mapping):
        raise TypeError("bundle provenance must be a mapping")
    return _json_ready(dict(provenance))


@dataclass(frozen=True, slots=True)
class MultimodalFeatureBundle:
    example_id: str
    sequence_embedding: ProteinEmbeddingResult | None = None
    structure_embedding: StructureEmbeddingResult | None = None
    ligand_embedding: LigandEmbeddingResult | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _clean_text(self.example_id))
        if not self.example_id:
            raise ValueError("example_id must be a non-empty string")
        object.__setattr__(self, "provenance", _bundle_provenance(self.provenance))

    def to_dict(self) -> dict[str, object]:
        return {
            "example_id": self.example_id,
            "sequence_embedding": _json_ready(self.sequence_embedding),
            "structure_embedding": _json_ready(self.structure_embedding),
            "ligand_embedding": _json_ready(self.ligand_embedding),
            "provenance": dict(self.provenance),
        }


def _coerce_feature_bundle(value: Any) -> MultimodalFeatureBundle:
    if isinstance(value, MultimodalFeatureBundle):
        return value
    if not isinstance(value, Mapping) and not any(
        hasattr(value, key)
        for key in ("example_id", "sequence_embedding", "structure_embedding", "ligand_embedding")
    ):
        raise TypeError(
            "feature bundles must be MultimodalFeatureBundle instances, "
            "mappings, or objects with bundle attributes"
        )
    example_id = _clean_text(_bundle_value(value, "example_id", "selected_example_id", "id"))
    if not example_id:
        raise ValueError("feature bundle must expose example_id")
    return MultimodalFeatureBundle(
        example_id=example_id,
        sequence_embedding=_bundle_value(value, "sequence_embedding"),
        structure_embedding=_bundle_value(value, "structure_embedding"),
        ligand_embedding=_bundle_value(value, "ligand_embedding"),
        provenance=_bundle_provenance(value),
    )


def _index_feature_bundles(
    values: Mapping[str, Any] | Iterable[Any] | None,
) -> dict[str, MultimodalFeatureBundle]:
    if values is None:
        return {}
    if isinstance(values, Mapping):
        return {
            _clean_text(key): _coerce_feature_bundle(bundle)
            for key, bundle in values.items()
            if _clean_text(key)
        }
    indexed: dict[str, MultimodalFeatureBundle] = {}
    for value in values:
        bundle = _coerce_feature_bundle(value)
        indexed[bundle.example_id] = bundle
    return indexed


def _feature_bundle_signature(feature_bundles: Mapping[str, MultimodalFeatureBundle]) -> str:
    if not feature_bundles:
        return "none"
    payload = {
        "example_ids": sorted(feature_bundles),
        "bundles": [
            {
                "example_id": bundle.example_id,
                "present_modalities": [
                    modality
                    for modality, embedding in (
                        ("sequence", bundle.sequence_embedding),
                        ("structure", bundle.structure_embedding),
                        ("ligand", bundle.ligand_embedding),
                    )
                    if embedding is not None
                ],
                "modality_sources": {
                    modality: _clean_text(getattr(embedding, "source", ""))
                    for modality, embedding in (
                        ("sequence", bundle.sequence_embedding),
                        ("structure", bundle.structure_embedding),
                        ("ligand", bundle.ligand_embedding),
                    )
                    if embedding is not None
                },
                "modality_models": {
                    modality: _clean_text(getattr(embedding, "model_name", ""))
                    for modality, embedding in (
                        ("sequence", bundle.sequence_embedding),
                        ("structure", bundle.structure_embedding),
                        ("ligand", bundle.ligand_embedding),
                    )
                    if embedding is not None
                },
                "modality_dims": {
                    modality: int(getattr(embedding, "embedding_dim", 0) or 0)
                    for modality, embedding in (
                        ("sequence", bundle.sequence_embedding),
                        ("structure", bundle.structure_embedding),
                        ("ligand", bundle.ligand_embedding),
                    )
                    if embedding is not None
                },
                "provenance": _json_ready(dict(bundle.provenance)),
            }
            for bundle in sorted(feature_bundles.values(), key=lambda item: item.example_id)
        ],
    }
    return _fingerprint(payload)


@dataclass(frozen=True, slots=True)
class ExecutedMultimodalExample:
    example_id: str
    step_index: int
    available_modalities: tuple[str, ...]
    requested_modalities: tuple[str, ...]
    input_mode: str
    target: float
    prediction: float
    loss: float
    fusion_result: FusionModelResult
    feature_bundle_provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "example_id": self.example_id,
            "step_index": self.step_index,
            "available_modalities": list(self.available_modalities),
            "requested_modalities": list(self.requested_modalities),
            "input_mode": self.input_mode,
            "target": self.target,
            "prediction": self.prediction,
            "loss": self.loss,
            "fusion_result": self.fusion_result.to_dict(),
            "feature_bundle_provenance": dict(self.feature_bundle_provenance),
        }


@dataclass(frozen=True, slots=True)
class MultimodalRuntimeCheckpoint:
    run_id: str
    checkpoint_tag: str
    checkpoint_ref: str
    checkpoint_path: str
    processed_examples: int
    completed_example_ids: tuple[str, ...]
    processable_example_ids: tuple[str, ...]
    deterministic_seed: int
    plan_signature: str
    dataset_signature: str
    feature_bundle_signature: str
    head_weights: tuple[float, ...]
    head_bias: float
    loss_history: tuple[float, ...]
    resumed_from: str | None = None
    provenance: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "checkpoint_tag": self.checkpoint_tag,
            "checkpoint_ref": self.checkpoint_ref,
            "checkpoint_path": self.checkpoint_path,
            "processed_examples": self.processed_examples,
            "completed_example_ids": list(self.completed_example_ids),
            "processable_example_ids": list(self.processable_example_ids),
            "deterministic_seed": self.deterministic_seed,
            "plan_signature": self.plan_signature,
            "dataset_signature": self.dataset_signature,
            "feature_bundle_signature": self.feature_bundle_signature,
            "head_weights": list(self.head_weights),
            "head_bias": self.head_bias,
            "loss_history": list(self.loss_history),
            "resumed_from": self.resumed_from,
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MultimodalRuntimeCheckpoint:
        return cls(
            run_id=_clean_text(payload.get("run_id")),
            checkpoint_tag=_clean_text(payload.get("checkpoint_tag")),
            checkpoint_ref=_clean_text(payload.get("checkpoint_ref")),
            checkpoint_path=_clean_text(payload.get("checkpoint_path")),
            processed_examples=int(payload.get("processed_examples") or 0),
            completed_example_ids=tuple(
                str(item) for item in payload.get("completed_example_ids") or ()
            ),
            processable_example_ids=tuple(
                str(item) for item in payload.get("processable_example_ids") or ()
            ),
            deterministic_seed=int(payload.get("deterministic_seed") or 0),
            plan_signature=_clean_text(payload.get("plan_signature")),
            dataset_signature=_clean_text(payload.get("dataset_signature")),
            feature_bundle_signature=_clean_text(payload.get("feature_bundle_signature"))
            or "none",
            head_weights=tuple(float(item) for item in payload.get("head_weights") or ()),
            head_bias=float(payload.get("head_bias") or 0.0),
            loss_history=tuple(float(item) for item in payload.get("loss_history") or ()),
            resumed_from=_clean_text(payload.get("resumed_from")) or None,
            provenance=dict(payload.get("provenance") or {}),
        )

    def to_checkpoint_record(self) -> CheckpointRecord:
        return CheckpointRecord(
            run_id=self.run_id,
            checkpoint_state=self.to_dict(),
            version=1,
            provenance=dict(self.provenance),
            metadata={
                "checkpoint_tag": self.checkpoint_tag,
                "checkpoint_ref": self.checkpoint_ref,
                "checkpoint_path": self.checkpoint_path,
                "resumed_from": self.resumed_from,
                "plan_signature": self.plan_signature,
                "dataset_signature": self.dataset_signature,
                "feature_bundle_signature": self.feature_bundle_signature,
            },
        )

    @classmethod
    def from_checkpoint_record(
        cls,
        record: CheckpointRecord,
    ) -> MultimodalRuntimeCheckpoint:
        if _clean_text(record.run_id) != _clean_text(record.checkpoint_state.get("run_id")):
            raise ValueError("checkpoint record run_id does not match checkpoint state")
        if record.node_id is not None:
            raise ValueError("multimodal runtime checkpoints must be run-level records")
        return cls.from_dict(record.checkpoint_state)


@dataclass(frozen=True, slots=True)
class ExecutableMultimodalTrainingResult:
    spec: Any
    dataset: Any
    fusion_model: Any
    plan: MultimodalTrainingPlan
    state: MultimodalTrainingState
    checkpoint: MultimodalRuntimeCheckpoint
    example_results: tuple[ExecutedMultimodalExample, ...]
    blockers: tuple[Any, ...] = field(default_factory=tuple)

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": _json_ready(self.spec),
            "dataset": _json_ready(self.dataset),
            "fusion_model": _json_ready(self.fusion_model),
            "plan": self.plan.to_dict(),
            "state": self.state.to_dict(),
            "checkpoint": self.checkpoint.to_dict(),
            "example_results": [item.to_dict() for item in self.example_results],
            "blockers": [_json_ready(item) for item in self.blockers],
        }


def _load_checkpoint(checkpoint_path: Path) -> MultimodalRuntimeCheckpoint:
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping) and "checkpoint_state" in payload:
        return MultimodalRuntimeCheckpoint.from_checkpoint_record(
            CheckpointRecord.from_dict(payload)
        )
    return MultimodalRuntimeCheckpoint.from_dict(payload)


def _write_checkpoint(checkpoint: MultimodalRuntimeCheckpoint) -> None:
    checkpoint_path = Path(checkpoint.checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(
        json.dumps(checkpoint.to_checkpoint_record().to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def execute_multimodal_training(
    storage_runtime: StorageRuntimeResult,
    *,
    ppi_representation: Mapping[str, Any] | Any | None = None,
    dataset_id: str | None = None,
    requested_modalities: Iterable[str] = (),
    model_name: str = "multimodal-fusion-baseline-v1",
    fusion_dim: int = 8,
    deterministic_seed: int = 0,
    feature_bundles: Mapping[str, Any] | Iterable[Any] | None = None,
    learning_rate: float = 0.1,
    checkpoint_dir: str | Path | None = None,
    checkpoint_path: str | Path | None = None,
    resume: bool = False,
    max_examples: int | None = None,
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> ExecutableMultimodalTrainingResult:
    if deterministic_seed < 0:
        raise ValueError("deterministic_seed must be non-negative")
    if learning_rate <= 0.0:
        raise ValueError("learning_rate must be > 0")
    if max_examples is not None and max_examples < 1:
        raise ValueError("max_examples must be >= 1 when provided")

    contract_result = prepare_multimodal_training(
        storage_runtime,
        ppi_representation=ppi_representation,
        dataset_id=dataset_id,
        requested_modalities=requested_modalities,
        model_name=model_name,
        fusion_dim=fusion_dim,
        deterministic_seed=deterministic_seed,
        provenance=provenance,
        notes=notes,
    )
    feature_bundle_index = _index_feature_bundles(feature_bundles)
    feature_bundle_signature = _feature_bundle_signature(feature_bundle_index)
    run_id = _run_id(
        contract_result,
        deterministic_seed=deterministic_seed,
        feature_bundle_signature=feature_bundle_signature,
    )
    resolved_checkpoint_path = (
        Path(checkpoint_path)
        if checkpoint_path is not None
        else Path(checkpoint_dir or DEFAULT_CHECKPOINT_ROOT)
        / f"{contract_result.state.checkpoint_tag}.json"
    )
    checkpoint_ref = f"checkpoint://{run_id}/{contract_result.state.checkpoint_tag}"
    stored_checkpoint: MultimodalRuntimeCheckpoint | None = None

    if resume:
        if not resolved_checkpoint_path.exists():
            raise FileNotFoundError(resolved_checkpoint_path)
        stored_checkpoint = _load_checkpoint(resolved_checkpoint_path)
        if stored_checkpoint.run_id != run_id:
            raise ValueError("resume checkpoint run_id does not match the current runtime inputs")
        if stored_checkpoint.plan_signature != contract_result.plan.plan_signature:
            raise ValueError(
                "resume checkpoint plan signature does not match the current runtime inputs"
            )
        if stored_checkpoint.dataset_signature != contract_result.state.dataset_signature:
            raise ValueError(
                "resume checkpoint dataset signature does not match the current runtime inputs"
            )
        weights = stored_checkpoint.head_weights
        bias = stored_checkpoint.head_bias
        loss_history = list(stored_checkpoint.loss_history)
        resumed_from = stored_checkpoint.checkpoint_ref
    else:
        weights = _initial_weights(
            contract_result.spec.fusion_dim,
            deterministic_seed=deterministic_seed,
        )
        bias = 0.0
        processed_examples = 0
        loss_history = []
        resumed_from = None

    processable_examples = [
        example
        for example in contract_result.dataset.examples
        if any(
            modality in contract_result.plan.fusion_modalities
            for modality in example.available_modalities
        )
    ]
    if not processable_examples:
        raise ValueError("dataset does not expose any fusion-supported modalities")
    processable_example_ids = tuple(example.example_id for example in processable_examples)

    if resume:
        if not stored_checkpoint.completed_example_ids:
            raise ValueError("resume checkpoint is missing example identity metadata")
        if not stored_checkpoint.processable_example_ids:
            raise ValueError("resume checkpoint is missing processable example identity metadata")
        if stored_checkpoint.feature_bundle_signature != feature_bundle_signature:
            raise ValueError(
                "resume checkpoint feature bundle signature does not match "
                "the current runtime inputs"
            )
        if stored_checkpoint.processable_example_ids != processable_example_ids:
            raise ValueError(
                "resume checkpoint example order does not match the current dataset"
            )
        resumed_example_ids = stored_checkpoint.completed_example_ids
        if processable_example_ids[: len(resumed_example_ids)] != resumed_example_ids:
            raise ValueError(
                "resume checkpoint example identities do not match the current dataset prefix"
            )
        processed_examples = len(resumed_example_ids)
    else:
        resumed_example_ids = ()

    start_index = min(processed_examples, len(processable_examples))
    remaining_examples = processable_examples[start_index:]
    if max_examples is not None:
        remaining_examples = remaining_examples[:max_examples]

    example_results: list[ExecutedMultimodalExample] = []
    completed_example_ids: list[str] = list(resumed_example_ids)
    feature_bundle_example_ids: list[str] = []
    surrogate_example_ids: list[str] = []
    for offset, example in enumerate(remaining_examples, start=1):
        feature_bundle = feature_bundle_index.get(example.example_id)
        bundle_has_inputs = feature_bundle is not None and any(
            (
                feature_bundle.sequence_embedding is not None,
                feature_bundle.structure_embedding is not None,
                feature_bundle.ligand_embedding is not None,
            )
        )
        if bundle_has_inputs:
            input_mode = "real-feature-bundle"
            feature_bundle_example_ids.append(example.example_id)
            fusion_result = contract_result.fusion_model.fuse(
                feature_bundle=feature_bundle,
                provenance={
                    "backend": DEFAULT_RUNTIME_BACKEND,
                    "objective": DEFAULT_RUNTIME_OBJECTIVE,
                    "example_id": example.example_id,
                    "run_id": run_id,
                    "input_mode": input_mode,
                    "feature_bundle_example_id": feature_bundle.example_id,
                },
            )
            feature_bundle_provenance = dict(feature_bundle.provenance)
        else:
            input_mode = "surrogate-materialized-ref"
            surrogate_example_ids.append(example.example_id)
            sequence_embedding = _sequence_embedding(
                example,
                fusion_dim=contract_result.spec.fusion_dim,
                deterministic_seed=deterministic_seed,
            )
            structure_embedding = _structure_embedding(
                example,
                fusion_dim=contract_result.spec.fusion_dim,
                deterministic_seed=deterministic_seed,
            )
            ligand_embedding = _ligand_embedding(
                example,
                fusion_dim=contract_result.spec.fusion_dim,
                deterministic_seed=deterministic_seed,
            )
            fusion_result = contract_result.fusion_model.fuse(
                sequence_embedding=sequence_embedding,
                structure_embedding=structure_embedding,
                ligand_embedding=ligand_embedding,
                provenance={
                    "backend": DEFAULT_RUNTIME_BACKEND,
                    "objective": DEFAULT_RUNTIME_OBJECTIVE,
                    "example_id": example.example_id,
                    "run_id": run_id,
                    "input_mode": input_mode,
                },
            )
            feature_bundle_provenance = {}
        target = _coverage_target(
            example,
            requested_modalities=contract_result.plan.requested_modalities,
        )
        prediction = (
            sum(
                weight * value
                for weight, value in zip(
                    weights,
                    fusion_result.fused_embedding,
                    strict=True,
                )
            )
            + bias
        )
        error = prediction - target
        loss = error * error
        gradient_scale = 2.0 * error
        weights = tuple(
            weight - learning_rate * gradient_scale * value
            for weight, value in zip(weights, fusion_result.fused_embedding, strict=True)
        )
        bias = bias - learning_rate * gradient_scale
        loss_history.append(loss)
        processed_examples += 1
        completed_example_ids.append(example.example_id)
        example_results.append(
            ExecutedMultimodalExample(
                example_id=example.example_id,
                step_index=start_index + offset,
                available_modalities=example.available_modalities,
                requested_modalities=contract_result.plan.requested_modalities,
                input_mode=input_mode,
                target=target,
                prediction=prediction,
                loss=loss,
                fusion_result=fusion_result,
                feature_bundle_provenance=feature_bundle_provenance,
            )
        )

    checkpoint = MultimodalRuntimeCheckpoint(
        run_id=run_id,
        checkpoint_tag=contract_result.state.checkpoint_tag,
        checkpoint_ref=checkpoint_ref,
        checkpoint_path=str(resolved_checkpoint_path).replace("\\", "/"),
        processed_examples=processed_examples,
        completed_example_ids=tuple(completed_example_ids),
        processable_example_ids=processable_example_ids,
        deterministic_seed=deterministic_seed,
        plan_signature=contract_result.plan.plan_signature,
        dataset_signature=contract_result.state.dataset_signature,
        feature_bundle_signature=feature_bundle_signature,
        head_weights=weights,
        head_bias=bias,
        loss_history=tuple(loss_history),
        resumed_from=resumed_from,
        provenance={
            "backend": DEFAULT_RUNTIME_BACKEND,
            "objective": DEFAULT_RUNTIME_OBJECTIVE,
            "learning_rate": learning_rate,
            "requested_modalities": list(contract_result.plan.requested_modalities),
            "fusion_modalities": list(contract_result.plan.fusion_modalities),
            "processed_example_ids": list(completed_example_ids),
            "completed_example_ids": list(completed_example_ids),
            "processable_example_ids": list(processable_example_ids),
            "feature_bundle_signature": feature_bundle_signature,
            "feature_bundle_example_ids": list(feature_bundle_example_ids),
            "surrogate_example_ids": list(surrogate_example_ids),
            "input_mode_counts": {
                "real_feature_bundle": len(feature_bundle_example_ids),
                "surrogate_materialized_ref": len(surrogate_example_ids),
            },
        },
    )
    _write_checkpoint(checkpoint)

    final_status = MultimodalTrainingRuntimeStatus(
        stage="trainer_runtime",
        requested_backend=f"{contract_result.spec.model_name}+multimodal-dataset-adapter",
        resolved_backend=DEFAULT_RUNTIME_BACKEND,
        backend_ready=True,
        contract_fidelity="fusion-forward-plus-checkpointed-prototype",
        provenance={
            "run_id": run_id,
            "checkpoint_ref": checkpoint.checkpoint_ref,
            "checkpoint_path": checkpoint.checkpoint_path,
            "objective": DEFAULT_RUNTIME_OBJECTIVE,
            "learning_rate": learning_rate,
            "processable_examples": len(processable_examples),
            "processed_examples": processed_examples,
            "resumed_from": resumed_from,
            "feature_bundle_signature": feature_bundle_signature,
            "feature_bundle_example_ids": list(feature_bundle_example_ids),
            "surrogate_example_ids": list(surrogate_example_ids),
            "input_mode_counts": {
                "real_feature_bundle": len(feature_bundle_example_ids),
                "surrogate_materialized_ref": len(surrogate_example_ids),
            },
            "surrogate_modalities": [
                "sequence materialized-ref surrogate",
                "structure materialized-ref surrogate",
                "ligand materialized-ref surrogate",
            ]
            if surrogate_example_ids
            else [],
            "retained_real_components": [
                "multimodal dataset adapter",
                "real feature-bundle inputs when provided",
                "fusion model forward pass",
                "checkpoint serialization",
                "deterministic resume continuity",
            ],
            "abstracted_components": [
                "production optimizer stack",
                "distributed training",
                "native biological sequence/structure/ligand encoders",
            ],
        },
        blocker=None,
    )
    final_plan = replace(contract_result.plan, status=final_status)
    phase = "completed" if processed_examples >= len(processable_examples) else "paused"
    state_signature = _fingerprint(
        {
            "run_id": run_id,
            "phase": phase,
            "processed_examples": processed_examples,
            "checkpoint_ref": checkpoint.checkpoint_ref,
            "feature_bundle_signature": feature_bundle_signature,
            "head_weights": list(weights),
            "head_bias": bias,
            "loss_history": list(loss_history),
        }
    )
    final_state = MultimodalTrainingState(
        phase=phase,
        processed_examples=processed_examples,
        checkpoint_tag=checkpoint.checkpoint_tag,
        deterministic_seed=deterministic_seed,
        dataset_signature=contract_result.state.dataset_signature,
        state_signature=state_signature,
    )
    return ExecutableMultimodalTrainingResult(
        spec=contract_result.spec,
        dataset=contract_result.dataset,
        fusion_model=contract_result.fusion_model,
        plan=final_plan,
        state=final_state,
        checkpoint=checkpoint,
        example_results=tuple(example_results),
        blockers=(),
    )


def train_multimodal_runtime(
    storage_runtime: StorageRuntimeResult,
    **kwargs: Any,
) -> ExecutableMultimodalTrainingResult:
    return execute_multimodal_training(storage_runtime, **kwargs)


__all__ = [
    "DEFAULT_RUNTIME_BACKEND",
    "DEFAULT_RUNTIME_OBJECTIVE",
    "ExecutedMultimodalExample",
    "ExecutableMultimodalTrainingResult",
    "MultimodalRuntimeCheckpoint",
    "execute_multimodal_training",
    "train_multimodal_runtime",
]
