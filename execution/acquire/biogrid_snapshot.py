from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)

SOURCE_NAME = "BioGRID"
SOURCE_FAMILY = "interaction"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "ProteoSphereV2-BioGRIDSnapshot/0.1"
PARSER_VERSION = "biogrid-tabular-text-v1"

BioGRIDSnapshotStatus = Literal["ok", "blocked", "unavailable"]


def _normalize_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _coerce_text_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _coerce_manifest(manifest: SourceReleaseManifest | Mapping[str, Any]) -> SourceReleaseManifest:
    if isinstance(manifest, SourceReleaseManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a SourceReleaseManifest or mapping")
    return validate_source_release_manifest_payload(dict(manifest))


def _normalize_manifest_source(manifest: SourceReleaseManifest) -> bool:
    return manifest.source_name.casefold() == SOURCE_NAME.casefold()


def _normalize_content(text: str) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    header: tuple[str, ...] = ()
    records: list[tuple[str, ...]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            candidate = line.lstrip("#").strip()
            if candidate and not header and "\t" in candidate:
                header = tuple(part.strip() for part in candidate.split("\t"))
            continue
        cells = tuple(part.strip() for part in raw_line.split("\t"))
        records.append(cells)

    return header, tuple(records)


def _read_local_artifact(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes()


def _fetch_remote_payload(
    source_locator: str,
    *,
    opener: Callable[..., Any] | None,
) -> bytes:
    request = Request(
        source_locator,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    request_opener = opener or urlopen
    with request_opener(request, timeout=DEFAULT_TIMEOUT) as response:
        return response.read()


@dataclass(frozen=True, slots=True)
class BioGRIDSnapshotContract:
    """Normalized acquisition contract for a pinned BioGRID interaction snapshot."""

    manifest: SourceReleaseManifest
    source_name: Literal["BioGRID"] = SOURCE_NAME
    source_family: str = SOURCE_FAMILY
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = "download"
    source_locator: str = ""
    local_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)
    reproducibility_metadata: tuple[str, ...] = field(default_factory=tuple)
    manifest_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "release_version",
            _normalize_optional_text(self.release_version) or "",
        )
        object.__setattr__(
            self,
            "release_date",
            _normalize_optional_text(self.release_date) or "",
        )
        object.__setattr__(
            self,
            "retrieval_mode",
            _normalize_text(self.retrieval_mode, "retrieval_mode"),
        )
        object.__setattr__(
            self,
            "source_locator",
            _normalize_optional_text(self.source_locator) or "",
        )
        object.__setattr__(
            self,
            "local_artifact_refs",
            _coerce_text_values(self.local_artifact_refs),
        )
        object.__setattr__(self, "provenance", _coerce_text_values(self.provenance))
        object.__setattr__(
            self,
            "reproducibility_metadata",
            _coerce_text_values(self.reproducibility_metadata),
        )
        manifest_id = _normalize_optional_text(self.manifest_id) or self.manifest.manifest_id
        object.__setattr__(self, "manifest_id", manifest_id)

    @property
    def snapshot_id(self) -> str:
        return self.manifest_id

    @property
    def release_stamp(self) -> str:
        return self.release_version or self.release_date or ""

    @property
    def has_local_artifact_refs(self) -> bool:
        return bool(self.local_artifact_refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "source_name": self.source_name,
            "source_family": self.source_family,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "local_artifact_refs": list(self.local_artifact_refs),
            "provenance": list(self.provenance),
            "reproducibility_metadata": list(self.reproducibility_metadata),
            "manifest_id": self.manifest_id,
            "snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True, slots=True)
class BioGRIDSnapshot:
    """Parsed BioGRID snapshot payload with provenance-preserving metadata."""

    source_name: Literal["BioGRID"] = SOURCE_NAME
    source_family: str = SOURCE_FAMILY
    manifest_id: str = ""
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = "download"
    content_source: str = ""
    content_sha256: str = ""
    byte_count: int = 0
    line_count: int = 0
    header: tuple[str, ...] = field(default_factory=tuple)
    records: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    raw_text: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_family": self.source_family,
            "manifest_id": self.manifest_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "content_source": self.content_source,
            "content_sha256": self.content_sha256,
            "byte_count": self.byte_count,
            "line_count": self.line_count,
            "record_count": self.record_count,
            "header": list(self.header),
            "records": [list(record) for record in self.records],
            "raw_text": self.raw_text,
            "provenance": dict(self.provenance),
        }

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass(frozen=True, slots=True)
class BioGRIDSnapshotResult:
    """Result wrapper that reports acquisition status honestly."""

    status: BioGRIDSnapshotStatus
    reason: str
    manifest: SourceReleaseManifest
    contract: BioGRIDSnapshotContract | None = None
    snapshot: BioGRIDSnapshot | None = None
    blocker_reason: str = ""
    unavailable_reason: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "manifest": self.manifest.to_dict(),
            "contract": self.contract.to_dict() if self.contract is not None else None,
            "snapshot": self.snapshot.to_dict() if self.snapshot is not None else None,
            "blocker_reason": self.blocker_reason,
            "unavailable_reason": self.unavailable_reason,
            "provenance": dict(self.provenance),
        }


def acquire_biogrid_snapshot(
    manifest: SourceReleaseManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> BioGRIDSnapshotResult:
    """Acquire a pinned BioGRID snapshot without pretending unavailable content exists."""

    normalized_manifest = _coerce_manifest(manifest)
    provenance = _build_manifest_provenance(normalized_manifest, acquired_on=acquired_on)

    if not _normalize_manifest_source(normalized_manifest):
        reason = "biogrid_manifest_source_mismatch"
        return BioGRIDSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            blocker_reason=reason,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
            ),
        )

    contract = BioGRIDSnapshotContract(
        manifest=normalized_manifest,
        release_version=normalized_manifest.release_version or "",
        release_date=normalized_manifest.release_date or "",
        retrieval_mode=normalized_manifest.retrieval_mode,
        source_locator=normalized_manifest.source_locator or "",
        local_artifact_refs=normalized_manifest.local_artifact_refs,
        provenance=normalized_manifest.provenance,
        reproducibility_metadata=normalized_manifest.reproducibility_metadata,
    )

    if not contract.source_locator and not contract.local_artifact_refs:
        reason = "biogrid_manifest_needs_source_locator_or_local_artifact_refs"
        return BioGRIDSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            blocker_reason=reason,
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
            ),
        )

    try:
        payload, content_source = _load_snapshot_payload(contract, opener=opener)
    except OSError as exc:
        reason = "biogrid_local_artifact_unavailable"
        return BioGRIDSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            blocker_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
            ),
        )
    except (HTTPError, URLError) as exc:
        reason = "biogrid_request_failed"
        return BioGRIDSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            blocker_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
            ),
        )

    if not payload:
        reason = "biogrid_empty_payload"
        return BioGRIDSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            unavailable_reason=reason,
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                unavailable_reason=reason,
                content_source=content_source,
                record_count=0,
            ),
        )

    try:
        raw_text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        reason = "biogrid_payload_not_utf8"
        return BioGRIDSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            unavailable_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                unavailable_reason=reason,
                error=str(exc),
                content_source=content_source,
                record_count=0,
            ),
        )

    header, records = _normalize_content(raw_text)
    if not records:
        reason = "biogrid_no_interaction_rows"
        return BioGRIDSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            unavailable_reason=reason,
            provenance=_update_provenance(
                provenance,
                availability="unavailable",
                unavailable_reason=reason,
                content_source=content_source,
                line_count=len(raw_text.splitlines()),
                record_count=0,
            ),
        )

    content_hash = sha256(payload).hexdigest()
    line_count = len(raw_text.splitlines())
    snapshot = BioGRIDSnapshot(
        manifest_id=contract.manifest_id,
        release_version=contract.release_version,
        release_date=contract.release_date,
        retrieval_mode=contract.retrieval_mode,
        content_source=content_source,
        content_sha256=content_hash,
        byte_count=len(payload),
        line_count=line_count,
        header=header,
        records=records,
        raw_text=raw_text,
        provenance=_build_snapshot_provenance(
            contract,
            provenance,
            acquired_on=acquired_on,
            content_source=content_source,
            content_sha256=content_hash,
            byte_count=len(payload),
            line_count=line_count,
            record_count=len(records),
        ),
    )
    return BioGRIDSnapshotResult(
        status="ok",
        reason="biogrid_snapshot_acquired",
        manifest=normalized_manifest,
        contract=contract,
        snapshot=snapshot,
        provenance=snapshot.provenance,
    )


def _load_snapshot_payload(
    contract: BioGRIDSnapshotContract,
    *,
    opener: Callable[..., Any] | None,
) -> tuple[bytes, str]:
    for artifact_ref in contract.local_artifact_refs:
        path = Path(artifact_ref)
        payload = _read_local_artifact(path)
        if payload is not None:
            return payload, f"local_artifact:{path}"

    if contract.source_locator:
        payload = _fetch_remote_payload(contract.source_locator, opener=opener)
        return payload, f"source_locator:{contract.source_locator}"

    raise FileNotFoundError("no local artifact exists and no source locator was provided")


def _build_manifest_provenance(
    manifest: SourceReleaseManifest,
    *,
    acquired_on: str | None,
) -> dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "source_family": SOURCE_FAMILY,
        "manifest_id": manifest.manifest_id,
        "snapshot_id": manifest.manifest_id,
        "source_name": manifest.source_name,
        "release_version": manifest.release_version,
        "release_date": manifest.release_date,
        "retrieval_mode": manifest.retrieval_mode,
        "source_locator": manifest.source_locator,
        "local_artifact_refs": list(manifest.local_artifact_refs),
        "provenance": list(manifest.provenance),
        "reproducibility_metadata": list(manifest.reproducibility_metadata),
        "acquired_on": acquired_on or datetime.now(UTC).isoformat(),
    }


def _build_snapshot_provenance(
    contract: BioGRIDSnapshotContract,
    manifest_provenance: dict[str, Any],
    *,
    acquired_on: str | None,
    content_source: str,
    content_sha256: str,
    byte_count: int,
    line_count: int,
    record_count: int,
) -> dict[str, Any]:
    provenance = dict(manifest_provenance)
    provenance.update(
        {
            "source": SOURCE_NAME,
            "source_family": SOURCE_FAMILY,
            "manifest_id": contract.manifest_id,
            "snapshot_id": contract.snapshot_id,
            "release_version": contract.release_version,
            "release_date": contract.release_date,
            "retrieval_mode": contract.retrieval_mode,
            "content_source": content_source,
            "content_sha256": content_sha256,
            "byte_count": byte_count,
            "line_count": line_count,
            "record_count": record_count,
            "parser_version": PARSER_VERSION,
        }
    )
    if acquired_on is not None:
        provenance["acquired_on"] = acquired_on
    return provenance


def _update_provenance(
    provenance: dict[str, Any],
    *,
    availability: BioGRIDSnapshotStatus,
    blocker_reason: str | None = None,
    unavailable_reason: str | None = None,
    error: str | None = None,
    content_source: str | None = None,
    line_count: int | None = None,
    record_count: int | None = None,
) -> dict[str, Any]:
    updated = dict(provenance)
    updated["availability"] = availability
    if blocker_reason is not None:
        updated["blocker_reason"] = blocker_reason
    if unavailable_reason is not None:
        updated["unavailable_reason"] = unavailable_reason
    if error is not None:
        updated["error"] = error
    if content_source is not None:
        updated["content_source"] = content_source
    if line_count is not None:
        updated["line_count"] = line_count
    if record_count is not None:
        updated["record_count"] = record_count
    return updated


__all__ = [
    "BioGRIDSnapshot",
    "BioGRIDSnapshotContract",
    "BioGRIDSnapshotResult",
    "BioGRIDSnapshotStatus",
    "SOURCE_FAMILY",
    "SOURCE_NAME",
    "acquire_biogrid_snapshot",
]
