from __future__ import annotations

import csv
import io
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

SOURCE_NAME = "ELM"
SOURCE_FAMILY = "motif"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "ProteoSphereV2-ELMSnapshot/0.1"
PARSER_VERSION = "elm-tsv-v1"
MANUAL_REVIEW_REQUIRED = True

ElmSnapshotStatus = Literal["ok", "blocked", "unavailable"]


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
    contract: "ElmSnapshotContract",
    *,
    opener: Callable[..., Any] | None,
) -> tuple[dict[str, bytes], str]:
    payloads: dict[str, bytes] = {}
    sources: list[str] = []
    for artifact_ref in contract.local_artifact_refs:
        path = Path(artifact_ref)
        if not path.is_file():
            continue
        try:
            payloads[path.name] = path.read_bytes()
            sources.append(f"local_artifact:{path}")
        except OSError:
            continue
    if payloads:
        return payloads, ", ".join(sources)

    if contract.source_locator:
        request = Request(
            contract.source_locator,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        request_opener = opener or urlopen
        with request_opener(request, timeout=DEFAULT_TIMEOUT) as response:
            payload = response.read()
        return {Path(contract.source_locator).name: payload}, f"source_locator:{contract.source_locator}"

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
    availability: ElmSnapshotStatus,
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


def _parse_comment_metadata(raw_text: str) -> tuple[str, str]:
    release_version = ""
    release_date = ""
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if line.startswith("#ELM_Classes_Download_Version:"):
            release_version = line.split(":", 1)[1].strip()
        elif line.startswith("#ELM_Classes_Download_Date:"):
            release_date = line.split(":", 1)[1].strip()
    return release_version, release_date


def _parse_tsv_payload(raw_text: str) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    data_lines = [line for line in raw_text.splitlines() if line.strip() and not line.startswith("#")]
    if not data_lines:
        return (), ()
    reader = csv.DictReader(io.StringIO("\n".join(data_lines)), delimiter="\t", quotechar='"')
    rows = tuple(
        {str(key).strip(): str(value).strip() for key, value in row.items() if key is not None}
        for row in reader
    )
    return tuple(reader.fieldnames or ()), rows


@dataclass(frozen=True, slots=True)
class ElmSnapshotContract:
    manifest: SourceReleaseManifest
    source_name: Literal["ELM"] = SOURCE_NAME
    source_family: str = SOURCE_FAMILY
    release_version: str = ""
    release_date: str = ""
    retrieval_mode: str = "download"
    source_locator: str = ""
    local_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)
    reproducibility_metadata: tuple[str, ...] = field(default_factory=tuple)
    manifest_id: str = ""
    manual_review_required: bool = MANUAL_REVIEW_REQUIRED

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
            "manual_review_required": self.manual_review_required,
        }


@dataclass(frozen=True, slots=True)
class ElmInteractionDomainRecord:
    elm: str
    domain: str
    interactor_elm: str
    interactor_domain: str
    start_elm: str
    stop_elm: str
    start_domain: str
    stop_domain: str
    affinity_min: str
    affinity_max: str
    pmids: tuple[str, ...] = field(default_factory=tuple)
    taxonomy_elm: str = ""
    taxonomy_domain: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_entry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "elm": self.elm,
            "domain": self.domain,
            "interactor_elm": self.interactor_elm,
            "interactor_domain": self.interactor_domain,
            "start_elm": self.start_elm,
            "stop_elm": self.stop_elm,
            "start_domain": self.start_domain,
            "stop_domain": self.stop_domain,
            "affinity_min": self.affinity_min,
            "affinity_max": self.affinity_max,
            "pmids": list(self.pmids),
            "taxonomy_elm": self.taxonomy_elm,
            "taxonomy_domain": self.taxonomy_domain,
            "provenance": dict(self.provenance),
            "raw_entry": dict(self.raw_entry),
        }


@dataclass(frozen=True, slots=True)
class ElmClassRecord:
    accession: str
    identifier: str
    functional_site_name: str
    description: str
    regex: str
    probability: str
    instance_count: int
    pdb_instance_count: int
    release_version: str
    release_date: str
    interaction_domain_count: int = 0
    interaction_domains: tuple[str, ...] = field(default_factory=tuple)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_entry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "identifier": self.identifier,
            "functional_site_name": self.functional_site_name,
            "description": self.description,
            "regex": self.regex,
            "probability": self.probability,
            "instance_count": self.instance_count,
            "pdb_instance_count": self.pdb_instance_count,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "interaction_domain_count": self.interaction_domain_count,
            "interaction_domains": list(self.interaction_domains),
            "provenance": dict(self.provenance),
            "raw_entry": dict(self.raw_entry),
        }


@dataclass(frozen=True, slots=True)
class ElmSnapshot:
    source_name: Literal["ELM"] = SOURCE_NAME
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
    class_records: tuple[ElmClassRecord, ...] = field(default_factory=tuple)
    interaction_records: tuple[ElmInteractionDomainRecord, ...] = field(default_factory=tuple)
    raw_classes_text: str = ""
    raw_interactions_text: str = ""
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
            "class_records": [record.to_dict() for record in self.class_records],
            "interaction_records": [record.to_dict() for record in self.interaction_records],
            "raw_classes_text": self.raw_classes_text,
            "raw_interactions_text": self.raw_interactions_text,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class ElmSnapshotResult:
    status: ElmSnapshotStatus
    reason: str
    manifest: SourceReleaseManifest
    contract: ElmSnapshotContract | None = None
    snapshot: ElmSnapshot | None = None
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


def _pick_artifact_refs(contract: ElmSnapshotContract) -> tuple[Path | None, Path | None]:
    classes_path: Path | None = None
    interactions_path: Path | None = None
    fallback: list[Path] = []
    for artifact_ref in contract.local_artifact_refs:
        path = Path(artifact_ref)
        if not path.is_file():
            continue
        fallback.append(path)
        lower_name = path.name.casefold()
        if lower_name == "elm_classes.tsv":
            classes_path = path
        elif lower_name == "elm_interaction_domains.tsv":
            interactions_path = path

    if classes_path is None and fallback and fallback[0].name.casefold() != "elm_interaction_domains.tsv":
        classes_path = fallback[0]
    if interactions_path is None and len(fallback) > 1:
        for path in fallback[1:]:
            if path != classes_path:
                interactions_path = path
                break
    return classes_path, interactions_path


def _parse_class_records(
    raw_text: str,
    *,
    release_version: str,
    release_date: str,
    interaction_index: Mapping[str, tuple[ElmInteractionDomainRecord, ...]],
) -> tuple[ElmClassRecord, ...]:
    _, rows = _parse_tsv_payload(raw_text)
    records: list[ElmClassRecord] = []
    for row in rows:
        identifier = row.get("ELMIdentifier", "")
        interaction_records = interaction_index.get(identifier, ())
        interaction_domains = tuple(
            sorted(
                {
                    record.interactor_domain
                    for record in interaction_records
                    if record.interactor_domain
                }
            )
        )
        records.append(
            ElmClassRecord(
                accession=row.get("Accession", ""),
                identifier=identifier,
                functional_site_name=row.get("FunctionalSiteName", ""),
                description=row.get("Description", ""),
                regex=row.get("Regex", ""),
                probability=row.get("Probability", ""),
                instance_count=int(row.get("#Instances") or 0),
                pdb_instance_count=int(row.get("#Instances_in_PDB") or 0),
                release_version=release_version,
                release_date=release_date,
                interaction_domain_count=len(interaction_records),
                interaction_domains=interaction_domains,
                provenance={"source_name": SOURCE_NAME},
                raw_entry=row,
            )
        )
    return tuple(records)


def _parse_interaction_records(raw_text: str) -> tuple[ElmInteractionDomainRecord, ...]:
    _, rows = _parse_tsv_payload(raw_text)
    records: list[ElmInteractionDomainRecord] = []
    for row in rows:
        records.append(
            ElmInteractionDomainRecord(
                elm=row.get("Elm", ""),
                domain=row.get("Domain", ""),
                interactor_elm=row.get("interactorElm", ""),
                interactor_domain=row.get("interactorDomain", ""),
                start_elm=row.get("StartElm", ""),
                stop_elm=row.get("StopElm", ""),
                start_domain=row.get("StartDomain", ""),
                stop_domain=row.get("StopDomain", ""),
                affinity_min=row.get("AffinityMin", ""),
                affinity_max=row.get("AffinityMax", ""),
                pmids=tuple(
                    item.strip()
                    for item in str(row.get("PMID", "")).split(",")
                    if item.strip()
                ),
                taxonomy_elm=row.get("taxonomyElm", ""),
                taxonomy_domain=row.get("taxonomyDomain", ""),
                provenance={"source_name": SOURCE_NAME},
                raw_entry=row,
            )
        )
    return tuple(records)


def acquire_elm_snapshot(
    manifest: SourceReleaseManifest | Mapping[str, Any] | None,
    *,
    opener: Callable[..., Any] | None = None,
    acquired_on: str | None = None,
) -> ElmSnapshotResult:
    manifest_data = _coerce_manifest(manifest or {})
    manifest_provenance = _build_manifest_provenance(manifest_data, acquired_on=acquired_on)
    contract = ElmSnapshotContract(
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
        reason = "elm_manifest_needs_source_locator_or_local_artifact_refs"
        return ElmSnapshotResult(
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
        payloads, content_source = _load_payload(contract, opener=opener)
    except FileNotFoundError as exc:
        reason = "elm_local_artifact_unavailable"
        return ElmSnapshotResult(
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
        reason = "elm_request_failed"
        return ElmSnapshotResult(
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

    classes_ref = next((name for name in payloads if name.casefold() == "elm_classes.tsv"), "")
    interactions_ref = next((name for name in payloads if name.casefold() == "elm_interaction_domains.tsv"), "")
    classes_payload = payloads.get(classes_ref, b"")
    interactions_payload = payloads.get(interactions_ref, b"")

    if not classes_payload:
        reason = "elm_classes_artifact_missing"
        return ElmSnapshotResult(
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
        classes_text = classes_payload.decode("utf-8")
        interactions_text = interactions_payload.decode("utf-8") if interactions_payload else ""
    except UnicodeDecodeError as exc:
        reason = "elm_payload_not_utf8"
        return ElmSnapshotResult(
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
                byte_count=sum(len(payload) for payload in payloads.values()),
                line_count=0,
                record_count=0,
            ),
        )

    line_count = len(classes_text.splitlines()) + len(interactions_text.splitlines())
    parsed_release_version, parsed_release_date = _parse_comment_metadata(classes_text)
    release_version = contract.release_version or parsed_release_version
    release_date = contract.release_date or parsed_release_date

    interaction_records = _parse_interaction_records(interactions_text) if interactions_text else ()
    interaction_index: dict[str, tuple[ElmInteractionDomainRecord, ...]] = {}
    for record in interaction_records:
        interaction_index[record.elm] = (*interaction_index.get(record.elm, ()), record)

    class_records = _parse_class_records(
        classes_text,
        release_version=release_version,
        release_date=release_date,
        interaction_index=interaction_index,
    )
    if not class_records:
        reason = "elm_no_class_records"
        return ElmSnapshotResult(
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
                byte_count=sum(len(payload) for payload in payloads.values()),
                line_count=line_count,
                record_count=0,
            ),
        )

    content_blob = classes_payload + (b"\n" + interactions_payload if interactions_payload else b"")
    content_hash = sha256(content_blob).hexdigest()
    snapshot = ElmSnapshot(
        manifest_id=contract.manifest_id,
        release_version=release_version,
        release_date=release_date,
        retrieval_mode=contract.retrieval_mode,
        content_source=content_source,
        content_sha256=content_hash,
        byte_count=sum(len(payload) for payload in payloads.values()),
        line_count=line_count,
        record_count=len(class_records),
        class_records=class_records,
        interaction_records=interaction_records,
        raw_classes_text=classes_text,
        raw_interactions_text=interactions_text,
        provenance=_update_provenance(
            manifest_provenance,
            availability="ok",
            content_source=content_source,
            byte_count=sum(len(payload) for payload in payloads.values()),
            line_count=line_count,
            record_count=len(class_records),
            content_sha256=content_hash,
        ),
    )
    snapshot.provenance["parser_version"] = PARSER_VERSION
    snapshot.provenance["source_name"] = contract.source_name
    snapshot.provenance["source_family"] = contract.source_family
    snapshot.provenance["manual_review_required"] = contract.manual_review_required
    snapshot.provenance["release_version"] = release_version
    snapshot.provenance["release_date"] = release_date

    return ElmSnapshotResult(
        status="ok",
        reason="elm_snapshot_acquired",
        manifest=manifest_data,
        contract=contract,
        snapshot=snapshot,
        provenance=snapshot.provenance,
    )


__all__ = [
    "ElmClassRecord",
    "ElmInteractionDomainRecord",
    "ElmSnapshot",
    "ElmSnapshotContract",
    "ElmSnapshotResult",
    "ElmSnapshotStatus",
    "MANUAL_REVIEW_REQUIRED",
    "PARSER_VERSION",
    "SOURCE_FAMILY",
    "SOURCE_NAME",
    "acquire_elm_snapshot",
]
