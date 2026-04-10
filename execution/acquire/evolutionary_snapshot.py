from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)

SOURCE_NAME = "Evolutionary / MSA corpus"
SOURCE_FAMILY = "evolutionary/corpus"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "ProteoSphereV2-EvolutionarySnapshot/0.1"

EvolutionarySnapshotStatus = Literal["ok", "blocked", "unavailable"]
EvolutionarySnapshotAvailability = Literal["available", "blocked", "unavailable"]

_ALLOWED_SOURCE_NAMES = {
    "evolutionary / msa corpus",
    "evolutionary corpus",
    "evolutionary msa corpus",
    "msa corpus",
}


class EvolutionarySnapshotError(ValueError):
    """Raised when a corpus snapshot manifest or payload is invalid."""


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _unique_text(values: Any) -> tuple[str, ...]:
    items: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return tuple(items)


def _normalize_int(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise EvolutionarySnapshotError(f"{field_name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise EvolutionarySnapshotError(f"{field_name} must be an integer") from exc


def _normalize_float(value: Any, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise EvolutionarySnapshotError(f"{field_name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EvolutionarySnapshotError(f"{field_name} must be numeric") from exc


def _normalize_json_value(value: Any, field_name: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            _clean_text(key): _normalize_json_value(item, f"{field_name}[{key!r}]")
            for key, item in value.items()
            if _clean_text(key)
        }
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return tuple(_normalize_json_value(item, field_name) for item in value)
    raise EvolutionarySnapshotError(f"{field_name} must contain JSON-serializable values")


def _normalize_json_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise EvolutionarySnapshotError(f"{field_name} must be a mapping")
    return {
        _clean_text(key): _normalize_json_value(item, f"{field_name}[{_clean_text(key)!r}]")
        for key, item in value.items()
        if _clean_text(key)
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _normalize_source_release(
    value: SourceReleaseManifest | Mapping[str, Any],
) -> SourceReleaseManifest:
    if isinstance(value, SourceReleaseManifest):
        release = value
    elif isinstance(value, Mapping):
        release = validate_source_release_manifest_payload(dict(value))
    else:
        raise EvolutionarySnapshotError(
            "source_release must be a SourceReleaseManifest or mapping"
        )
    if release.source_name.casefold() not in _ALLOWED_SOURCE_NAMES:
        raise EvolutionarySnapshotError(
            "source_release.source_name must describe the evolutionary corpus"
        )
    return release


@dataclass(frozen=True, slots=True)
class EvolutionarySnapshotManifest:
    source_release: SourceReleaseManifest
    corpus_snapshot_id: str
    aligner_version: str
    source_layers: tuple[str, ...] = field(default_factory=tuple)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    availability: EvolutionarySnapshotAvailability = "available"
    blocker_reason: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        source_release = _normalize_source_release(self.source_release)
        corpus_snapshot_id = _clean_text(self.corpus_snapshot_id)
        aligner_version = _clean_text(self.aligner_version)
        source_layers = _unique_text(self.source_layers)
        availability = _clean_text(self.availability).lower()
        blocker_reason = _clean_text(self.blocker_reason)
        notes = _unique_text(self.notes)

        if not corpus_snapshot_id:
            raise EvolutionarySnapshotError("corpus_snapshot_id must not be empty")
        if not aligner_version:
            raise EvolutionarySnapshotError("aligner_version must not be empty")
        if availability not in {"available", "blocked", "unavailable"}:
            raise EvolutionarySnapshotError(
                "availability must be one of: available, blocked, unavailable"
            )
        if availability == "available" and not (
            source_release.source_locator or source_release.local_artifact_refs
        ):
            raise EvolutionarySnapshotError(
                "source_release must define a source locator or local artifact reference"
            )

        object.__setattr__(self, "source_release", source_release)
        object.__setattr__(self, "corpus_snapshot_id", corpus_snapshot_id)
        object.__setattr__(self, "aligner_version", aligner_version)
        object.__setattr__(self, "source_layers", source_layers)
        object.__setattr__(
            self,
            "parameters",
            _normalize_json_mapping(self.parameters, "parameters"),
        )
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "blocker_reason", blocker_reason)
        object.__setattr__(self, "notes", notes)

    @property
    def manifest_id(self) -> str:
        return (
            f"{self.source_release.manifest_id}:"
            f"{self.corpus_snapshot_id}:{self.aligner_version}"
        )

    @property
    def source_locator(self) -> str | None:
        return self.source_release.source_locator

    @property
    def local_artifact_refs(self) -> tuple[str, ...]:
        return self.source_release.local_artifact_refs

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "source_release": self.source_release.to_dict(),
            "corpus_snapshot_id": self.corpus_snapshot_id,
            "aligner_version": self.aligner_version,
            "source_layers": list(self.source_layers),
            "parameters": _json_ready(dict(self.parameters)),
            "availability": self.availability,
            "blocker_reason": self.blocker_reason,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class EvolutionarySnapshotRecord:
    accession: str
    sequence_version: str | None = None
    sequence_hash: str | None = None
    sequence_length: int | None = None
    taxon_id: int | None = None
    uniref_cluster_ids: tuple[str, ...] = field(default_factory=tuple)
    orthogroup_ids: tuple[str, ...] = field(default_factory=tuple)
    alignment_depth: int | None = None
    alignment_coverage: float | None = None
    neff: float | None = None
    gap_fraction: float | None = None
    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    lazy_materialization_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        accession = _clean_text(self.accession)
        if not accession:
            raise EvolutionarySnapshotError("accession must not be empty")
        object.__setattr__(self, "accession", accession.upper())
        object.__setattr__(self, "sequence_version", _optional_text(self.sequence_version))
        object.__setattr__(self, "sequence_hash", _optional_text(self.sequence_hash))
        object.__setattr__(
            self,
            "sequence_length",
            _normalize_int(self.sequence_length, "sequence_length"),
        )
        object.__setattr__(self, "taxon_id", _normalize_int(self.taxon_id, "taxon_id"))
        object.__setattr__(self, "uniref_cluster_ids", _unique_text(self.uniref_cluster_ids))
        object.__setattr__(self, "orthogroup_ids", _unique_text(self.orthogroup_ids))
        object.__setattr__(
            self,
            "alignment_depth",
            _normalize_int(self.alignment_depth, "alignment_depth"),
        )
        object.__setattr__(
            self,
            "alignment_coverage",
            _normalize_float(self.alignment_coverage, "alignment_coverage"),
        )
        object.__setattr__(self, "neff", _normalize_float(self.neff, "neff"))
        object.__setattr__(
            self,
            "gap_fraction",
            _normalize_float(self.gap_fraction, "gap_fraction"),
        )
        object.__setattr__(self, "quality_flags", _unique_text(self.quality_flags))
        object.__setattr__(self, "source_refs", _unique_text(self.source_refs))
        object.__setattr__(
            self,
            "lazy_materialization_refs",
            _unique_text(self.lazy_materialization_refs),
        )
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "sequence_version": self.sequence_version,
            "sequence_hash": self.sequence_hash,
            "sequence_length": self.sequence_length,
            "taxon_id": self.taxon_id,
            "uniref_cluster_ids": list(self.uniref_cluster_ids),
            "orthogroup_ids": list(self.orthogroup_ids),
            "alignment_depth": self.alignment_depth,
            "alignment_coverage": self.alignment_coverage,
            "neff": self.neff,
            "gap_fraction": self.gap_fraction,
            "quality_flags": list(self.quality_flags),
            "source_refs": list(self.source_refs),
            "lazy_materialization_refs": list(self.lazy_materialization_refs),
            "metadata": _json_ready(dict(self.metadata)),
        }


@dataclass(frozen=True, slots=True)
class EvolutionarySnapshotProvenance:
    source: Literal["Evolutionary / MSA corpus"] = SOURCE_NAME
    source_family: str = SOURCE_FAMILY
    corpus_snapshot_id: str = ""
    manifest_id: str = ""
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = ""
    source_locator: str = ""
    source_layers: tuple[str, ...] = field(default_factory=tuple)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    raw_payload_sha256: str = ""
    byte_count: int = 0
    record_count: int = 0
    acquired_on: str = ""
    availability: EvolutionarySnapshotAvailability = "available"
    blocker_reason: str = ""
    error: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_family": self.source_family,
            "corpus_snapshot_id": self.corpus_snapshot_id,
            "manifest_id": self.manifest_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "source_layers": list(self.source_layers),
            "parameters": _json_ready(dict(self.parameters)),
            "raw_payload_sha256": self.raw_payload_sha256,
            "byte_count": self.byte_count,
            "record_count": self.record_count,
            "acquired_on": self.acquired_on,
            "availability": self.availability,
            "blocker_reason": self.blocker_reason,
            "error": self.error,
            "manifest": dict(self.manifest),
        }


@dataclass(frozen=True, slots=True)
class EvolutionarySnapshot:
    source_release: dict[str, Any]
    provenance: EvolutionarySnapshotProvenance
    records: tuple[EvolutionarySnapshotRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": dict(self.source_release),
            "provenance": self.provenance.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class EvolutionarySnapshotResult:
    status: EvolutionarySnapshotStatus
    reason: str
    manifest: EvolutionarySnapshotManifest
    provenance: EvolutionarySnapshotProvenance
    snapshot: EvolutionarySnapshot | None = None
    raw_payload: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "manifest": self.manifest.to_dict(),
            "provenance": self.provenance.to_dict(),
            "snapshot": None if self.snapshot is None else self.snapshot.to_dict(),
            "raw_payload": self.raw_payload,
        }


def build_evolutionary_snapshot_manifest(
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any],
    corpus_snapshot_id: str,
    aligner_version: str,
    source_layers: Iterable[Any] = (),
    parameters: Mapping[str, Any] | None = None,
    availability: EvolutionarySnapshotAvailability = "available",
    blocker_reason: str = "",
    notes: Iterable[Any] = (),
) -> EvolutionarySnapshotManifest:
    return EvolutionarySnapshotManifest(
        source_release=_normalize_source_release(source_release),
        corpus_snapshot_id=corpus_snapshot_id,
        aligner_version=aligner_version,
        source_layers=tuple(source_layers),
        parameters=parameters or {},
        availability=availability,
        blocker_reason=blocker_reason,
        notes=tuple(notes),
    )


def acquire_evolutionary_snapshot(
    manifest: EvolutionarySnapshotManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> EvolutionarySnapshotResult:
    try:
        normalized_manifest = _coerce_manifest(manifest)
    except (EvolutionarySnapshotError, TypeError, ValueError) as exc:
        fallback_manifest = _fallback_manifest()
        fallback_provenance = _build_provenance(
            fallback_manifest,
            acquired_on=acquired_on,
        )
        return EvolutionarySnapshotResult(
            status="blocked",
            reason=str(exc),
            manifest=fallback_manifest,
            provenance=fallback_provenance,
        )

    provenance = _build_provenance(normalized_manifest, acquired_on=acquired_on)

    if normalized_manifest.availability == "blocked":
        reason = normalized_manifest.blocker_reason or "evolutionary_snapshot_blocked"
        return EvolutionarySnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
            ),
        )

    if normalized_manifest.availability == "unavailable":
        reason = normalized_manifest.blocker_reason or "evolutionary_snapshot_unavailable"
        return EvolutionarySnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                blocker_reason=reason,
            ),
        )

    try:
        payload, content_source = _load_snapshot_payload(normalized_manifest, opener=opener)
    except (HTTPError, URLError, OSError, FileNotFoundError) as exc:
        reason = "evolutionary_snapshot_payload_unavailable"
        return EvolutionarySnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
            ),
        )

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        reason = "evolutionary_snapshot_payload_not_utf8"
        return EvolutionarySnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
                content_source=content_source,
            ),
        )

    try:
        records = _parse_records(text, normalized_manifest=normalized_manifest)
    except EvolutionarySnapshotError as exc:
        reason = "evolutionary_snapshot_payload_invalid"
        return EvolutionarySnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
                content_source=content_source,
            ),
            raw_payload=text,
        )

    if not records:
        reason = "evolutionary_snapshot_no_records"
        return EvolutionarySnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                blocker_reason=reason,
                content_source=content_source,
                record_count=0,
            ),
            raw_payload=text,
        )

    raw_payload_sha256 = f"sha256:{sha256(payload).hexdigest()}"
    snapshot_provenance = _update_provenance(
        provenance,
        availability="available",
        record_count=len(records),
        content_source=content_source,
        raw_payload_sha256=raw_payload_sha256,
        byte_count=len(payload),
    )
    snapshot = EvolutionarySnapshot(
        source_release=normalized_manifest.source_release.to_dict(),
        provenance=snapshot_provenance,
        records=records,
    )
    return EvolutionarySnapshotResult(
        status="ok",
        reason="evolutionary_snapshot_acquired",
        manifest=normalized_manifest,
        provenance=snapshot_provenance,
        snapshot=snapshot,
        raw_payload=text,
    )


def _coerce_manifest(
    manifest: EvolutionarySnapshotManifest | Mapping[str, Any],
) -> EvolutionarySnapshotManifest:
    if isinstance(manifest, EvolutionarySnapshotManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise EvolutionarySnapshotError("manifest must be a mapping")

    source_release_value = manifest.get("source_release")
    if source_release_value is None:
        source_release_value = {
            "source_name": manifest.get("source_name") or manifest.get("source") or SOURCE_NAME,
            "release_version": manifest.get("release_version")
            or manifest.get("release")
            or manifest.get("version"),
            "release_date": manifest.get("release_date") or manifest.get("date"),
            "retrieval_mode": manifest.get("retrieval_mode") or manifest.get("mode") or "download",
            "source_locator": manifest.get("source_locator")
            or manifest.get("source_url")
            or manifest.get("url"),
            "local_artifact_refs": manifest.get("local_artifact_refs")
            or manifest.get("artifact_refs")
            or (),
            "provenance": manifest.get("provenance") or (),
            "reproducibility_metadata": manifest.get("reproducibility_metadata")
            or manifest.get("reproducibility")
            or manifest.get("metadata")
            or (),
        }

    return EvolutionarySnapshotManifest(
        source_release=_normalize_source_release(source_release_value),
        corpus_snapshot_id=_clean_text(
            manifest.get("corpus_snapshot_id")
            or manifest.get("snapshot_id")
            or manifest.get("corpus_snapshot")
            or manifest.get("corpus_id")
            or "",
        ),
        aligner_version=_clean_text(
            manifest.get("aligner_version")
            or manifest.get("aligner")
            or manifest.get("msa_aligner_version")
            or manifest.get("sequence_aligner_version")
            or "",
        ),
        source_layers=_unique_text(
            manifest.get("source_layers")
            or manifest.get("sources")
            or manifest.get("corpus_sources")
            or manifest.get("layers")
        ),
        parameters=manifest.get("parameters")
        or manifest.get("alignment_parameters")
        or manifest.get("mmseqs2_parameters")
        or manifest.get("metadata")
        or {},
        availability=_clean_text(
            manifest.get("availability") or manifest.get("status") or "available"
        ),
        blocker_reason=_clean_text(
            manifest.get("blocker_reason")
            or manifest.get("blocked_reason")
            or manifest.get("reason")
            or "",
        ),
        notes=_unique_text(manifest.get("notes")),
    )


def _fallback_manifest() -> EvolutionarySnapshotManifest:
    return EvolutionarySnapshotManifest(
        source_release=SourceReleaseManifest(
            source_name=SOURCE_NAME,
            release_version="blocked",
            retrieval_mode="download",
            source_locator="",
        ),
        corpus_snapshot_id="blocked",
        aligner_version="blocked",
        source_layers=("fallback",),
        availability="blocked",
        blocker_reason="manifest invalid",
    )


def _build_provenance(
    manifest: EvolutionarySnapshotManifest,
    *,
    acquired_on: str | None,
) -> EvolutionarySnapshotProvenance:
    release = manifest.source_release
    return EvolutionarySnapshotProvenance(
        corpus_snapshot_id=manifest.corpus_snapshot_id,
        manifest_id=manifest.manifest_id,
        release_version=release.release_version or "",
        release_date=release.release_date or "",
        retrieval_mode=release.retrieval_mode,
        source_locator=release.source_locator or "",
        source_layers=manifest.source_layers,
        parameters=manifest.parameters,
        acquired_on=acquired_on or datetime.now(UTC).isoformat(),
        availability=manifest.availability,
        blocker_reason=manifest.blocker_reason,
        manifest=manifest.to_dict(),
    )


def _update_provenance(
    provenance: EvolutionarySnapshotProvenance,
    *,
    availability: EvolutionarySnapshotAvailability | None = None,
    blocker_reason: str | None = None,
    error: str | None = None,
    content_source: str | None = None,
    record_count: int | None = None,
    raw_payload_sha256: str | None = None,
    byte_count: int | None = None,
) -> EvolutionarySnapshotProvenance:
    return EvolutionarySnapshotProvenance(
        source=provenance.source,
        source_family=provenance.source_family,
        corpus_snapshot_id=provenance.corpus_snapshot_id,
        manifest_id=provenance.manifest_id,
        release_version=provenance.release_version,
        release_date=provenance.release_date,
        retrieval_mode=provenance.retrieval_mode,
        source_locator=provenance.source_locator,
        source_layers=provenance.source_layers,
        parameters=provenance.parameters,
        raw_payload_sha256=provenance.raw_payload_sha256
        if raw_payload_sha256 is None
        else raw_payload_sha256,
        byte_count=provenance.byte_count if byte_count is None else byte_count,
        record_count=provenance.record_count if record_count is None else record_count,
        acquired_on=provenance.acquired_on,
        availability=provenance.availability if availability is None else availability,
        blocker_reason=provenance.blocker_reason if blocker_reason is None else blocker_reason,
        error=(provenance.error if error is None else error)
        + (f"; {content_source}" if content_source and error else ""),
        manifest=dict(provenance.manifest),
    )


def _load_snapshot_payload(
    manifest: EvolutionarySnapshotManifest,
    *,
    opener: Callable[..., Any] | None,
) -> tuple[bytes, str]:
    for artifact_ref in manifest.local_artifact_refs:
        path = Path(artifact_ref)
        if path.is_file():
            return path.read_bytes(), f"local_artifact:{path}"

    source_locator = manifest.source_locator or ""
    if not source_locator:
        raise FileNotFoundError("no local artifact exists and no source locator was provided")

    parsed = urlparse(source_locator)
    if parsed.scheme in {"http", "https", "ftp"}:
        request = Request(source_locator, headers={"User-Agent": DEFAULT_USER_AGENT})
        request_opener = opener or urlopen
        with request_opener(request, timeout=DEFAULT_TIMEOUT) as response:
            return response.read(), f"source_locator:{source_locator}"

    if parsed.scheme == "file":
        path = Path(parsed.path)
        if path.is_file():
            return path.read_bytes(), f"local_artifact:{path}"
        raise FileNotFoundError(source_locator)

    path = Path(source_locator)
    if path.is_file():
        return path.read_bytes(), f"local_artifact:{path}"
    raise FileNotFoundError(source_locator)


def _parse_records(
    text: str,
    *,
    normalized_manifest: EvolutionarySnapshotManifest,
) -> tuple[EvolutionarySnapshotRecord, ...]:
    if not text.strip():
        return ()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = _parse_json_lines(text)

    records_payload: Any = payload
    if isinstance(payload, Mapping):
        records_payload = None
        for key in ("records", "items", "entries", "alignments"):
            if key in payload:
                records_payload = payload.get(key)
                break
        if records_payload is None and _looks_like_record(payload):
            records_payload = [payload]

    if records_payload is None:
        raise EvolutionarySnapshotError("payload does not contain evolutionary records")

    items = _coerce_record_items(records_payload)
    return tuple(
        _record_from_payload(item, normalized_manifest=normalized_manifest, source_index=index)
        for index, item in enumerate(items)
    )


def _parse_json_lines(text: str) -> Any:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ()
    records: list[Any] = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise EvolutionarySnapshotError(
                "payload must be JSON or JSONL with record objects"
            ) from exc
    return records


def _coerce_record_items(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(payload, Mapping):
        return (payload,)
    if isinstance(payload, (str, bytes)) or not isinstance(payload, Iterable):
        raise EvolutionarySnapshotError("records payload must be iterable mappings")
    items: list[Mapping[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise EvolutionarySnapshotError("records payload must contain mappings")
        items.append(item)
    return tuple(items)


def _looks_like_record(payload: Mapping[str, Any]) -> bool:
    return any(
        key in payload
        for key in ("accession", "uniprot_accession", "uniprot_id", "primary_accession")
    )


def _record_from_payload(
    payload: Mapping[str, Any],
    *,
    normalized_manifest: EvolutionarySnapshotManifest,
    source_index: int,
) -> EvolutionarySnapshotRecord:
    values = dict(payload)
    accession = _first_non_empty(
        values.pop("accession", None),
        values.pop("uniprot_accession", None),
        values.pop("uniprot_id", None),
        values.pop("primary_accession", None),
        values.pop("id", None),
    )
    if accession is None:
        raise EvolutionarySnapshotError(f"record {source_index} is missing an accession")

    metadata = dict(values)
    metadata.update(
        {
            "source_record_index": source_index,
            "corpus_snapshot_id": normalized_manifest.corpus_snapshot_id,
            "aligner_version": normalized_manifest.aligner_version,
            "source_layers": normalized_manifest.source_layers,
        }
    )

    return EvolutionarySnapshotRecord(
        accession=str(accession),
        sequence_version=_optional_text(
            _first_non_empty(values.pop("sequence_version", None), values.pop("version", None))
        ),
        sequence_hash=_optional_text(
            _first_non_empty(
                values.pop("sequence_hash", None),
                values.pop("md5", None),
                values.pop("checksum", None),
            )
        ),
        sequence_length=_normalize_int(
            _first_non_empty(values.pop("sequence_length", None), values.pop("length", None)),
            "sequence_length",
        ),
        taxon_id=_normalize_int(
            _first_non_empty(
                values.pop("taxon_id", None),
                values.pop("tax_id", None),
                values.pop("organism_taxon_id", None),
            ),
            "taxon_id",
        ),
        uniref_cluster_ids=_unique_text(
            values.pop("uniref_cluster_ids", None)
            or values.pop("uniref_clusters", None)
            or values.pop("cluster_ids", None)
        ),
        orthogroup_ids=_unique_text(
            values.pop("orthogroup_ids", None) or values.pop("orthodb_ids", None)
        ),
        alignment_depth=_normalize_int(
            _first_non_empty(values.pop("alignment_depth", None), values.pop("depth", None)),
            "alignment_depth",
        ),
        alignment_coverage=_normalize_float(
            _first_non_empty(
                values.pop("alignment_coverage", None),
                values.pop("coverage", None),
            ),
            "alignment_coverage",
        ),
        neff=_normalize_float(values.pop("neff", None), "neff"),
        gap_fraction=_normalize_float(
            _first_non_empty(values.pop("gap_fraction", None), values.pop("gap", None)),
            "gap_fraction",
        ),
        quality_flags=_unique_text(
            values.pop("quality_flags", None) or values.pop("flags", None)
        ),
        source_refs=_unique_text(
            values.pop("source_refs", None)
            or values.pop("provenance_refs", None)
            or values.pop("references", None)
            or values.pop("evidence", None)
        ),
        lazy_materialization_refs=_unique_text(
            values.pop("lazy_materialization_refs", None)
            or values.pop("lazy_refs", None)
            or values.pop("artifact_refs", None)
            or values.pop("alignment_refs", None)
            or values.pop("tree_refs", None)
            or values.pop("profile_refs", None)
        ),
        metadata=metadata,
    )


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


__all__ = [
    "EvolutionarySnapshot",
    "EvolutionarySnapshotAvailability",
    "EvolutionarySnapshotError",
    "EvolutionarySnapshotManifest",
    "EvolutionarySnapshotProvenance",
    "EvolutionarySnapshotRecord",
    "EvolutionarySnapshotResult",
    "EvolutionarySnapshotStatus",
    "SOURCE_FAMILY",
    "SOURCE_NAME",
    "acquire_evolutionary_snapshot",
    "build_evolutionary_snapshot_manifest",
]
