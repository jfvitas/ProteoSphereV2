from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from core.canonical.assay import CanonicalAssay

AssayMergeStatus = Literal["resolved", "ambiguous", "conflict", "unresolved"]
AssayConflictKind = Literal[
    "no_records",
    "missing_required_identifier",
    "measurement_type_mismatch",
    "unit_incompatible",
    "measurement_value_disagreement",
    "missing_measurement_value",
]

_VALUE_RE = re.compile(
    r"^\s*(?P<relation><=|>=|<|>|=)?\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[eE][+-]?\d+)?)\s*$"
)
_UNIT_FACTORS_TO_NM = {
    "am": ("aM", 1e-9),
    "fm": ("fM", 1e-6),
    "pm": ("pM", 1e-3),
    "nm": ("nM", 1.0),
    "um": ("uM", 1e3),
    "mm": ("mM", 1e6),
    "m": ("M", 1e9),
    "attomolar": ("aM", 1e-9),
    "femtomolar": ("fM", 1e-6),
    "picomolar": ("pM", 1e-3),
    "nanomolar": ("nM", 1.0),
    "micromolar": ("uM", 1e3),
    "millimolar": ("mM", 1e6),
    "molar": ("M", 1e9),
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _first_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            if value.strip():
                return value
        elif value is not None:
            return value
    return None


def _coerce_iterable(payload: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Iterable):
            return tuple(str(item) for item in value)
    return ()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean_text(value)
    return float(text) if text else None


def _parse_value(value: Any) -> tuple[float | None, str | None, str | None]:
    if value is None:
        return None, None, None
    if isinstance(value, (int, float)):
        return float(value), None, None
    text = _clean_text(value)
    if not text:
        return None, None, None
    match = _VALUE_RE.match(text)
    if not match:
        return None, None, text
    return float(match.group("value")), match.group("relation") or None, text


def _normalize_unit(value: Any) -> tuple[str | None, float | None, bool]:
    text = _clean_text(value)
    if not text:
        return None, None, True
    key = text.casefold().replace("μ", "u").replace("µ", "u")
    normalized = _UNIT_FACTORS_TO_NM.get(key)
    if normalized is None:
        return text, None, False
    return normalized[0], normalized[1], True


def _same_float(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _fmt_num(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.12g}"


@dataclass(frozen=True, slots=True)
class AssayObservation:
    target_id: str | None
    ligand_id: str | None
    measurement_type: str | None
    measurement_value: float | None
    measurement_unit: str | None
    relation: str | None
    confidence: float | None
    source: str
    source_id: str
    assay_conditions: str | None
    ph: float | None
    temperature_celsius: float | None
    references: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    raw_value: str | None
    raw_unit: str | None
    input_index: int

    def to_canonical_assay(self, *, assay_id: str | None = None) -> CanonicalAssay:
        if self.target_id is None or self.ligand_id is None or self.measurement_type is None:
            raise ValueError("target_id, ligand_id, and measurement_type are required")
        source = _clean_text(self.source) or "UNKNOWN"
        source_id = _clean_text(self.source_id) or f"input-{self.input_index + 1}"
        provenance = self.provenance_refs or (f"{source}:{source_id}",)
        return CanonicalAssay(
            assay_id=assay_id or f"assay:{source}:{source_id}",
            target_id=self.target_id,
            ligand_id=self.ligand_id,
            source=source,
            source_id=source_id,
            measurement_type=self.measurement_type,
            measurement_value=self.measurement_value,
            measurement_unit=self.measurement_unit,
            relation=self.relation,
            assay_conditions=self.assay_conditions,
            ph=self.ph,
            temperature_celsius=self.temperature_celsius,
            references=self.references,
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "ligand_id": self.ligand_id,
            "measurement_type": self.measurement_type,
            "measurement_value": self.measurement_value,
            "measurement_unit": self.measurement_unit,
            "relation": self.relation,
            "confidence": self.confidence,
            "source": self.source,
            "source_id": self.source_id,
            "assay_conditions": self.assay_conditions,
            "ph": self.ph,
            "temperature_celsius": self.temperature_celsius,
            "references": list(self.references),
            "provenance_refs": list(self.provenance_refs),
            "raw_value": self.raw_value,
            "raw_unit": self.raw_unit,
            "input_index": self.input_index,
        }


@dataclass(frozen=True, slots=True)
class AssayConflict:
    field_name: str
    kind: AssayConflictKind
    observed_values: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "kind": self.kind,
            "observed_values": list(self.observed_values),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class AssayMergeResult:
    status: AssayMergeStatus
    reason: str
    resolved_assay: CanonicalAssay | None
    evidence_assays: tuple[CanonicalAssay, ...]
    observations: tuple[AssayObservation, ...]
    target_id: str | None
    ligand_id: str | None
    measurement_type: str | None
    normalized_unit: str | None
    normalized_value: float | None
    references: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    conflicts: tuple[AssayConflict, ...] = field(default_factory=tuple)
    alternative_values: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.resolved_assay is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "resolved_assay": (
                self.resolved_assay.to_dict() if self.resolved_assay is not None else None
            ),
            "evidence_assays": [assay.to_dict() for assay in self.evidence_assays],
            "observations": [observation.to_dict() for observation in self.observations],
            "target_id": self.target_id,
            "ligand_id": self.ligand_id,
            "measurement_type": self.measurement_type,
            "normalized_unit": self.normalized_unit,
            "normalized_value": self.normalized_value,
            "references": list(self.references),
            "provenance_refs": list(self.provenance_refs),
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "alternative_values": {
                field_name: list(values)
                for field_name, values in sorted(self.alternative_values.items())
            },
        }


def merge_assay_records(records: Iterable[object]) -> AssayMergeResult:
    observations = tuple(
        _normalize_observation(record, input_index=index)
        for index, record in enumerate(records)
    )
    evidence_assays = tuple(
        observation.to_canonical_assay(
            assay_id=f"assay:{_source_key(observation)}:{index + 1}"
        )
        for index, observation in enumerate(observations)
        if observation.target_id and observation.ligand_id and observation.measurement_type
    )
    references = _dedupe(
        ref for observation in observations for ref in observation.references
    )
    provenance_refs = _dedupe(
        ref for observation in observations for ref in observation.provenance_refs
    )

    if not observations:
        return AssayMergeResult(
            status="unresolved",
            reason="no_records",
            resolved_assay=None,
            evidence_assays=(),
            observations=(),
            target_id=None,
            ligand_id=None,
            measurement_type=None,
            normalized_unit=None,
            normalized_value=None,
            references=(),
            provenance_refs=(),
            conflicts=(
                AssayConflict(
                    field_name="records",
                    kind="no_records",
                    observed_values=(),
                    message="no assay observations were supplied",
                ),
            ),
        )

    if any(
        observation.target_id is None
        or observation.ligand_id is None
        or observation.measurement_type is None
        for observation in observations
    ):
        return AssayMergeResult(
            status="unresolved",
            reason="missing_required_identifier",
            resolved_assay=None,
            evidence_assays=evidence_assays,
            observations=observations,
            target_id=_single_value(observations, "target_id"),
            ligand_id=_single_value(observations, "ligand_id"),
            measurement_type=_single_value(observations, "measurement_type"),
            normalized_unit=None,
            normalized_value=None,
            references=references,
            provenance_refs=provenance_refs,
            conflicts=_missing_identifier_conflicts(observations),
        )

    target_ids = _unique_values(observations, "target_id")
    ligand_ids = _unique_values(observations, "ligand_id")
    measurement_types = _unique_values(observations, "measurement_type")
    if len(target_ids) > 1 or len(ligand_ids) > 1:
        conflicts: list[AssayConflict] = []
        if len(target_ids) > 1:
            conflicts.append(
                AssayConflict(
                    field_name="target_id",
                    kind="missing_required_identifier",
                    observed_values=target_ids,
                    message="records reference different assay targets",
                )
            )
        if len(ligand_ids) > 1:
            conflicts.append(
                AssayConflict(
                    field_name="ligand_id",
                    kind="missing_required_identifier",
                    observed_values=ligand_ids,
                    message="records reference different ligands",
                )
            )
        return AssayMergeResult(
            status="unresolved",
            reason="identity_mismatch",
            resolved_assay=None,
            evidence_assays=evidence_assays,
            observations=observations,
            target_id=None,
            ligand_id=None,
            measurement_type=None,
            normalized_unit=None,
            normalized_value=None,
            references=references,
            provenance_refs=provenance_refs,
            conflicts=tuple(conflicts),
            alternative_values={"target_id": target_ids, "ligand_id": ligand_ids},
        )

    if len(measurement_types) > 1:
        return AssayMergeResult(
            status="unresolved",
            reason="measurement_type_mismatch",
            resolved_assay=None,
            evidence_assays=evidence_assays,
            observations=observations,
            target_id=target_ids[0],
            ligand_id=ligand_ids[0],
            measurement_type=None,
            normalized_unit=None,
            normalized_value=None,
            references=references,
            provenance_refs=provenance_refs,
            conflicts=(
                AssayConflict(
                    field_name="measurement_type",
                    kind="measurement_type_mismatch",
                    observed_values=measurement_types,
                    message="records contain incompatible assay measurement types",
                ),
            ),
            alternative_values={"measurement_type": measurement_types},
        )

    target_id = target_ids[0]
    ligand_id = ligand_ids[0]
    measurement_type = measurement_types[0]

    unit_values = [_normalize_observation_unit(observation) for observation in observations]
    if any(not item[2] for item in unit_values):
        raw_units = _dedupe(item[1] for item in unit_values if item[1])
        return _unit_failure(
            observations=observations,
            evidence_assays=evidence_assays,
            target_id=target_id,
            ligand_id=ligand_id,
            measurement_type=measurement_type,
            references=references,
            provenance_refs=provenance_refs,
            raw_units=raw_units,
        )

    present_raw_units = [item[1] for item in unit_values if item[1]]
    if 0 < len(present_raw_units) < len(unit_values):
        return _unit_failure(
            observations=observations,
            evidence_assays=evidence_assays,
            target_id=target_id,
            ligand_id=ligand_id,
            measurement_type=measurement_type,
            references=references,
            provenance_refs=provenance_refs,
            raw_units=_dedupe(present_raw_units),
        )

    normalized_units = _dedupe(item[0] for item in unit_values if item[0])
    raw_units = _dedupe(item[1] for item in unit_values if item[1])
    if len(normalized_units) > 1:
        return _unit_failure(
            observations=observations,
            evidence_assays=evidence_assays,
            target_id=target_id,
            ligand_id=ligand_id,
            measurement_type=measurement_type,
            references=references,
            provenance_refs=provenance_refs,
            raw_units=raw_units,
        )

    normalized_values = tuple(item[3] for item in unit_values)
    if any(value is None for value in normalized_values):
        return AssayMergeResult(
            status="unresolved",
            reason="missing_measurement_value",
            resolved_assay=None,
            evidence_assays=evidence_assays,
            observations=observations,
            target_id=target_id,
            ligand_id=ligand_id,
            measurement_type=measurement_type,
            normalized_unit=normalized_units[0] if normalized_units else None,
            normalized_value=None,
            references=references,
            provenance_refs=provenance_refs,
            conflicts=(
                AssayConflict(
                    field_name="measurement_value",
                    kind="missing_measurement_value",
                    observed_values=(),
                    message="one or more records did not provide a numeric assay value",
                ),
            ),
        )

    normalized_unit = normalized_units[0] if normalized_units else None
    if _all_equal(normalized_values):
        resolved_assay = _build_resolved_assay(
            observations,
            target_id=target_id,
            ligand_id=ligand_id,
            measurement_type=measurement_type,
            normalized_unit=normalized_unit,
            normalized_value=normalized_values[0],
        )
        metadata_variation = _metadata_variation(observations)
        return AssayMergeResult(
            status="ambiguous" if metadata_variation else "resolved",
            reason="metadata_variation_preserved"
            if metadata_variation
            else "merged_cleanly",
            resolved_assay=resolved_assay,
            evidence_assays=evidence_assays,
            observations=observations,
            target_id=target_id,
            ligand_id=ligand_id,
            measurement_type=measurement_type,
            normalized_unit=normalized_unit,
            normalized_value=normalized_values[0],
            references=references,
            provenance_refs=provenance_refs,
            alternative_values=metadata_variation,
        )

    return AssayMergeResult(
        status="conflict",
        reason="measurement_value_disagreement",
        resolved_assay=None,
        evidence_assays=evidence_assays,
        observations=observations,
        target_id=target_id,
        ligand_id=ligand_id,
        measurement_type=measurement_type,
        normalized_unit=normalized_unit,
        normalized_value=None,
        references=references,
        provenance_refs=provenance_refs,
        conflicts=(
            AssayConflict(
                field_name="measurement_value",
                kind="measurement_value_disagreement",
                observed_values=tuple(
                    _format_observed_value(value, normalized_unit) for value in normalized_values
                ),
                message="records disagree on the normalized assay value",
            ),
        ),
        alternative_values={
            "measurement_value": tuple(_fmt_num(value) for value in normalized_values),
            **_metadata_variation(observations),
        },
    )


def _normalize_observation(record: object, *, input_index: int) -> AssayObservation:
    payload = _to_mapping(record)
    target_id = _normalize_identifier(
        _first_value(payload, "target_id", "target", "protein_id", "uniprot_id")
    )
    ligand_id = _normalize_identifier(
        _first_value(payload, "ligand_id", "ligand", "compound_id", "molecule_id")
    )
    measurement_type = _normalize_text(
        _first_value(payload, "measurement_type", "type", "assay_type", "endpoint")
    )
    raw_value = _first_value(payload, "measurement_value", "value")
    measurement_value, relation_from_value, raw_value_text = _parse_value(raw_value)
    relation = _normalize_text(_first_value(payload, "relation", "inequality"))
    relation = relation or relation_from_value
    raw_unit = _normalize_text(_first_value(payload, "measurement_unit", "unit"))
    measurement_unit, unit_factor, _ = _normalize_unit(raw_unit)
    if measurement_value is not None and unit_factor is not None:
        measurement_value *= unit_factor
        measurement_unit = "nM"
    confidence = _to_float(_first_value(payload, "confidence"))
    assay_conditions = _normalize_text(
        _first_value(payload, "assay_conditions", "conditions")
    )
    ph = _to_float(_first_value(payload, "ph", "pH"))
    temperature_celsius = _to_float(
        _first_value(payload, "temperature_celsius", "temperature")
    )
    source = _normalize_text(_first_value(payload, "source", "source_name")) or "UNKNOWN"
    source_id = _normalize_text(
        _first_value(payload, "source_id", "assay_id", "bindingdb_assay_id")
    ) or f"input-{input_index + 1}"
    references = _dedupe(_coerce_iterable(payload, "references", "citations"))
    provenance_refs = _dedupe(
        _coerce_iterable(payload, "provenance_refs", "provenance", "evidence")
    ) or (f"{source}:{source_id}",)
    return AssayObservation(
        target_id=target_id,
        ligand_id=ligand_id,
        measurement_type=measurement_type,
        measurement_value=measurement_value,
        measurement_unit=measurement_unit,
        relation=relation,
        confidence=confidence,
        source=source,
        source_id=source_id,
        assay_conditions=assay_conditions,
        ph=ph,
        temperature_celsius=temperature_celsius,
        references=references,
        provenance_refs=provenance_refs,
        raw_value=raw_value_text,
        raw_unit=raw_unit,
        input_index=input_index,
    )


def _normalize_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _normalize_identifier(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _normalize_observation_unit(
    observation: AssayObservation,
) -> tuple[str | None, str | None, bool, float | None]:
    raw_unit = observation.raw_unit
    if raw_unit is None:
        return observation.measurement_unit, None, True, observation.measurement_value
    normalized_unit, factor, convertible = _normalize_unit(raw_unit)
    if observation.measurement_value is not None and factor is not None:
        normalized_unit = "nM"
    return normalized_unit, raw_unit, convertible, observation.measurement_value


def _unique_values(
    observations: tuple[AssayObservation, ...],
    field_name: str,
) -> tuple[str, ...]:
    return _dedupe(
        getattr(observation, field_name)
        for observation in observations
        if getattr(observation, field_name)
    )


def _single_value(observations: tuple[AssayObservation, ...], field_name: str) -> str | None:
    values = _unique_values(observations, field_name)
    return values[0] if len(values) == 1 else None


def _missing_identifier_conflicts(
    observations: tuple[AssayObservation, ...],
) -> tuple[AssayConflict, ...]:
    conflicts: list[AssayConflict] = []
    if not _unique_values(observations, "target_id"):
        conflicts.append(
            AssayConflict(
                field_name="target_id",
                kind="missing_required_identifier",
                observed_values=(),
                message="assay observations are missing a target identifier",
            )
        )
    if not _unique_values(observations, "ligand_id"):
        conflicts.append(
            AssayConflict(
                field_name="ligand_id",
                kind="missing_required_identifier",
                observed_values=(),
                message="assay observations are missing a ligand identifier",
            )
        )
    if not _unique_values(observations, "measurement_type"):
        conflicts.append(
            AssayConflict(
                field_name="measurement_type",
                kind="missing_required_identifier",
                observed_values=(),
                message="assay observations are missing a measurement type",
            )
        )
    return tuple(conflicts)


def _unit_failure(
    *,
    observations: tuple[AssayObservation, ...],
    evidence_assays: tuple[CanonicalAssay, ...],
    target_id: str,
    ligand_id: str,
    measurement_type: str,
    references: tuple[str, ...],
    provenance_refs: tuple[str, ...],
    raw_units: tuple[str, ...],
) -> AssayMergeResult:
    return AssayMergeResult(
        status="unresolved",
        reason="unit_incompatible",
        resolved_assay=None,
        evidence_assays=evidence_assays,
        observations=observations,
        target_id=target_id,
        ligand_id=ligand_id,
        measurement_type=measurement_type,
        normalized_unit=None,
        normalized_value=None,
        references=references,
        provenance_refs=provenance_refs,
        conflicts=(
            AssayConflict(
                field_name="measurement_unit",
                kind="unit_incompatible",
                observed_values=raw_units,
                message="assay units cannot be normalized onto a shared scale",
            ),
        ),
        alternative_values={"measurement_unit": raw_units},
    )


def _all_equal(values: tuple[float, ...]) -> bool:
    if not values:
        return False
    first = values[0]
    return all(_same_float(first, value) for value in values[1:])


def _metadata_variation(
    observations: tuple[AssayObservation, ...],
) -> dict[str, tuple[str, ...]]:
    alternative_values: dict[str, tuple[str, ...]] = {}
    for field_name in ("assay_conditions", "ph", "temperature_celsius"):
        values = _dedupe(
            _stringify(getattr(observation, field_name))
            for observation in observations
            if getattr(observation, field_name) is not None
        )
        if len(values) > 1:
            alternative_values[field_name] = values
    return alternative_values


def _stringify(value: Any) -> str:
    if isinstance(value, float):
        return _fmt_num(value)
    return _clean_text(value)


def _build_resolved_assay(
    observations: tuple[AssayObservation, ...],
    *,
    target_id: str,
    ligand_id: str,
    measurement_type: str,
    normalized_unit: str | None,
    normalized_value: float,
) -> CanonicalAssay:
    if len(observations) == 1:
        return observations[0].to_canonical_assay(
            assay_id=f"assay:{_source_key(observations[0])}",
        )
    provenance = _dedupe(
        ref for observation in observations for ref in observation.provenance_refs
    )
    references = _dedupe(ref for observation in observations for ref in observation.references)
    return CanonicalAssay(
        assay_id=(
            f"assay:CANONICAL:merge:{target_id}:{ligand_id}:{measurement_type}:"
            f"{normalized_unit or 'unitless'}:{_fmt_num(normalized_value)}"
        ),
        target_id=target_id,
        ligand_id=ligand_id,
        source="CANONICAL",
        source_id=(
            f"merge:{target_id}:{ligand_id}:{measurement_type}:"
            f"{normalized_unit or 'unitless'}:{_fmt_num(normalized_value)}"
        ),
        measurement_type=measurement_type,
        measurement_value=normalized_value,
        measurement_unit=normalized_unit,
        relation=_consensus_text(observations, "relation"),
        assay_conditions=_consensus_text(observations, "assay_conditions"),
        ph=_consensus_float(observations, "ph"),
        temperature_celsius=_consensus_float(observations, "temperature_celsius"),
        references=references,
        provenance=provenance,
    )


def _consensus_text(
    observations: tuple[AssayObservation, ...],
    field_name: str,
) -> str | None:
    values = _unique_values(observations, field_name)
    return values[0] if len(values) == 1 else None


def _consensus_float(
    observations: tuple[AssayObservation, ...],
    field_name: str,
) -> float | None:
    values = [
        getattr(observation, field_name)
        for observation in observations
        if getattr(observation, field_name) is not None
    ]
    if not values:
        return None
    first = values[0]
    return first if all(_same_float(first, value) for value in values[1:]) else None


def _source_key(observation: AssayObservation) -> str:
    source = _clean_text(observation.source) or "UNKNOWN"
    source_id = _clean_text(observation.source_id) or f"input-{observation.input_index + 1}"
    return f"{source}:{source_id}"


def _format_observed_value(value: float, unit: str | None) -> str:
    return f"{_fmt_num(value)} {unit}" if unit else _fmt_num(value)


def _to_mapping(record: object) -> Mapping[str, Any]:
    if isinstance(record, CanonicalAssay):
        return record.to_dict()
    if isinstance(record, Mapping):
        return record
    if hasattr(record, "__dict__"):
        return vars(record)
    raise TypeError("assay record must be a mapping or canonical assay instance")


__all__ = [
    "AssayConflict",
    "AssayConflictKind",
    "AssayMergeResult",
    "AssayMergeStatus",
    "AssayObservation",
    "merge_assay_records",
]
