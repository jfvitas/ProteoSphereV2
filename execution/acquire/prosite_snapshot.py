from __future__ import annotations

import re
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

SOURCE_NAME = "PROSITE"
SOURCE_FAMILY = "motif"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "ProteoSphereV2-PROSITESnapshot/0.1"
PARSER_VERSION = "prosite-flatfile-v1"

PrositeSnapshotStatus = Literal["ok", "blocked", "unavailable"]

_RELEASE_BANNER_RE = re.compile(
    r"Release\s+(?P<release_version>[^\s]+)\s+of\s+(?P<release_date>[0-9A-Za-z-]+)\."
)
_DT_RE = re.compile(
    r"(?P<created>\d{2}-[A-Z]{3}-\d{4}) CREATED;\s+"
    r"(?P<data_update>\d{2}-[A-Z]{3}-\d{4}) DATA UPDATE;\s+"
    r"(?P<info_update>\d{2}-[A-Z]{3}-\d{4}) INFO UPDATE\."
)


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


def _coerce_manifest(
    manifest: SourceReleaseManifest | Mapping[str, Any],
) -> SourceReleaseManifest:
    if isinstance(manifest, SourceReleaseManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a SourceReleaseManifest or mapping")
    return validate_source_release_manifest_payload(dict(manifest))


def _load_payload(
    contract: "PrositeSnapshotContract",
    *,
    opener: Callable[..., Any] | None,
) -> tuple[bytes, str]:
    preferred: list[Path] = []
    fallback: list[Path] = []
    for artifact_ref in contract.local_artifact_refs:
        path = Path(artifact_ref)
        if not path.is_file():
            continue
        fallback.append(path)
        if path.name.casefold() == "prosite.dat" or path.suffix.casefold() == ".dat":
            preferred.append(path)

    for path in [*preferred, *fallback]:
        try:
            return path.read_bytes(), f"local_artifact:{path}"
        except OSError:
            continue

    if contract.source_locator:
        request = Request(
            contract.source_locator,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        request_opener = opener or urlopen
        with request_opener(request, timeout=DEFAULT_TIMEOUT) as response:
            return response.read(), f"source_locator:{contract.source_locator}"

    raise FileNotFoundError("no local artifact exists and no source locator was provided")


def _build_manifest_provenance(
    manifest: SourceReleaseManifest,
    *,
    acquired_on: str | None,
) -> dict[str, Any]:
    return {
        "source_name": manifest.source_name,
        "manifest_id": manifest.manifest_id,
        "snapshot_id": manifest.manifest_id,
        "release_version": manifest.release_version,
        "release_date": manifest.release_date,
        "retrieval_mode": manifest.retrieval_mode,
        "source_locator": manifest.source_locator,
        "local_artifact_refs": list(manifest.local_artifact_refs),
        "provenance": list(manifest.provenance),
        "reproducibility_metadata": list(manifest.reproducibility_metadata),
        "acquired_on": acquired_on or datetime.now(UTC).isoformat(),
    }


def _update_provenance(
    provenance: dict[str, Any],
    *,
    availability: PrositeSnapshotStatus,
    blocker_reason: str | None = None,
    unavailable_reason: str | None = None,
    error: str | None = None,
    content_source: str | None = None,
    byte_count: int | None = None,
    line_count: int | None = None,
    record_count: int | None = None,
    content_sha256: str | None = None,
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
    if byte_count is not None:
        updated["byte_count"] = byte_count
    if line_count is not None:
        updated["line_count"] = line_count
    if record_count is not None:
        updated["record_count"] = record_count
    if content_sha256 is not None:
        updated["content_sha256"] = content_sha256
    return updated


@dataclass(frozen=True, slots=True)
class PrositeSnapshotContract:
    manifest: SourceReleaseManifest
    source_name: Literal["PROSITE"] = SOURCE_NAME
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
        object.__setattr__(self, "source_name", _normalize_text(self.source_name, "source_name"))
        object.__setattr__(self, "source_family", _normalize_text(self.source_family, "source_family"))
        object.__setattr__(self, "release_version", _normalize_optional_text(self.release_version) or "")
        object.__setattr__(self, "release_date", _normalize_optional_text(self.release_date) or "")
        object.__setattr__(self, "retrieval_mode", _normalize_text(self.retrieval_mode, "retrieval_mode"))
        object.__setattr__(self, "source_locator", _normalize_optional_text(self.source_locator) or "")
        object.__setattr__(self, "local_artifact_refs", _coerce_text_values(self.local_artifact_refs))
        object.__setattr__(self, "provenance", _coerce_text_values(self.provenance))
        object.__setattr__(
            self,
            "reproducibility_metadata",
            _coerce_text_values(self.reproducibility_metadata),
        )
        object.__setattr__(
            self,
            "manifest_id",
            _normalize_optional_text(self.manifest_id) or self.manifest.manifest_id,
        )

    @property
    def snapshot_id(self) -> str:
        return self.manifest_id

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
class PrositeMotifRecord:
    accession: str
    identifier: str
    motif_type: str
    description: str
    pattern: str
    release_version: str
    release_date: str
    created_date: str = ""
    data_update_date: str = ""
    info_update_date: str = ""
    profile_accession: str = ""
    doc_accession: str = ""
    comments: tuple[str, ...] = field(default_factory=tuple)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_entry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "identifier": self.identifier,
            "motif_type": self.motif_type,
            "description": self.description,
            "pattern": self.pattern,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "created_date": self.created_date,
            "data_update_date": self.data_update_date,
            "info_update_date": self.info_update_date,
            "profile_accession": self.profile_accession,
            "doc_accession": self.doc_accession,
            "comments": list(self.comments),
            "provenance": dict(self.provenance),
            "raw_entry": dict(self.raw_entry),
        }


@dataclass(frozen=True, slots=True)
class PrositeSnapshot:
    source_name: Literal["PROSITE"] = SOURCE_NAME
    source_family: str = SOURCE_FAMILY
    manifest_id: str = ""
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = "download"
    content_source: str = ""
    content_sha256: str = ""
    byte_count: int = 0
    line_count: int = 0
    record_count: int = 0
    raw_text: str = ""
    records: tuple[PrositeMotifRecord, ...] = field(default_factory=tuple)
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
            "raw_text": self.raw_text,
            "records": [record.to_dict() for record in self.records],
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class PrositeSnapshotResult:
    status: PrositeSnapshotStatus
    reason: str
    manifest: SourceReleaseManifest
    contract: PrositeSnapshotContract | None = None
    snapshot: PrositeSnapshot | None = None
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


def _parse_release_banner(raw_text: str) -> tuple[str, str]:
    for raw_line in raw_text.splitlines():
        match = _RELEASE_BANNER_RE.search(raw_line.strip())
        if match is not None:
            return match.group("release_version"), match.group("release_date")
    return "", ""


def _parse_dt_fields(value: str) -> tuple[str, str, str]:
    match = _DT_RE.search(value)
    if match is None:
        return "", "", ""
    return match.group("created"), match.group("data_update"), match.group("info_update")


def _parse_prosite_entries(
    raw_text: str,
    *,
    release_version: str,
    release_date: str,
) -> tuple[PrositeMotifRecord, ...]:
    records: list[PrositeMotifRecord] = []
    current: dict[str, Any] = {}
    current_key: str | None = None

    def emit() -> None:
        nonlocal current
        if not current:
            return
        accession = _normalize_optional_text(current.get("accession")) or ""
        identifier = _normalize_optional_text(current.get("identifier")) or ""
        description = _normalize_optional_text(current.get("description")) or ""
        pattern = _normalize_optional_text(current.get("pattern")) or ""
        if not accession or not identifier or not pattern:
            current = {}
            return
        dt_raw = _normalize_optional_text(current.get("dt")) or ""
        created_date, data_update_date, info_update_date = _parse_dt_fields(dt_raw)
        records.append(
            PrositeMotifRecord(
                accession=accession,
                identifier=identifier,
                motif_type=_normalize_optional_text(current.get("motif_type")) or "",
                description=description,
                pattern=pattern,
                release_version=release_version,
                release_date=release_date,
                created_date=created_date,
                data_update_date=data_update_date,
                info_update_date=info_update_date,
                profile_accession=_normalize_optional_text(current.get("profile_accession")) or "",
                doc_accession=_normalize_optional_text(current.get("doc_accession")) or "",
                comments=tuple(current.get("comments", ())),
                provenance=dict(current.get("provenance", {})),
                raw_entry=dict(current),
            )
        )
        current = {}

    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped == "//":
            emit()
            current_key = None
            continue
        if not stripped:
            continue
        if line.startswith("CC   Release "):
            continue
        if line.startswith(" ") and current_key in {"description", "pattern", "comments", "dt"}:
            fragment = stripped
            if current_key == "comments":
                current.setdefault("comments", []).append(fragment)
            else:
                current[current_key] = f"{current.get(current_key, '')} {fragment}".strip()
            continue

        code = line[:2]
        payload = line[5:].strip() if len(line) >= 5 else ""
        current_key = None

        if code == "ID":
            name, _, motif_type = payload.partition(";")
            current["identifier"] = name.strip()
            current["motif_type"] = motif_type.strip().rstrip(".")
        elif code == "AC":
            current["accession"] = payload.rstrip(";")
        elif code == "DE":
            current["description"] = payload
            current_key = "description"
        elif code == "PA":
            current["pattern"] = payload.rstrip(".")
            current_key = "pattern"
        elif code == "DT":
            current["dt"] = payload
            current_key = "dt"
        elif code == "CC":
            current.setdefault("comments", []).append(payload.rstrip(";"))
            current_key = "comments"
        elif code == "PR":
            current["profile_accession"] = payload.rstrip(";")
        elif code == "DO":
            current["doc_accession"] = payload.rstrip(";")

    emit()
    return tuple(records)


def acquire_prosite_snapshot(
    manifest: SourceReleaseManifest | Mapping[str, Any] | None,
    *,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> PrositeSnapshotResult:
    manifest_data = _coerce_manifest(manifest or {})
    manifest_provenance = _build_manifest_provenance(manifest_data, acquired_on=acquired_on)
    contract = PrositeSnapshotContract(
        manifest=manifest_data,
        release_version=manifest_data.release_version or "",
        release_date=manifest_data.release_date or "",
        retrieval_mode=manifest_data.retrieval_mode,
        source_locator=manifest_data.source_locator or "",
        local_artifact_refs=manifest_data.local_artifact_refs,
        provenance=manifest_data.provenance,
        reproducibility_metadata=manifest_data.reproducibility_metadata,
    )

    if not contract.source_locator and not contract.local_artifact_refs:
        reason = "prosite_manifest_needs_source_locator_or_local_artifact_refs"
        return PrositeSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=manifest_data,
            contract=contract,
            blocker_reason=reason,
            provenance=_update_provenance(
                manifest_provenance,
                availability="blocked",
                blocker_reason=reason,
            ),
        )

    try:
        payload, content_source = _load_payload(contract, opener=opener)
    except FileNotFoundError as exc:
        reason = "prosite_local_artifact_unavailable"
        return PrositeSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=manifest_data,
            contract=contract,
            blocker_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                manifest_provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
            ),
        )
    except (HTTPError, URLError) as exc:
        reason = "prosite_request_failed"
        return PrositeSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=manifest_data,
            contract=contract,
            blocker_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                manifest_provenance,
                availability="blocked",
                blocker_reason=reason,
                error=str(exc),
            ),
        )

    if not payload:
        reason = "prosite_empty_payload"
        return PrositeSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=manifest_data,
            contract=contract,
            unavailable_reason=reason,
            provenance=_update_provenance(
                manifest_provenance,
                availability="unavailable",
                unavailable_reason=reason,
                content_source=content_source,
                byte_count=0,
                line_count=0,
                record_count=0,
            ),
        )

    try:
        raw_text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        reason = "prosite_payload_not_utf8"
        return PrositeSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=manifest_data,
            contract=contract,
            unavailable_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                manifest_provenance,
                availability="unavailable",
                unavailable_reason=reason,
                error=str(exc),
                content_source=content_source,
                byte_count=len(payload),
                line_count=0,
                record_count=0,
            ),
        )

    line_count = len(raw_text.splitlines())
    parsed_release_version, parsed_release_date = _parse_release_banner(raw_text)
    release_version = contract.release_version or parsed_release_version
    release_date = contract.release_date or parsed_release_date
    records = _parse_prosite_entries(
        raw_text,
        release_version=release_version,
        release_date=release_date,
    )
    if not records:
        reason = "prosite_no_motif_records"
        return PrositeSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=manifest_data,
            contract=contract,
            unavailable_reason=reason,
            provenance=_update_provenance(
                manifest_provenance,
                availability="unavailable",
                unavailable_reason=reason,
                content_source=content_source,
                byte_count=len(payload),
                line_count=line_count,
                record_count=0,
            ),
        )

    content_hash = sha256(payload).hexdigest()
    snapshot = PrositeSnapshot(
        manifest_id=contract.manifest_id,
        release_version=release_version,
        release_date=release_date,
        retrieval_mode=contract.retrieval_mode,
        content_source=content_source,
        content_sha256=content_hash,
        byte_count=len(payload),
        line_count=line_count,
        record_count=len(records),
        raw_text=raw_text,
        records=records,
        provenance=_update_provenance(
            manifest_provenance,
            availability="ok",
            content_source=content_source,
            byte_count=len(payload),
            line_count=line_count,
            record_count=len(records),
            content_sha256=content_hash,
        ),
    )
    snapshot.provenance["parser_version"] = PARSER_VERSION
    snapshot.provenance["source_name"] = contract.source_name
    snapshot.provenance["source_family"] = contract.source_family
    snapshot.provenance["release_version"] = release_version
    snapshot.provenance["release_date"] = release_date

    return PrositeSnapshotResult(
        status="ok",
        reason="prosite_snapshot_acquired",
        manifest=manifest_data,
        contract=contract,
        snapshot=snapshot,
        provenance=snapshot.provenance,
    )


__all__ = [
    "PARSER_VERSION",
    "PrositeMotifRecord",
    "PrositeSnapshot",
    "PrositeSnapshotContract",
    "PrositeSnapshotResult",
    "PrositeSnapshotStatus",
    "SOURCE_FAMILY",
    "SOURCE_NAME",
    "acquire_prosite_snapshot",
]
