from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)

ALPHAFOLD_SOURCE_NAMES = {
    "alphafold",
    "alphafold db",
    "alphafold protein structure database",
}
ALPHAFOLD_API_BASE_URL = "https://alphafold.ebi.ac.uk/api"
ALPHAFOLD_DOWNLOAD_BASE_URL = "https://alphafold.ebi.ac.uk/download"
ALPHAFOLD_OPENAPI_URL = "https://alphafold.ebi.ac.uk/api/openapi.json"
ALPHAFOLD_SMOKE_ENV_VAR = "PROTEOSPHERE_ALPHAFOLD_SMOKE"
DEFAULT_SMOKE_QUALIFIER = "P69905"
SUPPORTED_ASSET_TYPES = (
    "bcif",
    "cif",
    "pdb",
    "msa",
    "plddt_doc",
    "pae_doc",
    "pae_image",
)


class AlphaFoldSnapshotError(ValueError):
    """Raised when an AlphaFold snapshot manifest or payload is invalid."""


class SnapshotSmokeDisabledError(RuntimeError):
    """Raised when the guarded live smoke path is called without opt-in."""


class AlphaFoldSnapshotStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


class AlphaFoldBlockerCode(StrEnum):
    MANIFEST_INVALID = "manifest_invalid"
    NETWORK = "network"
    PARSE = "parse"
    MISSING_ASSET_URL = "missing_asset_url"
    RUNTIME = "runtime"
    SMOKE_DISABLED = "smoke_disabled"


def _normalize_text(value: object | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AlphaFoldSnapshotError(f"{field_name} must be a non-empty string")
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
    raise AlphaFoldSnapshotError(f"could not normalize boolean value: {value!r}")


def _normalize_int(value: object | None, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise AlphaFoldSnapshotError(f"{field_name} must be an integer")
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise AlphaFoldSnapshotError(f"{field_name} must be an integer") from exc


def _normalize_float(value: object | None, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise AlphaFoldSnapshotError(f"{field_name} must be numeric") from exc


def _coerce_sequence(values: object | None) -> tuple[object | None, ...]:
    if values in (None, ""):
        return ()
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes, Mapping)):
        return tuple(values)
    return (values,)


def _normalize_optional_ints(values: object | None) -> tuple[int, ...]:
    items = _coerce_sequence(values)
    if not items:
        return ()
    normalized: list[int] = []
    seen: set[int] = set()
    for item in items:
        value = _normalize_int(item, "allVersions")
        if value is None or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _normalize_strings(values: object | None, *, upper: bool = False) -> tuple[str, ...]:
    items = _coerce_sequence(values)
    if not items:
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in items:
        text = _normalize_optional_text(raw_value)
        if text is None:
            continue
        text = text.upper() if upper else text
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _normalize_ints(values: object | None) -> tuple[int, ...]:
    items = _coerce_sequence(values)
    if not items:
        return ()
    normalized: list[int] = []
    seen: set[int] = set()
    for raw_value in items:
        if raw_value in (None, ""):
            continue
        value = _normalize_int(raw_value, "tax_id")
        if value is None or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _normalize_optional_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    return _normalize_bool(value)


def _normalize_asset_url_map(values: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise AlphaFoldSnapshotError("asset_urls must be a mapping")
    normalized: dict[str, str] = {}
    for key, value in values.items():
        text = _normalize_optional_text(value)
        if text is not None:
            normalized[str(key).strip().casefold()] = text
    return normalized


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


def _source_release_snapshot_fingerprint(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _first_text(mapping: Mapping[str, Any], *paths: str, default: str = "") -> str:
    value = _lookup(mapping, *paths)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _normalize_source_release(
    value: SourceReleaseManifest | Mapping[str, Any] | None,
) -> SourceReleaseManifest:
    if value is None:
        raise AlphaFoldSnapshotError("source_release is required")
    if isinstance(value, SourceReleaseManifest):
        manifest = value
    elif isinstance(value, Mapping):
        manifest = validate_source_release_manifest_payload(dict(value))
    else:
        raise AlphaFoldSnapshotError("source_release must be a SourceReleaseManifest or mapping")

    normalized_source = manifest.source_name.strip().casefold()
    if normalized_source not in ALPHAFOLD_SOURCE_NAMES:
        raise AlphaFoldSnapshotError(
            "source_release.source_name must describe AlphaFold DB"
        )
    retrieval_mode = manifest.retrieval_mode.casefold()
    if retrieval_mode not in {"api", "download"}:
        raise AlphaFoldSnapshotError(
            "AlphaFold acquisition only supports api or download retrieval modes"
        )
    return manifest


def _normalize_asset_types(values: object | None) -> tuple[str, ...]:
    items = _coerce_sequence(values)
    if not items:
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in items:
        text = _normalize_optional_text(raw_value)
        if text is None:
            continue
        asset_type = text.casefold()
        if asset_type in seen:
            continue
        seen.add(asset_type)
        normalized.append(asset_type)
    unsupported = sorted(set(normalized) - set(SUPPORTED_ASSET_TYPES))
    if unsupported:
        raise AlphaFoldSnapshotError(
            "unsupported coordinate asset type(s): " + ", ".join(unsupported)
        )
    return tuple(normalized)


def _coerce_items(payload: Any) -> tuple[dict[str, Any], ...]:
    if payload is None:
        return ()
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, tuple):
        items = list(payload)
    elif isinstance(payload, Mapping):
        for key in ("prediction", "complex", "entries", "items", "results", "data"):
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
        raise AlphaFoldSnapshotError("AlphaFold API payload must be a mapping or list")

    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise AlphaFoldSnapshotError("AlphaFold API items must be mappings")
        normalized.append(dict(item))
    return tuple(normalized)


def _read_payload(payload: bytes, content_kind: str) -> Any:
    if content_kind == "bytes":
        return payload
    text = payload.decode("utf-8")
    if content_kind == "text":
        return text
    return json.loads(text)


@dataclass(frozen=True, slots=True)
class AlphaFoldSnapshotManifest:
    """Pinned acquisition contract for AlphaFold DB predicted structure snapshots."""

    source_release: SourceReleaseManifest | Mapping[str, Any]
    qualifiers: tuple[str, ...]
    include_complexes: bool = False
    include_annotations: bool = False
    annotation_type: str = "MUTAGEN"
    coordinate_asset_types: tuple[str, ...] = ()
    api_base_url: str = ALPHAFOLD_API_BASE_URL
    download_base_url: str = ALPHAFOLD_DOWNLOAD_BASE_URL
    provenance: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        source_release = _normalize_source_release(self.source_release)
        qualifiers = tuple(
            dict.fromkeys(
                _normalize_text(qualifier, "qualifier").upper()
                for qualifier in _coerce_sequence(self.qualifiers)
            )
        )
        if not qualifiers:
            raise AlphaFoldSnapshotError("qualifiers must not be empty")

        object.__setattr__(self, "source_release", source_release)
        object.__setattr__(self, "qualifiers", qualifiers)
        object.__setattr__(self, "include_complexes", _normalize_bool(self.include_complexes))
        object.__setattr__(self, "include_annotations", _normalize_bool(self.include_annotations))
        object.__setattr__(
            self,
            "annotation_type",
            _normalize_text(self.annotation_type, "annotation_type"),
        )
        object.__setattr__(
            self,
            "coordinate_asset_types",
            _normalize_asset_types(self.coordinate_asset_types),
        )
        object.__setattr__(self, "api_base_url", _normalize_text(self.api_base_url, "api_base_url"))
        object.__setattr__(
            self,
            "download_base_url",
            _normalize_text(self.download_base_url, "download_base_url"),
        )
        if not isinstance(self.provenance, Mapping):
            raise AlphaFoldSnapshotError("provenance must be a mapping")
        if not isinstance(self.metadata, Mapping):
            raise AlphaFoldSnapshotError("metadata must be a mapping")
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
            "qualifiers": list(self.qualifiers),
            "include_complexes": self.include_complexes,
            "include_annotations": self.include_annotations,
            "annotation_type": self.annotation_type,
            "coordinate_asset_types": list(self.coordinate_asset_types),
            "api_base_url": self.api_base_url,
            "download_base_url": self.download_base_url,
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AlphaFoldSnapshotManifest:
        if not isinstance(payload, Mapping):
            raise AlphaFoldSnapshotError("manifest must be a mapping")
        source_release_payload = payload.get("source_release")
        if source_release_payload is None:
            source_release_payload = {
                "source_name": _first_text(
                    payload,
                    "source_name",
                    "source",
                    default="AlphaFold DB",
                ),
                "release_version": payload.get("release_version")
                or payload.get("release")
                or payload.get("version"),
                "release_date": payload.get("release_date") or payload.get("date"),
                "retrieval_mode": payload.get("retrieval_mode") or payload.get("mode") or "api",
                "source_locator": payload.get("source_locator")
                or payload.get("source_url")
                or ALPHAFOLD_OPENAPI_URL,
                "local_artifact_refs": payload.get("local_artifact_refs")
                or payload.get("artifact_refs")
                or (),
                "provenance": payload.get("source_provenance") or payload.get("provenance") or (),
                "reproducibility_metadata": payload.get("reproducibility_metadata")
                or payload.get("reproducibility")
                or payload.get("metadata")
                or (),
            }

        qualifiers = (
            _coerce_sequence(
                payload.get("qualifiers")
                or payload.get("accessions")
                or payload.get("model_ids")
                or payload.get("entries")
                or ()
            )
        )
        coordinate_asset_types = (
            _coerce_sequence(
                payload.get("coordinate_asset_types")
                or payload.get("asset_types")
                or payload.get("assets")
                or ()
            )
        )
        metadata = payload.get("metadata") or {}
        if not metadata and payload.get("notes") is not None:
            metadata = {"notes": payload.get("notes")}

        return cls(
            source_release=source_release_payload,
            qualifiers=tuple(qualifiers),
            include_complexes=_normalize_bool(payload.get("include_complexes", False)),
            include_annotations=_normalize_bool(payload.get("include_annotations", False)),
            annotation_type=str(payload.get("annotation_type") or "MUTAGEN"),
            coordinate_asset_types=tuple(coordinate_asset_types),
            api_base_url=str(payload.get("api_base_url") or ALPHAFOLD_API_BASE_URL),
            download_base_url=str(payload.get("download_base_url") or ALPHAFOLD_DOWNLOAD_BASE_URL),
            provenance=payload.get("provenance") or {},
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class AlphaFoldConfidenceSummary:
    global_metric_value: float | None = None
    confidence_fractions: dict[str, float] = field(default_factory=dict)
    complex_metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_metric_value": self.global_metric_value,
            "confidence_fractions": dict(self.confidence_fractions),
            "complex_metrics": dict(self.complex_metrics),
        }


@dataclass(frozen=True, slots=True)
class AlphaFoldComplexMember:
    identifier: str
    identifier_type: str
    stoichiometry: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", _normalize_text(self.identifier, "identifier"))
        object.__setattr__(
            self,
            "identifier_type",
            _normalize_text(self.identifier_type, "identifier_type"),
        )
        if self.stoichiometry < 1:
            raise AlphaFoldSnapshotError("stoichiometry must be >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "identifier_type": self.identifier_type,
            "stoichiometry": self.stoichiometry,
        }


@dataclass(frozen=True, slots=True)
class AlphaFoldProvenance:
    source_release: SourceReleaseManifest
    manifest_id: str
    qualifier: str
    endpoint: str
    fetched_at: str
    source_locator: str | None = None
    retrieval_mode: str = ""
    provider_id: str | None = None
    tool_used: str | None = None
    include_complexes: bool = False
    include_annotations: bool = False
    annotation_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": self.source_release.to_dict(),
            "manifest_id": self.manifest_id,
            "qualifier": self.qualifier,
            "endpoint": self.endpoint,
            "fetched_at": self.fetched_at,
            "source_locator": self.source_locator,
            "retrieval_mode": self.retrieval_mode,
            "provider_id": self.provider_id,
            "tool_used": self.tool_used,
            "include_complexes": self.include_complexes,
            "include_annotations": self.include_annotations,
            "annotation_type": self.annotation_type,
        }


@dataclass(frozen=True, slots=True)
class AlphaFoldSnapshotRecord:
    structure_kind: Literal["prediction", "complex"]
    qualifier: str
    model_entity_id: str
    provenance: AlphaFoldProvenance
    confidence: AlphaFoldConfidenceSummary
    raw_summary: Mapping[str, Any] = field(default_factory=dict)
    entry_id: str | None = None
    sequence_checksum: str | None = None
    latest_version: int | None = None
    all_versions: tuple[int, ...] = ()
    uniprot_accessions: tuple[str, ...] = ()
    uniprot_ids: tuple[str, ...] = ()
    entity_type: str | None = None
    provider_id: str | None = None
    tool_used: str | None = None
    is_uniprot: bool | None = None
    is_uniprot_reviewed: bool | None = None
    is_uniprot_reference_proteome: bool | None = None
    is_isoform: bool | None = None
    is_amdata: bool | None = None
    gene: tuple[str, ...] = ()
    tax_id: tuple[int, ...] = ()
    organism_scientific_name: tuple[str, ...] = ()
    sequence_start: int | None = None
    sequence_end: int | None = None
    sequence: str | None = None
    uniprot_start: int | None = None
    uniprot_end: int | None = None
    uniprot_sequence: str | None = None
    complex_name: str | None = None
    assembly_type: str | None = None
    oligomeric_state: str | None = None
    complex_composition: tuple[AlphaFoldComplexMember, ...] = ()
    asset_urls: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "qualifier", _normalize_text(self.qualifier, "qualifier"))
        object.__setattr__(
            self,
            "model_entity_id",
            _normalize_text(self.model_entity_id, "model_entity_id"),
        )
        object.__setattr__(self, "raw_summary", dict(self.raw_summary))
        object.__setattr__(self, "all_versions", _normalize_optional_ints(self.all_versions))
        object.__setattr__(
            self,
            "uniprot_accessions",
            _normalize_strings(self.uniprot_accessions, upper=True),
        )
        object.__setattr__(self, "uniprot_ids", _normalize_strings(self.uniprot_ids, upper=True))
        object.__setattr__(self, "gene", _normalize_strings(self.gene))
        object.__setattr__(self, "tax_id", _normalize_ints(self.tax_id))
        object.__setattr__(
            self,
            "organism_scientific_name",
            _normalize_strings(self.organism_scientific_name),
        )
        object.__setattr__(self, "asset_urls", _normalize_asset_url_map(self.asset_urls))
        object.__setattr__(self, "complex_composition", tuple(self.complex_composition))
        if self.structure_kind not in {"prediction", "complex"}:
            raise AlphaFoldSnapshotError("structure_kind must be prediction or complex")

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure_kind": self.structure_kind,
            "qualifier": self.qualifier,
            "model_entity_id": self.model_entity_id,
            "provenance": self.provenance.to_dict(),
            "confidence": self.confidence.to_dict(),
            "raw_summary": dict(self.raw_summary),
            "entry_id": self.entry_id,
            "sequence_checksum": self.sequence_checksum,
            "latest_version": self.latest_version,
            "all_versions": list(self.all_versions),
            "uniprot_accessions": list(self.uniprot_accessions),
            "uniprot_ids": list(self.uniprot_ids),
            "entity_type": self.entity_type,
            "provider_id": self.provider_id,
            "tool_used": self.tool_used,
            "is_uniprot": self.is_uniprot,
            "is_uniprot_reviewed": self.is_uniprot_reviewed,
            "is_uniprot_reference_proteome": self.is_uniprot_reference_proteome,
            "is_isoform": self.is_isoform,
            "is_amdata": self.is_amdata,
            "gene": list(self.gene),
            "tax_id": list(self.tax_id),
            "organism_scientific_name": list(self.organism_scientific_name),
            "sequence_start": self.sequence_start,
            "sequence_end": self.sequence_end,
            "sequence": self.sequence,
            "uniprot_start": self.uniprot_start,
            "uniprot_end": self.uniprot_end,
            "uniprot_sequence": self.uniprot_sequence,
            "complex_name": self.complex_name,
            "assembly_type": self.assembly_type,
            "oligomeric_state": self.oligomeric_state,
            "complex_composition": [member.to_dict() for member in self.complex_composition],
            "asset_urls": dict(self.asset_urls),
        }


@dataclass(frozen=True, slots=True)
class AlphaFoldSnapshotAsset:
    qualifier: str
    asset_type: str
    url: str
    content_kind: str
    payload: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "qualifier", _normalize_text(self.qualifier, "qualifier"))
        object.__setattr__(
            self,
            "asset_type",
            _normalize_text(self.asset_type, "asset_type").casefold(),
        )
        object.__setattr__(self, "url", _normalize_text(self.url, "url"))
        object.__setattr__(self, "content_kind", _normalize_text(self.content_kind, "content_kind"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "qualifier": self.qualifier,
            "asset_type": self.asset_type,
            "url": self.url,
            "content_kind": self.content_kind,
        }


@dataclass(frozen=True, slots=True)
class AlphaFoldSnapshotResult:
    status: AlphaFoldSnapshotStatus
    manifest: AlphaFoldSnapshotManifest
    provenance: Mapping[str, Any]
    records: tuple[AlphaFoldSnapshotRecord, ...] = ()
    assets: tuple[AlphaFoldSnapshotAsset, ...] = ()
    blocker_reason: str = ""
    unavailable_reason: str = ""
    missing_fields: tuple[str, ...] = ()
    invalid_qualifiers: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status == AlphaFoldSnapshotStatus.READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "manifest": self.manifest.to_dict(),
            "provenance": dict(self.provenance),
            "records": [record.to_dict() for record in self.records],
            "assets": [asset.to_dict() for asset in self.assets],
            "blocker_reason": self.blocker_reason,
            "unavailable_reason": self.unavailable_reason,
            "missing_fields": list(self.missing_fields),
            "invalid_qualifiers": list(self.invalid_qualifiers),
            "succeeded": self.succeeded,
        }


def build_alphafold_snapshot_manifest(
    qualifiers: Sequence[str],
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    release_version: str | None = None,
    release_date: str | None = None,
    retrieval_mode: str = "api",
    source_locator: str = ALPHAFOLD_OPENAPI_URL,
    include_complexes: bool = False,
    include_annotations: bool = False,
    annotation_type: str = "MUTAGEN",
    coordinate_asset_types: Sequence[str] = (),
    api_base_url: str = ALPHAFOLD_API_BASE_URL,
    download_base_url: str = ALPHAFOLD_DOWNLOAD_BASE_URL,
    provenance: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AlphaFoldSnapshotManifest:
    if source_release is None:
        source_release = SourceReleaseManifest(
            source_name="AlphaFold DB",
            release_version=release_version or "smoke",
            release_date=release_date,
            retrieval_mode=retrieval_mode,
            source_locator=source_locator,
        )
    return AlphaFoldSnapshotManifest(
        source_release=source_release,
        qualifiers=tuple(qualifiers),
        include_complexes=include_complexes,
        include_annotations=include_annotations,
        annotation_type=annotation_type,
        coordinate_asset_types=tuple(coordinate_asset_types),
        api_base_url=api_base_url,
        download_base_url=download_base_url,
        provenance={} if provenance is None else provenance,
        metadata={} if metadata is None else metadata,
    )


def build_accession_snapshot_manifest(
    accessions: Sequence[str],
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    include_complexes: bool = False,
    include_annotations: bool = False,
    annotation_type: str = "MUTAGEN",
    coordinate_asset_types: Sequence[str] = (),
    api_base_url: str = ALPHAFOLD_API_BASE_URL,
    download_base_url: str = ALPHAFOLD_DOWNLOAD_BASE_URL,
    provenance: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AlphaFoldSnapshotManifest:
    metadata_payload = dict(metadata or {})
    metadata_payload.setdefault(
        "accessions",
        [
            _normalize_text(accession, "accessions").upper()
            for accession in accessions
        ],
    )
    return build_alphafold_snapshot_manifest(
        accessions,
        source_release=source_release,
        include_complexes=include_complexes,
        include_annotations=include_annotations,
        annotation_type=annotation_type,
        coordinate_asset_types=coordinate_asset_types,
        api_base_url=api_base_url,
        download_base_url=download_base_url,
        provenance=provenance,
        metadata=metadata_payload,
    )


def acquire_alphafold_snapshot(
    manifest: AlphaFoldSnapshotManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    asset_opener: Callable[..., Any] | None = None,
) -> AlphaFoldSnapshotResult:
    normalized_manifest, blocked_result = _normalize_manifest(manifest)
    if blocked_result is not None:
        return blocked_result

    assert normalized_manifest is not None
    resolved_opener = opener or urlopen
    resolved_asset_opener = asset_opener or resolved_opener
    provenance = _build_manifest_provenance(normalized_manifest)
    records: list[AlphaFoldSnapshotRecord] = []
    assets: list[AlphaFoldSnapshotAsset] = []

    for qualifier in normalized_manifest.qualifiers:
        try:
            prediction_payload = _request_json(
                f"{normalized_manifest.api_base_url}/prediction/{qualifier}",
                opener=resolved_opener,
            )
            prediction_items = _coerce_items(prediction_payload)
            if not prediction_items:
                continue

            for item in prediction_items:
                record = _build_prediction_record(
                    qualifier,
                    item,
                    normalized_manifest,
                    provenance,
                    endpoint="prediction",
                )
                records.append(record)
                if normalized_manifest.coordinate_asset_types:
                    assets.extend(
                        _materialize_assets(
                            qualifier,
                            item,
                            normalized_manifest,
                            opener=resolved_asset_opener,
                        )
                    )

            if normalized_manifest.include_complexes:
                complex_payload = _request_json(
                    f"{normalized_manifest.api_base_url}/complex/{qualifier}",
                    opener=resolved_opener,
                )
                for item in _coerce_items(complex_payload):
                    records.append(
                        _build_complex_record(
                            qualifier,
                            item,
                            normalized_manifest,
                            provenance,
                            endpoint="complex",
                        )
                    )

            if normalized_manifest.include_annotations:
                accession = _first_prediction_accession(prediction_items[0])
                annotation_url = _annotation_url(
                    normalized_manifest.api_base_url,
                    accession,
                    normalized_manifest.annotation_type,
                )
                if annotation_url is None:
                    raise AlphaFoldSnapshotError(
                        "include_annotations requires a UniProt accession in the prediction payload"
                    )
                assets.append(
                    _fetch_asset(
                        qualifier,
                        "annotation",
                        annotation_url,
                        opener=resolved_asset_opener,
                        content_kind="json",
                    )
                )
        except (HTTPError, URLError, OSError) as exc:
            return AlphaFoldSnapshotResult(
                status=AlphaFoldSnapshotStatus.BLOCKED,
                manifest=normalized_manifest,
                provenance=provenance,
                records=tuple(records),
                assets=tuple(assets),
                blocker_reason=f"AlphaFold request failed: {exc}",
                invalid_qualifiers=(qualifier,),
            )
        except json.JSONDecodeError as exc:
            return AlphaFoldSnapshotResult(
                status=AlphaFoldSnapshotStatus.BLOCKED,
                manifest=normalized_manifest,
                provenance=provenance,
                records=tuple(records),
                assets=tuple(assets),
                blocker_reason=f"AlphaFold response could not be parsed: {exc}",
                invalid_qualifiers=(qualifier,),
            )
        except AlphaFoldSnapshotError as exc:
            return AlphaFoldSnapshotResult(
                status=AlphaFoldSnapshotStatus.BLOCKED,
                manifest=normalized_manifest,
                provenance=provenance,
                records=tuple(records),
                assets=tuple(assets),
                blocker_reason=str(exc),
                invalid_qualifiers=(qualifier,),
            )
        except Exception as exc:  # pragma: no cover - defensive runtime blocker
            return AlphaFoldSnapshotResult(
                status=AlphaFoldSnapshotStatus.BLOCKED,
                manifest=normalized_manifest,
                provenance=provenance,
                records=tuple(records),
                assets=tuple(assets),
                blocker_reason=f"unexpected runtime failure: {type(exc).__name__}: {exc}",
                invalid_qualifiers=(qualifier,),
            )

    if not records:
        return AlphaFoldSnapshotResult(
            status=AlphaFoldSnapshotStatus.UNAVAILABLE,
            manifest=normalized_manifest,
            provenance=provenance,
            unavailable_reason="AlphaFold API returned no prediction or complex records",
        )

    return AlphaFoldSnapshotResult(
        status=AlphaFoldSnapshotStatus.READY,
        manifest=normalized_manifest,
        provenance=provenance,
        records=tuple(records),
        assets=tuple(assets),
    )


def run_live_smoke_snapshot(
    qualifier: str = DEFAULT_SMOKE_QUALIFIER,
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    opener: Callable[..., Any] | None = None,
    asset_opener: Callable[..., Any] | None = None,
) -> AlphaFoldSnapshotResult:
    if os.getenv(ALPHAFOLD_SMOKE_ENV_VAR) != "1":
        raise SnapshotSmokeDisabledError(
            f"set {ALPHAFOLD_SMOKE_ENV_VAR}=1 to run the AlphaFold smoke path"
        )

    manifest = build_alphafold_snapshot_manifest(
        [qualifier],
        source_release=source_release,
        release_version="smoke",
        retrieval_mode="api",
        include_complexes=False,
        include_annotations=False,
    )
    return acquire_alphafold_snapshot(
        manifest,
        opener=opener,
        asset_opener=asset_opener,
    )


def _normalize_manifest(
    manifest: AlphaFoldSnapshotManifest | Mapping[str, Any],
) -> tuple[AlphaFoldSnapshotManifest | None, AlphaFoldSnapshotResult | None]:
    try:
        if isinstance(manifest, AlphaFoldSnapshotManifest):
            return manifest, None
        if not isinstance(manifest, Mapping):
            raise AlphaFoldSnapshotError("manifest must be a snapshot manifest or mapping")
        return AlphaFoldSnapshotManifest.from_mapping(manifest), None
    except (AlphaFoldSnapshotError, ValueError, TypeError) as exc:
        fallback_manifest = _blocked_manifest_from_invalid_input(manifest)
        return None, AlphaFoldSnapshotResult(
            status=AlphaFoldSnapshotStatus.BLOCKED,
            manifest=fallback_manifest,
            provenance={},
            blocker_reason=str(exc),
        )


def _blocked_manifest_from_invalid_input(
    manifest: AlphaFoldSnapshotManifest | Mapping[str, Any],
) -> AlphaFoldSnapshotManifest:
    if isinstance(manifest, AlphaFoldSnapshotManifest):
        return manifest

    qualifiers = _coerce_sequence(
        _lookup(
            manifest,
            "qualifiers",
            "accessions",
            "model_ids",
            "entries",
            "qualifier",
            "accession",
            "model_id",
        )
        or ("<invalid-manifest>",)
    )
    source_release_source = _lookup(manifest, "source_release")
    if isinstance(source_release_source, Mapping):
        source_release_source = source_release_source
    else:
        source_release_source = manifest

    requested_retrieval_mode = _normalize_optional_text(
        _lookup(source_release_source, "retrieval_mode") or _lookup(source_release_source, "mode")
    )
    retrieval_mode = requested_retrieval_mode or "api"
    blocked_metadata = dict(_lookup(manifest, "metadata") or {})
    if retrieval_mode.casefold() not in {"api", "download"}:
        blocked_metadata["requested_invalid_retrieval_mode"] = retrieval_mode
        retrieval_mode = "api"

    source_release_payload = {
        "source_name": _first_text(
            source_release_source,
            "source_name",
            "source",
            default="AlphaFold DB",
        ),
        "release_version": _lookup(source_release_source, "release_version")
        or _lookup(source_release_source, "release")
        or _lookup(source_release_source, "version")
        or "invalid",
        "release_date": _lookup(source_release_source, "release_date")
        or _lookup(source_release_source, "date"),
        "retrieval_mode": retrieval_mode,
        "source_locator": _lookup(source_release_source, "source_locator")
        or _lookup(source_release_source, "source_url")
        or ALPHAFOLD_OPENAPI_URL,
        "local_artifact_refs": _lookup(source_release_source, "local_artifact_refs")
        or _lookup(source_release_source, "artifact_refs")
        or (),
        "provenance": _lookup(source_release_source, "source_provenance")
        or _lookup(source_release_source, "provenance")
        or (),
        "reproducibility_metadata": _lookup(source_release_source, "reproducibility_metadata")
        or _lookup(source_release_source, "reproducibility")
        or _lookup(source_release_source, "metadata")
        or (),
    }

    blocked_manifest = AlphaFoldSnapshotManifest(
        source_release=source_release_payload,
        qualifiers=tuple(qualifiers),
        include_complexes=_normalize_bool(_lookup(manifest, "include_complexes",), default=False),
        include_annotations=_normalize_bool(
            _lookup(manifest, "include_annotations"),
            default=False,
        ),
        annotation_type=str(_lookup(manifest, "annotation_type") or "MUTAGEN"),
        coordinate_asset_types=tuple(
            _coerce_sequence(_lookup(manifest, "coordinate_asset_types") or ())
        ),
        api_base_url=str(_lookup(manifest, "api_base_url") or ALPHAFOLD_API_BASE_URL),
        download_base_url=str(
            _lookup(manifest, "download_base_url") or ALPHAFOLD_DOWNLOAD_BASE_URL
        ),
        provenance=_lookup(manifest, "provenance") or {},
        metadata=blocked_metadata,
    )

    return blocked_manifest


__all__ = [
    "ALPHAFOLD_API_BASE_URL",
    "ALPHAFOLD_DOWNLOAD_BASE_URL",
    "ALPHAFOLD_OPENAPI_URL",
    "ALPHAFOLD_SMOKE_ENV_VAR",
    "DEFAULT_SMOKE_QUALIFIER",
    "AlphaFoldBlockerCode",
    "AlphaFoldConfidenceSummary",
    "AlphaFoldComplexMember",
    "AlphaFoldProvenance",
    "AlphaFoldSnapshotAsset",
    "AlphaFoldSnapshotError",
    "AlphaFoldSnapshotManifest",
    "AlphaFoldSnapshotRecord",
    "AlphaFoldSnapshotResult",
    "AlphaFoldSnapshotStatus",
    "SnapshotSmokeDisabledError",
    "acquire_alphafold_snapshot",
    "build_accession_snapshot_manifest",
    "build_alphafold_snapshot_manifest",
    "run_live_smoke_snapshot",
]


def _build_manifest_provenance(manifest: AlphaFoldSnapshotManifest) -> dict[str, Any]:
    provenance = dict(manifest.provenance)
    provenance.update(
        {
            "manifest_id": manifest.manifest_id,
            "source_release": manifest.source_release.to_dict(),
            "source_locator": manifest.source_release.source_locator,
            "retrieval_mode": manifest.source_release.retrieval_mode,
            "qualifiers": list(manifest.qualifiers),
            "include_complexes": manifest.include_complexes,
            "include_annotations": manifest.include_annotations,
            "annotation_type": manifest.annotation_type,
        }
    )
    return provenance


def _request_json(url: str, *, opener: Callable[..., Any]) -> Any:
    payload = _request_payload(url, opener=opener)
    return json.loads(payload.decode("utf-8"))


def _request_payload(url: str, *, opener: Callable[..., Any]) -> bytes:
    request = Request(url, headers={"User-Agent": "ProteoSphereV2-AlphaFoldSnapshot/0.1"})
    with opener(request, timeout=30.0) as response:
        return response.read()


def _build_prediction_record(
    qualifier: str,
    payload: Mapping[str, Any],
    manifest: AlphaFoldSnapshotManifest,
    provenance: Mapping[str, Any],
    *,
    endpoint: str,
) -> AlphaFoldSnapshotRecord:
    asset_urls = _asset_url_map(payload)
    confidence = AlphaFoldConfidenceSummary(
        global_metric_value=_normalize_float(payload.get("globalMetricValue"), "globalMetricValue"),
        confidence_fractions=_prediction_confidence_fractions(payload),
    )
    return AlphaFoldSnapshotRecord(
        structure_kind="prediction",
        qualifier=qualifier,
        model_entity_id=_first_text(payload, "modelEntityId", "entryId", "id", default=qualifier),
        provenance=_build_record_provenance(
            manifest,
            qualifier,
            provenance,
            endpoint=endpoint,
            payload=payload,
        ),
        confidence=confidence,
        raw_summary=dict(payload),
        entry_id=_first_text(payload, "entryId", default="") or None,
        sequence_checksum=_normalize_optional_text(payload.get("sequenceChecksum")),
        latest_version=_normalize_int(payload.get("latestVersion"), "latestVersion"),
        all_versions=_normalize_optional_ints(payload.get("allVersions")),
        uniprot_accessions=_normalize_strings(payload.get("uniprotAccession"), upper=True),
        uniprot_ids=_normalize_strings(payload.get("uniprotId"), upper=True),
        entity_type=_normalize_optional_text(payload.get("entityType")),
        provider_id=_normalize_optional_text(payload.get("providerId")),
        tool_used=_normalize_optional_text(payload.get("toolUsed")),
        is_uniprot=_normalize_optional_bool(payload.get("isUniProt")),
        is_uniprot_reviewed=_normalize_optional_bool(payload.get("isUniProtReviewed")),
        is_uniprot_reference_proteome=_normalize_optional_bool(
            payload.get("isUniProtReferenceProteome")
        ),
        is_isoform=_normalize_optional_bool(payload.get("isIsoform")),
        is_amdata=_normalize_optional_bool(payload.get("isAMdata")),
        gene=_normalize_strings(payload.get("gene")),
        tax_id=_normalize_ints(payload.get("taxId")),
        organism_scientific_name=_normalize_strings(payload.get("organismScientificName")),
        sequence_start=_normalize_int(payload.get("sequenceStart"), "sequenceStart"),
        sequence_end=_normalize_int(payload.get("sequenceEnd"), "sequenceEnd"),
        sequence=_normalize_optional_text(payload.get("sequence")),
        uniprot_start=_normalize_int(payload.get("uniprotStart"), "uniprotStart"),
        uniprot_end=_normalize_int(payload.get("uniprotEnd"), "uniprotEnd"),
        uniprot_sequence=_normalize_optional_text(payload.get("uniprotSequence")),
        asset_urls=asset_urls,
    )


def _build_complex_record(
    qualifier: str,
    payload: Mapping[str, Any],
    manifest: AlphaFoldSnapshotManifest,
    provenance: Mapping[str, Any],
    *,
    endpoint: str,
) -> AlphaFoldSnapshotRecord:
    asset_urls = _asset_url_map(payload)
    confidence = AlphaFoldConfidenceSummary(
        global_metric_value=_normalize_float(payload.get("globalMetricValue"), "globalMetricValue"),
        complex_metrics=_complex_confidence_metrics(payload),
    )
    return AlphaFoldSnapshotRecord(
        structure_kind="complex",
        qualifier=qualifier,
        model_entity_id=_first_text(payload, "modelEntityId", "entryId", "id", default=qualifier),
        provenance=_build_record_provenance(
            manifest,
            qualifier,
            provenance,
            endpoint=endpoint,
            payload=payload,
        ),
        confidence=confidence,
        raw_summary=dict(payload),
        entry_id=_first_text(payload, "entryId", default="") or None,
        sequence_checksum=_normalize_optional_text(payload.get("sequenceChecksum")),
        latest_version=_normalize_int(payload.get("latestVersion"), "latestVersion"),
        all_versions=_normalize_optional_ints(payload.get("allVersions")),
        uniprot_accessions=_normalize_strings(payload.get("uniprotAccession"), upper=True),
        uniprot_ids=_normalize_strings(payload.get("uniprotId"), upper=True),
        entity_type=_normalize_optional_text(payload.get("entityType")),
        provider_id=_normalize_optional_text(payload.get("providerId")),
        tool_used=_normalize_optional_text(payload.get("toolUsed")),
        is_uniprot=_normalize_optional_bool(payload.get("isUniProt")),
        is_uniprot_reviewed=_normalize_optional_bool(payload.get("isUniProtReviewed")),
        is_uniprot_reference_proteome=_normalize_optional_bool(
            payload.get("isUniProtReferenceProteome")
        ),
        is_isoform=_normalize_optional_bool(payload.get("isIsoform")),
        is_amdata=_normalize_optional_bool(payload.get("isAMdata")),
        gene=_normalize_strings(payload.get("gene")),
        tax_id=_normalize_ints(payload.get("taxId")),
        organism_scientific_name=_normalize_strings(payload.get("organismScientificName")),
        sequence_start=_normalize_int(payload.get("sequenceStart"), "sequenceStart"),
        sequence_end=_normalize_int(payload.get("sequenceEnd"), "sequenceEnd"),
        sequence=_normalize_optional_text(payload.get("sequence")),
        uniprot_start=_normalize_int(payload.get("uniprotStart"), "uniprotStart"),
        uniprot_end=_normalize_int(payload.get("uniprotEnd"), "uniprotEnd"),
        uniprot_sequence=_normalize_optional_text(payload.get("uniprotSequence")),
        complex_name=_normalize_optional_text(payload.get("complexName")),
        assembly_type=_normalize_optional_text(payload.get("assemblyType")),
        oligomeric_state=_normalize_optional_text(payload.get("oligomericState")),
        complex_composition=_complex_composition(payload.get("complexComposition")),
        asset_urls=asset_urls,
    )


def _build_record_provenance(
    manifest: AlphaFoldSnapshotManifest,
    qualifier: str,
    provenance: Mapping[str, Any],
    *,
    endpoint: str,
    payload: Mapping[str, Any],
) -> AlphaFoldProvenance:
    return AlphaFoldProvenance(
        source_release=manifest.source_release,
        manifest_id=manifest.manifest_id,
        qualifier=qualifier,
        endpoint=endpoint,
        fetched_at=_normalize_optional_text(provenance.get("fetched_at")) or "unknown",
        source_locator=manifest.source_release.source_locator,
        retrieval_mode=manifest.source_release.retrieval_mode,
        provider_id=_normalize_optional_text(payload.get("providerId")),
        tool_used=_normalize_optional_text(payload.get("toolUsed")),
        include_complexes=manifest.include_complexes,
        include_annotations=manifest.include_annotations,
        annotation_type=manifest.annotation_type if manifest.include_annotations else None,
    )


def _prediction_confidence_fractions(payload: Mapping[str, Any]) -> dict[str, float]:
    fractions: dict[str, float] = {}
    for key in (
        "fractionVeryHigh",
        "fractionConfident",
        "fractionLow",
        "fractionVeryLow",
        "fractionDisordered",
        "fractionOrdered",
    ):
        value = payload.get(key)
        if value in (None, ""):
            continue
        fractions[key] = float(value)
    return fractions


def _complex_confidence_metrics(payload: Mapping[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key in (
        "complexPredictionAccuracy_ipTM",
        "complexPredictionAccuracy_ipSAE",
        "complexPredictionAccuracy_pDockQ",
        "complexPredictionAccuracy_pDockQ2",
        "complexPredictionAccuracy_LIS",
    ):
        value = payload.get(key)
        if value in (None, ""):
            continue
        metrics[key] = float(value)
    return metrics


def _asset_url_map(payload: Mapping[str, Any]) -> dict[str, str]:
    urls: dict[str, str] = {}
    for asset_type, key in {
        "bcif": "bcifUrl",
        "cif": "cifUrl",
        "pdb": "pdbUrl",
        "msa": "msaUrl",
        "plddt_doc": "plddtDocUrl",
        "pae_doc": "paeDocUrl",
        "pae_image": "paeImageUrl",
    }.items():
        value = _normalize_optional_text(payload.get(key))
        if value is not None:
            urls[asset_type] = value
    return urls


def _complex_composition(value: Any) -> tuple[AlphaFoldComplexMember, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, Mapping)):
        raise AlphaFoldSnapshotError("complexComposition must be a sequence")
    members: list[AlphaFoldComplexMember] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise AlphaFoldSnapshotError("complexComposition items must be mappings")
        identifier = _first_text(
            item,
            "identifier",
            "uniprotAccession",
            "sequenceChecksum",
            default="",
        )
        identifier_type = _first_text(item, "identifierType", default="")
        if not identifier_type:
            if _lookup(item, "uniprotAccession") is not None:
                identifier_type = "uniprotAccession"
            elif _lookup(item, "sequenceChecksum") is not None:
                identifier_type = "sequenceChecksum"
            else:
                identifier_type = "identifier"
        stoichiometry = _normalize_int(item.get("stoichiometry"), "stoichiometry") or 1
        members.append(
            AlphaFoldComplexMember(
                identifier=identifier,
                identifier_type=identifier_type,
                stoichiometry=stoichiometry,
            )
        )
    return tuple(members)


def _annotation_url(base_url: str, accession: str | None, annotation_type: str) -> str | None:
    if accession is None:
        return None
    return f"{base_url.rstrip('/')}/annotations/{accession}.json?type={annotation_type}"


def _first_prediction_accession(payload: Mapping[str, Any]) -> str | None:
    accessions = _normalize_strings(payload.get("uniprotAccession"), upper=True)
    return accessions[0] if accessions else None


def _normalize_asset_url_map(values: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise AlphaFoldSnapshotError("asset_urls must be a mapping")
    normalized: dict[str, str] = {}
    for key, value in values.items():
        text = _normalize_optional_text(value)
        if text is not None:
            normalized[str(key).strip().casefold()] = text
    return normalized


def _materialize_assets(
    qualifier: str,
    payload: Mapping[str, Any],
    manifest: AlphaFoldSnapshotManifest,
    *,
    opener: Callable[..., Any],
) -> tuple[AlphaFoldSnapshotAsset, ...]:
    asset_urls = _asset_url_map(payload)
    assets: list[AlphaFoldSnapshotAsset] = []
    for asset_type in manifest.coordinate_asset_types:
        url = asset_urls.get(asset_type)
        if url is None:
            raise AlphaFoldSnapshotError(f"missing {asset_type} URL for {qualifier}")
        assets.append(
            _fetch_asset(
                qualifier,
                asset_type,
                url,
                opener=opener,
                content_kind=_asset_content_kind(asset_type),
            )
        )
    return tuple(assets)


def _fetch_asset(
    qualifier: str,
    asset_type: str,
    url: str,
    *,
    opener: Callable[..., Any],
    content_kind: str,
) -> AlphaFoldSnapshotAsset:
    payload = _request_payload(url, opener=opener)
    return AlphaFoldSnapshotAsset(
        qualifier=qualifier,
        asset_type=asset_type,
        url=url,
        content_kind=content_kind,
        payload=_read_payload(payload, content_kind),
    )


def _asset_content_kind(asset_type: str) -> str:
    if asset_type in {"bcif", "cif", "pdb", "msa"}:
        return "bytes"
    if asset_type in {"plddt_doc", "pae_doc"}:
        return "json"
    if asset_type == "pae_image":
        return "bytes"
    return "bytes"


def _normalize_manifest(
    manifest: AlphaFoldSnapshotManifest | Mapping[str, Any],
) -> tuple[AlphaFoldSnapshotManifest | None, AlphaFoldSnapshotResult | None]:
    try:
        if isinstance(manifest, AlphaFoldSnapshotManifest):
            return manifest, None
        if not isinstance(manifest, Mapping):
            raise AlphaFoldSnapshotError("manifest must be a snapshot manifest or mapping")
        return AlphaFoldSnapshotManifest.from_mapping(manifest), None
    except (AlphaFoldSnapshotError, ValueError, TypeError) as exc:
        fallback_manifest = _blocked_manifest_from_invalid_input(manifest)
        return None, AlphaFoldSnapshotResult(
            status=AlphaFoldSnapshotStatus.BLOCKED,
            manifest=fallback_manifest,
            provenance={},
            blocker_reason=str(exc),
        )
