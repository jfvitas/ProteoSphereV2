from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)

DEFAULT_DISPROT_API_BASE_URL = "https://disprot.org/api"
DISPROT_SMOKE_ENV_VAR = "PROTEOSPHERE_DISPROT_SMOKE"
DEFAULT_SMOKE_ACCESSION = "P49913"
SUPPORTED_SOURCE_NAMES = {"disprot"}
SUPPORTED_RETRIEVAL_MODES = {"api", "download"}
DisProtSnapshotStatus = Literal["ready", "blocked", "unavailable"]


class DisProtSnapshotError(ValueError):
    """Raised when a DisProt snapshot manifest or payload cannot be normalized."""


class SnapshotSmokeDisabledError(RuntimeError):
    """Raised when the guarded live smoke path is invoked without opt-in."""


def _normalize_text(value: object | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DisProtSnapshotError(f"{field_name} must be a non-empty string")
    return text


def _normalize_optional_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_bool(value: object | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise DisProtSnapshotError(f"could not normalize boolean value: {value!r}")


def _normalize_optional_bool(value: object | None) -> bool | None:
    if value in (None, ""):
        return None
    return _normalize_bool(value)


def _normalize_int(value: object | None, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise DisProtSnapshotError(f"{field_name} must be an integer")
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise DisProtSnapshotError(f"{field_name} must be an integer") from exc


def _normalize_float(value: object | None, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise DisProtSnapshotError(f"{field_name} must be numeric") from exc


def _coerce_sequence(values: object | None) -> tuple[object, ...]:
    if values in (None, ""):
        return ()
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes, Mapping)):
        return tuple(values)
    return (values,)


def _coerce_text_tuple(values: object | None, *, uppercase: bool = False) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in _coerce_sequence(values):
        text = _normalize_optional_text(raw_value)
        if text is None:
            continue
        text = text.upper() if uppercase else text
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _coerce_accessions(values: object | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    normalized: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for raw_value in _coerce_sequence(values):
        accession = _normalize_accession(raw_value)
        if accession:
            if accession in seen:
                continue
            seen.add(accession)
            normalized.append(accession)
            continue
        text = str(raw_value or "").strip().upper()
        if text:
            invalid.append(text)
    return tuple(normalized), tuple(dict.fromkeys(invalid))


def _normalize_accession(value: object | None) -> str:
    accession = str(value or "").strip().upper()
    if not accession:
        return ""
    if not 6 <= len(accession) <= 10 or not accession.isalnum():
        return ""
    return accession


def _lookup(mapping: Mapping[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = mapping
        for key in path.split("."):
            if not isinstance(current, Mapping) or key not in current:
                current = None
                break
            current = current[key]
        if current not in (None, ""):
            return current
    return None


def _first_text(mapping: Mapping[str, Any], *paths: str, default: str = "") -> str:
    value = _lookup(mapping, *paths)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_source_release(
    value: SourceReleaseManifest | Mapping[str, Any] | None,
) -> SourceReleaseManifest:
    if value is None:
        raise DisProtSnapshotError("source_release is required")
    if isinstance(value, SourceReleaseManifest):
        manifest = value
    elif isinstance(value, Mapping):
        manifest = validate_source_release_manifest_payload(dict(value))
    else:
        raise DisProtSnapshotError("source_release must be a SourceReleaseManifest or mapping")

    if manifest.source_name.casefold() not in SUPPORTED_SOURCE_NAMES:
        raise DisProtSnapshotError("source_release.source_name must describe DisProt")
    if manifest.retrieval_mode.casefold() not in SUPPORTED_RETRIEVAL_MODES:
        raise DisProtSnapshotError(
            "DisProt acquisition only supports api or download retrieval modes"
        )
    return manifest


def _response_header(response: Any, header_name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is not None and hasattr(headers, "get"):
        value = headers.get(header_name)
        if value is None:
            value = headers.get(header_name.title())
        if value is None:
            value = headers.get(header_name.casefold())
        if value is not None:
            text = str(value).strip()
            return text or None
    getter = getattr(response, "getheader", None)
    if callable(getter):
        value = getter(header_name)
        if value is not None:
            text = str(value).strip()
            return text or None
    return None


def _payload_to_records(payload: Any) -> tuple[dict[str, Any], ...]:
    if payload is None:
        return ()
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, tuple):
        items = list(payload)
    elif isinstance(payload, Mapping):
        for key in ("data", "results", "items", "entries"):
            value = payload.get(key)
            if isinstance(value, list):
                items = value
                break
            if isinstance(value, tuple):
                items = list(value)
                break
        else:
            items = [dict(payload)]
    else:
        raise DisProtSnapshotError("DisProt payload must be a mapping or sequence")

    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise DisProtSnapshotError("DisProt payload items must be mappings")
        records.append(dict(item))
    return tuple(records)


def _clone_jsonish(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_jsonish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_jsonish(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_jsonish(item) for item in value)
    return value


def _coerce_raw_list(value: Any) -> tuple[Any, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, tuple):
        items = value
    elif isinstance(value, list):
        items = tuple(value)
    else:
        items = (value,)
    return tuple(_clone_jsonish(item) for item in items)


@dataclass(frozen=True, slots=True)
class DisProtSnapshotManifest:
    """Pinned acquisition contract for a DisProt disorder snapshot."""

    source_release: SourceReleaseManifest | Mapping[str, Any]
    accessions: tuple[str, ...] = ()
    api_base_url: str = DEFAULT_DISPROT_API_BASE_URL
    provenance: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        source_release = _coerce_source_release(self.source_release)
        accessions, invalid_accessions = _coerce_accessions(self.accessions)
        if invalid_accessions:
            raise DisProtSnapshotError(
                "manifest contains invalid accession(s): " + ", ".join(invalid_accessions)
            )
        if not isinstance(self.provenance, Mapping):
            raise DisProtSnapshotError("provenance must be a mapping")
        if not isinstance(self.metadata, Mapping):
            raise DisProtSnapshotError("metadata must be a mapping")

        object.__setattr__(self, "source_release", source_release)
        object.__setattr__(self, "accessions", accessions)
        object.__setattr__(self, "api_base_url", _normalize_text(self.api_base_url, "api_base_url"))
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def manifest_id(self) -> str:
        return self.source_release.manifest_id

    @property
    def pinned(self) -> bool:
        return self.source_release.has_release_stamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "source_release": self.source_release.to_dict(),
            "accessions": list(self.accessions),
            "api_base_url": self.api_base_url,
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
            "pinned": self.pinned,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DisProtSnapshotManifest:
        if not isinstance(payload, Mapping):
            raise DisProtSnapshotError("manifest must be a mapping")

        source_release_payload = payload.get("source_release")
        if source_release_payload is None:
            source_release_payload = {
                "source_name": _first_text(payload, "source_name", "source", default="DisProt"),
                "release_version": payload.get("release_version")
                or payload.get("release")
                or payload.get("version"),
                "release_date": payload.get("release_date") or payload.get("date"),
                "retrieval_mode": payload.get("retrieval_mode") or payload.get("mode") or "api",
                "source_locator": payload.get("source_locator")
                or payload.get("source_url")
                or payload.get("url"),
                "local_artifact_refs": payload.get("local_artifact_refs")
                or payload.get("artifact_refs")
                or (),
                "provenance": payload.get("source_provenance") or payload.get("provenance") or (),
                "reproducibility_metadata": payload.get("reproducibility_metadata")
                or payload.get("reproducibility")
                or payload.get("metadata")
                or (),
            }

        accessions = (
            payload.get("accessions")
            or payload.get("accession")
            or payload.get("uniprot_accessions")
            or ()
        )
        if isinstance(accessions, Sequence) and not isinstance(accessions, str):
            accessions = tuple(accessions)
        else:
            accessions = (accessions,)

        metadata = payload.get("metadata") or {}
        if not metadata and payload.get("notes") is not None:
            metadata = {"notes": payload.get("notes")}

        return cls(
            source_release=source_release_payload,
            accessions=accessions,
            api_base_url=str(payload.get("api_base_url") or DEFAULT_DISPROT_API_BASE_URL),
            provenance=payload.get("provenance") or {},
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class DisProtConsensusSpan:
    start: int
    end: int
    type: str

    def __post_init__(self) -> None:
        if self.start < 1:
            raise DisProtSnapshotError("consensus start must be >= 1")
        if self.end < self.start:
            raise DisProtSnapshotError("consensus end must be >= start")
        object.__setattr__(self, "type", _normalize_text(self.type, "type"))

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "type": self.type}


@dataclass(frozen=True, slots=True)
class DisProtRegionEvidence:
    region_id: str
    start: int
    end: int
    term_id: str
    term_name: str
    term_namespace: str
    term_ontology: str
    disprot_namespace: str
    label_family: str
    version: int | None = None
    ec_id: str | None = None
    ec_go: str | None = None
    ec_name: str | None = None
    ec_ontology: str | None = None
    reference_id: str | None = None
    reference_source: str | None = None
    reference_html: str | None = None
    curator_id: str | None = None
    curator_name: str | None = None
    curator_orcid: str | None = None
    validated: dict[str, Any] = field(default_factory=dict)
    date: str | None = None
    released: str | None = None
    uniprot_changed: bool | None = None
    cross_refs: tuple[Any, ...] = ()
    annotation_extensions: tuple[Any, ...] = ()
    conditions: tuple[Any, ...] = ()
    construct_alterations: tuple[Any, ...] = ()
    interaction_partner: tuple[Any, ...] = ()
    sample: tuple[Any, ...] = ()
    statement: tuple[Any, ...] = ()
    disprot_term_def: str | None = None
    disprot_term_comment: str | None = None
    disprot_term_is_obsolete: bool | None = None
    disprot_term_not_annotate: bool | None = None
    disprot_term_is_binding: bool | None = None
    disprot_term_xref: str | None = None
    unpublished: bool | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_region: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "region_id", _normalize_text(self.region_id, "region_id"))
        start = _normalize_int(self.start, "start")
        end = _normalize_int(self.end, "end")
        if start is None or end is None:
            raise DisProtSnapshotError("region start and end are required")
        if start < 1:
            raise DisProtSnapshotError("region start must be >= 1")
        if end < start:
            raise DisProtSnapshotError("region end must be >= start")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)
        object.__setattr__(self, "term_id", _normalize_text(self.term_id, "term_id"))
        object.__setattr__(self, "term_name", _normalize_text(self.term_name, "term_name"))
        object.__setattr__(
            self, "term_namespace", _normalize_text(self.term_namespace, "term_namespace")
        )
        object.__setattr__(
            self, "term_ontology", _normalize_text(self.term_ontology, "term_ontology")
        )
        object.__setattr__(
            self, "disprot_namespace", _normalize_text(self.disprot_namespace, "disprot_namespace")
        )
        object.__setattr__(self, "label_family", _normalize_text(self.label_family, "label_family"))
        object.__setattr__(self, "validated", dict(self.validated))
        object.__setattr__(self, "cross_refs", _coerce_raw_list(self.cross_refs))
        object.__setattr__(
            self, "annotation_extensions", _coerce_raw_list(self.annotation_extensions)
        )
        object.__setattr__(self, "conditions", _coerce_raw_list(self.conditions))
        object.__setattr__(
            self, "construct_alterations", _coerce_raw_list(self.construct_alterations)
        )
        object.__setattr__(self, "interaction_partner", _coerce_raw_list(self.interaction_partner))
        object.__setattr__(self, "sample", _coerce_raw_list(self.sample))
        object.__setattr__(self, "statement", _coerce_raw_list(self.statement))
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "raw_region", dict(self.raw_region))

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "start": self.start,
            "end": self.end,
            "term_id": self.term_id,
            "term_name": self.term_name,
            "term_namespace": self.term_namespace,
            "term_ontology": self.term_ontology,
            "disprot_namespace": self.disprot_namespace,
            "label_family": self.label_family,
            "version": self.version,
            "ec_id": self.ec_id,
            "ec_go": self.ec_go,
            "ec_name": self.ec_name,
            "ec_ontology": self.ec_ontology,
            "reference_id": self.reference_id,
            "reference_source": self.reference_source,
            "reference_html": self.reference_html,
            "curator_id": self.curator_id,
            "curator_name": self.curator_name,
            "curator_orcid": self.curator_orcid,
            "validated": dict(self.validated),
            "date": self.date,
            "released": self.released,
            "uniprot_changed": self.uniprot_changed,
            "cross_refs": [_clone_jsonish(item) for item in self.cross_refs],
            "annotation_extensions": [_clone_jsonish(item) for item in self.annotation_extensions],
            "conditions": [_clone_jsonish(item) for item in self.conditions],
            "construct_alterations": [_clone_jsonish(item) for item in self.construct_alterations],
            "interaction_partner": [_clone_jsonish(item) for item in self.interaction_partner],
            "sample": [_clone_jsonish(item) for item in self.sample],
            "statement": [_clone_jsonish(item) for item in self.statement],
            "disprot_term_def": self.disprot_term_def,
            "disprot_term_comment": self.disprot_term_comment,
            "disprot_term_is_obsolete": self.disprot_term_is_obsolete,
            "disprot_term_not_annotate": self.disprot_term_not_annotate,
            "disprot_term_is_binding": self.disprot_term_is_binding,
            "disprot_term_xref": self.disprot_term_xref,
            "unpublished": self.unpublished,
            "provenance": dict(self.provenance),
            "raw_region": dict(self.raw_region),
        }


@dataclass(frozen=True, slots=True)
class DisProtProteinRecord:
    accession: str
    disprot_id: str
    sequence: str
    length: int
    organism: str | None = None
    ncbi_taxon_id: int | None = None
    protein_name: str | None = None
    gene_names: tuple[str, ...] = ()
    gene_synonyms: tuple[str, ...] = ()
    orf_names: tuple[str, ...] = ()
    taxonomy: tuple[str, ...] = ()
    dataset: tuple[str, ...] = ()
    uniparc: str | None = None
    uniref50: str | None = None
    uniref90: str | None = None
    uniref100: str | None = None
    released: str | None = None
    date: str | None = None
    creator: str | None = None
    regions_counter: int | None = None
    disorder_content: float | None = None
    alphafold_very_low_content: float | None = None
    disprot_consensus: dict[str, tuple[DisProtConsensusSpan, ...]] = field(default_factory=dict)
    regions: tuple[DisProtRegionEvidence, ...] = ()
    features: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_record: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _normalize_text(self.accession, "accession").upper())
        object.__setattr__(self, "disprot_id", _normalize_text(self.disprot_id, "disprot_id"))
        object.__setattr__(self, "sequence", _normalize_text(self.sequence, "sequence"))
        object.__setattr__(
            self, "length", _normalize_int(self.length, "length") or len(self.sequence)
        )
        if self.length != len(self.sequence):
            object.__setattr__(self, "length", len(self.sequence))
        object.__setattr__(self, "organism", _normalize_optional_text(self.organism))
        object.__setattr__(self, "protein_name", _normalize_optional_text(self.protein_name))
        object.__setattr__(
            self, "ncbi_taxon_id", _normalize_int(self.ncbi_taxon_id, "ncbi_taxon_id")
        )
        object.__setattr__(self, "gene_names", _coerce_text_tuple(self.gene_names))
        object.__setattr__(self, "gene_synonyms", _coerce_text_tuple(self.gene_synonyms))
        object.__setattr__(self, "orf_names", _coerce_text_tuple(self.orf_names))
        object.__setattr__(self, "taxonomy", _coerce_text_tuple(self.taxonomy))
        object.__setattr__(self, "dataset", _coerce_text_tuple(self.dataset))
        object.__setattr__(self, "uniparc", _normalize_optional_text(self.uniparc))
        object.__setattr__(self, "uniref50", _normalize_optional_text(self.uniref50))
        object.__setattr__(self, "uniref90", _normalize_optional_text(self.uniref90))
        object.__setattr__(self, "uniref100", _normalize_optional_text(self.uniref100))
        object.__setattr__(self, "released", _normalize_optional_text(self.released))
        object.__setattr__(self, "date", _normalize_optional_text(self.date))
        object.__setattr__(self, "creator", _normalize_optional_text(self.creator))
        object.__setattr__(
            self, "regions_counter", _normalize_int(self.regions_counter, "regions_counter")
        )
        object.__setattr__(
            self, "disorder_content", _normalize_float(self.disorder_content, "disorder_content")
        )
        object.__setattr__(
            self,
            "alphafold_very_low_content",
            _normalize_float(self.alphafold_very_low_content, "alphafold_very_low_content"),
        )
        object.__setattr__(
            self,
            "disprot_consensus",
            {key: tuple(value) for key, value in self.disprot_consensus.items()},
        )
        object.__setattr__(self, "regions", tuple(self.regions))
        object.__setattr__(self, "features", dict(self.features))
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "raw_record", dict(self.raw_record))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "disprot_id": self.disprot_id,
            "sequence": self.sequence,
            "length": self.length,
            "organism": self.organism,
            "ncbi_taxon_id": self.ncbi_taxon_id,
            "protein_name": self.protein_name,
            "gene_names": list(self.gene_names),
            "gene_synonyms": list(self.gene_synonyms),
            "orf_names": list(self.orf_names),
            "taxonomy": list(self.taxonomy),
            "dataset": list(self.dataset),
            "uniparc": self.uniparc,
            "uniref50": self.uniref50,
            "uniref90": self.uniref90,
            "uniref100": self.uniref100,
            "released": self.released,
            "date": self.date,
            "creator": self.creator,
            "regions_counter": self.regions_counter,
            "disorder_content": self.disorder_content,
            "alphafold_very_low_content": self.alphafold_very_low_content,
            "disprot_consensus": {
                key: [span.to_dict() for span in value]
                for key, value in self.disprot_consensus.items()
            },
            "regions": [region.to_dict() for region in self.regions],
            "features": dict(self.features),
            "provenance": dict(self.provenance),
            "raw_record": dict(self.raw_record),
        }


@dataclass(frozen=True, slots=True)
class DisProtSnapshot:
    source_release: dict[str, Any]
    provenance: dict[str, Any]
    records: tuple[DisProtProteinRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": dict(self.source_release),
            "provenance": dict(self.provenance),
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class DisProtSnapshotProvenance:
    source: Literal["DisProt"] = "DisProt"
    source_release: dict[str, Any] = field(default_factory=dict)
    manifest_id: str = ""
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = ""
    source_locator: str = ""
    api_base_url: str = DEFAULT_DISPROT_API_BASE_URL
    requested_accessions: tuple[str, ...] = ()
    request_url: str = ""
    api_version: str = ""
    fetched_at: str = ""
    record_count: int = 0
    region_count: int = 0
    blocker_reason: str = ""
    unavailable_reason: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_release": dict(self.source_release),
            "manifest_id": self.manifest_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "api_base_url": self.api_base_url,
            "requested_accessions": list(self.requested_accessions),
            "request_url": self.request_url,
            "api_version": self.api_version,
            "fetched_at": self.fetched_at,
            "record_count": self.record_count,
            "region_count": self.region_count,
            "blocker_reason": self.blocker_reason,
            "unavailable_reason": self.unavailable_reason,
            "manifest": dict(self.manifest),
        }


@dataclass(frozen=True, slots=True)
class DisProtSnapshotResult:
    status: DisProtSnapshotStatus
    manifest: dict[str, Any] = field(default_factory=dict)
    contract: DisProtSnapshotManifest | None = None
    snapshot: DisProtSnapshot | None = None
    blocker_reason: str = ""
    unavailable_reason: str = ""
    missing_fields: tuple[str, ...] = ()
    invalid_accessions: tuple[str, ...] = ()
    missing_accessions: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "manifest": dict(self.manifest),
            "contract": self.contract.to_dict() if self.contract is not None else None,
            "snapshot": self.snapshot.to_dict() if self.snapshot is not None else None,
            "blocker_reason": self.blocker_reason,
            "unavailable_reason": self.unavailable_reason,
            "missing_fields": list(self.missing_fields),
            "invalid_accessions": list(self.invalid_accessions),
            "missing_accessions": list(self.missing_accessions),
            "provenance": dict(self.provenance),
        }


def build_disprot_snapshot_manifest(
    accessions: Sequence[str] = (),
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    release_version: str | None = None,
    release_date: str | None = None,
    retrieval_mode: str = "download",
    source_locator: str | None = None,
    api_base_url: str = DEFAULT_DISPROT_API_BASE_URL,
    provenance: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DisProtSnapshotManifest:
    if source_release is None:
        source_release = SourceReleaseManifest(
            source_name="DisProt",
            release_version=release_version or "smoke",
            release_date=release_date,
            retrieval_mode=retrieval_mode,
            source_locator=source_locator or api_base_url,
            provenance=(),
        )
    return DisProtSnapshotManifest(
        source_release=source_release,
        accessions=tuple(accessions),
        api_base_url=api_base_url,
        provenance={} if provenance is None else provenance,
        metadata={} if metadata is None else metadata,
    )


def acquire_disprot_snapshot(
    manifest: DisProtSnapshotManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    acquired_at: str | None = None,
) -> DisProtSnapshotResult:
    """Acquire a manifest-pinned DisProt snapshot with explicit disorder provenance."""

    try:
        normalized_manifest = _normalize_manifest(manifest)
    except DisProtSnapshotError as exc:
        return DisProtSnapshotResult(
            status="blocked",
            manifest=dict(manifest) if isinstance(manifest, Mapping) else {},
            blocker_reason=str(exc),
        )

    manifest_payload = normalized_manifest.to_dict()
    provenance = _build_manifest_provenance(normalized_manifest, acquired_at=acquired_at)

    if normalized_manifest.source_release.retrieval_mode == "download":
        source_locator = normalized_manifest.source_release.source_locator
        if not source_locator:
            return DisProtSnapshotResult(
                status="blocked",
                manifest=manifest_payload,
                contract=normalized_manifest,
                blocker_reason="DisProt download snapshots require source_release.source_locator",
                provenance={
                    **provenance,
                    "blocker_reason": (
                        "DisProt download snapshots require "
                        "source_release.source_locator"
                    ),
                },
            )
        try:
            payload, api_version = _request_json(source_locator, opener=opener)
            records = _materialize_records(
                payload,
                normalized_manifest,
                provenance,
                request_url=source_locator,
            )
        except (HTTPError, URLError, OSError) as exc:
            return DisProtSnapshotResult(
                status="blocked",
                manifest=manifest_payload,
                contract=normalized_manifest,
                blocker_reason=f"DisProt request failed: {exc}",
                provenance={**provenance, "blocker_reason": f"DisProt request failed: {exc}"},
            )
        except json.JSONDecodeError as exc:
            return DisProtSnapshotResult(
                status="blocked",
                manifest=manifest_payload,
                contract=normalized_manifest,
                blocker_reason=f"DisProt response could not be parsed: {exc}",
                provenance={
                    **provenance,
                    "blocker_reason": f"DisProt response could not be parsed: {exc}",
                },
            )
        except DisProtSnapshotError as exc:
            return DisProtSnapshotResult(
                status="blocked",
                manifest=manifest_payload,
                contract=normalized_manifest,
                blocker_reason=str(exc),
                provenance={**provenance, "blocker_reason": str(exc)},
            )
        except Exception as exc:  # pragma: no cover - defensive runtime blocker
            return DisProtSnapshotResult(
                status="blocked",
                manifest=manifest_payload,
                contract=normalized_manifest,
                blocker_reason=f"unexpected runtime failure: {type(exc).__name__}: {exc}",
                provenance={
                    **provenance,
                    "blocker_reason": f"unexpected runtime failure: {type(exc).__name__}: {exc}",
                },
            )

        if normalized_manifest.accessions:
            requested = set(normalized_manifest.accessions)
            filtered = [record for record in records if record.accession in requested]
            missing_accessions = tuple(
                accession
                for accession in normalized_manifest.accessions
                if accession not in {record.accession for record in filtered}
            )
            if missing_accessions:
                return DisProtSnapshotResult(
                    status="unavailable",
                    manifest=manifest_payload,
                    contract=normalized_manifest,
                    unavailable_reason=(
                        "DisProt snapshot did not contain requested accession(s): "
                        + ", ".join(missing_accessions)
                    ),
                    missing_accessions=missing_accessions,
                    provenance={
                        **provenance,
                        "unavailable_reason": (
                            "DisProt snapshot did not contain requested accession(s): "
                            + ", ".join(missing_accessions)
                        ),
                        "missing_accessions": list(missing_accessions),
                    },
                )
            records = filtered

        if not records:
            return _unavailable_result(
                normalized_manifest,
                manifest_payload,
                provenance,
                unavailable_reason="DisProt snapshot returned no records",
            )

        return _ready_result(
            normalized_manifest,
            manifest_payload,
            provenance,
            records,
            request_url=source_locator,
            api_version=api_version,
        )

    if not normalized_manifest.accessions:
        return DisProtSnapshotResult(
            status="blocked",
            manifest=manifest_payload,
            contract=normalized_manifest,
            blocker_reason="DisProt API snapshots require at least one accession",
            provenance={
                **provenance,
                "blocker_reason": "DisProt API snapshots require at least one accession",
            },
        )

    records: list[DisProtProteinRecord] = []
    missing_accessions: list[str] = []
    request_url = ""
    api_version = ""

    try:
        for accession in normalized_manifest.accessions:
            request_url = _build_api_request_url(normalized_manifest.api_base_url, accession)
            payload, api_version = _request_json(request_url, opener=opener)
            accession_records = _materialize_records(
                payload,
                normalized_manifest,
                provenance,
                request_url=request_url,
            )
            matching = [record for record in accession_records if record.accession == accession]
            if not matching:
                missing_accessions.append(accession)
                continue
            records.append(matching[0])
    except (HTTPError, URLError, OSError) as exc:
        return DisProtSnapshotResult(
            status="blocked",
            manifest=manifest_payload,
            contract=normalized_manifest,
            blocker_reason=f"DisProt request failed: {exc}",
            provenance={**provenance, "blocker_reason": f"DisProt request failed: {exc}"},
        )
    except json.JSONDecodeError as exc:
        return DisProtSnapshotResult(
            status="blocked",
            manifest=manifest_payload,
            contract=normalized_manifest,
            blocker_reason=f"DisProt response could not be parsed: {exc}",
            provenance={
                **provenance,
                "blocker_reason": f"DisProt response could not be parsed: {exc}",
            },
        )
    except DisProtSnapshotError as exc:
        return DisProtSnapshotResult(
            status="blocked",
            manifest=manifest_payload,
            contract=normalized_manifest,
            blocker_reason=str(exc),
            provenance={**provenance, "blocker_reason": str(exc)},
        )
    except Exception as exc:  # pragma: no cover - defensive runtime blocker
        return DisProtSnapshotResult(
            status="blocked",
            manifest=manifest_payload,
            contract=normalized_manifest,
            blocker_reason=f"unexpected runtime failure: {type(exc).__name__}: {exc}",
            provenance={
                **provenance,
                "blocker_reason": f"unexpected runtime failure: {type(exc).__name__}: {exc}",
            },
        )

    if missing_accessions:
        reason = "DisProt snapshot did not resolve requested accession(s): " + ", ".join(
            missing_accessions
        )
        return DisProtSnapshotResult(
            status="unavailable",
            manifest=manifest_payload,
            contract=normalized_manifest,
            unavailable_reason=reason,
            missing_accessions=tuple(missing_accessions),
            provenance={
                **provenance,
                "unavailable_reason": reason,
                "missing_accessions": missing_accessions,
            },
        )

    if not records:
        return _unavailable_result(
            normalized_manifest,
            manifest_payload,
            provenance,
            unavailable_reason="DisProt snapshot returned no records",
        )

    return _ready_result(
        normalized_manifest,
        manifest_payload,
        provenance,
        records,
        request_url=request_url,
        api_version=api_version,
    )


def run_live_smoke_snapshot(
    accession: str = DEFAULT_SMOKE_ACCESSION,
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    opener: Callable[..., Any] | None = None,
) -> DisProtSnapshotResult:
    if os.getenv(DISPROT_SMOKE_ENV_VAR) != "1":
        raise SnapshotSmokeDisabledError(
            f"set {DISPROT_SMOKE_ENV_VAR}=1 to run the DisProt smoke path"
        )

    manifest = build_disprot_snapshot_manifest(
        [accession],
        source_release=source_release,
        release_version="smoke",
        retrieval_mode="api",
        source_locator=DEFAULT_DISPROT_API_BASE_URL,
    )
    return acquire_disprot_snapshot(manifest, opener=opener)


def _normalize_manifest(
    manifest: DisProtSnapshotManifest | Mapping[str, Any],
) -> DisProtSnapshotManifest:
    if isinstance(manifest, DisProtSnapshotManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise DisProtSnapshotError("manifest must be a DisProtSnapshotManifest or mapping")
    try:
        return DisProtSnapshotManifest.from_mapping(manifest)
    except (DisProtSnapshotError, ValueError, TypeError) as exc:
        raise DisProtSnapshotError(str(exc)) from exc


def _request_json(url: str, *, opener: Callable[..., Any] | None) -> tuple[Any, str]:
    request = Request(url, headers={"User-Agent": "ProteoSphereV2-DisProtSnapshot/0.1"})
    request_opener = opener or urlopen
    with request_opener(request, timeout=30.0) as response:
        payload = response.read()
        api_version = _response_header(response, "api-version") or ""
    return json.loads(payload.decode("utf-8")), api_version


def _build_api_request_url(api_base_url: str, accession: str) -> str:
    return f"{api_base_url.rstrip('/')}/search?query={quote(accession)}"


def _materialize_records(
    payload: Any,
    manifest: DisProtSnapshotManifest,
    provenance: Mapping[str, Any],
    *,
    request_url: str,
) -> list[DisProtProteinRecord]:
    records: list[DisProtProteinRecord] = []
    for payload_record in _payload_to_records(payload):
        record = _build_protein_record(
            payload_record,
            manifest=manifest,
            provenance=provenance,
            request_url=request_url,
        )
        if manifest.accessions and record.accession not in manifest.accessions:
            continue
        records.append(record)
    return records


def _build_protein_record(
    payload: Mapping[str, Any],
    *,
    manifest: DisProtSnapshotManifest,
    provenance: Mapping[str, Any],
    request_url: str,
) -> DisProtProteinRecord:
    accession = _normalize_accession(_first_text(payload, "acc", "accession", "uniprot_accession"))
    if not accession:
        raise DisProtSnapshotError("DisProt record is missing an accession")
    sequence = _first_text(payload, "sequence")
    if not sequence:
        raise DisProtSnapshotError(f"DisProt record {accession!r} is missing sequence")
    disprot_id = _first_text(payload, "disprot_id", "id")
    if not disprot_id:
        raise DisProtSnapshotError(f"DisProt record {accession!r} is missing disprot_id")

    regions = tuple(
        _build_region_record(
            region,
            accession=accession,
            disprot_id=disprot_id,
            manifest=manifest,
            provenance=provenance,
            request_url=request_url,
        )
        for region in _coerce_sequence(payload.get("regions"))
        if isinstance(region, Mapping)
    )

    gene_names, gene_synonyms, orf_names = _build_gene_labels(payload.get("genes"))
    consensus = _build_consensus(payload.get("disprot_consensus"))

    return DisProtProteinRecord(
        accession=accession,
        disprot_id=disprot_id,
        sequence=sequence,
        length=_normalize_int(payload.get("length"), "length") or len(sequence),
        organism=_normalize_optional_text(payload.get("organism")),
        ncbi_taxon_id=_normalize_int(payload.get("ncbi_taxon_id"), "ncbi_taxon_id"),
        protein_name=_normalize_optional_text(payload.get("name")),
        gene_names=gene_names,
        gene_synonyms=gene_synonyms,
        orf_names=orf_names,
        taxonomy=_coerce_text_tuple(payload.get("taxonomy")),
        dataset=_coerce_text_tuple(payload.get("dataset")),
        uniparc=_first_text(payload, "UniParc", "uniparc", default="") or None,
        uniref50=_normalize_optional_text(payload.get("uniref50")),
        uniref90=_normalize_optional_text(payload.get("uniref90")),
        uniref100=_normalize_optional_text(payload.get("uniref100")),
        released=_normalize_optional_text(payload.get("released")),
        date=_normalize_optional_text(payload.get("date")),
        creator=_normalize_optional_text(payload.get("creator")),
        regions_counter=_normalize_int(payload.get("regions_counter"), "regions_counter"),
        disorder_content=_normalize_float(payload.get("disorder_content"), "disorder_content"),
        alphafold_very_low_content=_normalize_float(
            payload.get("alphafold_very_low_content"),
            "alphafold_very_low_content",
        ),
        disprot_consensus=consensus,
        regions=regions,
        features=dict(payload.get("features") or {}),
        provenance=_build_record_provenance(
            manifest,
            payload,
            provenance,
            request_url=request_url,
        ),
        raw_record=dict(payload),
    )


def _build_record_provenance(
    manifest: DisProtSnapshotManifest,
    payload: Mapping[str, Any],
    provenance: Mapping[str, Any],
    *,
    request_url: str,
) -> dict[str, Any]:
    record_provenance = dict(provenance)
    record_provenance.update(
        {
            "source": "DisProt",
            "manifest_id": manifest.manifest_id,
            "accession": _normalize_accession(_first_text(payload, "acc", "accession")),
            "disprot_id": _first_text(payload, "disprot_id", "id"),
            "released": _normalize_optional_text(payload.get("released")),
            "date": _normalize_optional_text(payload.get("date")),
            "request_url": request_url,
        }
    )
    return record_provenance


def _build_region_record(
    payload: Mapping[str, Any],
    *,
    accession: str,
    disprot_id: str,
    manifest: DisProtSnapshotManifest,
    provenance: Mapping[str, Any],
    request_url: str,
) -> DisProtRegionEvidence:
    disprot_namespace = _first_text(payload, "disprot_namespace", "term_namespace", default="")
    term_namespace = _first_text(payload, "term_namespace", "disprot_namespace", default="")
    label_family = disprot_namespace or term_namespace or "unknown"
    region_provenance = dict(provenance)
    region_provenance.update(
        {
            "source": "DisProt",
            "manifest_id": manifest.manifest_id,
            "accession": accession,
            "disprot_id": disprot_id,
            "region_id": _first_text(payload, "region_id", "id"),
            "label_family": label_family,
            "term_id": _first_text(payload, "term_id"),
            "request_url": request_url,
        }
    )
    start = _normalize_int(payload.get("start"), "start")
    end = _normalize_int(payload.get("end"), "end")
    if start is None or end is None:
        raise DisProtSnapshotError("DisProt region is missing start or end")
    return DisProtRegionEvidence(
        region_id=_first_text(payload, "region_id", "id"),
        start=start,
        end=end,
        term_id=_first_text(payload, "term_id"),
        term_name=_first_text(payload, "term_name"),
        term_namespace=term_namespace or label_family,
        term_ontology=_first_text(payload, "term_ontology"),
        disprot_namespace=disprot_namespace or term_namespace or label_family,
        label_family=label_family,
        version=_normalize_int(payload.get("version"), "version"),
        ec_id=_normalize_optional_text(payload.get("ec_id")),
        ec_go=_normalize_optional_text(payload.get("ec_go")),
        ec_name=_normalize_optional_text(payload.get("ec_name")),
        ec_ontology=_normalize_optional_text(payload.get("ec_ontology")),
        reference_id=_normalize_optional_text(payload.get("reference_id")),
        reference_source=_normalize_optional_text(payload.get("reference_source")),
        reference_html=_normalize_optional_text(payload.get("reference_html")),
        curator_id=_normalize_optional_text(payload.get("curator_id")),
        curator_name=_normalize_optional_text(payload.get("curator_name")),
        curator_orcid=_normalize_optional_text(payload.get("curator_orcid")),
        validated=dict(payload.get("validated") or {}),
        date=_normalize_optional_text(payload.get("date")),
        released=_normalize_optional_text(payload.get("released")),
        uniprot_changed=_normalize_optional_bool(payload.get("uniprot_changed")),
        cross_refs=_coerce_raw_list(payload.get("cross_refs")),
        annotation_extensions=_coerce_raw_list(payload.get("annotation_extensions")),
        conditions=_coerce_raw_list(payload.get("conditions")),
        construct_alterations=_coerce_raw_list(payload.get("construct_alterations")),
        interaction_partner=_coerce_raw_list(payload.get("interaction_partner")),
        sample=_coerce_raw_list(payload.get("sample")),
        statement=_coerce_raw_list(payload.get("statement")),
        disprot_term_def=_normalize_optional_text(payload.get("term_def")),
        disprot_term_comment=_normalize_optional_text(payload.get("term_comment")),
        disprot_term_is_obsolete=_normalize_optional_bool(payload.get("term_is_obsolete")),
        disprot_term_not_annotate=_normalize_optional_bool(payload.get("term_not_annotate")),
        disprot_term_is_binding=_normalize_optional_bool(payload.get("term_is_binding")),
        disprot_term_xref=_normalize_optional_text(payload.get("term_xref")),
        unpublished=_normalize_optional_bool(payload.get("unpublished")),
        provenance=region_provenance,
        raw_region=dict(payload),
    )


def _build_consensus(value: Any) -> dict[str, tuple[DisProtConsensusSpan, ...]]:
    if value in (None, ""):
        return {}
    if not isinstance(value, Mapping):
        raise DisProtSnapshotError("disprot_consensus must be a mapping")
    consensus: dict[str, tuple[DisProtConsensusSpan, ...]] = {}
    for label, spans in value.items():
        if spans in (None, ""):
            continue
        if not isinstance(spans, Sequence) or isinstance(spans, (str, bytes, Mapping)):
            raise DisProtSnapshotError("disprot_consensus entries must be sequences")
        consensus[str(label)] = tuple(
            DisProtConsensusSpan(
                start=_normalize_int(span.get("start"), "start") or 0,
                end=_normalize_int(span.get("end"), "end") or 0,
                type=_normalize_text(span.get("type"), "type"),
            )
            for span in spans
            if isinstance(span, Mapping)
        )
    return consensus


def _build_gene_labels(value: Any) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if value in (None, ""):
        return (), (), ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, Mapping)):
        raise DisProtSnapshotError("genes must be a sequence")
    gene_names: list[str] = []
    gene_synonyms: list[str] = []
    orf_names: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = _first_text(item, "name.value")
        if name:
            gene_names.append(name)
        for synonym in _coerce_sequence(item.get("synonyms")):
            if isinstance(synonym, Mapping):
                synonym_text = _first_text(synonym, "value")
            else:
                synonym_text = str(synonym or "").strip()
            if synonym_text:
                gene_synonyms.append(synonym_text)
        for orf_name in _coerce_sequence(item.get("orfNames")):
            if isinstance(orf_name, Mapping):
                orf_text = _first_text(orf_name, "value")
            else:
                orf_text = str(orf_name or "").strip()
            if orf_text:
                orf_names.append(orf_text)
        for oln_name in _coerce_sequence(item.get("olnNames")):
            if isinstance(oln_name, Mapping):
                oln_text = _first_text(oln_name, "value")
            else:
                oln_text = str(oln_name or "").strip()
            if oln_text:
                gene_names.append(oln_text)
    return (
        _coerce_text_tuple(gene_names),
        _coerce_text_tuple(gene_synonyms),
        _coerce_text_tuple(orf_names),
    )


def _ready_result(
    manifest: DisProtSnapshotManifest,
    manifest_payload: dict[str, Any],
    provenance: dict[str, Any],
    records: Sequence[DisProtProteinRecord],
    *,
    request_url: str,
    api_version: str,
) -> DisProtSnapshotResult:
    snapshot = DisProtSnapshot(
        source_release=manifest.source_release.to_dict(),
        provenance={
            **provenance,
            "record_count": len(records),
            "region_count": sum(len(record.regions) for record in records),
            "requested_accessions": list(manifest.accessions),
            "request_url": request_url,
            "api_version": api_version,
        },
        records=tuple(records),
    )
    return DisProtSnapshotResult(
        status="ready",
        manifest=manifest_payload,
        contract=manifest,
        snapshot=snapshot,
        provenance=snapshot.provenance,
    )


def _unavailable_result(
    manifest: DisProtSnapshotManifest,
    manifest_payload: dict[str, Any],
    provenance: dict[str, Any],
    *,
    unavailable_reason: str,
    missing_accessions: tuple[str, ...] = (),
) -> DisProtSnapshotResult:
    return DisProtSnapshotResult(
        status="unavailable",
        manifest=manifest_payload,
        contract=manifest,
        unavailable_reason=unavailable_reason,
        missing_accessions=missing_accessions,
        provenance={
            **provenance,
            "unavailable_reason": unavailable_reason,
            "missing_accessions": list(missing_accessions),
        },
    )


def _build_manifest_provenance(
    manifest: DisProtSnapshotManifest,
    *,
    acquired_at: str | None,
) -> dict[str, Any]:
    provenance = dict(manifest.provenance)
    provenance.update(
        {
            "manifest_id": manifest.manifest_id,
            "source_release": manifest.source_release.to_dict(),
            "source_locator": manifest.source_release.source_locator,
            "retrieval_mode": manifest.source_release.retrieval_mode,
            "accessions": list(manifest.accessions),
            "api_base_url": manifest.api_base_url,
            "source_name": manifest.source_release.source_name,
            "release_version": manifest.source_release.release_version,
            "release_date": manifest.source_release.release_date,
            "acquired_at": acquired_at or datetime.now(UTC).isoformat(),
        }
    )
    return provenance


__all__ = [
    "DEFAULT_DISPROT_API_BASE_URL",
    "DEFAULT_SMOKE_ACCESSION",
    "DISPROT_SMOKE_ENV_VAR",
    "DisProtConsensusSpan",
    "DisProtProteinRecord",
    "DisProtRegionEvidence",
    "DisProtSnapshot",
    "DisProtSnapshotError",
    "DisProtSnapshotManifest",
    "DisProtSnapshotProvenance",
    "DisProtSnapshotResult",
    "DisProtSnapshotStatus",
    "SnapshotSmokeDisabledError",
    "acquire_disprot_snapshot",
    "build_disprot_snapshot_manifest",
    "run_live_smoke_snapshot",
]
