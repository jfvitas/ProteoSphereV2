from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

_RETRIEVAL_MODE_ALIASES: dict[str, str] = {
    "download": "download",
    "bulk_download": "download",
    "bulkdownload": "download",
    "file_download": "download",
    "ftp": "download",
    "scrape": "scrape",
    "web_scrape": "scrape",
    "webscrape": "scrape",
    "html_scrape": "scrape",
    "api": "api",
    "endpoint": "api",
    "query": "api",
}


def _clean_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _clean_list(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        item = _clean_text(value)
        if item is None or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return tuple(cleaned)


def _normalize_release_date(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError("release_date must be ISO-8601 formatted") from exc


def _normalize_retrieved_at(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _clean_text(value)


def _normalize_retrieval_mode(value: object | None) -> str:
    text = _clean_text(value)
    if text is None:
        raise ValueError("retrieval_mode is required")
    normalized = text.replace("-", "_").replace(" ", "_").casefold()
    retrieval_mode = _RETRIEVAL_MODE_ALIASES.get(normalized)
    if retrieval_mode is None:
        raise ValueError(f"unsupported retrieval_mode: {value!r}")
    return retrieval_mode


@dataclass(frozen=True, slots=True)
class RawCacheManifest:
    """Immutable manifest for pinned raw cache artifacts and rebuild inputs."""

    source_name: str
    release_version: str | None = None
    release_date: str | date | datetime | None = None
    retrieval_mode: str = "download"
    source_locator: str | None = None
    retrieved_at: str | date | datetime | None = None
    local_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    retrieval_provenance: tuple[str, ...] = field(default_factory=tuple)
    integrity_fields: tuple[str, ...] = field(default_factory=tuple)
    rebuild_metadata: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        source_name = _clean_text(self.source_name)
        release_version = _clean_text(self.release_version)
        source_locator = _clean_text(self.source_locator)
        release_date = _normalize_release_date(self.release_date)
        retrieved_at = _normalize_retrieved_at(self.retrieved_at)
        retrieval_mode = _normalize_retrieval_mode(self.retrieval_mode)
        local_artifact_refs = _clean_list(self.local_artifact_refs)
        artifact_refs = _clean_list(self.artifact_refs)
        retrieval_provenance = _clean_list(self.retrieval_provenance)
        integrity_fields = _clean_list(self.integrity_fields)
        rebuild_metadata = _clean_list(self.rebuild_metadata)

        if not source_name:
            raise ValueError("source_name is required")
        if release_version is None and release_date is None:
            raise ValueError("release_version or release_date is required")

        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "release_version", release_version)
        object.__setattr__(self, "release_date", release_date)
        object.__setattr__(self, "retrieval_mode", retrieval_mode)
        object.__setattr__(self, "source_locator", source_locator)
        object.__setattr__(self, "retrieved_at", retrieved_at)
        object.__setattr__(self, "local_artifact_refs", local_artifact_refs)
        object.__setattr__(self, "artifact_refs", artifact_refs)
        object.__setattr__(self, "retrieval_provenance", retrieval_provenance)
        object.__setattr__(self, "integrity_fields", integrity_fields)
        object.__setattr__(self, "rebuild_metadata", rebuild_metadata)

    @property
    def manifest_id(self) -> str:
        stamp = self.release_version or self.release_date or "unreleased"
        return f"{self.source_name}:{stamp}:{self.retrieval_mode}:raw"

    @property
    def has_release_stamp(self) -> bool:
        return bool(self.release_version or self.release_date)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "source_name": self.source_name,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "retrieved_at": self.retrieved_at,
            "local_artifact_refs": list(self.local_artifact_refs),
            "artifact_refs": list(self.artifact_refs),
            "retrieval_provenance": list(self.retrieval_provenance),
            "integrity_fields": list(self.integrity_fields),
            "rebuild_metadata": list(self.rebuild_metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RawCacheManifest:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=str(payload.get("source_name") or payload.get("source") or ""),
            release_version=str(
                payload.get("release_version")
                or payload.get("version")
                or payload.get("release")
                or ""
            )
            or None,
            release_date=payload.get("release_date") or payload.get("date"),
            retrieval_mode=str(payload.get("retrieval_mode") or payload.get("mode") or "download"),
            source_locator=str(
                payload.get("source_locator")
                or payload.get("source_url")
                or payload.get("url")
                or payload.get("endpoint")
                or ""
            )
            or None,
            retrieved_at=payload.get("retrieved_at")
            or payload.get("retrieval_timestamp")
            or payload.get("timestamp")
            or payload.get("retrieved"),
            local_artifact_refs=_iter_values(
                payload.get("local_artifact_refs")
                or payload.get("local_paths")
                or payload.get("paths")
                or payload.get("artifact_paths")
            ),
            artifact_refs=_iter_values(
                payload.get("artifact_refs")
                or payload.get("artifacts")
                or payload.get("source_artifact_refs")
            ),
            retrieval_provenance=_iter_values(
                payload.get("retrieval_provenance")
                or payload.get("provenance")
                or payload.get("evidence")
            ),
            integrity_fields=_iter_values(
                payload.get("integrity_fields")
                or payload.get("integrity")
                or payload.get("checksums")
                or payload.get("hashes")
                or payload.get("digests")
            ),
            rebuild_metadata=_iter_values(
                payload.get("rebuild_metadata")
                or payload.get("rebuild")
                or payload.get("reproducibility_metadata")
                or payload.get("metadata")
            ),
        )


def validate_raw_cache_manifest_payload(payload: Mapping[str, Any]) -> RawCacheManifest:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return RawCacheManifest.from_dict(payload)


__all__ = [
    "RawCacheManifest",
    "validate_raw_cache_manifest_payload",
]
