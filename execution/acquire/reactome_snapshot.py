from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)

ReactomeSnapshotStatus = Literal["ok", "blocked", "unavailable"]
ReactomeSnapshotAvailability = Literal["available", "blocked", "unavailable"]
ReactomeAssetStatus = Literal["ok", "blocked", "unavailable"]

_DEFAULT_SOURCE_FAMILY = "pathway/reaction"
_DEFAULT_USER_AGENT = "ProteoSphereV2-ReactomeSnapshot/0.1"
_DEFAULT_TIMEOUT = 30.0


def _clean_text(value: Any, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _clean_optional_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_text_values(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        raise TypeError(f"{field_name} must be a string or sequence of strings")

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_optional_text(item)
        if not text:
            continue
        normalized = text.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return tuple(cleaned)


def _clean_optional_text_values(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_clean_text(value, field_name),)
    if isinstance(value, Sequence):
        return tuple(
            item for item in (_clean_optional_text(element) for element in value) if item
        )
    raise TypeError(f"{field_name} must be a string or sequence of strings")


def _clean_text_values(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        raise TypeError(f"{field_name} must be a string or sequence of strings")

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_optional_text(item)
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _clean_number(value: Any, field_name: str) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    if isinstance(value, int | float):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        if any(marker in text.lower() for marker in (".", "e")):
            return float(text)
        return int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric") from exc


def _mapping_get(mapping: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def _normalize_source_release(
    payload: Mapping[str, Any] | SourceReleaseManifest,
) -> SourceReleaseManifest:
    if isinstance(payload, SourceReleaseManifest):
        release = payload
    else:
        release = validate_source_release_manifest_payload(dict(payload))

    if release.source_name.casefold() != "reactome":
        raise ValueError("source_name must be Reactome")
    return release


@dataclass(frozen=True, slots=True)
class ReactomeSnapshotAssetSpec:
    """Manifest entry for a single Reactome pathway or reaction asset."""

    asset_name: str
    asset_url: str = ""
    asset_kind: str = "pathway"
    stable_ids: tuple[str, ...] = ()
    species: str = ""
    local_artifact_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_name", _clean_text(self.asset_name, "asset_name"))
        object.__setattr__(self, "asset_url", _clean_optional_text(self.asset_url))
        object.__setattr__(self, "asset_kind", _clean_text(self.asset_kind, "asset_kind").lower())
        object.__setattr__(self, "stable_ids", _clean_text_values(self.stable_ids, "stable_ids"))
        object.__setattr__(self, "species", _clean_optional_text(self.species))
        object.__setattr__(
            self,
            "local_artifact_refs",
            _clean_text_values(self.local_artifact_refs, "local_artifact_refs"),
        )
        object.__setattr__(
            self,
            "notes",
            tuple(
                item
                for item in (_clean_optional_text(note) for note in self.notes)
                if item
            ),
        )
        if not self.asset_url and not self.local_artifact_refs:
            raise ValueError("asset_url or local_artifact_refs must be provided")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReactomeSnapshotAssetSpec:
        if not isinstance(payload, Mapping):
            raise TypeError("asset payload must be a mapping")
        return cls(
            asset_name=_mapping_get(payload, ("asset_name", "name")),
            asset_url=_mapping_get(
                payload,
                ("asset_url", "download_url", "url", "source_url"),
                "",
            ),
            asset_kind=_mapping_get(payload, ("asset_kind", "kind", "asset_type"), "pathway"),
            stable_ids=_clean_optional_text_values(
                _mapping_get(payload, ("stable_ids", "stable_id", "stable_identifier", "ids")),
                "stable_ids",
            ),
            species=_mapping_get(payload, ("species", "organism"), ""),
            local_artifact_refs=_clean_text_values(
                _mapping_get(
                    payload,
                    ("local_artifact_refs", "artifact_refs", "local_artifact_ref"),
                    (),
                ),
                "local_artifact_refs",
            ),
            notes=_clean_optional_text_values(
                _mapping_get(payload, ("notes", "provenance"), ()),
                "notes",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_name": self.asset_name,
            "asset_url": self.asset_url,
            "asset_kind": self.asset_kind,
            "stable_ids": list(self.stable_ids),
            "species": self.species,
            "local_artifact_refs": list(self.local_artifact_refs),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ReactomeSnapshotManifest:
    """Manifest-aware contract for pinned Reactome pathway/reaction snapshots."""

    release: SourceReleaseManifest
    assets: tuple[ReactomeSnapshotAssetSpec, ...]
    availability: ReactomeSnapshotAvailability = "available"
    blocker_reason: str = ""
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        release = _normalize_source_release(self.release)
        assets = tuple(self.assets)
        availability = _clean_text(self.availability, "availability").lower()
        blocker_reason = _clean_optional_text(self.blocker_reason)
        notes = tuple(item for item in (_clean_optional_text(note) for note in self.notes) if item)

        if availability not in {"available", "blocked", "unavailable"}:
            raise ValueError("availability must be one of: available, blocked, unavailable")
        if availability == "available" and not assets:
            raise ValueError("assets must not be empty when availability is available")

        normalized_assets: list[ReactomeSnapshotAssetSpec] = []
        for asset in assets:
            if not isinstance(asset, ReactomeSnapshotAssetSpec):
                raise TypeError("assets must contain ReactomeSnapshotAssetSpec instances")
            normalized_assets.append(asset)

        object.__setattr__(self, "release", release)
        object.__setattr__(self, "assets", tuple(normalized_assets))
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "blocker_reason", blocker_reason)
        object.__setattr__(self, "notes", notes)

    @property
    def manifest_id(self) -> str:
        return self.release.manifest_id

    @property
    def source_name(self) -> str:
        return self.release.source_name

    @property
    def release_version(self) -> str | None:
        return self.release.release_version

    @property
    def release_date(self) -> str | None:
        return self.release.release_date

    @property
    def retrieval_mode(self) -> str:
        return self.release.retrieval_mode

    @property
    def source_locator(self) -> str | None:
        return self.release.source_locator

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ReactomeSnapshotManifest:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")

        release_payload = payload.get("release")
        if isinstance(release_payload, Mapping):
            release = _normalize_source_release(release_payload)
        else:
            release = _normalize_source_release(payload)

        assets = _coerce_assets(payload)
        availability = _mapping_get(payload, ("availability", "status"), "available")
        blocker_reason = _mapping_get(payload, ("blocker_reason", "blocked_reason", "reason"), "")
        notes = _clean_optional_text_values(_mapping_get(payload, ("notes",), ()), "notes")

        return cls(
            release=release,
            assets=assets,
            availability=str(availability),
            blocker_reason=str(blocker_reason),
            notes=notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "release": self.release.to_dict(),
            "manifest_id": self.manifest_id,
            "availability": self.availability,
            "blocker_reason": self.blocker_reason,
            "notes": list(self.notes),
            "assets": [asset.to_dict() for asset in self.assets],
        }


@dataclass(frozen=True, slots=True)
class ReactomeSnapshotAsset:
    """Downloaded Reactome pathway or reaction asset with explicit provenance."""

    asset_name: str
    asset_url: str
    content_source: str
    asset_kind: str
    stable_ids: tuple[str, ...]
    species: str
    status: ReactomeAssetStatus
    reason: str
    text: str
    byte_length: int
    source_release_manifest_id: str
    source_release_version: str
    source_release_date: str
    retrieval_mode: str
    source_locator: str
    acquired_on: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_name": self.asset_name,
            "asset_url": self.asset_url,
            "content_source": self.content_source,
            "asset_kind": self.asset_kind,
            "stable_ids": list(self.stable_ids),
            "species": self.species,
            "status": self.status,
            "reason": self.reason,
            "text": self.text,
            "byte_length": self.byte_length,
            "source_release_manifest_id": self.source_release_manifest_id,
            "source_release_version": self.source_release_version,
            "source_release_date": self.source_release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "acquired_on": self.acquired_on,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class ReactomeSnapshotProvenance:
    source: Literal["Reactome"] = "Reactome"
    source_family: str = _DEFAULT_SOURCE_FAMILY
    release_manifest_id: str = ""
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = ""
    source_locator: str = ""
    asset_names: tuple[str, ...] = ()
    asset_urls: tuple[str, ...] = ()
    asset_kinds: tuple[str, ...] = ()
    stable_ids: tuple[str, ...] = ()
    asset_count: int = 0
    content_sources: tuple[str, ...] = ()
    acquired_on: str = ""
    availability: ReactomeSnapshotAvailability = "available"
    blocker_reason: str = ""
    error: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_family": self.source_family,
            "release_manifest_id": self.release_manifest_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "asset_names": list(self.asset_names),
            "asset_urls": list(self.asset_urls),
            "asset_kinds": list(self.asset_kinds),
            "stable_ids": list(self.stable_ids),
            "asset_count": self.asset_count,
            "content_sources": list(self.content_sources),
            "acquired_on": self.acquired_on,
            "availability": self.availability,
            "blocker_reason": self.blocker_reason,
            "error": self.error,
            "manifest": dict(self.manifest),
        }


@dataclass(frozen=True, slots=True)
class ReactomeSnapshotResult:
    status: ReactomeSnapshotStatus
    reason: str
    manifest: ReactomeSnapshotManifest
    provenance: ReactomeSnapshotProvenance
    assets: tuple[ReactomeSnapshotAsset, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "manifest": self.manifest.to_dict(),
            "provenance": self.provenance.to_dict(),
            "assets": [asset.to_dict() for asset in self.assets],
        }


def acquire_reactome_snapshot(
    manifest: Mapping[str, Any] | ReactomeSnapshotManifest,
    *,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> ReactomeSnapshotResult:
    """Acquire a pinned Reactome snapshot with explicit release and asset provenance."""

    snapshot_manifest = _coerce_manifest(manifest)
    provenance = _build_provenance(snapshot_manifest, acquired_on=acquired_on)

    if snapshot_manifest.availability == "blocked":
        reason = snapshot_manifest.blocker_reason or "reactome_snapshot_blocked"
        return ReactomeSnapshotResult(
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
        reason = snapshot_manifest.blocker_reason or "reactome_snapshot_unavailable"
        return ReactomeSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=snapshot_manifest,
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                blocker_reason=reason,
            ),
        )

    assets: list[ReactomeSnapshotAsset] = []
    overall_status: ReactomeSnapshotStatus = "ok"
    overall_reason = "reactome_snapshot_acquired"

    for asset_spec in snapshot_manifest.assets:
        asset = _download_asset(
            asset_spec,
            snapshot_manifest,
            opener=opener,
            acquired_on=acquired_on or date.today().isoformat(),
        )
        assets.append(asset)
        if asset.status == "blocked":
            overall_status = "blocked"
            overall_reason = asset.reason
        elif asset.status == "unavailable" and overall_status == "ok":
            overall_status = "unavailable"
            overall_reason = asset.reason

    return ReactomeSnapshotResult(
        status=overall_status,
        reason=overall_reason,
        manifest=snapshot_manifest,
        provenance=_update_provenance(
            provenance,
            asset_names=tuple(asset.asset_name for asset in assets),
            asset_urls=tuple(asset.asset_url for asset in assets),
            asset_kinds=tuple(asset.asset_kind for asset in assets),
            stable_ids=_union_stable_ids(asset.stable_ids for asset in snapshot_manifest.assets),
            asset_count=len(assets),
            content_sources=tuple(asset.content_source for asset in assets),
            availability=overall_status,
            blocker_reason=overall_reason if overall_status != "ok" else "",
            error=_first_non_empty(asset.error for asset in assets),
        ),
        assets=tuple(assets),
    )


def _coerce_manifest(
    manifest: Mapping[str, Any] | ReactomeSnapshotManifest,
) -> ReactomeSnapshotManifest:
    if isinstance(manifest, ReactomeSnapshotManifest):
        return manifest
    return ReactomeSnapshotManifest.from_dict(manifest)


def _coerce_assets(payload: Mapping[str, Any]) -> tuple[ReactomeSnapshotAssetSpec, ...]:
    assets_payload = payload.get("assets")
    if isinstance(assets_payload, Sequence) and not isinstance(assets_payload, str):
        return tuple(
            ReactomeSnapshotAssetSpec.from_dict(asset_payload)
            for asset_payload in assets_payload
            if isinstance(asset_payload, Mapping)
        )

    asset_name = _mapping_get(payload, ("asset_name", "name"))
    asset_url = _mapping_get(payload, ("asset_url", "download_url", "url", "source_url"))
    if asset_name is None and asset_url is None:
        return ()

    stable_ids = _mapping_get(payload, ("stable_ids", "stable_id", "stable_identifier", "ids"), ())
    notes = _mapping_get(payload, ("notes", "provenance"), ())
    return (
        ReactomeSnapshotAssetSpec(
            asset_name=asset_name,
            asset_url=asset_url,
            asset_kind=_mapping_get(payload, ("asset_kind", "kind", "asset_type"), "pathway"),
            stable_ids=_clean_optional_text_values(stable_ids, "stable_ids"),
            species=_mapping_get(payload, ("species", "organism"), ""),
            notes=_clean_optional_text_values(notes, "notes"),
        ),
    )


def _download_asset(
    asset_spec: ReactomeSnapshotAssetSpec,
    manifest: ReactomeSnapshotManifest,
    *,
    opener: Callable[..., Any] | None,
    acquired_on: str,
) -> ReactomeSnapshotAsset:
    for local_artifact_ref in asset_spec.local_artifact_refs:
        path = Path(local_artifact_ref)
        if not path.is_file():
            continue
        try:
            payload = path.read_bytes()
        except OSError as exc:
            return _build_asset_record(
                asset_spec,
                manifest,
                acquired_on=acquired_on,
                status="blocked",
                reason="reactome_asset_local_read_failed",
                text="",
                content_source=f"local_artifact:{path}",
                error=str(exc),
            )
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            return _build_asset_record(
                asset_spec,
                manifest,
                acquired_on=acquired_on,
                status="blocked",
                reason="reactome_asset_local_decode_failed",
                text="",
                content_source=f"local_artifact:{path}",
                error=str(exc),
            )
        if not text.strip():
            return _build_asset_record(
                asset_spec,
                manifest,
                acquired_on=acquired_on,
                status="unavailable",
                reason="reactome_asset_empty",
                text="",
                content_source=f"local_artifact:{path}",
            )
        return _build_asset_record(
            asset_spec,
            manifest,
            acquired_on=acquired_on,
            status="ok",
            reason="reactome_asset_loaded_from_local_artifact",
            text=text,
            content_source=f"local_artifact:{path}",
        )

    if not asset_spec.asset_url:
        return _build_asset_record(
            asset_spec,
            manifest,
            acquired_on=acquired_on,
            status="blocked",
            reason="reactome_asset_requires_asset_url_or_local_artifact_refs",
            text="",
            content_source="unavailable",
        )

    request = Request(
        asset_spec.asset_url,
        headers={"User-Agent": _DEFAULT_USER_AGENT},
    )
    request_opener = opener or urlopen

    try:
        with request_opener(request, timeout=_DEFAULT_TIMEOUT) as response:
            payload = response.read()
    except HTTPError as exc:
        reason = "reactome_asset_download_failed"
        return _build_asset_record(
            asset_spec,
            manifest,
            acquired_on=acquired_on,
            status="blocked",
            reason=reason,
            text="",
            content_source=f"source_locator:{asset_spec.asset_url}",
            error=f"HTTP {exc.code}",
        )
    except (URLError, OSError) as exc:
        reason = "reactome_asset_download_failed"
        return _build_asset_record(
            asset_spec,
            manifest,
            acquired_on=acquired_on,
            status="blocked",
            reason=reason,
            text="",
            content_source=f"source_locator:{asset_spec.asset_url}",
            error=str(exc),
        )

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _build_asset_record(
            asset_spec,
            manifest,
            acquired_on=acquired_on,
            status="blocked",
            reason="reactome_asset_decode_failed",
            text="",
            content_source=f"source_locator:{asset_spec.asset_url}",
            error=str(exc),
        )
    if not text.strip():
        return _build_asset_record(
            asset_spec,
            manifest,
            acquired_on=acquired_on,
            status="unavailable",
            reason="reactome_asset_empty",
            text="",
            content_source=f"source_locator:{asset_spec.asset_url}",
        )

    return _build_asset_record(
        asset_spec,
        manifest,
        acquired_on=acquired_on,
        status="ok",
        reason="reactome_asset_downloaded",
        text=text,
        content_source=f"source_locator:{asset_spec.asset_url}",
    )


def _build_asset_record(
    asset_spec: ReactomeSnapshotAssetSpec,
    manifest: ReactomeSnapshotManifest,
    *,
    acquired_on: str,
    status: ReactomeAssetStatus,
    reason: str,
    text: str,
    content_source: str,
    error: str = "",
) -> ReactomeSnapshotAsset:
    return ReactomeSnapshotAsset(
        asset_name=asset_spec.asset_name,
        asset_url=asset_spec.asset_url,
        content_source=content_source,
        asset_kind=asset_spec.asset_kind,
        stable_ids=asset_spec.stable_ids,
        species=asset_spec.species,
        status=status,
        reason=reason,
        text=text,
        byte_length=len(text.encode("utf-8")),
        source_release_manifest_id=manifest.manifest_id,
        source_release_version=manifest.release_version or "",
        source_release_date=manifest.release_date or "",
        retrieval_mode=manifest.retrieval_mode,
        source_locator=manifest.source_locator or "",
        acquired_on=acquired_on,
        error=error,
    )


def _build_provenance(
    manifest: ReactomeSnapshotManifest,
    *,
    acquired_on: str | None,
) -> ReactomeSnapshotProvenance:
    asset_stable_ids = _union_stable_ids(asset.stable_ids for asset in manifest.assets)
    return ReactomeSnapshotProvenance(
        release_manifest_id=manifest.manifest_id,
        release_version=manifest.release_version or "",
        release_date=manifest.release_date or "",
        retrieval_mode=manifest.retrieval_mode,
        source_locator=manifest.source_locator or "",
        asset_names=tuple(asset.asset_name for asset in manifest.assets),
        asset_urls=tuple(asset.asset_url for asset in manifest.assets),
        asset_kinds=tuple(asset.asset_kind for asset in manifest.assets),
        stable_ids=asset_stable_ids,
        asset_count=len(manifest.assets),
        acquired_on=acquired_on or date.today().isoformat(),
        availability=manifest.availability,
        blocker_reason=manifest.blocker_reason,
        manifest=manifest.to_dict(),
    )


def _update_provenance(
    provenance: ReactomeSnapshotProvenance,
    *,
    asset_names: tuple[str, ...] | None = None,
    asset_urls: tuple[str, ...] | None = None,
    asset_kinds: tuple[str, ...] | None = None,
    stable_ids: tuple[str, ...] | None = None,
    asset_count: int | None = None,
    content_sources: tuple[str, ...] | None = None,
    availability: ReactomeSnapshotAvailability | None = None,
    blocker_reason: str | None = None,
    error: str | None = None,
) -> ReactomeSnapshotProvenance:
    return ReactomeSnapshotProvenance(
        source=provenance.source,
        source_family=provenance.source_family,
        release_manifest_id=provenance.release_manifest_id,
        release_version=provenance.release_version,
        release_date=provenance.release_date,
        retrieval_mode=provenance.retrieval_mode,
        source_locator=provenance.source_locator,
        asset_names=provenance.asset_names if asset_names is None else asset_names,
        asset_urls=provenance.asset_urls if asset_urls is None else asset_urls,
        asset_kinds=provenance.asset_kinds if asset_kinds is None else asset_kinds,
        stable_ids=provenance.stable_ids if stable_ids is None else stable_ids,
        asset_count=provenance.asset_count if asset_count is None else asset_count,
        content_sources=provenance.content_sources if content_sources is None else content_sources,
        acquired_on=provenance.acquired_on,
        availability=provenance.availability if availability is None else availability,
        blocker_reason=provenance.blocker_reason if blocker_reason is None else blocker_reason,
        error=provenance.error if error is None else error,
        manifest=dict(provenance.manifest),
    )


def _union_stable_ids(values: Sequence[Sequence[str]]) -> tuple[str, ...]:
    seen: set[str] = set()
    stable_ids: list[str] = []
    for group in values:
        for value in group:
            if value in seen:
                continue
            seen.add(value)
            stable_ids.append(value)
    return tuple(stable_ids)


def _first_non_empty(values: Sequence[str]) -> str:
    for value in values:
        if value:
            return value
    return ""


__all__ = [
    "ReactomeAssetStatus",
    "ReactomeSnapshotAsset",
    "ReactomeSnapshotAssetSpec",
    "ReactomeSnapshotAvailability",
    "ReactomeSnapshotManifest",
    "ReactomeSnapshotProvenance",
    "ReactomeSnapshotResult",
    "ReactomeSnapshotStatus",
    "acquire_reactome_snapshot",
]
