from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from connectors.bindingdb.client import BindingDBClient, BindingDBClientError
from connectors.bindingdb.parsers import BindingDBAssayRecord, parse_bindingdb_assays

BindingDBSnapshotStatus = Literal["ok", "blocked", "unavailable"]
BindingDBSnapshotAvailability = Literal["available", "blocked", "unavailable"]
BindingDBSnapshotQueryKind = Literal["pdb", "pdbs", "uniprot", "uniprots"]

_BINDINGDB_DOWNLOAD_URL = (
    "https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp"
    "?ac9Lxm0azk=7fyZSysHNn4XK4G"
)
_BINDINGDB_SOURCE_URL = "https://www.bindingdb.org/rwd/bind/info.jsp"
_DEFAULT_ACQUISITION_MODE = "rest"
_DEFAULT_SOURCE_FAMILY = "assay"


def _normalize_text(value: Any, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _normalize_query_values(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Sequence):
        values = list(value)
    else:
        raise TypeError(f"{field_name} must be a string or sequence of strings")

    normalized = tuple(
        dict.fromkeys(
            _normalize_text(item, field_name).upper()
            for item in values
            if item is not None and str(item).strip()
        )
    )
    return normalized


def _normalize_optional_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _normalize_optional_number(value: Any, field_name: str) -> int | float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, bool):
            raise TypeError
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return value
        text = str(value).strip()
        if not text:
            return None
        if any(marker in text.lower() for marker in (".", "e")):
            return float(text)
        return int(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc


def _mapping_get(mapping: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


@dataclass(frozen=True, slots=True)
class BindingDBSnapshotManifest:
    """Snapshot acquisition contract for pinned BindingDB assay pulls."""

    snapshot_id: str
    query_kind: BindingDBSnapshotQueryKind
    query_values: tuple[str, ...] = ()
    availability: BindingDBSnapshotAvailability = "available"
    release_pin: str = ""
    source_url: str = _BINDINGDB_DOWNLOAD_URL
    archive_url: str = ""
    acquisition_mode: str = _DEFAULT_ACQUISITION_MODE
    cutoff: float | int | None = None
    identity: int | None = None
    blocker_reason: str = ""
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", _normalize_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(
            self,
            "query_kind",
            _normalize_text(self.query_kind, "query_kind").lower(),
        )
        object.__setattr__(
            self,
            "query_values",
            _normalize_query_values(self.query_values, "query_values"),
        )
        object.__setattr__(
            self,
            "availability",
            _normalize_text(self.availability, "availability").lower(),
        )
        object.__setattr__(self, "release_pin", str(self.release_pin).strip())
        object.__setattr__(self, "source_url", _normalize_text(self.source_url, "source_url"))
        object.__setattr__(self, "archive_url", str(self.archive_url).strip())
        object.__setattr__(
            self,
            "acquisition_mode",
            _normalize_text(self.acquisition_mode, "acquisition_mode"),
        )
        object.__setattr__(self, "cutoff", _normalize_optional_number(self.cutoff, "cutoff"))
        object.__setattr__(self, "identity", _normalize_optional_int(self.identity, "identity"))
        object.__setattr__(self, "blocker_reason", str(self.blocker_reason).strip())
        object.__setattr__(
            self,
            "notes",
            tuple(
                str(note).strip()
                for note in self.notes
                if str(note).strip()
            ),
        )

        if self.query_kind not in {"pdb", "pdbs", "uniprot", "uniprots"}:
            raise ValueError("query_kind must be one of: pdb, pdbs, uniprot, uniprots")
        if self.availability not in {"available", "blocked", "unavailable"}:
            raise ValueError("availability must be one of: available, blocked, unavailable")
        if not self.query_values and self.availability == "available":
            raise ValueError("query_values must not be empty when availability is available")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> BindingDBSnapshotManifest:
        if not isinstance(value, Mapping):
            raise TypeError("manifest must be a mapping")

        snapshot_id = _mapping_get(value, ("snapshot_id", "manifest_id", "release_pin", "id"))
        query_kind = _mapping_get(value, ("query_kind", "lookup_kind", "endpoint_kind", "kind"))
        query_values = _mapping_get(
            value,
            ("query_values", "pdb_ids", "pdb_id", "uniprot_ids", "uniprot_id", "target_ids"),
        )
        if query_values is None:
            query_values = ()

        availability = _mapping_get(value, ("availability", "status"), "available")
        release_pin = _mapping_get(value, ("release_pin", "release_id", "archive_pin"), "")
        source_url = _mapping_get(value, ("source_url", "download_url"), _BINDINGDB_DOWNLOAD_URL)
        archive_url = _mapping_get(value, ("archive_url", "source_archive_url"), "")
        acquisition_mode = _mapping_get(
            value,
            ("acquisition_mode", "mode"),
            _DEFAULT_ACQUISITION_MODE,
        )
        cutoff = _mapping_get(value, ("cutoff",), None)
        identity = _mapping_get(value, ("identity",), None)
        blocker_reason = _mapping_get(value, ("blocker_reason", "blocked_reason", "reason"), "")
        notes = _mapping_get(value, ("notes",), ())

        if snapshot_id is None:
            raise ValueError("manifest must define snapshot_id, manifest_id, release_pin, or id")
        if query_kind is None:
            if "pdb_ids" in value or "pdb_id" in value:
                query_kind = "pdbs"
            elif "uniprot_ids" in value:
                query_kind = "uniprots"
            elif "uniprot_id" in value:
                query_kind = "uniprot"
            else:
                raise ValueError("manifest must define query_kind or an identifier family")

        if isinstance(query_values, str) or not isinstance(query_values, Sequence):
            query_values = (query_values,) if query_values is not None else ()

        return cls(
            snapshot_id=snapshot_id,
            query_kind=query_kind,
            query_values=tuple(query_values),
            availability=str(availability),
            release_pin=str(release_pin),
            source_url=str(source_url),
            archive_url=str(archive_url),
            acquisition_mode=str(acquisition_mode),
            cutoff=cutoff,
            identity=identity,
            blocker_reason=str(blocker_reason),
            notes=(
                tuple(notes)
                if isinstance(notes, Sequence) and not isinstance(notes, str)
                else (() if notes is None else (str(notes),))
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "query_kind": self.query_kind,
            "query_values": list(self.query_values),
            "availability": self.availability,
            "release_pin": self.release_pin,
            "source_url": self.source_url,
            "archive_url": self.archive_url,
            "acquisition_mode": self.acquisition_mode,
            "cutoff": self.cutoff,
            "identity": self.identity,
            "blocker_reason": self.blocker_reason,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class BindingDBSnapshotProvenance:
    source: Literal["BindingDB"] = "BindingDB"
    source_family: str = _DEFAULT_SOURCE_FAMILY
    source_url: str = _BINDINGDB_SOURCE_URL
    snapshot_id: str = ""
    release_pin: str = ""
    acquisition_mode: str = _DEFAULT_ACQUISITION_MODE
    query_kind: str = ""
    query_values: tuple[str, ...] = ()
    endpoint: str = ""
    record_count: int = 0
    acquired_on: str = ""
    availability: BindingDBSnapshotAvailability = "available"
    blocker_reason: str = ""
    error: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_family": self.source_family,
            "source_url": self.source_url,
            "snapshot_id": self.snapshot_id,
            "release_pin": self.release_pin,
            "acquisition_mode": self.acquisition_mode,
            "query_kind": self.query_kind,
            "query_values": list(self.query_values),
            "endpoint": self.endpoint,
            "record_count": self.record_count,
            "acquired_on": self.acquired_on,
            "availability": self.availability,
            "blocker_reason": self.blocker_reason,
            "error": self.error,
            "manifest": dict(self.manifest),
        }


@dataclass(frozen=True, slots=True)
class BindingDBSnapshotResult:
    status: BindingDBSnapshotStatus
    reason: str
    manifest: BindingDBSnapshotManifest
    provenance: BindingDBSnapshotProvenance
    records: tuple[BindingDBAssayRecord, ...] = ()
    raw_payload: Any = None

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "manifest": self.manifest.to_dict(),
            "provenance": self.provenance.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "raw_payload": self.raw_payload,
        }


def acquire_bindingdb_snapshot(
    manifest: Mapping[str, Any] | BindingDBSnapshotManifest,
    *,
    client: BindingDBClient | None = None,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> BindingDBSnapshotResult:
    """Acquire a pinned BindingDB assay snapshot with explicit provenance."""

    snapshot_manifest = _coerce_manifest(manifest)
    provenance = _build_provenance(snapshot_manifest, acquired_on=acquired_on)

    if snapshot_manifest.availability == "blocked":
        reason = snapshot_manifest.blocker_reason or "bindingdb_snapshot_blocked"
        return BindingDBSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=snapshot_manifest,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
            ),
        )

    if snapshot_manifest.availability == "unavailable":
        reason = snapshot_manifest.blocker_reason or "bindingdb_snapshot_unavailable"
        return BindingDBSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=snapshot_manifest,
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                blocker_reason=reason,
            ),
        )

    bindingdb_client = client or BindingDBClient()
    try:
        payload, endpoint = _fetch_bindingdb_payload(
            bindingdb_client,
            snapshot_manifest,
            opener=opener,
        )
    except BindingDBClientError as exc:
        reason = "bindingdb_request_failed"
        return BindingDBSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=snapshot_manifest,
            provenance=_update_provenance(
                provenance,
                endpoint="",
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
            ),
            raw_payload=None,
        )

    records = tuple(parse_bindingdb_assays(payload, source=endpoint))
    if not records:
        reason = "bindingdb_no_assay_records"
        return BindingDBSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=snapshot_manifest,
            provenance=_update_provenance(
                provenance,
                endpoint=endpoint,
                availability="unavailable",
                blocker_reason=reason,
            ),
            raw_payload=payload,
        )

    return BindingDBSnapshotResult(
        status="ok",
        reason="bindingdb_snapshot_acquired",
        manifest=snapshot_manifest,
        provenance=_update_provenance(
            provenance,
            endpoint=endpoint,
            availability="available",
            record_count=len(records),
        ),
        records=records,
        raw_payload=payload,
    )


def _coerce_manifest(
    manifest: Mapping[str, Any] | BindingDBSnapshotManifest,
) -> BindingDBSnapshotManifest:
    if isinstance(manifest, BindingDBSnapshotManifest):
        return manifest
    return BindingDBSnapshotManifest.from_mapping(manifest)


def _build_provenance(
    manifest: BindingDBSnapshotManifest,
    *,
    acquired_on: str | None,
) -> BindingDBSnapshotProvenance:
    return BindingDBSnapshotProvenance(
        snapshot_id=manifest.snapshot_id,
        release_pin=manifest.release_pin,
        acquisition_mode=manifest.acquisition_mode,
        query_kind=manifest.query_kind,
        query_values=manifest.query_values,
        source_url=manifest.source_url,
        acquired_on=acquired_on or date.today().isoformat(),
        availability=manifest.availability,
        blocker_reason=manifest.blocker_reason,
        manifest=manifest.to_dict(),
    )


def _update_provenance(
    provenance: BindingDBSnapshotProvenance,
    *,
    endpoint: str | None = None,
    availability: BindingDBSnapshotAvailability | None = None,
    blocker_reason: str | None = None,
    error: str | None = None,
    record_count: int | None = None,
) -> BindingDBSnapshotProvenance:
    return BindingDBSnapshotProvenance(
        source=provenance.source,
        source_family=provenance.source_family,
        source_url=provenance.source_url,
        snapshot_id=provenance.snapshot_id,
        release_pin=provenance.release_pin,
        acquisition_mode=provenance.acquisition_mode,
        query_kind=provenance.query_kind,
        query_values=provenance.query_values,
        endpoint=provenance.endpoint if endpoint is None else endpoint,
        record_count=provenance.record_count if record_count is None else record_count,
        acquired_on=provenance.acquired_on,
        availability=provenance.availability if availability is None else availability,
        blocker_reason=provenance.blocker_reason if blocker_reason is None else blocker_reason,
        error=provenance.error if error is None else error,
        manifest=dict(provenance.manifest),
    )


def _fetch_bindingdb_payload(
    client: BindingDBClient,
    manifest: BindingDBSnapshotManifest,
    *,
    opener: Callable[..., Any] | None,
) -> tuple[Any, str]:
    if manifest.query_kind in {"pdb", "pdbs"}:
        payload = client.get_ligands_by_pdbs(
            manifest.query_values,
            cutoff=manifest.cutoff,
            identity=manifest.identity,
            opener=opener,
        )
        return payload, "getLigandsByPDBs"

    if manifest.query_kind == "uniprot" and len(manifest.query_values) == 1:
        payload = client.get_ligands_by_uniprot(
            manifest.query_values[0],
            cutoff=manifest.cutoff,
            opener=opener,
        )
        return payload, "getLigandsByUniprot"

    payload = client.get_ligands_by_uniprots(
        manifest.query_values,
        cutoff=manifest.cutoff,
        opener=opener,
    )
    return payload, "getLigandsByUniprots"


__all__ = [
    "BindingDBSnapshotAvailability",
    "BindingDBSnapshotManifest",
    "BindingDBSnapshotProvenance",
    "BindingDBSnapshotResult",
    "BindingDBSnapshotStatus",
    "BindingDBSnapshotQueryKind",
    "acquire_bindingdb_snapshot",
]
