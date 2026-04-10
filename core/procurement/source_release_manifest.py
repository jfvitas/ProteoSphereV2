from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
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


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _stable_checksum(payload: dict[str, Any]) -> str:
    blob = json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
class SourceReleaseManifest:
    """Immutable manifest for pinned source releases and scrape runs."""

    source_name: str
    release_version: str | None = None
    release_date: str | date | datetime | None = None
    retrieval_mode: str = "download"
    source_locator: str | None = None
    local_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)
    reproducibility_metadata: tuple[str, ...] = field(default_factory=tuple)
    snapshot_fingerprint: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        source_name = _clean_text(self.source_name)
        release_version = _clean_text(self.release_version)
        source_locator = _clean_text(self.source_locator)
        release_date = _normalize_release_date(self.release_date)
        retrieval_mode = _normalize_retrieval_mode(self.retrieval_mode)
        local_artifact_refs = _clean_list(self.local_artifact_refs)
        provenance = _clean_list(self.provenance)
        reproducibility_metadata = _clean_list(self.reproducibility_metadata)

        if not source_name:
            raise ValueError("source_name is required")
        if release_version is None and release_date is None:
            raise ValueError("release_version or release_date is required")

        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "release_version", release_version)
        object.__setattr__(self, "release_date", release_date)
        object.__setattr__(self, "retrieval_mode", retrieval_mode)
        object.__setattr__(self, "source_locator", source_locator)
        object.__setattr__(self, "local_artifact_refs", local_artifact_refs)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "reproducibility_metadata", reproducibility_metadata)
        object.__setattr__(
            self,
            "snapshot_fingerprint",
            _stable_checksum(
                {
                    "source_name": source_name,
                    "release_version": release_version,
                    "release_date": release_date,
                    "retrieval_mode": retrieval_mode,
                    "source_locator": source_locator,
                    "local_artifact_refs": local_artifact_refs,
                    "provenance": provenance,
                    "reproducibility_metadata": reproducibility_metadata,
                }
            )[:16],
        )

    @property
    def manifest_id(self) -> str:
        stamp = self.release_version or self.release_date or "unreleased"
        return f"{self.source_name}:{stamp}:{self.retrieval_mode}:{self.snapshot_fingerprint}"

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
            "local_artifact_refs": list(self.local_artifact_refs),
            "provenance": list(self.provenance),
            "reproducibility_metadata": list(self.reproducibility_metadata),
            "snapshot_fingerprint": self.snapshot_fingerprint,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SourceReleaseManifest:
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
                or ""
            )
            or None,
            local_artifact_refs=_iter_values(
                payload.get("local_artifact_refs")
                or payload.get("artifact_refs")
                or payload.get("artifacts")
            ),
            provenance=_iter_values(payload.get("provenance") or payload.get("evidence")),
            reproducibility_metadata=_iter_values(
                payload.get("reproducibility_metadata")
                or payload.get("reproducibility")
                or payload.get("metadata")
            ),
        )


def validate_source_release_manifest_payload(payload: dict[str, Any]) -> SourceReleaseManifest:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")
    return SourceReleaseManifest.from_dict(payload)


__all__ = [
    "SourceReleaseManifest",
    "validate_source_release_manifest_payload",
]
