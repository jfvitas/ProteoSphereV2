from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from core.library.summary_record import ProteinProteinSummaryRecord
from models.multimodal.ligand_encoder import LigandEmbeddingResult

DEFAULT_PAIR_LIGAND_CONTEXT_MODEL = "pair-ligand-context-baseline-v1"
DEFAULT_PAIR_LIGAND_CONTEXT_DIM = 8
DEFAULT_MODALITY_ORDER = ("pair", "ligand")


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


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Sequence):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


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


def _payload_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _project_vector(values: Sequence[float], *, width: int) -> tuple[float, ...]:
    numbers = [float(value) for value in values]
    if width < 1:
        raise ValueError("context_dim must be >= 1")
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


def _token_embedding(field_name: str, value: Any, *, width: int) -> tuple[float, ...]:
    text = f"{field_name}:{_clean_text(value)}"
    if width < 1:
        raise ValueError("context_dim must be >= 1")
    if not text:
        return tuple(0.0 for _ in range(width))

    codepoints = [ord(char) for char in text]
    mean_value = sum(codepoints) / len(codepoints)
    min_value = float(min(codepoints))
    max_value = float(max(codepoints))
    l2_value = sqrt(sum(value * value for value in codepoints))
    length_value = float(len(text))
    unique_value = float(len(set(text)))
    digit_count = float(sum(char.isdigit() for char in text))
    hash_value = float(sum(codepoints) % 997) / 997.0
    summary = [
        length_value,
        mean_value,
        min_value,
        max_value,
        l2_value,
        unique_value,
        digit_count,
        hash_value,
    ]
    while len(summary) < width:
        summary.append(mean_value)
    return tuple(summary[:width])


def _coerce_pair_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "present": False,
            "token_ids": (),
            "token_count": 0,
            "pooled_embedding": (),
            "provenance": {},
            "source": None,
            "model_name": None,
            "pair_summary_id": None,
            "protein_a_ref": None,
            "protein_b_ref": None,
        }
    if isinstance(value, Mapping) and {
        "token_ids",
        "token_embeddings",
        "pooled_embedding",
    }.issubset(value.keys()):
        token_ids = _dedupe_text(value.get("token_ids"))
        token_embeddings = tuple(
            tuple(float(item) for item in row)
            for row in _iter_values(value.get("token_embeddings"))
        )
        pooled_embedding = tuple(
            float(item) for item in _iter_values(value.get("pooled_embedding"))
        )
        if not token_embeddings or not pooled_embedding:
            raise TypeError("pair embeddings must contain token_embeddings and pooled_embedding")
        provenance = _coerce_provenance(value.get("provenance"))
        return {
            "present": True,
            "token_ids": token_ids,
            "token_count": len(token_ids),
            "pooled_embedding": pooled_embedding,
            "provenance": provenance,
            "source": _clean_text(value.get("source")) or "pair_context",
            "model_name": _clean_text(value.get("model_name")) or "pair_context_embedding",
            "pair_summary_id": _clean_text(value.get("pair_summary_id")) or None,
            "protein_a_ref": _clean_text(value.get("protein_a_ref")) or None,
            "protein_b_ref": _clean_text(value.get("protein_b_ref")) or None,
            "ligand_canonical_id": _clean_text(value.get("ligand_canonical_id")) or None,
            "ligand_id": _clean_text(value.get("ligand_id")) or None,
        }

    if isinstance(value, ProteinProteinSummaryRecord):
        record = value
    elif isinstance(value, Mapping):
        record = ProteinProteinSummaryRecord.from_dict(dict(value))
    else:
        record = ProteinProteinSummaryRecord.from_dict(
            {
                "summary_id": _mapping_or_attributes(value, "summary_id") or "",
                "protein_a_ref": _mapping_or_attributes(value, "protein_a_ref") or "",
                "protein_b_ref": _mapping_or_attributes(value, "protein_b_ref") or "",
                "interaction_type": _mapping_or_attributes(value, "interaction_type") or "",
                "interaction_id": _mapping_or_attributes(value, "interaction_id"),
                "interaction_refs": _mapping_or_attributes(value, "interaction_refs") or (),
                "evidence_refs": _mapping_or_attributes(value, "evidence_refs") or (),
                "organism_name": _mapping_or_attributes(value, "organism_name") or "",
                "taxon_id": _mapping_or_attributes(value, "taxon_id"),
                "physical_interaction": _mapping_or_attributes(value, "physical_interaction"),
                "directionality": _mapping_or_attributes(value, "directionality"),
                "evidence_count": _mapping_or_attributes(value, "evidence_count"),
                "confidence": _mapping_or_attributes(value, "confidence"),
                "join_status": _mapping_or_attributes(value, "join_status") or "joined",
                "join_reason": _mapping_or_attributes(value, "join_reason") or "",
                "context": _mapping_or_attributes(value, "context") or {},
                "notes": _mapping_or_attributes(value, "notes") or (),
            }
        )

    token_specs: list[tuple[str, Any]] = [
        ("summary_id", record.summary_id),
        ("protein_a_ref", record.protein_a_ref),
        ("protein_b_ref", record.protein_b_ref),
        ("interaction_type", record.interaction_type),
        ("interaction_id", record.interaction_id),
        ("interaction_refs", "|".join(record.interaction_refs)),
        ("evidence_refs", "|".join(record.evidence_refs)),
        ("organism_name", record.organism_name),
        ("taxon_id", record.taxon_id),
        ("physical_interaction", record.physical_interaction),
        ("directionality", record.directionality),
        ("evidence_count", record.evidence_count),
        ("confidence", record.confidence),
        ("join_status", record.join_status),
        ("join_reason", record.join_reason),
        ("notes", "|".join(record.notes)),
        ("storage_tier", record.context.storage_tier),
        ("planning_index_keys", "|".join(record.context.planning_index_keys)),
        ("storage_notes", "|".join(record.context.storage_notes)),
    ]
    token_ids: list[str] = []
    token_embeddings: list[tuple[float, ...]] = []
    for field_name, value in token_specs:
        if value in (None, ""):
            continue
        token_ids.append(field_name)
        token_embeddings.append(
            _token_embedding(field_name, value, width=DEFAULT_PAIR_LIGAND_CONTEXT_DIM)
        )

    provenance = {
        "pair_summary_id": record.summary_id,
        "protein_a_ref": record.protein_a_ref,
        "protein_b_ref": record.protein_b_ref,
        "interaction_id": record.interaction_id,
        "interaction_refs": list(record.interaction_refs),
        "evidence_refs": list(record.evidence_refs),
        "join_status": record.join_status,
        "join_reason": record.join_reason,
        "physical_interaction": record.physical_interaction,
        "directionality": record.directionality,
        "evidence_count": record.evidence_count,
        "confidence": record.confidence,
        "organism_name": record.organism_name,
        "taxon_id": record.taxon_id,
        "context": record.context.to_dict(),
    }
    return {
        "present": True,
        "token_ids": tuple(token_ids),
        "token_count": len(token_ids),
        "pooled_embedding": _mean_rows(token_embeddings),
        "provenance": provenance,
        "source": "protein_protein_summary",
        "model_name": "pair_context_baseline",
        "pair_summary_id": record.summary_id,
        "protein_a_ref": record.protein_a_ref,
        "protein_b_ref": record.protein_b_ref,
        "ligand_canonical_id": None,
        "ligand_id": None,
    }


def _coerce_ligand_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "present": False,
            "token_ids": (),
            "token_count": 0,
            "pooled_embedding": (),
            "provenance": {},
            "source": None,
            "model_name": None,
            "canonical_id": None,
            "ligand_id": None,
        }
    if isinstance(value, LigandEmbeddingResult):
        token_ids = tuple(value.token_ids)
        token_embeddings = tuple(
            tuple(float(item) for item in row) for row in value.token_embeddings
        )
        if not token_embeddings:
            raise TypeError("ligand embeddings must contain token_embeddings")
        return {
            "present": True,
            "token_ids": token_ids,
            "token_count": len(token_ids),
            "pooled_embedding": tuple(float(item) for item in value.pooled_embedding),
            "provenance": dict(value.provenance),
            "source": value.source,
            "model_name": value.model_name,
            "canonical_id": value.canonical_id,
            "ligand_id": value.ligand_id,
            "ligand_canonical_id": value.canonical_id,
        }
    if not isinstance(value, Mapping) and not any(
        hasattr(value, key)
        for key in ("token_ids", "token_embeddings", "pooled_embedding", "canonical_id")
    ):
        raise TypeError("ligand_context must be a LigandEmbeddingResult or mapping")
    token_ids = _dedupe_text(_mapping_or_attributes(value, "token_ids"))
    token_embeddings = tuple(
        tuple(float(item) for item in row)
        for row in _iter_values(_mapping_or_attributes(value, "token_embeddings"))
    )
    pooled_embedding = tuple(
        float(item) for item in _iter_values(_mapping_or_attributes(value, "pooled_embedding"))
    )
    if not token_embeddings or not pooled_embedding:
        raise TypeError("ligand context must contain token_embeddings and pooled_embedding")
    provenance = _coerce_provenance(_mapping_or_attributes(value, "provenance"))
    return {
        "present": True,
        "token_ids": token_ids,
        "token_count": len(token_ids),
        "pooled_embedding": pooled_embedding,
        "provenance": provenance,
        "source": _clean_text(_mapping_or_attributes(value, "source")) or "ligand_context",
        "model_name": _clean_text(_mapping_or_attributes(value, "model_name"))
        or "ligand_context_embedding",
        "canonical_id": _clean_text(_mapping_or_attributes(value, "canonical_id")) or None,
        "ligand_id": _clean_text(_mapping_or_attributes(value, "ligand_id")) or None,
        "ligand_canonical_id": _clean_text(_mapping_or_attributes(value, "canonical_id"))
        or None,
    }


@dataclass(frozen=True, slots=True)
class PairLigandContextResult:
    model_name: str
    context_dim: int
    modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    modality_token_ids: dict[str, tuple[str, ...]]
    modality_token_counts: dict[str, int]
    modality_embeddings: dict[str, tuple[float, ...]]
    modality_weights: dict[str, float]
    fused_embedding: tuple[float, ...]
    feature_names: tuple[str, ...]
    feature_vector: tuple[float, ...]
    metrics: dict[str, float]
    source_kind: str = "pair_ligand_context_baseline"
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
            "context_dim": self.context_dim,
            "modalities": list(self.modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "modality_token_ids": {
                key: list(value) for key, value in self.modality_token_ids.items()
            },
            "modality_token_counts": dict(self.modality_token_counts),
            "modality_embeddings": {
                key: list(value) for key, value in self.modality_embeddings.items()
            },
            "modality_weights": dict(self.modality_weights),
            "fused_embedding": list(self.fused_embedding),
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "metrics": dict(self.metrics),
            "source_kind": self.source_kind,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class PairLigandContext:
    model_name: str = DEFAULT_PAIR_LIGAND_CONTEXT_MODEL
    context_dim: int = DEFAULT_PAIR_LIGAND_CONTEXT_DIM
    source_kind: str = "pair_ligand_context_baseline"
    modalities: tuple[str, ...] = DEFAULT_MODALITY_ORDER

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
        if self.context_dim < 1:
            raise ValueError("context_dim must be >= 1")
        if not modalities:
            raise ValueError("modalities must contain at least one modality name")
        invalid_modalities = sorted(
            modality for modality in modalities if modality not in DEFAULT_MODALITY_ORDER
        )
        if invalid_modalities:
            raise ValueError("modalities must be drawn from: " + ", ".join(DEFAULT_MODALITY_ORDER))
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "source_kind", source_kind or "pair_ligand_context_baseline")
        object.__setattr__(self, "modalities", modalities)

    def fuse(
        self,
        feature_bundle: Any | None = None,
        *,
        pair_context: ProteinProteinSummaryRecord | Mapping[str, Any] | Any | None = None,
        ligand_embedding: LigandEmbeddingResult | Mapping[str, Any] | Any | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> PairLigandContextResult:
        bundle_provenance: dict[str, Any] = {}
        if feature_bundle is not None:
            if isinstance(feature_bundle, Mapping):
                bundle_provenance = _coerce_provenance(_payload_value(feature_bundle, "provenance"))
            else:
                bundle_provenance = _coerce_provenance(
                    _mapping_or_attributes(feature_bundle, "provenance")
                )
            if pair_context is None:
                pair_context = _mapping_or_attributes(
                    feature_bundle,
                    "pair_context",
                    "pair_summary",
                    "protein_pair",
                )
            if ligand_embedding is None:
                ligand_embedding = _mapping_or_attributes(
                    feature_bundle,
                    "ligand_embedding",
                    "ligand_context",
                )

        summaries = {
            "pair": _coerce_pair_context(pair_context),
            "ligand": _coerce_ligand_context(ligand_embedding),
        }
        available_modalities = tuple(
            modality for modality in self.modalities if summaries[modality]["present"]
        )
        if not available_modalities:
            raise ValueError("at least one modality context must be provided")
        missing_modalities = tuple(
            modality for modality in self.modalities if modality not in available_modalities
        )

        modality_embeddings: dict[str, tuple[float, ...]] = {}
        modality_token_ids: dict[str, tuple[str, ...]] = {}
        modality_token_counts: dict[str, int] = {}
        modality_weights: dict[str, float] = {modality: 0.0 for modality in self.modalities}

        for modality in self.modalities:
            summary = summaries[modality]
            modality_token_ids[modality] = tuple(summary["token_ids"])
            modality_token_counts[modality] = int(summary["token_count"])
            if summary["present"]:
                modality_embeddings[modality] = _project_vector(
                    summary["pooled_embedding"],
                    width=self.context_dim,
                )

        active_embeddings = [modality_embeddings[modality] for modality in available_modalities]
        active_weight = 1.0 / float(len(active_embeddings))
        for modality in available_modalities:
            modality_weights[modality] = active_weight

        fused_embedding = _project_vector(
            _mean_rows(active_embeddings),
            width=self.context_dim,
        )

        feature_names: list[str] = []
        feature_vector: list[float] = []
        for modality in self.modalities:
            summary = summaries[modality]
            feature_names.append(f"{modality}_present")
            feature_vector.append(1.0 if summary["present"] else 0.0)
            feature_names.append(f"{modality}_token_count")
            feature_vector.append(float(summary["token_count"]))
            default_embedding = (0.0,) * self.context_dim
            for index, value in enumerate(modality_embeddings.get(modality, default_embedding)):
                feature_names.append(f"{modality}_pooled_{index}")
                feature_vector.append(float(value))

        for index, value in enumerate(fused_embedding):
            feature_names.append(f"fused_{index}")
            feature_vector.append(float(value))

        metrics = {
            "available_count": float(len(available_modalities)),
            "missing_count": float(len(missing_modalities)),
            "coverage": float(len(available_modalities)) / float(len(self.modalities)),
            "feature_vector_length": float(len(feature_vector)),
            "fused_l2_norm": float(_vector_norm(fused_embedding)),
            "pair_token_count": float(modality_token_counts.get("pair", 0)),
            "ligand_token_count": float(modality_token_counts.get("ligand", 0)),
        }

        provenance_payload = dict(bundle_provenance)
        if provenance is not None:
            provenance_payload.update(_coerce_provenance(provenance))
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source_kind": self.source_kind,
                "modalities": list(self.modalities),
                "available_modalities": list(available_modalities),
                "missing_modalities": list(missing_modalities),
                "modality_provenance": {
                    modality: dict(summaries[modality]["provenance"])
                    for modality in self.modalities
                    if summaries[modality]["present"]
                },
                "modality_sources": {
                    modality: summaries[modality]["source"]
                    for modality in self.modalities
                    if summaries[modality]["present"]
                },
                "modality_models": {
                    modality: summaries[modality]["model_name"]
                    for modality in self.modalities
                    if summaries[modality]["present"]
                },
                "context_dim": self.context_dim,
            }
        )

        for key in (
            "pair_summary_id",
            "protein_a_ref",
            "protein_b_ref",
            "ligand_canonical_id",
            "ligand_id",
        ):
            for modality in self.modalities:
                value = summaries[modality].get(key)
                if value is not None:
                    provenance_payload.setdefault(key, value)
        if summaries["ligand"].get("ligand_id") is not None:
            provenance_payload.setdefault("ligand_id", summaries["ligand"]["ligand_id"])

        return PairLigandContextResult(
            model_name=self.model_name,
            context_dim=self.context_dim,
            modalities=self.modalities,
            available_modalities=available_modalities,
            missing_modalities=missing_modalities,
            modality_token_ids=modality_token_ids,
            modality_token_counts=modality_token_counts,
            modality_embeddings=modality_embeddings,
            modality_weights=modality_weights,
            fused_embedding=fused_embedding,
            feature_names=tuple(feature_names),
            feature_vector=tuple(feature_vector),
            metrics=metrics,
            source_kind=self.source_kind,
            frozen=True,
            provenance=provenance_payload,
        )


def build_pair_ligand_context(
    feature_bundle: Any | None = None,
    *,
    pair_context: ProteinProteinSummaryRecord | Mapping[str, Any] | Any | None = None,
    ligand_embedding: LigandEmbeddingResult | Mapping[str, Any] | Any | None = None,
    model_name: str = DEFAULT_PAIR_LIGAND_CONTEXT_MODEL,
    context_dim: int = DEFAULT_PAIR_LIGAND_CONTEXT_DIM,
    source_kind: str = "pair_ligand_context_baseline",
    modalities: Sequence[str] = DEFAULT_MODALITY_ORDER,
    provenance: Mapping[str, Any] | None = None,
) -> PairLigandContextResult:
    return PairLigandContext(
        model_name=model_name,
        context_dim=context_dim,
        source_kind=source_kind,
        modalities=tuple(modalities),
    ).fuse(
        feature_bundle,
        pair_context=pair_context,
        ligand_embedding=ligand_embedding,
        provenance=provenance,
    )


__all__ = [
    "DEFAULT_PAIR_LIGAND_CONTEXT_DIM",
    "DEFAULT_PAIR_LIGAND_CONTEXT_MODEL",
    "DEFAULT_MODALITY_ORDER",
    "PairLigandContext",
    "PairLigandContextResult",
    "build_pair_ligand_context",
]
