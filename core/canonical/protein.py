from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")


def _clean_text(value: str) -> str:
    return value.strip()


def _normalize_accession(value: str) -> str:
    accession = _clean_text(value).upper()
    if not accession:
        raise ValueError("accession must not be empty")
    return accession


def _normalize_sequence(value: str) -> str:
    sequence = "".join(str(value).split()).upper()
    if not sequence:
        raise ValueError("sequence must not be empty")
    invalid = sorted(set(sequence) - _AMINO_ACIDS)
    if invalid:
        raise ValueError(
            "sequence contains invalid residue codes: " + ", ".join(invalid)
        )
    return sequence


def _normalize_strings(values: Iterable[str] | None) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        item = _clean_text(str(value))
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return tuple(cleaned)


@dataclass(frozen=True, slots=True)
class CanonicalProtein:
    """Immutable canonical protein record."""

    accession: str
    sequence: str
    name: str = ""
    gene_names: tuple[str, ...] = field(default_factory=tuple)
    organism: str = ""
    description: str = ""
    source: str = "UniProt"
    aliases: tuple[str, ...] = field(default_factory=tuple)
    annotations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _normalize_accession(self.accession))
        object.__setattr__(self, "sequence", _normalize_sequence(self.sequence))
        object.__setattr__(self, "name", _clean_text(self.name))
        object.__setattr__(self, "organism", _clean_text(self.organism))
        object.__setattr__(self, "description", _clean_text(self.description))
        object.__setattr__(self, "source", _clean_text(self.source) or "UniProt")
        object.__setattr__(self, "gene_names", _normalize_strings(self.gene_names))
        object.__setattr__(self, "aliases", _normalize_strings(self.aliases))
        object.__setattr__(self, "annotations", _normalize_strings(self.annotations))

    @property
    def canonical_id(self) -> str:
        return f"protein:{self.accession}"

    @property
    def canonical_protein_id(self) -> str:
        return self.canonical_id

    @property
    def sequence_length(self) -> int:
        return len(self.sequence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "canonical_protein_id": self.canonical_protein_id,
            "accession": self.accession,
            "sequence": self.sequence,
            "sequence_length": self.sequence_length,
            "name": self.name,
            "gene_names": list(self.gene_names),
            "organism": self.organism,
            "description": self.description,
            "source": self.source,
            "aliases": list(self.aliases),
            "annotations": list(self.annotations),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CanonicalProtein:
        return cls(
            accession=str(payload.get("accession") or payload.get("uniprot_id") or ""),
            sequence=str(payload.get("sequence") or ""),
            name=str(payload.get("name") or payload.get("protein_name") or ""),
            gene_names=tuple(
                str(value)
                for value in payload.get("gene_names")
                or payload.get("genes")
                or ()
            ),
            organism=str(payload.get("organism") or payload.get("species") or ""),
            description=str(payload.get("description") or ""),
            source=str(payload.get("source") or "UniProt"),
            aliases=tuple(str(value) for value in payload.get("aliases") or ()),
            annotations=tuple(str(value) for value in payload.get("annotations") or ()),
        )


__all__ = ["CanonicalProtein"]
