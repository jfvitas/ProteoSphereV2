from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _clean_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        text = value.strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


@dataclass(frozen=True, slots=True)
class CanonicalLigand:
    ligand_id: str
    name: str
    source: str
    source_id: str
    smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    formula: str | None = None
    charge: int | None = None
    synonyms: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ligand_id = _clean_text(self.ligand_id)
        name = _clean_text(self.name)
        source = _clean_text(self.source)
        source_id = _clean_text(self.source_id)
        if not ligand_id:
            raise ValueError("ligand_id is required")
        if not name:
            raise ValueError("name is required")
        if not source:
            raise ValueError("source is required")
        if not source_id:
            raise ValueError("source_id is required")
        if self.charge is not None and not isinstance(self.charge, int):
            raise TypeError("charge must be an integer or None")
        if self.charge is not None and self.charge < -16:
            raise ValueError("charge is implausibly low")
        if self.charge is not None and self.charge > 16:
            raise ValueError("charge is implausibly high")

        object.__setattr__(self, "ligand_id", ligand_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "source", source.upper())
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "smiles", _clean_text(self.smiles))
        object.__setattr__(self, "inchi", _clean_text(self.inchi))
        object.__setattr__(self, "inchikey", _clean_text(self.inchikey))
        object.__setattr__(self, "formula", _clean_text(self.formula))
        object.__setattr__(self, "synonyms", tuple(_clean_list(self.synonyms)))
        object.__setattr__(self, "provenance", tuple(_clean_list(self.provenance)))

    @property
    def has_chemical_structure(self) -> bool:
        return any((self.smiles, self.inchi, self.inchikey))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ligand_id": self.ligand_id,
            "name": self.name,
            "source": self.source,
            "source_id": self.source_id,
            "smiles": self.smiles,
            "inchi": self.inchi,
            "inchikey": self.inchikey,
            "formula": self.formula,
            "charge": self.charge,
            "synonyms": list(self.synonyms),
            "provenance": list(self.provenance),
        }


def validate_ligand_payload(payload: dict[str, Any]) -> CanonicalLigand:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")
    return CanonicalLigand(
        ligand_id=str(payload.get("ligand_id", "")),
        name=str(payload.get("name", "")),
        source=str(payload.get("source", "")),
        source_id=str(payload.get("source_id", "")),
        smiles=payload.get("smiles"),
        inchi=payload.get("inchi"),
        inchikey=payload.get("inchikey"),
        formula=payload.get("formula"),
        charge=payload.get("charge"),
        synonyms=tuple(payload.get("synonyms", ())),
        provenance=tuple(payload.get("provenance", ())),
    )

