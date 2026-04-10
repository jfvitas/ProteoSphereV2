from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import exp, sqrt
from typing import Any, Literal

from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult

DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_MODEL = "seq-struct-cross-attention-baseline-v1"
DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_DIM = 8
DEFAULT_MODALITIES: tuple[str, ...] = ("sequence", "structure")

SeqStructCrossAttentionStatus = Literal["ok", "degraded"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _coerce_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping")
    return _json_ready(dict(value))


def _payload_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _mapping_or_attributes(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            return getattr(value, key)
    return None


def _project_vector(values: Sequence[float], *, width: int) -> tuple[float, ...]:
    numbers = [float(value) for value in values]
    if width < 1:
        raise ValueError("attention_dim must be >= 1")
    if not numbers:
        return tuple(0.0 for _ in range(width))
    if len(numbers) == width:
        return tuple(numbers)

    mean_value = sum(numbers) / len(numbers)
    min_value = min(numbers)
    max_value = max(numbers)
    l2_value = sqrt(sum(value * value for value in numbers))
    summary = [mean_value, min_value, max_value, l2_value, numbers[0], numbers[-1]]
    while len(summary) < width:
        summary.append(mean_value)
    return tuple(summary[:width])


def _mean_rows(rows: Sequence[Sequence[float]]) -> tuple[float, ...]:
    if not rows:
        return ()
    width = len(rows[0])
    totals = [0.0] * width
    for row in rows:
        if len(row) != width:
            raise ValueError("embedding rows must share a common width")
        for index, value in enumerate(row):
            totals[index] += float(value)
    return tuple(total / len(rows) for total in totals)


def _vector_norm(values: Sequence[float]) -> float:
    return sqrt(sum(float(value) * float(value) for value in values))


def _token_ids_for_sequence(sequence_length: int) -> tuple[str, ...]:
    return tuple(str(index) for index in range(1, sequence_length + 1))


def _normalize_mask(values: Any, *, length: int, field_name: str) -> tuple[bool, ...]:
    if values is None:
        return tuple(True for _ in range(length))
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a sequence of booleans")
    if not isinstance(values, Sequence):
        raise TypeError(f"{field_name} must be a sequence of booleans")
    mask = tuple(bool(value) for value in values)
    if len(mask) != length:
        raise ValueError(f"{field_name} must have length {length}")
    return mask


def _weighted_sum(
    vectors: Sequence[Sequence[float]],
    weights: Sequence[float],
) -> tuple[float, ...]:
    if not vectors:
        return ()
    if len(vectors) != len(weights):
        raise ValueError("weights must align with vectors")
    width = len(vectors[0])
    totals = [0.0] * width
    for vector, weight in zip(vectors, weights, strict=True):
        if len(vector) != width:
            raise ValueError("embedding rows must share a common width")
        for index, value in enumerate(vector):
            totals[index] += float(value) * float(weight)
    return tuple(totals)


def _softmax(logits: Sequence[float | None], mask: Sequence[bool]) -> tuple[float, ...]:
    visible_logits = [float(logit) for logit, keep in zip(logits, mask, strict=True) if keep]
    if not visible_logits:
        return tuple(0.0 for _ in logits)
    max_logit = max(visible_logits)
    exps = [
        exp(float(logit) - max_logit) if keep else 0.0
        for logit, keep in zip(logits, mask, strict=True)
    ]
    total = sum(exps)
    if total <= 0.0:
        return tuple(0.0 for _ in logits)
    return tuple(value / total if keep else 0.0 for value, keep in zip(exps, mask, strict=True))


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must share a common width")
    return sum(float(lval) * float(rval) for lval, rval in zip(left, right, strict=True))


def _attention_rows(
    query_vectors: Sequence[Sequence[float]],
    query_mask: Sequence[bool],
    key_vectors: Sequence[Sequence[float]],
    key_mask: Sequence[bool],
) -> tuple[tuple[tuple[float, ...], ...], tuple[tuple[float, ...], ...]]:
    if not query_vectors:
        return (), ()
    if len(query_vectors) != len(query_mask):
        raise ValueError("query mask must align with query vectors")
    width = len(query_vectors[0])
    if any(len(vector) != width for vector in query_vectors):
        raise ValueError("query vectors must share a common width")
    if not key_vectors:
        zero_context = tuple(0.0 for _ in range(width))
        rows = tuple(
            tuple() if keep else tuple()
            for keep in query_mask
        )
        return rows, tuple(zero_context for _ in query_vectors)

    if any(len(vector) != width for vector in key_vectors):
        raise ValueError("key vectors must share a common width")

    zero_row = tuple(0.0 for _ in key_vectors)
    zero_context = tuple(0.0 for _ in range(width))
    rows: list[tuple[float, ...]] = []
    contexts: list[tuple[float, ...]] = []
    scale = sqrt(float(width))

    for query_vector, keep_query in zip(query_vectors, query_mask, strict=True):
        if not keep_query:
            rows.append(zero_row)
            contexts.append(zero_context)
            continue

        logits: list[float | None] = []
        for key_vector, keep_key in zip(key_vectors, key_mask, strict=True):
            if not keep_key:
                logits.append(None)
            else:
                logits.append(_dot(query_vector, key_vector) / scale)

        weights = _softmax(logits, key_mask)
        rows.append(weights)
        contexts.append(_weighted_sum(key_vectors, weights))

    return tuple(rows), tuple(contexts)


def _sequence_embedding_payload(value: Any) -> dict[str, Any]:
    provenance = _coerce_provenance(_mapping_or_attributes(value, "provenance"))
    source = _clean_text(_mapping_or_attributes(value, "source")) or None
    model_name = _clean_text(_mapping_or_attributes(value, "model_name")) or None
    residue_embeddings = _mapping_or_attributes(value, "residue_embeddings", "token_embeddings")
    pooled_embedding = _mapping_or_attributes(value, "pooled_embedding")
    token_ids = _mapping_or_attributes(value, "token_ids")
    if residue_embeddings is None or pooled_embedding is None:
        raise TypeError(
            "sequence embeddings must expose residue_embeddings and pooled_embedding"
        )
    normalized_residue_embeddings = tuple(
        tuple(float(item) for item in row) for row in residue_embeddings
    )
    if not normalized_residue_embeddings:
        raise ValueError("sequence embedding must contain at least one residue embedding")
    normalized_token_ids = (
        tuple(str(item) for item in token_ids)
        if token_ids is not None
        else _token_ids_for_sequence(len(normalized_residue_embeddings))
    )
    if len(normalized_token_ids) != len(normalized_residue_embeddings):
        raise ValueError("sequence token_ids must align with residue embeddings")
    return {
        "present": True,
        "token_ids": normalized_token_ids,
        "token_embeddings": normalized_residue_embeddings,
        "pooled_embedding": tuple(float(item) for item in pooled_embedding),
        "provenance": provenance,
        "source": source,
        "model_name": model_name,
    }


def _structure_embedding_payload(value: Any) -> dict[str, Any]:
    provenance = _coerce_provenance(_mapping_or_attributes(value, "provenance"))
    source = _clean_text(_mapping_or_attributes(value, "source")) or None
    model_name = _clean_text(_mapping_or_attributes(value, "model_name")) or None
    token_ids = _mapping_or_attributes(value, "token_ids")
    token_embeddings = _mapping_or_attributes(value, "token_embeddings")
    pooled_embedding = _mapping_or_attributes(value, "pooled_embedding")
    if token_ids is None or token_embeddings is None or pooled_embedding is None:
        raise TypeError(
            "structure embeddings must expose token_ids, token_embeddings, and pooled_embedding"
        )
    normalized_token_ids = tuple(str(item) for item in token_ids)
    normalized_token_embeddings = tuple(
        tuple(float(item) for item in row) for row in token_embeddings
    )
    if not normalized_token_embeddings:
        raise ValueError("structure embedding must contain at least one token embedding")
    if len(normalized_token_ids) != len(normalized_token_embeddings):
        raise ValueError("structure token_ids must align with token_embeddings")
    return {
        "present": True,
        "token_ids": normalized_token_ids,
        "token_embeddings": normalized_token_embeddings,
        "pooled_embedding": tuple(float(item) for item in pooled_embedding),
        "provenance": provenance,
        "source": source,
        "model_name": model_name,
    }


def _missing_payload() -> dict[str, Any]:
    return {
        "present": False,
        "token_ids": (),
        "token_embeddings": (),
        "pooled_embedding": (),
        "provenance": {},
        "source": None,
        "model_name": None,
    }


@dataclass(frozen=True, slots=True)
class SeqStructCrossAttentionResult:
    model_name: str
    attention_dim: int
    modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    sequence_token_ids: tuple[str, ...]
    structure_token_ids: tuple[str, ...]
    sequence_token_mask: tuple[bool, ...]
    structure_token_mask: tuple[bool, ...]
    sequence_attention_weights: tuple[tuple[float, ...], ...]
    structure_attention_weights: tuple[tuple[float, ...], ...]
    sequence_summary_embedding: tuple[float, ...]
    structure_summary_embedding: tuple[float, ...]
    sequence_context_embedding: tuple[float, ...]
    structure_context_embedding: tuple[float, ...]
    fused_embedding: tuple[float, ...]
    feature_names: tuple[str, ...]
    feature_vector: tuple[float, ...]
    metrics: dict[str, float]
    source_kind: str = "sequence_structure_cross_attention_baseline"
    frozen: bool = True
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def available_count(self) -> int:
        return len(self.available_modalities)

    @property
    def missing_count(self) -> int:
        return len(self.missing_modalities)

    @property
    def coverage(self) -> float:
        if not self.modalities:
            return 0.0
        return self.available_count / float(len(self.modalities))

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "attention_dim": self.attention_dim,
            "modalities": list(self.modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "sequence_token_ids": list(self.sequence_token_ids),
            "structure_token_ids": list(self.structure_token_ids),
            "sequence_token_mask": list(self.sequence_token_mask),
            "structure_token_mask": list(self.structure_token_mask),
            "sequence_attention_weights": [
                list(row) for row in self.sequence_attention_weights
            ],
            "structure_attention_weights": [
                list(row) for row in self.structure_attention_weights
            ],
            "sequence_summary_embedding": list(self.sequence_summary_embedding),
            "structure_summary_embedding": list(self.structure_summary_embedding),
            "sequence_context_embedding": list(self.sequence_context_embedding),
            "structure_context_embedding": list(self.structure_context_embedding),
            "fused_embedding": list(self.fused_embedding),
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "metrics": dict(self.metrics),
            "source_kind": self.source_kind,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class SeqStructCrossAttentionBaseline:
    model_name: str = DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_MODEL
    attention_dim: int = DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_DIM
    source_kind: str = "sequence_structure_cross_attention_baseline"
    modalities: tuple[str, ...] = DEFAULT_MODALITIES

    def __post_init__(self) -> None:
        model_name = _clean_text(self.model_name)
        source_kind = _clean_text(self.source_kind)
        modalities = tuple(
            modality
            for modality in (_clean_text(name) for name in self.modalities)
            if modality
        )
        if not model_name:
            raise ValueError("model_name must be a non-empty string")
        if self.attention_dim < 1:
            raise ValueError("attention_dim must be >= 1")
        if modalities != DEFAULT_MODALITIES:
            invalid_modalities = sorted(
                modality for modality in modalities if modality not in DEFAULT_MODALITIES
            )
            if invalid_modalities or len(modalities) != len(DEFAULT_MODALITIES):
                raise ValueError("modalities must be ('sequence', 'structure')")
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(
            self,
            "source_kind",
            source_kind or "sequence_structure_cross_attention_baseline",
        )
        object.__setattr__(self, "modalities", DEFAULT_MODALITIES)

    def forward(
        self,
        feature_bundle: Any | None = None,
        *,
        sequence_embedding: ProteinEmbeddingResult | Mapping[str, Any] | Any | None = None,
        structure_embedding: StructureEmbeddingResult | Mapping[str, Any] | Any | None = None,
        sequence_token_mask: Sequence[bool] | None = None,
        structure_token_mask: Sequence[bool] | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> SeqStructCrossAttentionResult:
        bundle_provenance: dict[str, Any] = {}
        if feature_bundle is not None:
            if isinstance(feature_bundle, Mapping):
                bundle_provenance = _coerce_provenance(_payload_value(feature_bundle, "provenance"))
            else:
                bundle_provenance = _coerce_provenance(
                    _mapping_or_attributes(feature_bundle, "provenance")
                )
            if sequence_embedding is None:
                sequence_embedding = _mapping_or_attributes(feature_bundle, "sequence_embedding")
            if structure_embedding is None:
                structure_embedding = _mapping_or_attributes(feature_bundle, "structure_embedding")
            if sequence_token_mask is None:
                sequence_token_mask = _mapping_or_attributes(feature_bundle, "sequence_token_mask")
            if structure_token_mask is None:
                structure_token_mask = _mapping_or_attributes(
                    feature_bundle, "structure_token_mask"
                )

        sequence = (
            _sequence_embedding_payload(sequence_embedding)
            if sequence_embedding is not None
            else _missing_payload()
        )
        structure = (
            _structure_embedding_payload(structure_embedding)
            if structure_embedding is not None
            else _missing_payload()
        )

        if not sequence["present"] and not structure["present"]:
            raise ValueError("at least one modality embedding must be provided")

        sequence_vectors = tuple(
            _project_vector(row, width=self.attention_dim) for row in sequence["token_embeddings"]
        )
        structure_vectors = tuple(
            _project_vector(row, width=self.attention_dim) for row in structure["token_embeddings"]
        )

        sequence_mask = _normalize_mask(
            sequence_token_mask,
            length=len(sequence_vectors),
            field_name="sequence_token_mask",
        )
        structure_mask = _normalize_mask(
            structure_token_mask,
            length=len(structure_vectors),
            field_name="structure_token_mask",
        )

        sequence_to_structure_attention, sequence_context_rows = _attention_rows(
            sequence_vectors,
            sequence_mask,
            structure_vectors,
            structure_mask,
        )
        structure_to_sequence_attention, structure_context_rows = _attention_rows(
            structure_vectors,
            structure_mask,
            sequence_vectors,
            sequence_mask,
        )

        sequence_summary_embedding = (
            _project_vector(sequence["pooled_embedding"], width=self.attention_dim)
            if sequence["present"]
            else tuple(0.0 for _ in range(self.attention_dim))
        )
        structure_summary_embedding = (
            _project_vector(structure["pooled_embedding"], width=self.attention_dim)
            if structure["present"]
            else tuple(0.0 for _ in range(self.attention_dim))
        )
        sequence_context_embedding = (
            _mean_rows(sequence_context_rows)
            if sequence_context_rows
            else tuple(0.0 for _ in range(self.attention_dim))
        )
        structure_context_embedding = (
            _mean_rows(structure_context_rows)
            if structure_context_rows
            else tuple(0.0 for _ in range(self.attention_dim))
        )

        available_vectors: list[tuple[float, ...]] = []
        if sequence["present"]:
            available_vectors.extend(
                [sequence_summary_embedding, sequence_context_embedding]
            )
        if structure["present"]:
            available_vectors.extend(
                [structure_summary_embedding, structure_context_embedding]
            )
        fused_embedding = (
            _mean_rows(available_vectors)
            if available_vectors
            else tuple(0.0 for _ in range(self.attention_dim))
        )
        sequence_attention_mass = (
            sum(sum(row) for row in sequence_to_structure_attention)
            / len(sequence_to_structure_attention)
            if sequence_to_structure_attention
            else 0.0
        )
        structure_attention_mass = (
            sum(sum(row) for row in structure_to_sequence_attention)
            / len(structure_to_sequence_attention)
            if structure_to_sequence_attention
            else 0.0
        )
        cross_modal_alignment = 0.0
        if sequence["present"] and structure["present"]:
            cross_modal_alignment = _dot(
                sequence_summary_embedding,
                structure_summary_embedding,
            ) / sqrt(float(self.attention_dim))

        available_modalities = tuple(
            modality
            for modality, payload in (
                ("sequence", sequence),
                ("structure", structure),
            )
            if payload["present"]
        )
        missing_modalities = tuple(
            modality
            for modality, payload in (
                ("sequence", sequence),
                ("structure", structure),
            )
            if not payload["present"]
        )
        sequence_masked_count = float(sum(1 for item in sequence_mask if not item))
        structure_masked_count = float(sum(1 for item in structure_mask if not item))
        sequence_masked_fraction = (
            sequence_masked_count / float(len(sequence_mask)) if sequence_mask else 0.0
        )
        structure_masked_fraction = (
            structure_masked_count / float(len(structure_mask)) if structure_mask else 0.0
        )

        feature_names = (
            "sequence_present",
            "structure_present",
            "sequence_token_count",
            "structure_token_count",
            "sequence_masked_count",
            "structure_masked_count",
            "sequence_attention_mass",
            "structure_attention_mass",
            "sequence_context_l2_norm",
            "structure_context_l2_norm",
            "cross_modal_alignment",
            "coverage",
            "fused_l2_norm",
        )
        feature_vector = (
            1.0 if sequence["present"] else 0.0,
            1.0 if structure["present"] else 0.0,
            float(len(sequence_vectors)),
            float(len(structure_vectors)),
            sequence_masked_count,
            structure_masked_count,
            sequence_attention_mass,
            structure_attention_mass,
            _vector_norm(sequence_context_embedding),
            _vector_norm(structure_context_embedding),
            cross_modal_alignment,
            float(len(available_modalities)) / float(len(DEFAULT_MODALITIES)),
            _vector_norm(fused_embedding),
        )
        metrics = {
            "coverage": float(len(available_modalities)) / float(len(DEFAULT_MODALITIES)),
            "available_count": float(len(available_modalities)),
            "missing_count": float(len(missing_modalities)),
            "sequence_token_count": float(len(sequence_vectors)),
            "structure_token_count": float(len(structure_vectors)),
            "sequence_masked_count": sequence_masked_count,
            "structure_masked_count": structure_masked_count,
            "sequence_masked_fraction": sequence_masked_fraction,
            "structure_masked_fraction": structure_masked_fraction,
            "sequence_attention_mass": sequence_attention_mass,
            "structure_attention_mass": structure_attention_mass,
            "cross_modal_alignment": cross_modal_alignment,
            "fused_l2_norm": _vector_norm(fused_embedding),
        }

        provenance_payload = dict(bundle_provenance)
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source_kind": self.source_kind,
                "attention_dim": self.attention_dim,
                "modalities": list(DEFAULT_MODALITIES),
                "available_modalities": list(available_modalities),
                "missing_modalities": list(missing_modalities),
                "sequence_source": sequence["source"],
                "sequence_model_name": sequence["model_name"],
                "sequence_provenance": dict(sequence["provenance"]),
                "structure_source": structure["source"],
                "structure_model_name": structure["model_name"],
                "structure_provenance": dict(structure["provenance"]),
                "sequence_token_mask": list(sequence_mask),
                "structure_token_mask": list(structure_mask),
                "sequence_token_count": len(sequence_vectors),
                "structure_token_count": len(structure_vectors),
                "sequence_masked_count": int(sequence_masked_count),
                "structure_masked_count": int(structure_masked_count),
                "notes": (
                    "Deterministic cross-attention surrogate used until a concrete "
                    "sequence-structure attention trainer is wired into the repository."
                ),
            }
        )
        if provenance is not None:
            provenance_payload.update(_coerce_provenance(provenance))
        if sequence["provenance"]:
            provenance_payload.setdefault("sequence_input_provenance", dict(sequence["provenance"]))
        if structure["provenance"]:
            provenance_payload.setdefault(
                "structure_input_provenance",
                dict(structure["provenance"]),
            )

        status = "ok" if len(available_modalities) == len(DEFAULT_MODALITIES) else "degraded"
        return SeqStructCrossAttentionResult(
            model_name=self.model_name,
            attention_dim=self.attention_dim,
            modalities=DEFAULT_MODALITIES,
            available_modalities=available_modalities,
            missing_modalities=missing_modalities,
            sequence_token_ids=sequence["token_ids"],
            structure_token_ids=structure["token_ids"],
            sequence_token_mask=sequence_mask,
            structure_token_mask=structure_mask,
            sequence_attention_weights=sequence_to_structure_attention,
            structure_attention_weights=structure_to_sequence_attention,
            sequence_summary_embedding=sequence_summary_embedding,
            structure_summary_embedding=structure_summary_embedding,
            sequence_context_embedding=sequence_context_embedding,
            structure_context_embedding=structure_context_embedding,
            fused_embedding=fused_embedding,
            feature_names=feature_names,
            feature_vector=feature_vector,
            metrics=metrics,
            source_kind=self.source_kind,
            frozen=True,
            provenance=provenance_payload | {"status": status},
        )

    def attend(self, *args: Any, **kwargs: Any) -> SeqStructCrossAttentionResult:
        return self.forward(*args, **kwargs)


def cross_attend_sequence_structure(
    feature_bundle: Any | None = None,
    *,
    sequence_embedding: ProteinEmbeddingResult | Mapping[str, Any] | Any | None = None,
    structure_embedding: StructureEmbeddingResult | Mapping[str, Any] | Any | None = None,
    sequence_token_mask: Sequence[bool] | None = None,
    structure_token_mask: Sequence[bool] | None = None,
    provenance: Mapping[str, Any] | None = None,
    attention_dim: int = DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_DIM,
    model_name: str = DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_MODEL,
    source_kind: str = "sequence_structure_cross_attention_baseline",
) -> SeqStructCrossAttentionResult:
    return SeqStructCrossAttentionBaseline(
        model_name=model_name,
        attention_dim=attention_dim,
        source_kind=source_kind,
    ).forward(
        feature_bundle,
        sequence_embedding=sequence_embedding,
        structure_embedding=structure_embedding,
        sequence_token_mask=sequence_token_mask,
        structure_token_mask=structure_token_mask,
        provenance=provenance,
    )


__all__ = [
    "DEFAULT_MODALITIES",
    "DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_DIM",
    "DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_MODEL",
    "SeqStructCrossAttentionBaseline",
    "SeqStructCrossAttentionResult",
    "cross_attend_sequence_structure",
]
