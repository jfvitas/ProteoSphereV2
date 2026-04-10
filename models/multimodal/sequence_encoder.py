from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core.canonical.protein import CanonicalProtein
from features.esm2_embeddings import ProteinEmbeddingResult

DEFAULT_SEQUENCE_ENCODER_MODEL = "sequence-baseline-v1"
DEFAULT_SEQUENCE_ENCODER_DIM = 8

_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")
_HYDROPHOBIC = frozenset("AILMFWV")
_POLAR = frozenset("STNQCY")
_CHARGED = frozenset("DEKRH")
_AROMATIC = frozenset("FWYH")
_SMALL = frozenset("AGSC")
_SPECIAL = frozenset("PG")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_sequence(value: Any) -> str:
    sequence = "".join(str(value or "").split()).upper()
    if not sequence:
        raise ValueError("sequence must not be empty")
    invalid = sorted(set(sequence) - _AMINO_ACIDS)
    if invalid:
        raise ValueError(
            "sequence contains invalid residue codes: " + ", ".join(invalid)
        )
    return sequence


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _payload_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        text = _clean_text(values)
        return (text,) if text else ()
    if not isinstance(values, Iterable):
        values = (values,)
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _coerce_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping")
    return _json_ready(dict(value))


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


def _project_vector(values: Sequence[float], *, width: int) -> tuple[float, ...]:
    numbers = [float(value) for value in values]
    if width < 1:
        raise ValueError("embedding_dim must be >= 1")
    if not numbers:
        return tuple(0.0 for _ in range(width))
    if len(numbers) == width:
        return tuple(numbers)

    mean_value = sum(numbers) / len(numbers)
    min_value = min(numbers)
    max_value = max(numbers)
    l2_value = sum(value * value for value in numbers) ** 0.5
    summary = [mean_value, min_value, max_value, l2_value, numbers[0], numbers[-1]]
    while len(summary) < width:
        summary.append(mean_value)
    return tuple(summary[:width])


def _residue_features(residue: str, position: int, total: int) -> tuple[float, ...]:
    normalized_position = 0.0 if total <= 1 else position / float(total - 1)
    ordinal = (ord(residue) - 64) / 26.0
    return (
        ordinal,
        normalized_position,
        1.0 if residue in _HYDROPHOBIC else 0.0,
        1.0 if residue in _POLAR else 0.0,
        1.0 if residue in _CHARGED else 0.0,
        1.0 if residue in _AROMATIC else 0.0,
        1.0 if residue in _SMALL else 0.0,
        1.0 if residue in _SPECIAL else 0.0,
    )


def _coerce_input(value: str | CanonicalProtein | Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(value, CanonicalProtein):
        return value.sequence, {
            "input_kind": "canonical_protein",
            "canonical_id": value.canonical_id,
            "accession": value.accession,
            "source": value.source,
            "source_id": value.accession,
            "name": value.name,
            "gene_names": list(value.gene_names),
            "organism": value.organism,
            "provenance": {},
        }
    if isinstance(value, str):
        return value, {"input_kind": "sequence_string", "provenance": {}}
    if not isinstance(value, Mapping):
        raise TypeError("value must be a sequence string, CanonicalProtein, or mapping")

    outer = value
    payload = outer
    if "canonical_payload" in outer and isinstance(outer["canonical_payload"], Mapping):
        payload = outer["canonical_payload"]

    sequence = _payload_value(payload, "sequence", "amino_acid_sequence", "value")
    if sequence is None:
        sequence = _payload_value(outer, "sequence", "amino_acid_sequence", "value")

    provenance = _coerce_provenance(_payload_value(outer, "provenance", "provenance_record"))
    if not provenance:
        provenance = _coerce_provenance(_payload_value(payload, "provenance", "provenance_record"))
    if not provenance and "provenance" in outer and isinstance(outer["provenance"], Mapping):
        provenance = _coerce_provenance(outer["provenance"])

    metadata = {
        "input_kind": "mapping",
        "canonical_id": _clean_text(
            _payload_value(outer, "canonical_id", "canonical_protein_id", "id")
            or _payload_value(payload, "canonical_id", "canonical_protein_id", "id")
        )
        or None,
        "accession": _clean_text(
            _payload_value(outer, "accession", "primaryAccession", "uniprot_id", "record_id")
            or _payload_value(payload, "accession", "primaryAccession", "uniprot_id", "record_id")
        )
        or None,
        "source": _clean_text(_payload_value(outer, "source") or _payload_value(payload, "source"))
        or "sequence",
        "source_id": _clean_text(
            _payload_value(outer, "source_id", "entry_name")
            or _payload_value(payload, "source_id", "entry_name")
        )
        or None,
        "name": _clean_text(_payload_value(outer, "name") or _payload_value(payload, "name"))
        or None,
        "organism": _clean_text(
            _payload_value(outer, "organism", "organism_name")
            or _payload_value(payload, "organism", "organism_name")
        )
        or None,
        "gene_names": _normalize_text_tuple(
            _payload_value(outer, "gene_names") or _payload_value(payload, "gene_names")
        ),
        "provenance": provenance,
    }
    return sequence, metadata


@dataclass(frozen=True, slots=True)
class SequenceEncoder:
    model_name: str = DEFAULT_SEQUENCE_ENCODER_MODEL
    embedding_dim: int = DEFAULT_SEQUENCE_ENCODER_DIM
    source: str = "sequence_baseline"

    def __post_init__(self) -> None:
        model_name = _clean_text(self.model_name)
        if not model_name:
            raise ValueError("model_name must be a non-empty string")
        if self.embedding_dim < 1:
            raise ValueError("embedding_dim must be >= 1")
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "source", _clean_text(self.source) or "sequence_baseline")

    def encode(
        self,
        value: str | CanonicalProtein | Mapping[str, Any],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> ProteinEmbeddingResult:
        sequence, metadata = _coerce_input(value)
        normalized_sequence = _normalize_sequence(sequence)
        residue_embeddings = tuple(
            _project_vector(
                _residue_features(residue, index, len(normalized_sequence)),
                width=self.embedding_dim,
            )
            for index, residue in enumerate(normalized_sequence)
        )
        pooled_embedding = _project_vector(
            _mean_rows(residue_embeddings),
            width=self.embedding_dim,
        )
        provenance_payload = dict(metadata.get("provenance", {}))
        if provenance is not None:
            provenance_payload.update(_coerce_provenance(provenance))
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source": self.source,
                "embedding_dim": self.embedding_dim,
                "sequence_length": len(normalized_sequence),
            }
        )
        for key in ("canonical_id", "accession", "source_id", "name", "organism"):
            if metadata.get(key) is not None:
                provenance_payload.setdefault(key, metadata[key])
        if metadata.get("gene_names"):
            provenance_payload.setdefault("gene_names", list(metadata["gene_names"]))

        return ProteinEmbeddingResult(
            sequence=normalized_sequence,
            model_name=self.model_name,
            embedding_dim=self.embedding_dim,
            residue_embeddings=residue_embeddings,
            pooled_embedding=pooled_embedding,
            cls_embedding=pooled_embedding,
            source=self.source,
            frozen=True,
            provenance=provenance_payload,
        )

    def encode_sequence(
        self,
        sequence: str,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> ProteinEmbeddingResult:
        return self.encode(sequence, provenance=provenance)

    def encode_protein(
        self,
        protein: CanonicalProtein,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> ProteinEmbeddingResult:
        return self.encode(protein, provenance=provenance)

    def encode_many(
        self,
        values: Iterable[str | CanonicalProtein | Mapping[str, Any]],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> tuple[ProteinEmbeddingResult, ...]:
        return tuple(self.encode(value, provenance=provenance) for value in values)


def encode_sequence(
    value: str | CanonicalProtein | Mapping[str, Any],
    *,
    model_name: str = DEFAULT_SEQUENCE_ENCODER_MODEL,
    embedding_dim: int = DEFAULT_SEQUENCE_ENCODER_DIM,
    source: str = "sequence_baseline",
    provenance: Mapping[str, Any] | None = None,
) -> ProteinEmbeddingResult:
    return SequenceEncoder(
        model_name=model_name,
        embedding_dim=embedding_dim,
        source=source,
    ).encode(value, provenance=provenance)


__all__ = [
    "DEFAULT_SEQUENCE_ENCODER_DIM",
    "DEFAULT_SEQUENCE_ENCODER_MODEL",
    "SequenceEncoder",
    "encode_sequence",
]
