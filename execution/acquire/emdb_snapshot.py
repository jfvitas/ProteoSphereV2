from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import SourceReleaseManifest

SOURCE_NAME = "EMDB"
SOURCE_FAMILY = "map"
DEFAULT_PAYLOAD_FORMAT = "auto"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "ProteoSphereV2-EMDBSnapshot/0.1"

EMDBSnapshotStatus = Literal["ok", "blocked", "unavailable"]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_optional_text(value: Any) -> str:
    return _normalize_text(value)


def _split_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, str):
        values = list(value)
    else:
        values = re.split(r"[|;,]", str(value))
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _normalize_text(item)
        if not text or text == "-" or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _split_int_values(value: Any) -> tuple[int, ...]:
    values = _split_values(value)
    normalized: list[int] = []
    seen: set[int] = set()
    for item in values:
        number = _coerce_int_or_none(item)
        if number is None or number in seen:
            continue
        seen.add(number)
        normalized.append(number)
    return tuple(normalized)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return _normalize_text(value).casefold() in {"1", "true", "t", "yes", "y"}


def _coerce_int_or_none(value: Any) -> int | None:
    text = _normalize_text(value)
    if not text or text == "-":
        return None
    match = re.search(r"(\d+)", text)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _normalize_accession(value: Any) -> str:
    accession = _normalize_text(value).upper()
    if not accession:
        return ""
    if not accession.startswith("EMD-"):
        return ""
    if not re.fullmatch(r"EMD-\d+", accession):
        return ""
    return accession


def _normalize_payload_format(value: Any) -> str:
    text = _normalize_text(value) or DEFAULT_PAYLOAD_FORMAT
    normalized = text.casefold().replace("_", "").replace("-", "")
    if normalized in {"auto", "json", "xml", "tsv"}:
        return normalized
    raise ValueError(f"unsupported payload_format: {value!r}")


def _lookup(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _coerce_list_of_mappings(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return (dict(value),)
    if isinstance(value, Sequence) and not isinstance(value, str):
        rows: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, Mapping):
                rows.append(dict(item))
        return tuple(rows)
    return ()


def _coerce_manifest(
    manifest: EMDBSnapshotManifest | Mapping[str, Any],
) -> EMDBSnapshotManifest:
    if isinstance(manifest, EMDBSnapshotManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a mapping or EMDBSnapshotManifest")
    return EMDBSnapshotManifest.from_mapping(manifest)


@dataclass(frozen=True, slots=True)
class EMDBSnapshotManifest:
    """Manifest-aware acquisition contract for pinned EMDB snapshots."""

    source_release: SourceReleaseManifest
    accessions: tuple[str, ...]
    payload_format: str = DEFAULT_PAYLOAD_FORMAT
    include_validation: bool = True
    provenance: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source_release.source_name.casefold() != SOURCE_NAME.casefold():
            raise ValueError("source_release.source_name must be EMDB")
        if not self.source_release.has_release_stamp:
            raise ValueError("source_release must include a release_version or release_date")
        raw_accessions = tuple(_normalize_text(item).upper() for item in self.accessions)
        invalid = [item for item in raw_accessions if item and _normalize_accession(item) == ""]
        if invalid:
            raise ValueError("accessions must be valid EMDB accessions")
        normalized_accessions = tuple(
            dict.fromkeys(
                accession
                for accession in (
                    _normalize_accession(item) for item in raw_accessions
                )
                if accession
            )
        )
        if not normalized_accessions:
            raise ValueError("accessions must not be empty")

        object.__setattr__(self, "accessions", normalized_accessions)
        object.__setattr__(self, "payload_format", _normalize_payload_format(self.payload_format))
        object.__setattr__(self, "include_validation", bool(self.include_validation))
        if not isinstance(self.provenance, Mapping):
            raise ValueError("provenance must be a mapping")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def manifest_id(self) -> str:
        return self.source_release.manifest_id

    @property
    def source_locator(self) -> str:
        return _normalize_optional_text(self.source_release.source_locator)

    @property
    def local_artifact_refs(self) -> tuple[str, ...]:
        return self.source_release.local_artifact_refs

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "source_release": self.source_release.to_dict(),
            "accessions": list(self.accessions),
            "payload_format": self.payload_format,
            "include_validation": self.include_validation,
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> EMDBSnapshotManifest:
        if not isinstance(payload, Mapping):
            raise TypeError("manifest must be a mapping")
        source_release_payload = payload.get("source_release")
        if isinstance(source_release_payload, Mapping):
            source_release = SourceReleaseManifest.from_dict(dict(source_release_payload))
        else:
            source_release = SourceReleaseManifest.from_dict(dict(payload))

        accessions = _split_values(
            _lookup(
                payload,
                "accessions",
                "accession",
                "entry_accessions",
                "emdb_accessions",
                "entries",
                default=(),
            )
        )
        metadata = payload.get("metadata") or {}
        if not metadata and payload.get("notes") is not None:
            metadata = {"notes": payload.get("notes")}
        return cls(
            source_release=source_release,
            accessions=tuple(accessions),
            payload_format=payload.get("payload_format")
            or payload.get("format")
            or DEFAULT_PAYLOAD_FORMAT,
            include_validation=_coerce_bool(payload.get("include_validation", True)),
            provenance=payload.get("provenance") or {},
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class EMDBEntryRecord:
    accession: str
    title: str
    status: str
    schema_version: str
    release_date: str
    deposition_date: str
    sample_type: str
    organism: str
    microscopy_method: str
    resolution: float | None
    map_class: str
    primary_map_ref: str
    map_file_refs: tuple[str, ...]
    auxiliary_file_refs: tuple[str, ...]
    linked_pdb_ids: tuple[str, ...]
    linked_empiar_ids: tuple[str, ...]
    linked_uniprot_accessions: tuple[str, ...]
    linked_alphafold_db_ids: tuple[str, ...]
    validation_summary: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_entry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "title": self.title,
            "status": self.status,
            "schema_version": self.schema_version,
            "release_date": self.release_date,
            "deposition_date": self.deposition_date,
            "sample_type": self.sample_type,
            "organism": self.organism,
            "microscopy_method": self.microscopy_method,
            "resolution": self.resolution,
            "map_class": self.map_class,
            "primary_map_ref": self.primary_map_ref,
            "map_file_refs": list(self.map_file_refs),
            "auxiliary_file_refs": list(self.auxiliary_file_refs),
            "linked_pdb_ids": list(self.linked_pdb_ids),
            "linked_empiar_ids": list(self.linked_empiar_ids),
            "linked_uniprot_accessions": list(self.linked_uniprot_accessions),
            "linked_alphafold_db_ids": list(self.linked_alphafold_db_ids),
            "validation_summary": dict(self.validation_summary),
            "provenance": dict(self.provenance),
            "raw_entry": dict(self.raw_entry),
        }


@dataclass(frozen=True, slots=True)
class EMDBSnapshotProvenance:
    source: Literal["EMDB"] = SOURCE_NAME
    source_family: str = SOURCE_FAMILY
    source_release: dict[str, Any] = field(default_factory=dict)
    source_release_id: str = ""
    source_locator: str = ""
    payload_format: str = DEFAULT_PAYLOAD_FORMAT
    acquired_on: str = ""
    record_count: int = 0
    linked_pdb_count: int = 0
    linked_empiar_count: int = 0
    linked_uniprot_count: int = 0
    validation_record_count: int = 0
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_family": self.source_family,
            "source_release": dict(self.source_release),
            "source_release_id": self.source_release_id,
            "source_locator": self.source_locator,
            "payload_format": self.payload_format,
            "acquired_on": self.acquired_on,
            "record_count": self.record_count,
            "linked_pdb_count": self.linked_pdb_count,
            "linked_empiar_count": self.linked_empiar_count,
            "linked_uniprot_count": self.linked_uniprot_count,
            "validation_record_count": self.validation_record_count,
            "manifest": dict(self.manifest),
        }


@dataclass(frozen=True, slots=True)
class EMDBSnapshot:
    source_release: dict[str, Any]
    provenance: EMDBSnapshotProvenance
    records: tuple[EMDBEntryRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": dict(self.source_release),
            "provenance": self.provenance.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class EMDBSnapshotResult:
    status: EMDBSnapshotStatus
    manifest: EMDBSnapshotManifest | None
    reason: str
    provenance: EMDBSnapshotProvenance
    snapshot: EMDBSnapshot | None = None
    raw_payload: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "manifest": None if self.manifest is None else self.manifest.to_dict(),
            "reason": self.reason,
            "provenance": self.provenance.to_dict(),
            "snapshot": None if self.snapshot is None else self.snapshot.to_dict(),
            "raw_payload": self.raw_payload,
        }


def acquire_emdb_snapshot(
    manifest: EMDBSnapshotManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
) -> EMDBSnapshotResult:
    try:
        normalized_manifest = _coerce_manifest(manifest)
    except (TypeError, ValueError) as exc:
        provenance = _build_provenance(None)
        return EMDBSnapshotResult(
            status="blocked",
            manifest=None,
            reason=str(exc),
            provenance=provenance,
        )

    source_locator = normalized_manifest.source_locator or _first_local_artifact(
        normalized_manifest.local_artifact_refs
    )
    if not source_locator:
        reason = "EMDB snapshot manifest must define a source locator or local artifact reference"
        return EMDBSnapshotResult(
            status="blocked",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(normalized_manifest, reason=reason),
        )

    try:
        raw_payload = _load_payload(source_locator, opener=opener)
    except (HTTPError, URLError, OSError) as exc:
        reason = f"EMDB snapshot acquisition unavailable: {exc}"
        return EMDBSnapshotResult(
            status="unavailable",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(normalized_manifest, reason=reason),
        )

    try:
        records = _parse_records(
            raw_payload,
            manifest=normalized_manifest,
            source_locator=source_locator,
        )
    except ValueError as exc:
        reason = f"EMDB snapshot acquisition unavailable: {exc}"
        return EMDBSnapshotResult(
            status="unavailable",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(
                normalized_manifest,
                reason=reason,
                raw_payload_present=True,
            ),
            raw_payload=raw_payload,
        )

    requested = normalized_manifest.accessions
    if requested:
        record_by_accession = {record.accession: record for record in records}
        ordered_records = []
        missing = [accession for accession in requested if accession not in record_by_accession]
        if missing:
            reason = "EMDB snapshot acquisition unavailable: missing requested accession(s)"
            return EMDBSnapshotResult(
                status="unavailable",
                manifest=normalized_manifest,
                reason=f"{reason}: {', '.join(missing)}",
                provenance=_build_provenance(
                    normalized_manifest,
                    reason=reason,
                    raw_payload_present=True,
                ),
                raw_payload=raw_payload,
            )
        ordered_records = [record_by_accession[accession] for accession in requested]
        records = tuple(ordered_records)

    if not records:
        reason = "EMDB snapshot acquisition unavailable: no entry records were parsed"
        return EMDBSnapshotResult(
            status="unavailable",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(
                normalized_manifest,
                reason=reason,
                raw_payload_present=True,
            ),
            raw_payload=raw_payload,
        )

    linked_pdb_count, linked_empiar_count, linked_uniprot_count = _build_snapshot_link_counts(
        records
    )
    provenance = _build_provenance(
        normalized_manifest,
        record_count=len(records),
        linked_pdb_count=linked_pdb_count,
        linked_empiar_count=linked_empiar_count,
        linked_uniprot_count=linked_uniprot_count,
        validation_record_count=sum(1 for record in records if record.validation_summary),
        raw_payload_present=True,
    )
    snapshot = EMDBSnapshot(
        source_release=normalized_manifest.source_release.to_dict(),
        provenance=provenance,
        records=records,
    )
    return EMDBSnapshotResult(
        status="ok",
        manifest=normalized_manifest,
        reason="EMDB snapshot acquired",
        provenance=provenance,
        snapshot=snapshot,
        raw_payload=raw_payload,
    )


def _first_local_artifact(values: tuple[str, ...]) -> str:
    for value in values:
        text = _normalize_optional_text(value)
        if text:
            return text
    return ""


def _build_provenance(
    manifest: EMDBSnapshotManifest | None,
    *,
    record_count: int = 0,
    linked_pdb_count: int = 0,
    linked_empiar_count: int = 0,
    linked_uniprot_count: int = 0,
    validation_record_count: int = 0,
    reason: str = "",
    raw_payload_present: bool = False,
) -> EMDBSnapshotProvenance:
    if manifest is None:
        return EMDBSnapshotProvenance(acquired_on=datetime.now(UTC).isoformat())

    source_release = manifest.source_release
    source_release_dict = {
        "manifest_id": source_release.manifest_id,
        "source_name": source_release.source_name,
        "release_version": source_release.release_version,
        "release_date": source_release.release_date,
        "retrieval_mode": source_release.retrieval_mode,
        "source_locator": source_release.source_locator,
        "local_artifact_refs": list(source_release.local_artifact_refs),
        "provenance": list(source_release.provenance),
        "reproducibility_metadata": list(source_release.reproducibility_metadata),
    }
    if reason:
        source_release_dict["reason"] = reason
    if raw_payload_present:
        source_release_dict["raw_payload_present"] = True

    return EMDBSnapshotProvenance(
        source_release=source_release_dict,
        source_release_id=source_release.manifest_id,
        source_locator=manifest.source_locator,
        payload_format=manifest.payload_format,
        acquired_on=datetime.now(UTC).isoformat(),
        record_count=record_count,
        linked_pdb_count=linked_pdb_count,
        linked_empiar_count=linked_empiar_count,
        linked_uniprot_count=linked_uniprot_count,
        validation_record_count=validation_record_count,
        manifest=manifest.to_dict(),
    )


def _load_payload(source_locator: str, *, opener: Callable[..., Any] | None) -> str:
    parsed = urlparse(source_locator)
    if parsed.scheme in {"http", "https", "ftp"}:
        request = Request(
            source_locator,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        request_opener = opener or urlopen
        with request_opener(request, timeout=DEFAULT_TIMEOUT) as response:
            return _decode_payload(response.read())
    if parsed.scheme == "file":
        path = Path(parsed.path)
        if parsed.netloc and not path.is_absolute():
            path = Path(f"{parsed.netloc}{parsed.path}")
        return path.read_text(encoding="utf-8")
    path = Path(source_locator)
    if path.exists():
        return path.read_text(encoding="utf-8")
    request = Request(
        source_locator,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    request_opener = opener or urlopen
    with request_opener(request, timeout=DEFAULT_TIMEOUT) as response:
        return _decode_payload(response.read())


def _decode_payload(payload: bytes | str) -> str:
    return payload if isinstance(payload, str) else payload.decode("utf-8")


def _parse_records(
    raw_payload: str,
    *,
    manifest: EMDBSnapshotManifest,
    source_locator: str,
) -> tuple[EMDBEntryRecord, ...]:
    payload_format = manifest.payload_format
    if payload_format == "auto":
        payload_format = _detect_payload_format(raw_payload)
    if payload_format == "json":
        entries = _parse_json_entries(raw_payload)
    elif payload_format == "xml":
        entries = _parse_xml_entries(raw_payload)
    elif payload_format == "tsv":
        entries = _parse_tsv_entries(raw_payload)
    else:
        raise ValueError(f"unsupported payload format: {payload_format}")
    return tuple(
        _record_from_mapping(
            entry,
            manifest=manifest,
            source_locator=source_locator,
            raw_entry=entry,
        )
        for entry in entries
    )


def _detect_payload_format(raw_payload: str) -> str:
    stripped = raw_payload.lstrip()
    if not stripped:
        return "json"
    if stripped.startswith("<"):
        return "xml"
    if "\t" in raw_payload:
        return "tsv"
    return "json"


def _parse_json_entries(raw_payload: str) -> tuple[dict[str, Any], ...]:
    payload = json.loads(raw_payload)
    if isinstance(payload, list):
        return tuple(dict(item) for item in payload if isinstance(item, Mapping))
    if isinstance(payload, Mapping):
        for key in ("entries", "results", "items", "data", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return tuple(dict(item) for item in value if isinstance(item, Mapping))
        return (dict(payload),)
    raise ValueError("EMDB JSON payload must be a mapping or list")


def _parse_tsv_entries(raw_payload: str) -> tuple[dict[str, Any], ...]:
    lines = [
        line.rstrip("\n")
        for line in raw_payload.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return ()
    header = [column.strip() for column in lines[0].split("\t")]
    records: list[dict[str, Any]] = []
    for line in lines[1:]:
        values = line.split("\t")
        row: dict[str, Any] = {}
        for index, key in enumerate(header):
            if index < len(values):
                row[key] = values[index]
        records.append(row)
    return tuple(records)


def _parse_xml_entries(raw_payload: str) -> tuple[dict[str, Any], ...]:
    root = ET.fromstring(raw_payload)
    entry_nodes = list(root.findall(".//entry"))
    if not entry_nodes and root.tag.lower() == "entry":
        entry_nodes = [root]
    if not entry_nodes:
        return (dict(_xml_node_to_mapping(root)),)
    return tuple(_xml_node_to_mapping(node) for node in entry_nodes)


def _xml_node_to_mapping(node: ET.Element) -> dict[str, Any]:
    mapping: dict[str, Any] = {key: value for key, value in node.attrib.items()}
    for child in list(node):
        key = child.tag.split("}")[-1]
        value = _xml_node_text(child)
        if key in mapping:
            existing = mapping[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                mapping[key] = [existing, value]
            continue
        mapping[key] = value
    text = _normalize_optional_text(node.text)
    if text and not mapping:
        mapping["text"] = text
    return mapping


def _xml_node_text(node: ET.Element) -> Any:
    children = list(node)
    if not children:
        return _normalize_optional_text(node.text)
    return _xml_node_to_mapping(node)


def _record_from_mapping(
    mapping: Mapping[str, Any],
    *,
    manifest: EMDBSnapshotManifest,
    source_locator: str,
    raw_entry: Mapping[str, Any],
) -> EMDBEntryRecord:
    accession = _normalize_accession(
        _lookup(mapping, "accession", "emd_accession", "emd_id", default="")
    )
    if not accession:
        raise ValueError("EMDB entry did not contain a valid accession")

    title = _normalize_optional_text(_lookup(mapping, "title", "entry_title", default=""))
    status = _normalize_optional_text(_lookup(mapping, "status", "release_status", default=""))
    schema_version = _normalize_optional_text(
        _lookup(mapping, "schema_version", "schemaVersion", "xsd_version", default="")
    )
    release_date = _normalize_optional_text(
        _lookup(mapping, "release_date", "releaseDate", default="")
    )
    deposition_date = _normalize_optional_text(
        _lookup(mapping, "deposition_date", "deposit_date", "depositionDate", default="")
    )
    sample_type = _normalize_optional_text(
        _lookup(mapping, "sample_type", "sampleType", default="")
    )
    organism = _normalize_optional_text(
        _lookup(mapping, "organism", "sample_organism", "scientific_name", default="")
    )
    microscopy_method = _normalize_optional_text(
        _lookup(mapping, "microscopy_method", "method", "microscopyMethod", default="")
    )
    resolution = _coerce_float(
        _lookup(mapping, "resolution", "map_resolution", "validation_resolution")
    )
    map_class = _normalize_optional_text(_lookup(mapping, "map_class", "mapClass", default=""))
    primary_map_ref = _normalize_optional_text(
        _lookup(mapping, "primary_map_ref", "primary_map", "map_ref", "mapUrl", default="")
    )
    map_file_refs = _split_values(
        _lookup(mapping, "map_file_refs", "map_files", "mapFiles", default=())
    )
    auxiliary_file_refs = _split_values(
        _lookup(mapping, "auxiliary_file_refs", "auxiliary_files", "auxiliaryFiles", default=())
    )
    linked_pdb_ids = tuple(
        accession.upper()
        for accession in _split_values(
            _lookup(mapping, "linked_pdb_ids", "pdb_ids", "pdb_id", "pdbIds", default=())
        )
    )
    linked_empiar_ids = tuple(
        accession.upper()
        for accession in _split_values(
            _lookup(
                mapping,
                "linked_empiar_ids",
                "empiar_ids",
                "empiar_id",
                "empiarIds",
                default=(),
            )
        )
    )
    linked_uniprot_accessions = tuple(
        accession.upper()
        for accession in _split_values(
            _lookup(
                mapping,
                "linked_uniprot_accessions",
                "uniprot_ids",
                "uniprot_accessions",
                "uniprotAccessions",
                default=(),
            )
        )
    )
    linked_alphafold_db_ids = tuple(
        _split_values(
            _lookup(
                mapping,
                "linked_alphafold_db_ids",
                "alphafold_db_ids",
                "alpha_fold_db_ids",
                "alphafold_model_ids",
                default=(),
            )
        )
    )
    validation_summary = _coerce_validation_summary(mapping) if manifest.include_validation else {}

    return EMDBEntryRecord(
        accession=accession,
        title=title,
        status=status,
        schema_version=schema_version,
        release_date=release_date,
        deposition_date=deposition_date,
        sample_type=sample_type,
        organism=organism,
        microscopy_method=microscopy_method,
        resolution=resolution,
        map_class=map_class,
        primary_map_ref=primary_map_ref,
        map_file_refs=map_file_refs,
        auxiliary_file_refs=auxiliary_file_refs,
        linked_pdb_ids=linked_pdb_ids,
        linked_empiar_ids=linked_empiar_ids,
        linked_uniprot_accessions=linked_uniprot_accessions,
        linked_alphafold_db_ids=linked_alphafold_db_ids,
        validation_summary=validation_summary,
        provenance=_build_record_provenance(
            manifest,
            accession=accession,
            source_locator=source_locator,
            linked_pdb_ids=linked_pdb_ids,
            linked_empiar_ids=linked_empiar_ids,
            linked_uniprot_accessions=linked_uniprot_accessions,
        ),
        raw_entry=dict(raw_entry),
    )


def _coerce_validation_summary(mapping: Mapping[str, Any]) -> dict[str, Any]:
    value = _lookup(mapping, "validation_summary", "validation", "validationMetrics", default={})
    if not isinstance(value, Mapping):
        return {}
    summary = dict(value)
    if "resolution" not in summary:
        resolution = _coerce_float(
            _lookup(summary, "resolution", "map_resolution", "fsc_resolution")
        )
        if resolution is not None:
            summary["resolution"] = resolution
    return summary


def _build_record_provenance(
    manifest: EMDBSnapshotManifest,
    *,
    accession: str,
    source_locator: str,
    linked_pdb_ids: tuple[str, ...],
    linked_empiar_ids: tuple[str, ...],
    linked_uniprot_accessions: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "source": SOURCE_NAME,
        "source_family": SOURCE_FAMILY,
        "manifest_id": manifest.manifest_id,
        "source_release_id": manifest.manifest_id,
        "source_locator": source_locator,
        "payload_format": manifest.payload_format,
        "accession": accession,
        "linked_pdb_ids": list(linked_pdb_ids),
        "linked_empiar_ids": list(linked_empiar_ids),
        "linked_uniprot_accessions": list(linked_uniprot_accessions),
    }


def _coerce_float(value: Any) -> float | None:
    text = _normalize_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _build_source_release_dict(manifest: EMDBSnapshotManifest) -> dict[str, Any]:
    source_release = manifest.source_release
    return {
        "manifest_id": source_release.manifest_id,
        "source_name": source_release.source_name,
        "release_version": source_release.release_version,
        "release_date": source_release.release_date,
        "retrieval_mode": source_release.retrieval_mode,
        "source_locator": source_release.source_locator,
        "local_artifact_refs": list(source_release.local_artifact_refs),
        "provenance": list(source_release.provenance),
        "reproducibility_metadata": list(source_release.reproducibility_metadata),
        "accessions": list(manifest.accessions),
    }


def _build_snapshot_link_counts(records: tuple[EMDBEntryRecord, ...]) -> tuple[int, int, int]:
    linked_pdb_ids = {pdb_id for record in records for pdb_id in record.linked_pdb_ids}
    linked_empiar_ids = {empiar_id for record in records for empiar_id in record.linked_empiar_ids}
    linked_uniprot_accessions = {
        accession for record in records for accession in record.linked_uniprot_accessions
    }
    return (
        len(linked_pdb_ids),
        len(linked_empiar_ids),
        len(linked_uniprot_accessions),
    )


__all__ = [
    "EMDBEntryRecord",
    "EMDBSnapshot",
    "EMDBSnapshotManifest",
    "EMDBSnapshotProvenance",
    "EMDBSnapshotResult",
    "EMDBSnapshotStatus",
    "acquire_emdb_snapshot",
]
