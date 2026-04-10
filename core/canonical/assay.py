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


def _clean_float(value: float | int | None, *, field_name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number or None")
    return float(value)


@dataclass(frozen=True, slots=True)
class CanonicalAssay:
    assay_id: str
    target_id: str
    ligand_id: str
    source: str
    source_id: str
    measurement_type: str
    measurement_value: float | None = None
    measurement_unit: str | None = None
    relation: str | None = None
    assay_conditions: str | None = None
    ph: float | None = None
    temperature_celsius: float | None = None
    references: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        assay_id = _clean_text(self.assay_id)
        target_id = _clean_text(self.target_id)
        ligand_id = _clean_text(self.ligand_id)
        source = _clean_text(self.source)
        source_id = _clean_text(self.source_id)
        measurement_type = _clean_text(self.measurement_type)
        if not assay_id:
            raise ValueError("assay_id is required")
        if not target_id:
            raise ValueError("target_id is required")
        if not ligand_id:
            raise ValueError("ligand_id is required")
        if not source:
            raise ValueError("source is required")
        if not source_id:
            raise ValueError("source_id is required")
        if not measurement_type:
            raise ValueError("measurement_type is required")

        measurement_value = _clean_float(self.measurement_value, field_name="measurement_value")
        ph = _clean_float(self.ph, field_name="ph")
        temperature_celsius = _clean_float(
            self.temperature_celsius,
            field_name="temperature_celsius",
        )
        if ph is not None and not (0.0 <= ph <= 14.0):
            raise ValueError("ph must be between 0 and 14")
        if temperature_celsius is not None and temperature_celsius < -273.15:
            raise ValueError("temperature_celsius is implausibly low")
        if temperature_celsius is not None and temperature_celsius > 300.0:
            raise ValueError("temperature_celsius is implausibly high")

        object.__setattr__(self, "assay_id", assay_id)
        object.__setattr__(self, "target_id", target_id)
        object.__setattr__(self, "ligand_id", ligand_id)
        object.__setattr__(self, "source", source.upper())
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "measurement_type", measurement_type)
        object.__setattr__(self, "measurement_value", measurement_value)
        object.__setattr__(self, "measurement_unit", _clean_text(self.measurement_unit))
        object.__setattr__(self, "relation", _clean_text(self.relation))
        object.__setattr__(self, "assay_conditions", _clean_text(self.assay_conditions))
        object.__setattr__(self, "ph", ph)
        object.__setattr__(self, "temperature_celsius", temperature_celsius)
        object.__setattr__(self, "references", tuple(_clean_list(self.references)))
        object.__setattr__(self, "provenance", tuple(_clean_list(self.provenance)))

    @property
    def canonical_id(self) -> str:
        return f"assay:{self.source}:{self.source_id}"

    @property
    def canonical_assay_id(self) -> str:
        return self.canonical_id

    @property
    def has_quantitative_measurement(self) -> bool:
        return self.measurement_value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "canonical_assay_id": self.canonical_assay_id,
            "assay_id": self.assay_id,
            "target_id": self.target_id,
            "ligand_id": self.ligand_id,
            "source": self.source,
            "source_id": self.source_id,
            "measurement_type": self.measurement_type,
            "measurement_value": self.measurement_value,
            "measurement_unit": self.measurement_unit,
            "relation": self.relation,
            "assay_conditions": self.assay_conditions,
            "ph": self.ph,
            "temperature_celsius": self.temperature_celsius,
            "references": list(self.references),
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CanonicalAssay:
        return cls(
            assay_id=str(payload.get("assay_id") or payload.get("id") or ""),
            target_id=str(
                payload.get("target_id")
                or payload.get("protein_id")
                or payload.get("uniprot_id")
                or ""
            ),
            ligand_id=str(
                payload.get("ligand_id")
                or payload.get("compound_id")
                or payload.get("molecule_id")
                or ""
            ),
            source=str(payload.get("source") or ""),
            source_id=str(
                payload.get("source_id")
                or payload.get("bindingdb_assay_id")
                or payload.get("reactant_set_id")
                or ""
            ),
            measurement_type=str(
                payload.get("measurement_type")
                or payload.get("assay_type")
                or payload.get("endpoint")
                or ""
            ),
            measurement_value=payload.get("measurement_value", payload.get("value")),
            measurement_unit=payload.get("measurement_unit") or payload.get("unit"),
            relation=payload.get("relation") or payload.get("inequality"),
            assay_conditions=payload.get("assay_conditions") or payload.get("conditions"),
            ph=payload.get("ph") or payload.get("pH"),
            temperature_celsius=payload.get("temperature_celsius")
            or payload.get("temperature"),
            references=tuple(payload.get("references") or payload.get("citations") or ()),
            provenance=tuple(payload.get("provenance") or payload.get("evidence") or ()),
        )


def validate_assay_payload(payload: dict[str, Any]) -> CanonicalAssay:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")
    return CanonicalAssay.from_dict(payload)


__all__ = ["CanonicalAssay", "validate_assay_payload"]
