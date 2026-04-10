from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from connectors.rcsb.client import RCSBClient, RCSBClientError
from connectors.rcsb.parsers import (
    RCSBParserError,
    RCSBStructureBundle,
    parse_structure_bundle,
)

DEFAULT_PDBe_BASE_URL = "https://www.ebi.ac.uk/pdbe/api"
DEFAULT_SMOKE_PDB_ID = "1CBS"
LIVE_SMOKE_ENV_VAR = "PROTEOSPHERE_RCSB_PDBE_SMOKE"
SUPPORTED_PDBe_RESOURCES = (
    "uniprot_mapping",
    "chains",
    "secondary_structure",
    "binding_sites",
    "annotations",
    "domains",
    "rfam",
    "variation",
)


class SnapshotAcquisitionError(ValueError):
    """Raised when a release or snapshot manifest cannot be normalized."""


class SnapshotSmokeDisabledError(RuntimeError):
    """Raised when the guarded live smoke path is invoked without opt-in."""


class SnapshotStatus(StrEnum):
    COMPLETE = "complete"
    BLOCKED = "blocked"


class SnapshotBlockerCode(StrEnum):
    MANIFEST_UNPINNED = "manifest_unpinned"
    NETWORK = "network"
    PARSE = "parse"
    MISSING_TEMPLATE = "missing_template"
    RUNTIME = "runtime"
    SMOKE_DISABLED = "smoke_disabled"


def _normalize_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SnapshotAcquisitionError(f"{field_name} must be a non-empty string")
    return text


def _normalize_optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _unique_texts(values: Iterable[Any], field_name: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        text = str(raw_value or "").strip()
        if not text:
            raise SnapshotAcquisitionError(f"{field_name} entries must be non-empty strings")
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _normalize_pdb_ids(values: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        pdb_id = _normalize_pdb_id(str(raw_value), "pdb_ids")
        if pdb_id in seen:
            continue
        seen.add(pdb_id)
        normalized.append(pdb_id)
    return tuple(normalized)


def _normalize_accessions(values: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        accession = _normalize_text(str(raw_value), "accessions").upper()
        if accession in seen:
            continue
        seen.add(accession)
        normalized.append(accession)
    return tuple(normalized)


def _normalize_pdbe_resources(values: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        resource = _normalize_text(str(raw_value), "pdbe_resources").lower()
        if resource in seen:
            continue
        seen.add(resource)
        normalized.append(resource)
    return tuple(normalized)


def _normalize_pdb_id(pdb_id: str, field_name: str = "pdb_id") -> str:
    value = _normalize_text(pdb_id, field_name).upper()
    if len(value) != 4 or not value.isalnum():
        raise SnapshotAcquisitionError(f"{field_name} must be a 4-character alphanumeric ID")
    return value


def _coerce_request_dict(value: Any) -> SnapshotRequest:
    if isinstance(value, SnapshotRequest):
        return value
    if not isinstance(value, Mapping):
        raise SnapshotAcquisitionError("additional_requests entries must be mappings")
    return SnapshotRequest.from_mapping(value)


def _supported_pdbe_resources() -> frozenset[str]:
    return frozenset(SUPPORTED_PDBe_RESOURCES)


def _payload_to_text(payload: bytes, content_kind: str) -> Any:
    if content_kind == "bytes":
        return payload
    text = payload.decode("utf-8")
    if content_kind == "text":
        return text
    return json.loads(text)


@dataclass(frozen=True, slots=True)
class SnapshotRequest:
    source: str
    resource: str
    url: str
    content_kind: str = "json"
    identifier: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _normalize_text(self.source, "source"))
        object.__setattr__(self, "resource", _normalize_text(self.resource, "resource"))
        object.__setattr__(self, "url", _normalize_text(self.url, "url"))
        object.__setattr__(self, "content_kind", _normalize_text(self.content_kind, "content_kind"))
        identifier = _normalize_optional_text(self.identifier) or self.resource
        object.__setattr__(self, "identifier", identifier)
        if self.content_kind not in {"json", "text", "bytes"}:
            raise SnapshotAcquisitionError("content_kind must be json, text, or bytes")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SnapshotRequest:
        return cls(
            source=value.get("source") or value.get("source_name") or "custom",
            resource=value.get("resource") or value.get("kind") or value.get("name") or "custom",
            url=value.get("url"),
            content_kind=value.get("content_kind") or value.get("format") or "json",
            identifier=value.get("identifier") or value.get("id") or "",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "resource": self.resource,
            "url": self.url,
            "content_kind": self.content_kind,
            "identifier": self.identifier,
        }


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    release_id: str | None
    snapshot_id: str | None
    pdb_ids: tuple[str, ...]
    pdbe_resources: tuple[str, ...] = ("uniprot_mapping", "chains")
    additional_requests: tuple[SnapshotRequest, ...] = ()
    include_mmcif: bool = False
    include_validation: bool = False
    pdbe_base_url: str = DEFAULT_PDBe_BASE_URL
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        release_id = _normalize_optional_text(self.release_id)
        snapshot_id = _normalize_optional_text(self.snapshot_id)
        if not self.pdb_ids:
            raise SnapshotAcquisitionError("manifest must include at least one pdb_id")
        if not isinstance(self.metadata, Mapping):
            raise SnapshotAcquisitionError("metadata must be a mapping")

        object.__setattr__(self, "release_id", release_id)
        object.__setattr__(self, "snapshot_id", snapshot_id)
        object.__setattr__(self, "pdb_ids", _normalize_pdb_ids(self.pdb_ids))
        object.__setattr__(self, "pdbe_resources", _normalize_pdbe_resources(self.pdbe_resources))
        unsupported = set(self.pdbe_resources) - _supported_pdbe_resources()
        if unsupported:
            unsupported_list = ", ".join(sorted(unsupported))
            raise SnapshotAcquisitionError(
                f"unsupported PDBe resource(s): {unsupported_list}"
            )
        object.__setattr__(
            self,
            "additional_requests",
            tuple(_coerce_request_dict(request) for request in self.additional_requests),
        )
        object.__setattr__(
            self,
            "pdbe_base_url",
            _normalize_text(self.pdbe_base_url, "pdbe_base_url"),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def pin_label(self) -> str:
        return self.release_id or self.snapshot_id or ""

    @property
    def pinned(self) -> bool:
        return bool(self.release_id or self.snapshot_id)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SnapshotManifest:
        metadata = value.get("metadata") or {}
        notes = value.get("notes")
        if notes and not metadata:
            metadata = {"notes": notes}
        return cls(
            release_id=value.get("release_id")
            or value.get("release")
            or value.get("release_label"),
            snapshot_id=value.get("snapshot_id")
            or value.get("snapshot")
            or value.get("snapshot_label"),
            pdb_ids=tuple(
                value.get("pdb_ids")
                or value.get("entries")
                or value.get("entry_ids")
                or ()
            ),
            pdbe_resources=tuple(
                value.get("pdbe_resources")
                or value.get("resources")
                or ("uniprot_mapping", "chains")
            ),
            additional_requests=tuple(
                _coerce_request_dict(request)
                for request in value.get("additional_requests", ())
            ),
            include_mmcif=bool(value.get("include_mmcif", False)),
            include_validation=bool(value.get("include_validation", False)),
            pdbe_base_url=value.get("pdbe_base_url") or DEFAULT_PDBe_BASE_URL,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "snapshot_id": self.snapshot_id,
            "pdb_ids": list(self.pdb_ids),
            "pdbe_resources": list(self.pdbe_resources),
            "additional_requests": [request.to_dict() for request in self.additional_requests],
            "include_mmcif": self.include_mmcif,
            "include_validation": self.include_validation,
            "pdbe_base_url": self.pdbe_base_url,
            "metadata": dict(self.metadata),
            "pin_label": self.pin_label,
            "pinned": self.pinned,
        }


@dataclass(frozen=True, slots=True)
class SnapshotBlocker:
    source: str
    code: SnapshotBlockerCode
    message: str
    request: SnapshotRequest | None = None
    retryable: bool = False
    detail: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _normalize_text(self.source, "source"))
        object.__setattr__(self, "message", _normalize_text(self.message, "message"))
        if self.detail is not None:
            object.__setattr__(self, "detail", _normalize_optional_text(self.detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "code": self.code.value,
            "message": self.message,
            "request": None if self.request is None else self.request.to_dict(),
            "retryable": self.retryable,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class SnapshotAsset:
    source: str
    resource: str
    identifier: str
    url: str
    payload: Any
    content_kind: str = "json"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _normalize_text(self.source, "source"))
        object.__setattr__(self, "resource", _normalize_text(self.resource, "resource"))
        object.__setattr__(self, "identifier", _normalize_text(self.identifier, "identifier"))
        object.__setattr__(self, "url", _normalize_text(self.url, "url"))
        object.__setattr__(self, "content_kind", _normalize_text(self.content_kind, "content_kind"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "resource": self.resource,
            "identifier": self.identifier,
            "url": self.url,
            "content_kind": self.content_kind,
        }


@dataclass(frozen=True, slots=True)
class SnapshotAcquisitionResult:
    manifest: SnapshotManifest
    structure_bundles: tuple[RCSBStructureBundle, ...]
    assets: tuple[SnapshotAsset, ...]
    blockers: tuple[SnapshotBlocker, ...]

    @property
    def status(self) -> SnapshotStatus:
        return SnapshotStatus.COMPLETE if not self.blockers else SnapshotStatus.BLOCKED

    @property
    def succeeded(self) -> bool:
        return self.status == SnapshotStatus.COMPLETE

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "status": self.status.value,
            "succeeded": self.succeeded,
            "structure_bundle_count": len(self.structure_bundles),
            "assets": [asset.to_dict() for asset in self.assets],
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def build_snapshot_manifest(
    pdb_ids: Sequence[str],
    *,
    release_id: str | None = None,
    snapshot_id: str | None = None,
    pdbe_resources: Sequence[str] = ("uniprot_mapping", "chains"),
    additional_requests: Sequence[SnapshotRequest | Mapping[str, Any]] = (),
    include_mmcif: bool = False,
    include_validation: bool = False,
    pdbe_base_url: str = DEFAULT_PDBe_BASE_URL,
    metadata: Mapping[str, Any] | None = None,
) -> SnapshotManifest:
    return SnapshotManifest(
        release_id=release_id,
        snapshot_id=snapshot_id,
        pdb_ids=tuple(pdb_ids),
        pdbe_resources=tuple(pdbe_resources),
        additional_requests=tuple(_coerce_request_dict(request) for request in additional_requests),
        include_mmcif=include_mmcif,
        include_validation=include_validation,
        pdbe_base_url=pdbe_base_url,
        metadata={} if metadata is None else metadata,
    )


def build_accession_enrichment_manifest(
    accessions: Sequence[str],
    *,
    accession_pdb_ids: Mapping[str, Sequence[str]],
    release_id: str | None = None,
    snapshot_id: str | None = None,
    pdbe_resources: Sequence[str] = ("uniprot_mapping", "chains"),
    additional_requests: Sequence[SnapshotRequest | Mapping[str, Any]] = (),
    include_mmcif: bool = False,
    include_validation: bool = False,
    pdbe_base_url: str = DEFAULT_PDBe_BASE_URL,
    metadata: Mapping[str, Any] | None = None,
) -> SnapshotManifest:
    normalized_accessions = _normalize_accessions(accessions)
    normalized_accession_pdb_ids: dict[str, list[str]] = {}
    resolved_pdb_ids: list[str] = []
    unresolved_accessions: list[str] = []

    for accession in normalized_accessions:
        mapped_ids = _normalize_pdb_ids(accession_pdb_ids.get(accession, ()))
        normalized_accession_pdb_ids[accession] = list(mapped_ids)
        if mapped_ids:
            resolved_pdb_ids.extend(mapped_ids)
        else:
            unresolved_accessions.append(accession)

    if not resolved_pdb_ids:
        raise SnapshotAcquisitionError(
            "accession enrichment requires at least one resolved PDB identifier"
        )

    merged_metadata = dict(metadata or {})
    merged_metadata.setdefault("accessions", list(normalized_accessions))
    merged_metadata["accession_pdb_ids"] = {
        accession: list(pdb_ids)
        for accession, pdb_ids in sorted(normalized_accession_pdb_ids.items())
    }
    merged_metadata["unresolved_accessions"] = unresolved_accessions
    merged_metadata["resolved_accession_count"] = len(normalized_accessions) - len(
        unresolved_accessions
    )

    return build_snapshot_manifest(
        resolved_pdb_ids,
        release_id=release_id,
        snapshot_id=snapshot_id,
        pdbe_resources=pdbe_resources,
        additional_requests=additional_requests,
        include_mmcif=include_mmcif,
        include_validation=include_validation,
        pdbe_base_url=pdbe_base_url,
        metadata=merged_metadata,
    )


def acquire_rcsb_pdbe_snapshot(
    manifest: SnapshotManifest | Mapping[str, Any],
    *,
    client: RCSBClient | None = None,
    opener: Callable[..., Any] | None = None,
    pdbe_opener: Callable[..., Any] | None = None,
) -> SnapshotAcquisitionResult:
    normalized_manifest = _normalize_manifest(manifest)
    if not normalized_manifest.pinned:
        return SnapshotAcquisitionResult(
            manifest=normalized_manifest,
            structure_bundles=(),
            assets=(),
            blockers=(
                SnapshotBlocker(
                    source="manifest",
                    code=SnapshotBlockerCode.MANIFEST_UNPINNED,
                    message="manifest must pin a release or snapshot before acquisition",
                ),
            ),
        )

    client = client or RCSBClient()
    pdbe_opener = opener if pdbe_opener is None else pdbe_opener
    assets: list[SnapshotAsset] = []
    blockers: list[SnapshotBlocker] = []
    structure_bundles: list[Any] = []

    for pdb_id in normalized_manifest.pdb_ids:
        try:
            entry_payload = client.get_entry(pdb_id, opener=opener)
            entry_record = parse_structure_bundle(entry_payload, (), ()).entry
            entity_payloads = [
                _fetch_entity_payload(client, pdb_id, entity_id, opener)
                for entity_id in entry_record.polymer_entity_ids
            ]
            assembly_payloads = [
                _fetch_assembly_payload(client, pdb_id, assembly_id, opener)
                for assembly_id in entry_record.assembly_ids
            ]
            structure_bundles.append(
                parse_structure_bundle(entry_payload, entity_payloads, assembly_payloads)
            )
            assets.append(
                SnapshotAsset(
                    source="rcsb",
                    resource="entry",
                    identifier=pdb_id,
                    url=f"{client.base_url}/core/entry/{pdb_id.lower()}",
                    payload=entry_payload,
                )
            )
            for entity_payload in entity_payloads:
                entity_id = str(entity_payload.get("entity", {}).get("id") or "").strip()
                assets.append(
                    SnapshotAsset(
                        source="rcsb",
                        resource="polymer_entity",
                        identifier=f"{pdb_id}:{entity_id}",
                        url=f"{client.base_url}/core/polymer_entity/{pdb_id.lower()}/{entity_id}",
                        payload=entity_payload,
                    )
                )
            for assembly_payload in assembly_payloads:
                assembly_id = str(assembly_payload.get("id") or "").strip()
                assets.append(
                    SnapshotAsset(
                        source="rcsb",
                        resource="assembly",
                        identifier=f"{pdb_id}:{assembly_id}",
                        url=f"{client.base_url}/core/assembly/{pdb_id.lower()}/{assembly_id}",
                        payload=assembly_payload,
                    )
                )
            if normalized_manifest.include_mmcif:
                mmcif_text = client.get_mmcif(pdb_id, opener=opener)
                assets.append(
                    SnapshotAsset(
                        source="rcsb",
                        resource="mmcif",
                        identifier=pdb_id,
                        url=f"{client.archive_url}/{pdb_id.lower()}.cif",
                        payload=mmcif_text,
                        content_kind="text",
                    )
                )
            if normalized_manifest.include_validation:
                validation_request = _validation_request(normalized_manifest, pdb_id)
                assets.append(
                    SnapshotAsset(
                        source=validation_request.source,
                        resource=validation_request.resource,
                        identifier=validation_request.identifier,
                        url=validation_request.url,
                        payload=_fetch_request_payload(
                            validation_request,
                            opener=pdbe_opener,
                        ),
                        content_kind=validation_request.content_kind,
                    )
                )
            for request in _pdbe_requests(normalized_manifest, pdb_id, entry_record):
                assets.append(
                    SnapshotAsset(
                        source=request.source,
                        resource=request.resource,
                        identifier=request.identifier,
                        url=request.url,
                        payload=_fetch_request_payload(request, opener=pdbe_opener),
                        content_kind=request.content_kind,
                    )
                )
            for request in normalized_manifest.additional_requests:
                assets.append(
                    SnapshotAsset(
                        source=request.source,
                        resource=request.resource,
                        identifier=request.identifier,
                        url=request.url,
                        payload=_fetch_request_payload(request, opener=pdbe_opener),
                        content_kind=request.content_kind,
                    )
                )
        except json.JSONDecodeError as exc:
            blockers.append(
                SnapshotBlocker(
                    source="pdbe",
                    code=SnapshotBlockerCode.PARSE,
                    message="PDBe payload could not be normalized",
                    detail=str(exc),
                )
            )
            break
        except (RCSBClientError, URLError, OSError) as exc:
            blockers.append(
                SnapshotBlocker(
                    source="rcsb",
                    code=SnapshotBlockerCode.NETWORK,
                    message="RCSB acquisition failed",
                    detail=str(exc),
                    retryable=True,
                )
            )
            break
        except SnapshotAcquisitionError as exc:
            blockers.append(
                SnapshotBlocker(
                    source="manifest",
                    code=SnapshotBlockerCode.MISSING_TEMPLATE,
                    message="snapshot manifest did not define a required template",
                    detail=str(exc),
                )
            )
            break
        except RCSBParserError as exc:
            blockers.append(
                SnapshotBlocker(
                    source="rcsb",
                    code=SnapshotBlockerCode.PARSE,
                    message="RCSB payload could not be normalized",
                    detail=str(exc),
                )
            )
            break
        except SnapshotSmokeDisabledError as exc:
            blockers.append(
                SnapshotBlocker(
                    source="runtime",
                    code=SnapshotBlockerCode.SMOKE_DISABLED,
                    message=str(exc),
                )
            )
            break
        except Exception as exc:  # pragma: no cover - defensive runtime blocker
            blockers.append(
                SnapshotBlocker(
                    source="runtime",
                    code=SnapshotBlockerCode.RUNTIME,
                    message="unexpected runtime failure during acquisition",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
            break

    return SnapshotAcquisitionResult(
        manifest=normalized_manifest,
        structure_bundles=tuple(structure_bundles),
        assets=tuple(assets),
        blockers=tuple(blockers),
    )


def run_live_smoke_snapshot(
    pdb_id: str = DEFAULT_SMOKE_PDB_ID,
    *,
    release_id: str = "live-smoke",
    snapshot_id: str = "guarded-live-smoke",
    client: RCSBClient | None = None,
    opener: Callable[..., Any] | None = None,
    pdbe_opener: Callable[..., Any] | None = None,
) -> SnapshotAcquisitionResult:
    if os.getenv(LIVE_SMOKE_ENV_VAR) != "1":
        raise SnapshotSmokeDisabledError(
            f"set {LIVE_SMOKE_ENV_VAR}=1 to run the live RCSB/PDBe smoke path"
        )

    manifest = build_snapshot_manifest(
        [pdb_id],
        release_id=release_id,
        snapshot_id=snapshot_id,
        pdbe_resources=("uniprot_mapping",),
        include_mmcif=False,
    )
    return acquire_rcsb_pdbe_snapshot(
        manifest,
        client=client,
        opener=opener,
        pdbe_opener=pdbe_opener,
    )


def _normalize_manifest(manifest: SnapshotManifest | Mapping[str, Any]) -> SnapshotManifest:
    if isinstance(manifest, SnapshotManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise SnapshotAcquisitionError("manifest must be a SnapshotManifest or mapping")
    return SnapshotManifest.from_mapping(manifest)


def _fetch_request_payload(
    request: SnapshotRequest,
    *,
    opener: Callable[..., Any] | None = None,
) -> Any:
    raw = _request_bytes(request.url, opener=opener)
    return _payload_to_text(raw, request.content_kind)


def _request_bytes(url: str, opener: Callable[..., Any] | None = None) -> bytes:
    request = Request(url, headers={"User-Agent": "ProteoSphereV2-RCSBPDBeSnapshot/0.1"})
    request_opener = opener or urlopen
    with request_opener(request, timeout=30.0) as response:
        return response.read()


def _fetch_entity_payload(
    client: RCSBClient,
    pdb_id: str,
    entity_id: str,
    opener: Callable[..., Any] | None,
) -> dict[str, Any]:
    return client.get_entity(pdb_id, entity_id, opener=opener)


def _fetch_assembly_payload(
    client: RCSBClient,
    pdb_id: str,
    assembly_id: str,
    opener: Callable[..., Any] | None,
) -> dict[str, Any]:
    return client.get_assembly(pdb_id, assembly_id, opener=opener)


def _pdbe_requests(
    manifest: SnapshotManifest,
    pdb_id: str,
    entry_bundle: Any,
) -> tuple[SnapshotRequest, ...]:
    entity_ids = tuple(entry_bundle.polymer_entity_ids)
    requests: list[SnapshotRequest] = []
    for entity_id in entity_ids:
        for resource in manifest.pdbe_resources:
            requests.append(
                SnapshotRequest(
                    source="pdbe",
                    resource=resource,
                    identifier=f"{pdb_id}:{entity_id}:{resource}",
                    url=_pdbe_resource_url(manifest.pdbe_base_url, pdb_id, entity_id, resource),
                )
            )
    return tuple(requests)


def _pdbe_resource_url(
    base_url: str,
    pdb_id: str,
    entity_id: str,
    resource: str,
) -> str:
    supported_resources = {
        "uniprot_mapping",
        "chains",
        "secondary_structure",
        "binding_sites",
        "annotations",
        "domains",
        "rfam",
        "variation",
    }
    if resource not in supported_resources:
        raise SnapshotAcquisitionError(f"unsupported PDBe resource: {resource}")
    normalized_base = base_url.rstrip("/")
    return (
        f"{normalized_base}/pdb/entry/{resource}/"
        f"{pdb_id.lower()}/{entity_id}"
    )


def _validation_request(manifest: SnapshotManifest, pdb_id: str) -> SnapshotRequest:
    template = _normalize_optional_text(
        manifest.metadata.get("validation_url_template")
        if isinstance(manifest.metadata, Mapping)
        else None
    )
    if not template:
        raise SnapshotAcquisitionError(
            "include_validation requires metadata.validation_url_template"
        )
    url = template.format(pdb_id=pdb_id.lower(), pdb_id_upper=pdb_id.upper())
    return SnapshotRequest(
        source="rcsb",
        resource="validation",
        identifier=pdb_id,
        url=url,
        content_kind="text",
    )
