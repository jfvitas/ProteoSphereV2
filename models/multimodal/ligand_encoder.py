from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from core.canonical.ligand import CanonicalLigand, validate_ligand_payload

DEFAULT_LIGAND_ENCODER_MODEL = "ligand-baseline-v1"
DEFAULT_LIGAND_ENCODER_DIM = 8


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_smiles(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError("smiles must not be empty")
    return text


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _unique_text(values: Any) -> tuple[str, ...]:
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
    return value


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


def _text_features(value: str) -> tuple[float, ...]:
    text = value.strip()
    if not text:
        return (0.0,) * 8
    length = len(text)
    letters = sum(character.isalpha() for character in text)
    digits = sum(character.isdigit() for character in text)
    whitespace = sum(character.isspace() for character in text)
    punctuation = sum(not character.isalnum() and not character.isspace() for character in text)
    upper = sum(character.isupper() for character in text)
    unique = len(set(text))
    digest = int(sha256(text.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    return (
        min(length / 64.0, 1.0),
        letters / length,
        digits / length,
        whitespace / length,
        punctuation / length,
        unique / length,
        upper / length,
        digest,
    )


def _charge_features(charge: int | None) -> tuple[float, ...]:
    if charge is None:
        return (0.0,) * 8
    clipped = max(min(int(charge), 16), -16)
    return (
        1.0,
        clipped / 16.0,
        abs(clipped) / 16.0,
        1.0 if clipped == 0 else 0.0,
        1.0 if clipped > 0 else 0.0,
        1.0 if clipped < 0 else 0.0,
        (clipped + 16) / 32.0,
        float(clipped * clipped) / 256.0,
    )


def _vector_for_field(field_name: str, value: Any) -> tuple[float, ...]:
    if value is None:
        return (0.0,) * 8
    if field_name == "charge":
        return _charge_features(value if isinstance(value, int) else int(value))
    if isinstance(value, tuple):
        text = "|".join(str(item) for item in value)
    else:
        text = str(value)
    return _text_features(f"{field_name}:{text}")


def _token_embedding(field_name: str, value: Any, *, width: int) -> tuple[float, ...]:
    return _project_vector(_vector_for_field(field_name, value), width=width)


def _canonical_id_for_ligand(*, ligand_id: str | None, source: str, source_id: str) -> str:
    if ligand_id:
        return f"ligand:{ligand_id}"
    digest = sha256(f"{source}|{source_id}".encode()).hexdigest()[:16]
    return f"ligand:{source.casefold()}:{digest}"


def _coerce_ligand(value: CanonicalLigand | Mapping[str, Any]) -> CanonicalLigand:
    if isinstance(value, CanonicalLigand):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("value must be a CanonicalLigand or mapping")
    payload = dict(value)
    if "canonical_payload" in payload and isinstance(payload["canonical_payload"], Mapping):
        payload = dict(payload["canonical_payload"])
    return validate_ligand_payload(payload)


def _coerce_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping")
    return _json_ready(dict(value))


@dataclass(frozen=True, slots=True)
class LigandEmbeddingResult:
    canonical_id: str
    ligand_id: str | None
    name: str
    source: str
    source_id: str
    smiles: str | None
    inchi: str | None
    inchikey: str | None
    formula: str | None
    charge: int | None
    model_name: str
    embedding_dim: int
    token_ids: tuple[str, ...]
    token_embeddings: tuple[tuple[float, ...], ...]
    pooled_embedding: tuple[float, ...]
    source_kind: str = "ligand_baseline"
    frozen: bool = True
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def feature_count(self) -> int:
        return len(self.token_embeddings)

    @property
    def has_chemical_structure(self) -> bool:
        return any((self.smiles, self.inchi, self.inchikey))

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_id": self.canonical_id,
            "ligand_id": self.ligand_id,
            "name": self.name,
            "source": self.source,
            "source_id": self.source_id,
            "smiles": self.smiles,
            "inchi": self.inchi,
            "inchikey": self.inchikey,
            "formula": self.formula,
            "charge": self.charge,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "feature_count": self.feature_count,
            "token_ids": list(self.token_ids),
            "token_embeddings": [list(row) for row in self.token_embeddings],
            "pooled_embedding": list(self.pooled_embedding),
            "source_kind": self.source_kind,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class LigandEncoder:
    model_name: str = DEFAULT_LIGAND_ENCODER_MODEL
    embedding_dim: int = DEFAULT_LIGAND_ENCODER_DIM
    source_kind: str = "ligand_baseline"

    def __post_init__(self) -> None:
        model_name = _clean_text(self.model_name)
        source_kind = _clean_text(self.source_kind)
        if not model_name:
            raise ValueError("model_name must be a non-empty string")
        if self.embedding_dim < 1:
            raise ValueError("embedding_dim must be >= 1")
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "source_kind", source_kind or "ligand_baseline")

    def encode(
        self,
        value: CanonicalLigand | Mapping[str, Any] | str,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> LigandEmbeddingResult:
        if isinstance(value, str):
            return self.encode_smiles(value, provenance=provenance)
        return self.encode_ligand(value, provenance=provenance)

    def encode_ligand(
        self,
        value: CanonicalLigand | Mapping[str, Any],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> LigandEmbeddingResult:
        ligand = _coerce_ligand(value)
        source = ligand.source
        source_id = ligand.source_id
        canonical_id = _canonical_id_for_ligand(
            ligand_id=ligand.ligand_id,
            source=source,
            source_id=source_id,
        )
        return self._encode_normalized(
            canonical_id=canonical_id,
            ligand_id=ligand.ligand_id,
            name=ligand.name,
            source=source,
            source_id=source_id,
            smiles=ligand.smiles,
            inchi=ligand.inchi,
            inchikey=ligand.inchikey,
            formula=ligand.formula,
            charge=ligand.charge,
            provenance=provenance,
            input_kind="canonical_ligand" if isinstance(value, CanonicalLigand) else "mapping",
            synonym_count=len(ligand.synonyms),
        )

    def encode_smiles(
        self,
        smiles: str,
        *,
        provenance: Mapping[str, Any] | None = None,
        name: str = "",
        source: str = "smiles",
        source_id: str | None = None,
        ligand_id: str | None = None,
        inchi: str | None = None,
        inchikey: str | None = None,
        formula: str | None = None,
        charge: int | None = None,
    ) -> LigandEmbeddingResult:
        normalized_smiles = _normalize_smiles(smiles)
        normalized_source = _clean_text(source) or "smiles"
        normalized_source_id = _clean_text(source_id) or normalized_smiles
        canonical_id = _canonical_id_for_ligand(
            ligand_id=ligand_id,
            source=normalized_source,
            source_id=normalized_source_id,
        )
        return self._encode_normalized(
            canonical_id=canonical_id,
            ligand_id=ligand_id,
            name=_clean_text(name),
            source=normalized_source,
            source_id=normalized_source_id,
            smiles=normalized_smiles,
            inchi=_clean_text(inchi) or None,
            inchikey=_clean_text(inchikey) or None,
            formula=_clean_text(formula) or None,
            charge=charge,
            provenance=provenance,
            input_kind="smiles",
            synonym_count=0,
        )

    def encode_many(
        self,
        values: Iterable[CanonicalLigand | Mapping[str, Any] | str],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> tuple[LigandEmbeddingResult, ...]:
        return tuple(self.encode(value, provenance=provenance) for value in values)

    def _encode_normalized(
        self,
        *,
        canonical_id: str,
        ligand_id: str | None,
        name: str,
        source: str,
        source_id: str,
        smiles: str | None,
        inchi: str | None,
        inchikey: str | None,
        formula: str | None,
        charge: int | None,
        provenance: Mapping[str, Any] | None,
        input_kind: str,
        synonym_count: int,
    ) -> LigandEmbeddingResult:
        token_specs: list[tuple[str, Any]] = []
        if ligand_id:
            token_specs.append(("ligand_id", ligand_id))
        if name:
            token_specs.append(("name", name))
        if source:
            token_specs.append(("source", source))
        if source_id:
            token_specs.append(("source_id", source_id))
        if smiles:
            token_specs.append(("smiles", smiles))
        if inchi:
            token_specs.append(("inchi", inchi))
        if inchikey:
            token_specs.append(("inchikey", inchikey))
        if formula:
            token_specs.append(("formula", formula))
        if charge is not None:
            token_specs.append(("charge", charge))
        if synonym_count:
            token_specs.append(("synonyms", f"{synonym_count} synonyms"))

        token_ids: list[str] = []
        token_embeddings: list[tuple[float, ...]] = []
        for field_name, value in token_specs:
            token_ids.append(field_name)
            token_embeddings.append(
                _token_embedding(field_name, value, width=self.embedding_dim)
            )

        provenance_payload = _coerce_provenance(provenance)
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source_kind": self.source_kind,
                "input_kind": input_kind,
                "canonical_id": canonical_id,
                "ligand_id": ligand_id,
                "source": source,
                "source_id": source_id,
                "smiles": smiles,
                "inchi": inchi,
                "inchikey": inchikey,
                "formula": formula,
                "charge": charge,
                "synonym_count": synonym_count,
                "has_chemical_structure": any((smiles, inchi, inchikey)),
                "token_ids": list(token_ids),
            }
        )

        return LigandEmbeddingResult(
            canonical_id=canonical_id,
            ligand_id=ligand_id,
            name=name,
            source=source,
            source_id=source_id,
            smiles=smiles,
            inchi=inchi,
            inchikey=inchikey,
            formula=formula,
            charge=charge,
            model_name=self.model_name,
            embedding_dim=self.embedding_dim,
            token_ids=tuple(token_ids),
            token_embeddings=tuple(token_embeddings),
            pooled_embedding=_project_vector(
                _mean_rows(token_embeddings),
                width=self.embedding_dim,
            ),
            source_kind=self.source_kind,
            frozen=True,
            provenance=provenance_payload,
        )


def encode_ligand(
    value: CanonicalLigand | Mapping[str, Any] | str,
    *,
    model_name: str = DEFAULT_LIGAND_ENCODER_MODEL,
    embedding_dim: int = DEFAULT_LIGAND_ENCODER_DIM,
    source_kind: str = "ligand_baseline",
    provenance: Mapping[str, Any] | None = None,
) -> LigandEmbeddingResult:
    return LigandEncoder(
        model_name=model_name,
        embedding_dim=embedding_dim,
        source_kind=source_kind,
    ).encode(value, provenance=provenance)


def encode_smiles(
    smiles: str,
    *,
    model_name: str = DEFAULT_LIGAND_ENCODER_MODEL,
    embedding_dim: int = DEFAULT_LIGAND_ENCODER_DIM,
    source_kind: str = "ligand_baseline",
    provenance: Mapping[str, Any] | None = None,
    name: str = "",
    source: str = "smiles",
    source_id: str | None = None,
    ligand_id: str | None = None,
    inchi: str | None = None,
    inchikey: str | None = None,
    formula: str | None = None,
    charge: int | None = None,
) -> LigandEmbeddingResult:
    return LigandEncoder(
        model_name=model_name,
        embedding_dim=embedding_dim,
        source_kind=source_kind,
    ).encode_smiles(
        smiles,
        provenance=provenance,
        name=name,
        source=source,
        source_id=source_id,
        ligand_id=ligand_id,
        inchi=inchi,
        inchikey=inchikey,
        formula=formula,
        charge=charge,
    )


__all__ = [
    "DEFAULT_LIGAND_ENCODER_DIM",
    "DEFAULT_LIGAND_ENCODER_MODEL",
    "LigandEmbeddingResult",
    "LigandEncoder",
    "encode_ligand",
    "encode_smiles",
]
