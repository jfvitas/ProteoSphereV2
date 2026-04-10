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

SOURCE_FAMILY_MOTIF = "motif"
SOURCE_FAMILY_RELATED = "related"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "ProteoSphereV2-InterProMotifSnapshot/0.1"
PARSER_VERSION = "interpro-motif-text-v1"

InterProMotifSnapshotStatus = Literal["ok", "blocked", "unavailable"]

_SOURCE_PROFILES: dict[str, dict[str, Any]] = {
    "interpro": {
        "source_name": "InterPro",
        "source_family": SOURCE_FAMILY_MOTIF,
        "target_id": "motif_interpro_entry",
        "source_locator_prefix": "https://www.ebi.ac.uk/interpro/entry/",
        "provenance_rules": (
            "prefer accession-scoped entry pages over directory navigation",
            "retain member-database back-links as provenance",
        ),
        "reproducibility_rules": (
            "capture the exact InterPro entry accession",
            "avoid broad entry listing pages",
        ),
    },
    "prosite": {
        "source_name": "PROSITE",
        "source_family": SOURCE_FAMILY_MOTIF,
        "target_id": "motif_prosite_details",
        "source_locator_prefix": "https://prosite.expasy.org/",
        "provenance_rules": (
            "record the pattern or profile accession",
            "keep documentation page references separate from motif calls",
        ),
        "reproducibility_rules": (
            "pin the PROSITE release or documentation timestamp when available",
            "capture the exact accessioned page only",
        ),
    },
    "elm": {
        "source_name": "ELM",
        "source_family": SOURCE_FAMILY_MOTIF,
        "target_id": "motif_elm_class",
        "source_locator_prefix": "https://elm.eu.org/elms/elmPages/",
        "provenance_rules": (
            "record the ELM class accession and instance evidence count",
            "preserve organism and partner-context hints where present",
        ),
        "reproducibility_rules": (
            "capture the class page accession only",
            "avoid exploratory traversal across unrelated ELM pages",
        ),
    },
    "rcsb": {
        "source_name": "RCSB",
        "source_family": SOURCE_FAMILY_RELATED,
        "target_id": "related_rcsb_sequence_motif_search",
        "source_locator_prefix": "https://www.rcsb.org/search?",
        "provenance_rules": (
            "record the exact motif query and search filters",
            "preserve the matched structure identifiers and residue spans",
        ),
        "reproducibility_rules": (
            "record the search parameters verbatim",
            "do not expand search results beyond the requested query scope",
        ),
    },
}


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


def _normalize_source_key(value: str) -> str:
    return value.strip().casefold()


def _resolve_source_profile(
    manifest: SourceReleaseManifest,
) -> tuple[dict[str, Any] | None, str | None]:
    profile = _SOURCE_PROFILES.get(_normalize_source_key(manifest.source_name))
    if profile is None:
        return None, "interpro_motif_unsupported_source"

    locator = _normalize_optional_text(manifest.source_locator)
    prefix = profile["source_locator_prefix"]
    if locator and not locator.casefold().startswith(prefix.casefold()):
        return None, "interpro_motif_source_locator_prefix_mismatch"
    return profile, None


def _load_payload(
    contract: InterProMotifSnapshotContract,
    *,
    opener: Callable[..., Any] | None,
) -> tuple[bytes, str]:
    for artifact_ref in contract.local_artifact_refs:
        path = Path(artifact_ref)
        if not path.is_file():
            continue
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
    availability: InterProMotifSnapshotStatus,
    blocker_reason: str | None = None,
    unavailable_reason: str | None = None,
    error: str | None = None,
    content_source: str | None = None,
    line_count: int | None = None,
    nonempty_line_count: int | None = None,
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
    if line_count is not None:
        updated["line_count"] = line_count
    if nonempty_line_count is not None:
        updated["nonempty_line_count"] = nonempty_line_count
    if content_sha256 is not None:
        updated["content_sha256"] = content_sha256
    return updated


@dataclass(frozen=True, slots=True)
class InterProMotifSnapshotContract:
    """Normalized acquisition contract for InterPro and approved motif sources."""

    manifest: SourceReleaseManifest
    requested_source_name: str
    source_name: str
    source_family: str
    target_id: str
    source_locator_prefix: str
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = "download"
    source_locator: str = ""
    local_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)
    reproducibility_metadata: tuple[str, ...] = field(default_factory=tuple)
    provenance_rules: tuple[str, ...] = field(default_factory=tuple)
    reproducibility_rules: tuple[str, ...] = field(default_factory=tuple)
    manifest_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requested_source_name",
            _normalize_text(self.requested_source_name, "requested_source_name"),
        )
        object.__setattr__(
            self,
            "source_name",
            _normalize_text(self.source_name, "source_name"),
        )
        object.__setattr__(
            self,
            "source_family",
            _normalize_text(self.source_family, "source_family"),
        )
        object.__setattr__(
            self,
            "target_id",
            _normalize_text(self.target_id, "target_id"),
        )
        object.__setattr__(
            self,
            "source_locator_prefix",
            _normalize_text(self.source_locator_prefix, "source_locator_prefix"),
        )
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
        object.__setattr__(self, "provenance_rules", _coerce_text_values(self.provenance_rules))
        object.__setattr__(
            self,
            "reproducibility_rules",
            _coerce_text_values(self.reproducibility_rules),
        )
        manifest_id = _normalize_optional_text(self.manifest_id) or self.manifest.manifest_id
        object.__setattr__(self, "manifest_id", manifest_id)

    @property
    def snapshot_id(self) -> str:
        return self.manifest_id

    @property
    def has_local_artifact_refs(self) -> bool:
        return bool(self.local_artifact_refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "requested_source_name": self.requested_source_name,
            "source_name": self.source_name,
            "source_family": self.source_family,
            "target_id": self.target_id,
            "source_locator_prefix": self.source_locator_prefix,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "local_artifact_refs": list(self.local_artifact_refs),
            "provenance": list(self.provenance),
            "reproducibility_metadata": list(self.reproducibility_metadata),
            "provenance_rules": list(self.provenance_rules),
            "reproducibility_rules": list(self.reproducibility_rules),
            "manifest_id": self.manifest_id,
            "snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True, slots=True)
class InterProMotifSnapshot:
    """Text snapshot payload for InterPro and approved motif sources."""

    source_name: str
    requested_source_name: str
    source_family: str
    target_id: str
    manifest_id: str
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = "download"
    source_locator: str = ""
    source_locator_prefix: str = ""
    content_source: str = ""
    content_sha256: str = ""
    byte_count: int = 0
    line_count: int = 0
    nonempty_line_count: int = 0
    raw_text: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "requested_source_name": self.requested_source_name,
            "source_family": self.source_family,
            "target_id": self.target_id,
            "manifest_id": self.manifest_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "retrieval_mode": self.retrieval_mode,
            "source_locator": self.source_locator,
            "source_locator_prefix": self.source_locator_prefix,
            "content_source": self.content_source,
            "content_sha256": self.content_sha256,
            "byte_count": self.byte_count,
            "line_count": self.line_count,
            "nonempty_line_count": self.nonempty_line_count,
            "raw_text": self.raw_text,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class InterProMotifSnapshotResult:
    """Result wrapper that reports acquisition status honestly."""

    status: InterProMotifSnapshotStatus
    reason: str
    manifest: SourceReleaseManifest
    contract: InterProMotifSnapshotContract | None = None
    snapshot: InterProMotifSnapshot | None = None
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


def acquire_interpro_motif_snapshot(
    manifest: SourceReleaseManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> InterProMotifSnapshotResult:
    """Acquire an InterPro or approved motif snapshot without faking success."""

    normalized_manifest = _coerce_manifest(manifest)
    manifest_provenance = _build_manifest_provenance(
        normalized_manifest,
        acquired_on=acquired_on,
    )
    profile, blocker_reason = _resolve_source_profile(normalized_manifest)
    if profile is None:
        reason = blocker_reason or "interpro_motif_unsupported_source"
        return InterProMotifSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
            blocker_reason=reason,
            provenance=_update_provenance(
                manifest_provenance,
                availability="blocked",
                blocker_reason=reason,
            ),
        )

    contract = InterProMotifSnapshotContract(
        manifest=normalized_manifest,
        requested_source_name=normalized_manifest.source_name,
        source_name=profile["source_name"],
        source_family=profile["source_family"],
        target_id=profile["target_id"],
        source_locator_prefix=profile["source_locator_prefix"],
        release_version=normalized_manifest.release_version or "",
        release_date=normalized_manifest.release_date or "",
        retrieval_mode=normalized_manifest.retrieval_mode,
        source_locator=normalized_manifest.source_locator or "",
        local_artifact_refs=normalized_manifest.local_artifact_refs,
        provenance=normalized_manifest.provenance,
        reproducibility_metadata=normalized_manifest.reproducibility_metadata,
        provenance_rules=profile["provenance_rules"],
        reproducibility_rules=profile["reproducibility_rules"],
    )

    if not contract.source_locator and not contract.local_artifact_refs:
        reason = "interpro_motif_manifest_needs_source_locator_or_local_artifact_refs"
        return InterProMotifSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
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
        reason = "interpro_motif_local_artifact_unavailable"
        return InterProMotifSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
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
        reason = "interpro_motif_request_failed"
        return InterProMotifSnapshotResult(
            status="blocked",
            reason=reason,
            manifest=normalized_manifest,
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
        reason = "interpro_motif_empty_payload"
        return InterProMotifSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            unavailable_reason=reason,
            provenance=_update_provenance(
                manifest_provenance,
                availability="unavailable",
                unavailable_reason=reason,
                content_source=content_source,
                line_count=0,
                nonempty_line_count=0,
            ),
        )

    try:
        raw_text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        reason = "interpro_motif_payload_not_utf8"
        return InterProMotifSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            unavailable_reason=f"{reason}: {exc}",
            provenance=_update_provenance(
                manifest_provenance,
                availability="unavailable",
                unavailable_reason=reason,
                error=str(exc),
                content_source=content_source,
                line_count=0,
                nonempty_line_count=0,
            ),
        )

    line_count = len(raw_text.splitlines())
    nonempty_line_count = sum(1 for line in raw_text.splitlines() if line.strip())
    if nonempty_line_count == 0:
        reason = "interpro_motif_empty_payload"
        return InterProMotifSnapshotResult(
            status="unavailable",
            reason=reason,
            manifest=normalized_manifest,
            contract=contract,
            unavailable_reason=reason,
            provenance=_update_provenance(
                manifest_provenance,
                availability="unavailable",
                unavailable_reason=reason,
                content_source=content_source,
                line_count=line_count,
                nonempty_line_count=nonempty_line_count,
            ),
        )

    content_hash = sha256(payload).hexdigest()
    snapshot = InterProMotifSnapshot(
        source_name=contract.source_name,
        requested_source_name=contract.requested_source_name,
        source_family=contract.source_family,
        target_id=contract.target_id,
        manifest_id=contract.manifest_id,
        release_version=contract.release_version,
        release_date=contract.release_date,
        retrieval_mode=contract.retrieval_mode,
        source_locator=contract.source_locator,
        source_locator_prefix=contract.source_locator_prefix,
        content_source=content_source,
        content_sha256=content_hash,
        byte_count=len(payload),
        line_count=line_count,
        nonempty_line_count=nonempty_line_count,
        raw_text=raw_text,
        provenance=_update_provenance(
            manifest_provenance,
            availability="ok",
            content_source=content_source,
            line_count=line_count,
            nonempty_line_count=nonempty_line_count,
            content_sha256=content_hash,
        ),
    )
    snapshot.provenance["source_name"] = contract.source_name
    snapshot.provenance["requested_source_name"] = contract.requested_source_name
    snapshot.provenance["source_family"] = contract.source_family
    snapshot.provenance["target_id"] = contract.target_id
    snapshot.provenance["source_locator_prefix"] = contract.source_locator_prefix
    snapshot.provenance["provenance_rules"] = list(contract.provenance_rules)
    snapshot.provenance["reproducibility_rules"] = list(contract.reproducibility_rules)
    snapshot.provenance["parser_version"] = PARSER_VERSION

    return InterProMotifSnapshotResult(
        status="ok",
        reason="interpro_motif_snapshot_acquired",
        manifest=normalized_manifest,
        contract=contract,
        snapshot=snapshot,
        provenance=snapshot.provenance,
    )


def _build_manifest_provenance(
    manifest: SourceReleaseManifest,
    *,
    acquired_on: str | None,
) -> dict[str, Any]:
    return {
        "requested_source_name": manifest.source_name,
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


__all__ = [
    "InterProMotifSnapshot",
    "InterProMotifSnapshotContract",
    "InterProMotifSnapshotResult",
    "InterProMotifSnapshotStatus",
    "PARSER_VERSION",
    "SOURCE_FAMILY_MOTIF",
    "SOURCE_FAMILY_RELATED",
    "acquire_interpro_motif_snapshot",
]
