from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from connectors.uniprot.parsers import UniProtSequenceRecord

STANDARD_AMINO_ACIDS: tuple[str, ...] = tuple("ACDEFGHIKLMNPQRSTVWY")
AMBIGUOUS_AMINO_ACIDS: tuple[str, ...] = tuple("BJOUXZ")
ALLOWED_AMINO_ACIDS = frozenset((*STANDARD_AMINO_ACIDS, *AMBIGUOUS_AMINO_ACIDS))

RESIDUE_CLASS_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "hydrophobic": ("A", "C", "F", "I", "L", "M", "V", "W", "Y"),
    "polar": ("N", "Q", "S", "T"),
    "positive": ("H", "K", "R"),
    "negative": ("D", "E"),
    "special": ("G", "P"),
}

DEFAULT_SEQUENCE_FEATURE_NAMES: tuple[str, ...] = (
    "sequence_length",
    "canonical_residue_count",
    "ambiguous_residue_count",
    "ambiguous_residue_fraction",
    *(f"fraction_{residue}" for residue in STANDARD_AMINO_ACIDS),
    *(f"fraction_{label}" for label in RESIDUE_CLASS_DEFINITIONS),
)


def normalize_protein_sequence(sequence: str, *, allow_ambiguous: bool = True) -> str:
    normalized = "".join(str(sequence or "").split()).upper()
    if not normalized:
        raise ValueError("sequence must not be empty")
    invalid = sorted(
        residue
        for residue in set(normalized)
        if residue not in ALLOWED_AMINO_ACIDS
        or (not allow_ambiguous and residue in AMBIGUOUS_AMINO_ACIDS)
    )
    if invalid:
        raise ValueError(
            "sequence contains invalid residue codes: " + ", ".join(invalid)
        )
    return normalized


def residue_counts(sequence: str, *, include_ambiguous: bool = False) -> dict[str, int]:
    normalized = normalize_protein_sequence(sequence)
    alphabet = STANDARD_AMINO_ACIDS
    if include_ambiguous:
        alphabet = (*STANDARD_AMINO_ACIDS, *AMBIGUOUS_AMINO_ACIDS)
    counts = {residue: 0 for residue in alphabet}
    for residue in normalized:
        if residue in counts:
            counts[residue] += 1
    return counts


def residue_fractions(sequence: str) -> dict[str, float]:
    normalized = normalize_protein_sequence(sequence)
    length = len(normalized)
    counts = residue_counts(normalized)
    return {
        residue: counts[residue] / length
        for residue in STANDARD_AMINO_ACIDS
    }


def residue_class_counts(sequence: str) -> dict[str, int]:
    normalized = normalize_protein_sequence(sequence)
    counts = {label: 0 for label in RESIDUE_CLASS_DEFINITIONS}
    for residue in normalized:
        for label, members in RESIDUE_CLASS_DEFINITIONS.items():
            if residue in members:
                counts[label] += 1
                break
    return counts


@dataclass(frozen=True, slots=True)
class SequenceFeatureResult:
    sequence: str
    sequence_length: int
    residue_counts: dict[str, int]
    residue_fractions: dict[str, float]
    residue_class_counts: dict[str, int]
    residue_class_fractions: dict[str, float]
    ambiguous_residue_counts: dict[str, int]
    canonical_residue_count: int
    ambiguous_residue_count: int
    accession: str | None = None
    source: str = "sequence_primitives"
    source_format: str | None = None
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def feature_names(self) -> tuple[str, ...]:
        return DEFAULT_SEQUENCE_FEATURE_NAMES

    @property
    def feature_values(self) -> dict[str, float | int]:
        values: dict[str, float | int] = {
            "sequence_length": self.sequence_length,
            "canonical_residue_count": self.canonical_residue_count,
            "ambiguous_residue_count": self.ambiguous_residue_count,
            "ambiguous_residue_fraction": self.ambiguous_residue_count / self.sequence_length,
        }
        values.update(
            {
                f"fraction_{residue}": self.residue_fractions[residue]
                for residue in STANDARD_AMINO_ACIDS
            }
        )
        values.update(
            {
                f"fraction_{label}": self.residue_class_fractions[label]
                for label in RESIDUE_CLASS_DEFINITIONS
            }
        )
        return values

    @property
    def feature_vector(self) -> tuple[float | int, ...]:
        values = self.feature_values
        return tuple(values[name] for name in self.feature_names)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "sequence": self.sequence,
            "sequence_length": self.sequence_length,
            "canonical_residue_count": self.canonical_residue_count,
            "ambiguous_residue_count": self.ambiguous_residue_count,
            "residue_counts": dict(self.residue_counts),
            "residue_fractions": dict(self.residue_fractions),
            "residue_class_counts": dict(self.residue_class_counts),
            "residue_class_fractions": dict(self.residue_class_fractions),
            "ambiguous_residue_counts": dict(self.ambiguous_residue_counts),
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "feature_values": dict(self.feature_values),
            "source": self.source,
            "source_format": self.source_format,
            "provenance": dict(self.provenance),
        }


def extract_sequence_features(
    sequence: str,
    *,
    accession: str | None = None,
    source: str = "sequence_primitives",
    source_format: str | None = None,
    provenance: Mapping[str, object] | None = None,
) -> SequenceFeatureResult:
    normalized = normalize_protein_sequence(sequence)
    total_length = len(normalized)
    canonical_counts = residue_counts(normalized)
    ambiguous_counts = {
        residue: count
        for residue, count in residue_counts(normalized, include_ambiguous=True).items()
        if residue in AMBIGUOUS_AMINO_ACIDS and count > 0
    }
    class_counts = residue_class_counts(normalized)
    canonical_count = sum(canonical_counts.values())
    ambiguous_count = sum(ambiguous_counts.values())
    return SequenceFeatureResult(
        accession=str(accession).strip().upper() if accession else None,
        sequence=normalized,
        sequence_length=total_length,
        residue_counts=canonical_counts,
        residue_fractions={
            residue: canonical_counts[residue] / total_length
            for residue in STANDARD_AMINO_ACIDS
        },
        residue_class_counts=class_counts,
        residue_class_fractions={
            label: class_counts[label] / total_length
            for label in RESIDUE_CLASS_DEFINITIONS
        },
        ambiguous_residue_counts=ambiguous_counts,
        canonical_residue_count=canonical_count,
        ambiguous_residue_count=ambiguous_count,
        source=source,
        source_format=source_format,
        provenance=dict(provenance or {}),
    )


def extract_uniprot_sequence_features(record: UniProtSequenceRecord) -> SequenceFeatureResult:
    if not isinstance(record, UniProtSequenceRecord):
        raise TypeError("record must be a UniProtSequenceRecord")
    return extract_sequence_features(
        record.sequence,
        accession=record.accession,
        source="uniprot_sequence_record",
        source_format=record.source_format,
        provenance={
            "entry_name": record.entry_name,
            "protein_name": record.protein_name,
            "organism_name": record.organism_name,
            "gene_names": list(record.gene_names),
            "reviewed": record.reviewed,
        },
    )


__all__ = [
    "ALLOWED_AMINO_ACIDS",
    "AMBIGUOUS_AMINO_ACIDS",
    "DEFAULT_SEQUENCE_FEATURE_NAMES",
    "RESIDUE_CLASS_DEFINITIONS",
    "STANDARD_AMINO_ACIDS",
    "SequenceFeatureResult",
    "extract_sequence_features",
    "extract_uniprot_sequence_features",
    "normalize_protein_sequence",
    "residue_class_counts",
    "residue_counts",
    "residue_fractions",
]
