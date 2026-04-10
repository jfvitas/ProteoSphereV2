from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

DEFAULT_ASSAY_FEATURE_NAMES = (
    "accession",
    "measurement_technique",
    "assay_name",
    "source_name",
    "source_record_id",
    "reported_pH",
    "reported_temperature_celsius",
    "i_conc_range",
    "e_conc_range",
    "s_conc_range",
    "candidate_only",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _optional_float(value: Any, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric or None")
    if not isinstance(value, (int, float)):
        try:
            return float(str(value).strip())
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise TypeError(f"{field_name} must be numeric or None") from exc
    return float(value)


def _optional_bool(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    text = _clean_text(value).casefold()
    if text in {"true", "yes", "y", "1"}:
        return True
    if text in {"false", "no", "n", "0"}:
        return False
    return bool(text)


def _unique_text(values: Iterable[Any]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _range_from_values(values: Iterable[float | None]) -> tuple[float, float] | None:
    collected = [float(value) for value in values if value is not None]
    if not collected:
        return None
    return (min(collected), max(collected))


def _row_value(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _assay_context(row: Mapping[str, Any]) -> Mapping[str, Any]:
    context = row.get("assay_context")
    if isinstance(context, Mapping):
        return context
    return {}


@dataclass(frozen=True, slots=True)
class AssayFeatureRecord:
    accession: str
    measurement_technique: str = ""
    assay_name: str = ""
    source_name: str = ""
    source_record_id: str | None = None
    reported_pH: float | None = None
    reported_temperature_celsius: float | None = None
    i_conc_range: str | None = None
    e_conc_range: str | None = None
    s_conc_range: str | None = None
    candidate_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        object.__setattr__(self, "measurement_technique", _clean_text(self.measurement_technique))
        object.__setattr__(self, "assay_name", _clean_text(self.assay_name))
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(
            self,
            "reported_pH",
            _optional_float(self.reported_pH, "reported_pH"),
        )
        object.__setattr__(
            self,
            "reported_temperature_celsius",
            _optional_float(self.reported_temperature_celsius, "reported_temperature_celsius"),
        )
        object.__setattr__(self, "i_conc_range", _optional_text(self.i_conc_range))
        object.__setattr__(self, "e_conc_range", _optional_text(self.e_conc_range))
        object.__setattr__(self, "s_conc_range", _optional_text(self.s_conc_range))
        object.__setattr__(self, "candidate_only", _optional_bool(self.candidate_only))

    @property
    def condition_flags(self) -> dict[str, bool]:
        return {
            "reported_pH": self.reported_pH is not None,
            "reported_temperature_celsius": self.reported_temperature_celsius is not None,
            "i_conc_range": self.i_conc_range is not None,
            "e_conc_range": self.e_conc_range is not None,
            "s_conc_range": self.s_conc_range is not None,
        }

    @property
    def feature_names(self) -> tuple[str, ...]:
        return DEFAULT_ASSAY_FEATURE_NAMES

    @property
    def feature_vector(self) -> tuple[Any, ...]:
        return (
            self.accession,
            self.measurement_technique,
            self.assay_name,
            self.source_name,
            self.source_record_id,
            self.reported_pH,
            self.reported_temperature_celsius,
            self.i_conc_range,
            self.e_conc_range,
            self.s_conc_range,
            self.candidate_only,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "measurement_technique": self.measurement_technique,
            "assay_name": self.assay_name,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "reported_pH": self.reported_pH,
            "reported_temperature_celsius": self.reported_temperature_celsius,
            "i_conc_range": self.i_conc_range,
            "e_conc_range": self.e_conc_range,
            "s_conc_range": self.s_conc_range,
            "candidate_only": self.candidate_only,
            "condition_flags": dict(self.condition_flags),
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AssayFeatureRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            accession=payload.get("accession") or "",
            measurement_technique=payload.get("measurement_technique")
            or payload.get("bindingdb_measurement_technique")
            or "",
            assay_name=payload.get("assay_name") or payload.get("bindingdb_assay_name") or "",
            source_name=payload.get("source_name") or "",
            source_record_id=payload.get("source_record_id"),
            reported_pH=payload.get("reported_pH") or payload.get("ph"),
            reported_temperature_celsius=payload.get("reported_temperature_celsius")
            or payload.get("temp"),
            i_conc_range=payload.get("i_conc_range")
            or _assay_context(payload).get("i_conc_range"),
            e_conc_range=payload.get("e_conc_range")
            or _assay_context(payload).get("e_conc_range"),
            s_conc_range=payload.get("s_conc_range")
            or _assay_context(payload).get("s_conc_range"),
            candidate_only=payload.get("candidate_only"),
        )


@dataclass(frozen=True, slots=True)
class AssayFeatureSummary:
    accession: str
    rows: tuple[AssayFeatureRecord, ...]
    measurement_techniques: tuple[str, ...] = ()
    assay_names: tuple[str, ...] = ()
    source_names: tuple[str, ...] = ()
    row_count: int = 0
    rows_with_reported_pH: int = 0
    rows_with_reported_temperature: int = 0
    i_conc_range_count: int = 0
    e_conc_range_count: int = 0
    s_conc_range_count: int = 0
    candidate_only_count: int = 0
    reported_pH_range: tuple[float, float] | None = None
    reported_temperature_celsius_range: tuple[float, float] | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        rows = tuple(self.rows)
        for row in rows:
            if not isinstance(row, AssayFeatureRecord):
                raise TypeError("rows must contain AssayFeatureRecord objects")
            if row.accession != self.accession:
                raise ValueError("rows must all share the same accession")
        object.__setattr__(self, "rows", rows)
        object.__setattr__(
            self,
            "measurement_techniques",
            _unique_text(
                self.measurement_techniques
                or (row.measurement_technique for row in rows)
            ),
        )
        object.__setattr__(
            self,
            "assay_names",
            _unique_text(self.assay_names or (row.assay_name for row in rows)),
        )
        object.__setattr__(
            self,
            "source_names",
            _unique_text(self.source_names or (row.source_name for row in rows)),
        )
        object.__setattr__(self, "row_count", int(self.row_count or len(rows)))
        object.__setattr__(
            self,
            "rows_with_reported_pH",
            int(
                self.rows_with_reported_pH
                or sum(1 for row in rows if row.reported_pH is not None)
            ),
        )
        object.__setattr__(
            self,
            "rows_with_reported_temperature",
            int(
                self.rows_with_reported_temperature
                or sum(1 for row in rows if row.reported_temperature_celsius is not None)
            ),
        )
        object.__setattr__(
            self,
            "i_conc_range_count",
            int(self.i_conc_range_count or sum(1 for row in rows if row.i_conc_range is not None)),
        )
        object.__setattr__(
            self,
            "e_conc_range_count",
            int(self.e_conc_range_count or sum(1 for row in rows if row.e_conc_range is not None)),
        )
        object.__setattr__(
            self,
            "s_conc_range_count",
            int(self.s_conc_range_count or sum(1 for row in rows if row.s_conc_range is not None)),
        )
        object.__setattr__(
            self,
            "candidate_only_count",
            int(self.candidate_only_count or sum(1 for row in rows if row.candidate_only)),
        )
        object.__setattr__(
            self,
            "reported_pH_range",
            self.reported_pH_range
            if self.reported_pH_range is not None
            else _range_from_values(row.reported_pH for row in rows),
        )
        object.__setattr__(
            self,
            "reported_temperature_celsius_range",
            self.reported_temperature_celsius_range
            if self.reported_temperature_celsius_range is not None
            else _range_from_values(row.reported_temperature_celsius for row in rows),
        )
        object.__setattr__(self, "provenance", dict(self.provenance))

    @property
    def has_condition_data(self) -> bool:
        return any(
            (
                self.rows_with_reported_pH,
                self.rows_with_reported_temperature,
                self.i_conc_range_count,
                self.e_conc_range_count,
                self.s_conc_range_count,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "row_count": self.row_count,
            "measurement_techniques": list(self.measurement_techniques),
            "assay_names": list(self.assay_names),
            "source_names": list(self.source_names),
            "rows_with_reported_pH": self.rows_with_reported_pH,
            "rows_with_reported_temperature": self.rows_with_reported_temperature,
            "i_conc_range_count": self.i_conc_range_count,
            "e_conc_range_count": self.e_conc_range_count,
            "s_conc_range_count": self.s_conc_range_count,
            "candidate_only_count": self.candidate_only_count,
            "reported_pH_range": list(self.reported_pH_range)
            if self.reported_pH_range is not None
            else None,
            "reported_temperature_celsius_range": list(self.reported_temperature_celsius_range)
            if self.reported_temperature_celsius_range is not None
            else None,
            "has_condition_data": self.has_condition_data,
            "rows": [row.to_dict() for row in self.rows],
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AssayFeatureSummary:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        rows = tuple(
            item
            if isinstance(item, AssayFeatureRecord)
            else AssayFeatureRecord.from_dict(item)
            for item in payload.get("rows") or ()
        )
        reported_pH_range = payload.get("reported_pH_range")
        temperature_range = payload.get("reported_temperature_celsius_range")
        return cls(
            accession=payload.get("accession") or "",
            rows=rows,
            measurement_techniques=payload.get("measurement_techniques") or (),
            assay_names=payload.get("assay_names") or (),
            source_names=payload.get("source_names") or (),
            row_count=payload.get("row_count") or len(rows),
            rows_with_reported_pH=payload.get("rows_with_reported_pH") or 0,
            rows_with_reported_temperature=payload.get("rows_with_reported_temperature") or 0,
            i_conc_range_count=payload.get("i_conc_range_count") or 0,
            e_conc_range_count=payload.get("e_conc_range_count") or 0,
            s_conc_range_count=payload.get("s_conc_range_count") or 0,
            candidate_only_count=payload.get("candidate_only_count") or 0,
            reported_pH_range=tuple(reported_pH_range) if reported_pH_range is not None else None,
            reported_temperature_celsius_range=tuple(temperature_range)
            if temperature_range is not None
            else None,
            provenance=payload.get("provenance") or {},
        )


def extract_assay_row_features(row: Mapping[str, Any]) -> AssayFeatureRecord:
    if not isinstance(row, Mapping):
        raise TypeError("row must be a mapping")
    context = _assay_context(row)
    accession = _required_text(_row_value(row, "accession"), "accession")
    return AssayFeatureRecord(
        accession=accession,
        measurement_technique=(
            _row_value(row, "bindingdb_measurement_technique", "measurement_technique")
            or ""
        ),
        assay_name=_row_value(row, "bindingdb_assay_name", "assay_name") or "",
        source_name=_row_value(row, "source_name", "source") or "",
        source_record_id=_row_value(row, "source_record_id", "measurement_id"),
        reported_pH=_row_value(row, "reported_pH", "ph"),
        reported_temperature_celsius=_row_value(
            row,
            "reported_temperature_celsius",
            "temp",
        ),
        i_conc_range=_row_value(row, "i_conc_range") or context.get("i_conc_range"),
        e_conc_range=_row_value(row, "e_conc_range") or context.get("e_conc_range"),
        s_conc_range=_row_value(row, "s_conc_range") or context.get("s_conc_range"),
        candidate_only=row.get("candidate_only"),
    )


def summarize_assay_features(
    rows: Iterable[Mapping[str, Any]],
    *,
    accession: str | None = None,
) -> AssayFeatureSummary:
    extracted: list[AssayFeatureRecord] = []
    observed_accessions: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError("rows must contain mapping rows")
        record = extract_assay_row_features(row)
        if accession is not None and record.accession != accession:
            continue
        extracted.append(record)
        observed_accessions.append(record.accession)

    if not extracted:
        raise ValueError("no assay rows were available for the requested accession")
    resolved_accession = accession or observed_accessions[0]
    if accession is None and len(_unique_text(observed_accessions)) > 1:
        raise ValueError("rows must share a single accession or an accession must be provided")
    return AssayFeatureSummary(
        accession=resolved_accession,
        rows=tuple(extracted),
        provenance={"source_row_count": len(extracted)},
    )


__all__ = [
    "AssayFeatureRecord",
    "AssayFeatureSummary",
    "DEFAULT_ASSAY_FEATURE_NAMES",
    "extract_assay_row_features",
    "summarize_assay_features",
]
