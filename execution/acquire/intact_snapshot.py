from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.procurement.source_release_manifest import SourceReleaseManifest

IntActSnapshotStatus = Literal["ok", "blocked", "unavailable"]
_DEFAULT_PAYLOAD_FORMAT = "mitab"
_SUPPORTED_PAYLOAD_FORMATS = {"mitab", "mitab2.5", "mitab2.6", "mitab2.7", "tab", "tsv"}

_HEADER_ALIASES = {
    "interaction ac": "interaction_ac",
    "imex id": "imex_id",
    "interactor a ids": "participant_a_ids",
    "participant a ids": "participant_a_ids",
    "interactor a alt ids": "participant_a_alt_ids",
    "participant a alt ids": "participant_a_alt_ids",
    "interactor a alternative ids": "participant_a_alt_ids",
    "participant a alternative ids": "participant_a_alt_ids",
    "interactor b ids": "participant_b_ids",
    "participant b ids": "participant_b_ids",
    "interactor b alt ids": "participant_b_alt_ids",
    "participant b alt ids": "participant_b_alt_ids",
    "interactor b alternative ids": "participant_b_alt_ids",
    "participant b alternative ids": "participant_b_alt_ids",
    "interactor a aliases": "participant_a_aliases",
    "interactor b aliases": "participant_b_aliases",
    "interaction detection method": "detection_method",
    "detection method": "detection_method",
    "publication ids": "publication_ids",
    "taxid a": "participant_a_tax_id",
    "taxid interactor a": "participant_a_tax_id",
    "taxid b": "participant_b_tax_id",
    "taxid interactor b": "participant_b_tax_id",
    "interaction type": "interaction_type",
    "source database": "source_database",
    "confidence values": "confidence_values",
    "confidence": "confidence_values",
    "native complex": "native_complex",
    "expanded from complex": "expanded_from_complex",
    "expansion method": "expansion_method",
    "projection mode": "interaction_representation",
}

_MITAB_COLUMNS = (
    "participant_a_ids",
    "participant_b_ids",
    "participant_a_alt_ids",
    "participant_b_alt_ids",
    "participant_a_aliases",
    "participant_b_aliases",
    "detection_method",
    "first_author",
    "publication_ids",
    "participant_a_tax_id",
    "participant_b_tax_id",
    "interaction_type",
    "source_database",
    "interaction_ids",
    "confidence_values",
    "expansion_method",
)


def _text(value: object | None) -> str:
    return str(value or "").strip()


def _split_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, str):
        parts = list(value)
    else:
        parts = re.split(r"[|;,]", str(value))
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = _text(part)
        if not text or text == "-" or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return _text(value).casefold() in {"1", "true", "t", "yes", "y"}


def _int_or_none(value: Any) -> int | None:
    text = _text(value)
    if not text or text == "-":
        return None
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _primary_join_id(values: tuple[str, ...]) -> tuple[str, str]:
    for namespace in ("uniprotkb", "refseq"):
        for item in values:
            if ":" not in item:
                continue
            ns, identifier = item.split(":", 1)
            if ns.strip().casefold() == namespace:
                return namespace, identifier.strip().upper()
    for item in values:
        if ":" in item:
            ns, identifier = item.split(":", 1)
            return ns.strip().casefold(), identifier.strip().upper()
    return "", ""


def _interaction_ac_from_ids(values: tuple[str, ...]) -> str:
    for item in values:
        if ":" not in item:
            continue
        namespace, identifier = item.split(":", 1)
        if namespace.strip().casefold() == "intact":
            return identifier.strip().upper()
    return ""


def _imex_id_from_ids(values: tuple[str, ...]) -> str:
    for item in values:
        if ":" not in item:
            continue
        namespace, identifier = item.split(":", 1)
        if namespace.strip().casefold() == "imex":
            return identifier.strip().upper()
    return ""


def _looks_like_header(columns: Sequence[str]) -> bool:
    return any(_text(column).casefold() in _HEADER_ALIASES for column in columns)


def _header_name(column: str) -> str:
    return _HEADER_ALIASES.get(_text(column).casefold(), _text(column).casefold().replace(" ", "_"))


def _row_mapping(columns: Sequence[str], values: Sequence[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index, key in enumerate(columns):
        if index >= len(values):
            break
        mapping[key] = values[index]
    return mapping


def _mapping_text(mapping: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = _text(value)
        if text:
            return text
    return default


def _mapping_bool(mapping: Mapping[str, Any], *keys: str, default: bool = False) -> bool:
    for key in keys:
        if key in mapping:
            return _truthy(mapping[key])
    return default


def _mapping_int(mapping: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in mapping:
            return _int_or_none(mapping[key])
    return None


def _lineage_blockers(interaction_ac: str, imex_id: str) -> tuple[str, ...]:
    blockers: list[str] = []
    if not _text(interaction_ac):
        blockers.append("missing_interaction_ac")
    if not _text(imex_id):
        blockers.append("missing_imex_id")
    return tuple(blockers)


def _lineage_state(interaction_ac: str, imex_id: str) -> str:
    blockers = _lineage_blockers(interaction_ac, imex_id)
    if not blockers:
        return "canonical_interaction"
    if len(blockers) == 1:
        return "partial_interaction_lineage"
    return "participant_only"


@dataclass(frozen=True, slots=True)
class IntActSnapshotManifest:
    source_release: SourceReleaseManifest
    payload_format: str = _DEFAULT_PAYLOAD_FORMAT
    projection_policy: str = "preserve"
    include_native_complexes: bool = True
    include_binary_projections: bool = True

    def __post_init__(self) -> None:
        if self.source_release.source_name.casefold() != "intact":
            raise ValueError("source_release.source_name must be IntAct")
        payload_format = (
            _text(self.payload_format)
            .casefold()
            .replace("_", "")
            .replace("-", "")
            .replace(".", "")
        )
        if payload_format not in {value.replace(".", "") for value in _SUPPORTED_PAYLOAD_FORMATS}:
            raise ValueError(f"unsupported payload_format: {self.payload_format!r}")
        object.__setattr__(self, "payload_format", payload_format)
        object.__setattr__(self, "projection_policy", _text(self.projection_policy) or "preserve")
        object.__setattr__(self, "include_native_complexes", bool(self.include_native_complexes))
        object.__setattr__(
            self,
            "include_binary_projections",
            bool(self.include_binary_projections),
        )

    @property
    def manifest_id(self) -> str:
        return self.source_release.manifest_id

    @property
    def source_locator(self) -> str:
        return _text(self.source_release.source_locator)

    @property
    def local_artifact_refs(self) -> tuple[str, ...]:
        return self.source_release.local_artifact_refs

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": self.source_release.to_dict(),
            "payload_format": self.payload_format,
            "projection_policy": self.projection_policy,
            "include_native_complexes": self.include_native_complexes,
            "include_binary_projections": self.include_binary_projections,
            "manifest_id": self.manifest_id,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> IntActSnapshotManifest:
        if not isinstance(value, Mapping):
            raise TypeError("manifest must be a mapping")
        source_release_payload = value.get("source_release")
        source_release = (
            SourceReleaseManifest.from_dict(dict(source_release_payload))
            if isinstance(source_release_payload, Mapping)
            else SourceReleaseManifest.from_dict(dict(value))
        )
        return cls(
            source_release=source_release,
            payload_format=(
                value.get("payload_format") or value.get("format") or _DEFAULT_PAYLOAD_FORMAT
            ),
            projection_policy=(
                value.get("projection_policy") or value.get("projection") or "preserve"
            ),
            include_native_complexes=bool(value.get("include_native_complexes", True)),
            include_binary_projections=bool(value.get("include_binary_projections", True)),
        )


@dataclass(frozen=True, slots=True)
class IntActInteractionRecord:
    interaction_ac: str
    imex_id: str
    participant_a_ids: tuple[str, ...]
    participant_b_ids: tuple[str, ...]
    participant_a_aliases: tuple[str, ...]
    participant_b_aliases: tuple[str, ...]
    participant_a_primary_id: str
    participant_b_primary_id: str
    participant_a_identity_namespace: str
    participant_b_identity_namespace: str
    participant_a_tax_id: int | None
    participant_b_tax_id: int | None
    interaction_type: str
    detection_method: str
    source_database: str
    publication_ids: tuple[str, ...]
    confidence_values: tuple[str, ...]
    interaction_ids: tuple[str, ...]
    expanded_from_complex: bool
    native_complex: bool
    interaction_representation: str
    lineage_state: str = "participant_only"
    lineage_blockers: tuple[str, ...] = field(default_factory=tuple)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_row: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_ac": self.interaction_ac,
            "imex_id": self.imex_id,
            "participant_a_ids": list(self.participant_a_ids),
            "participant_b_ids": list(self.participant_b_ids),
            "participant_a_aliases": list(self.participant_a_aliases),
            "participant_b_aliases": list(self.participant_b_aliases),
            "participant_a_primary_id": self.participant_a_primary_id,
            "participant_b_primary_id": self.participant_b_primary_id,
            "participant_a_identity_namespace": self.participant_a_identity_namespace,
            "participant_b_identity_namespace": self.participant_b_identity_namespace,
            "participant_a_tax_id": self.participant_a_tax_id,
            "participant_b_tax_id": self.participant_b_tax_id,
            "interaction_type": self.interaction_type,
            "detection_method": self.detection_method,
            "source_database": self.source_database,
            "publication_ids": list(self.publication_ids),
            "confidence_values": list(self.confidence_values),
            "interaction_ids": list(self.interaction_ids),
            "expanded_from_complex": self.expanded_from_complex,
            "native_complex": self.native_complex,
            "interaction_representation": self.interaction_representation,
            "lineage_state": self.lineage_state,
            "lineage_blockers": list(self.lineage_blockers),
            "provenance": dict(self.provenance),
            "raw_row": self.raw_row,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntActInteractionRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            interaction_ac=_text(payload.get("interaction_ac")),
            imex_id=_text(payload.get("imex_id")),
            participant_a_ids=_split_values(payload.get("participant_a_ids")),
            participant_b_ids=_split_values(payload.get("participant_b_ids")),
            participant_a_aliases=_split_values(payload.get("participant_a_aliases")),
            participant_b_aliases=_split_values(payload.get("participant_b_aliases")),
            participant_a_primary_id=_text(payload.get("participant_a_primary_id")),
            participant_b_primary_id=_text(payload.get("participant_b_primary_id")),
            participant_a_identity_namespace=_text(
                payload.get("participant_a_identity_namespace")
            ),
            participant_b_identity_namespace=_text(
                payload.get("participant_b_identity_namespace")
            ),
            participant_a_tax_id=_int_or_none(payload.get("participant_a_tax_id")),
            participant_b_tax_id=_int_or_none(payload.get("participant_b_tax_id")),
            interaction_type=_text(payload.get("interaction_type")),
            detection_method=_text(payload.get("detection_method")),
            source_database=_text(payload.get("source_database")),
            publication_ids=_split_values(payload.get("publication_ids")),
            confidence_values=_split_values(payload.get("confidence_values")),
            interaction_ids=_split_values(payload.get("interaction_ids")),
            expanded_from_complex=_truthy(payload.get("expanded_from_complex")),
            native_complex=_truthy(payload.get("native_complex")),
            interaction_representation=_text(payload.get("interaction_representation")),
            lineage_state=_text(payload.get("lineage_state")) or "participant_only",
            lineage_blockers=_split_values(payload.get("lineage_blockers")),
            provenance=dict(payload.get("provenance") or {}),
            raw_row=_text(payload.get("raw_row")),
        )


@dataclass(frozen=True, slots=True)
class IntActSnapshotProvenance:
    source: Literal["IntAct"] = "IntAct"
    ecosystem: Literal["IMEx"] = "IMEx"
    source_release: dict[str, Any] = field(default_factory=dict)
    source_release_id: str = ""
    source_locator: str = ""
    payload_format: str = _DEFAULT_PAYLOAD_FORMAT
    projection_policy: str = "preserve"
    acquired_on: str = ""
    record_count: int = 0
    native_complex_count: int = 0
    binary_projection_count: int = 0
    imex_record_count: int = 0
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ecosystem": self.ecosystem,
            "source_release": dict(self.source_release),
            "source_release_id": self.source_release_id,
            "source_locator": self.source_locator,
            "payload_format": self.payload_format,
            "projection_policy": self.projection_policy,
            "acquired_on": self.acquired_on,
            "record_count": self.record_count,
            "native_complex_count": self.native_complex_count,
            "binary_projection_count": self.binary_projection_count,
            "imex_record_count": self.imex_record_count,
            "manifest": dict(self.manifest),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntActSnapshotProvenance:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source=_text(payload.get("source")) or "IntAct",
            ecosystem=_text(payload.get("ecosystem")) or "IMEx",
            source_release=dict(payload.get("source_release") or {}),
            source_release_id=_text(payload.get("source_release_id")),
            source_locator=_text(payload.get("source_locator")),
            payload_format=_text(payload.get("payload_format")) or _DEFAULT_PAYLOAD_FORMAT,
            projection_policy=_text(payload.get("projection_policy")) or "preserve",
            acquired_on=_text(payload.get("acquired_on")),
            record_count=int(payload.get("record_count") or 0),
            native_complex_count=int(payload.get("native_complex_count") or 0),
            binary_projection_count=int(payload.get("binary_projection_count") or 0),
            imex_record_count=int(payload.get("imex_record_count") or 0),
            manifest=dict(payload.get("manifest") or {}),
        )


@dataclass(frozen=True, slots=True)
class IntActSnapshot:
    source_release: dict[str, Any]
    provenance: IntActSnapshotProvenance
    records: tuple[IntActInteractionRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": dict(self.source_release),
            "provenance": self.provenance.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntActSnapshot:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_release=dict(payload.get("source_release") or {}),
            provenance=IntActSnapshotProvenance.from_dict(
                dict(payload.get("provenance") or {})
            ),
            records=tuple(
                IntActInteractionRecord.from_dict(record)
                for record in payload.get("records") or ()
            ),
        )


@dataclass(frozen=True, slots=True)
class IntActSnapshotResult:
    status: IntActSnapshotStatus
    manifest: IntActSnapshotManifest | None
    reason: str
    provenance: IntActSnapshotProvenance
    snapshot: IntActSnapshot | None = None
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

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntActSnapshotResult:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        manifest_payload = payload.get("manifest")
        snapshot_payload = payload.get("snapshot")
        provenance_payload = dict(payload.get("provenance") or {})
        if snapshot_payload is None and ("records" in payload or "source_release" in payload):
            snapshot_payload = payload
        snapshot = (
            IntActSnapshot.from_dict(dict(snapshot_payload))
            if isinstance(snapshot_payload, Mapping)
            else None
        )
        manifest = (
            IntActSnapshotManifest.from_mapping(dict(manifest_payload))
            if isinstance(manifest_payload, Mapping)
            else (
                IntActSnapshotManifest(
                    source_release=SourceReleaseManifest.from_dict(
                        dict(payload.get("source_release") or {})
                    ),
                    payload_format=_text(provenance_payload.get("payload_format"))
                    or _DEFAULT_PAYLOAD_FORMAT,
                    projection_policy=_text(provenance_payload.get("projection_policy"))
                    or "preserve",
                )
                if snapshot is not None and payload.get("source_release")
                else None
            )
        )
        provenance = (
            IntActSnapshotProvenance.from_dict(provenance_payload)
            if provenance_payload
            else (
                snapshot.provenance
                if snapshot is not None
                else _build_provenance(manifest)
            )
        )
        return cls(
            status=_text(payload.get("status")) or "ok",
            manifest=manifest,
            reason=_text(payload.get("reason")) or "IntAct snapshot acquired",
            provenance=provenance,
            snapshot=snapshot,
            raw_payload=_text(payload.get("raw_payload")),
        )


def acquire_intact_snapshot(
    manifest: IntActSnapshotManifest | Mapping[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
) -> IntActSnapshotResult:
    try:
        normalized_manifest = _coerce_manifest(manifest)
    except (TypeError, ValueError) as exc:
        provenance = _build_provenance(None)
        return IntActSnapshotResult(
            status="blocked",
            manifest=None,
            reason=str(exc),
            provenance=provenance,
        )

    source_locator = normalized_manifest.source_locator or _first_local_artifact(
        normalized_manifest.local_artifact_refs
    )
    if not source_locator:
        reason = "IntAct snapshot manifest must define a source locator or local artifact reference"
        return IntActSnapshotResult(
            status="blocked",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(normalized_manifest, reason=reason),
        )

    try:
        raw_payload = _load_payload(source_locator, opener=opener)
    except (HTTPError, URLError, OSError) as exc:
        reason = f"IntAct snapshot acquisition unavailable: {exc}"
        return IntActSnapshotResult(
            status="unavailable",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(normalized_manifest, reason=reason),
        )

    try:
        records = _parse_records(
            raw_payload,
            normalized_manifest=normalized_manifest,
            source_locator=source_locator,
        )
    except ValueError as exc:
        reason = f"IntAct snapshot acquisition unavailable: {exc}"
        return IntActSnapshotResult(
            status="unavailable",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(
                normalized_manifest,
                raw_payload=raw_payload,
                reason=reason,
            ),
            raw_payload=raw_payload,
        )

    if not records:
        reason = "IntAct snapshot acquisition unavailable: no interaction rows were parsed"
        return IntActSnapshotResult(
            status="unavailable",
            manifest=normalized_manifest,
            reason=reason,
            provenance=_build_provenance(
                normalized_manifest,
                raw_payload=raw_payload,
                reason=reason,
            ),
            raw_payload=raw_payload,
        )

    provenance = _build_provenance(
        normalized_manifest,
        record_count=len(records),
        native_complex_count=sum(1 for record in records if record.native_complex),
        binary_projection_count=sum(1 for record in records if record.expanded_from_complex),
        imex_record_count=sum(1 for record in records if record.imex_id),
        raw_payload=raw_payload,
    )
    snapshot = IntActSnapshot(
        source_release=normalized_manifest.source_release.to_dict(),
        provenance=provenance,
        records=records,
    )
    return IntActSnapshotResult(
        status="ok",
        manifest=normalized_manifest,
        reason="IntAct snapshot acquired",
        provenance=provenance,
        snapshot=snapshot,
        raw_payload=raw_payload,
    )


def _coerce_manifest(
    manifest: IntActSnapshotManifest | SourceReleaseManifest | Mapping[str, Any],
) -> IntActSnapshotManifest:
    if isinstance(manifest, IntActSnapshotManifest):
        return manifest
    if isinstance(manifest, SourceReleaseManifest):
        return IntActSnapshotManifest(source_release=manifest)
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a mapping or IntActSnapshotManifest")
    return IntActSnapshotManifest.from_mapping(manifest)


def _build_provenance(
    manifest: IntActSnapshotManifest | None,
    *,
    record_count: int = 0,
    native_complex_count: int = 0,
    binary_projection_count: int = 0,
    imex_record_count: int = 0,
    raw_payload: str = "",
    reason: str = "",
) -> IntActSnapshotProvenance:
    if manifest is None:
        return IntActSnapshotProvenance(acquired_on=datetime.now(UTC).isoformat())

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
    if raw_payload:
        source_release_dict["raw_payload_present"] = True

    return IntActSnapshotProvenance(
        source_release=source_release_dict,
        source_release_id=source_release.manifest_id,
        source_locator=manifest.source_locator,
        payload_format=manifest.payload_format,
        projection_policy=manifest.projection_policy,
        acquired_on=datetime.now(UTC).isoformat(),
        record_count=record_count,
        native_complex_count=native_complex_count,
        binary_projection_count=binary_projection_count,
        imex_record_count=imex_record_count,
        manifest=manifest.to_dict(),
    )


def _first_local_artifact(values: tuple[str, ...]) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _load_payload(source_locator: str, *, opener: Callable[..., Any] | None) -> str:
    parsed = urlparse(source_locator)
    if parsed.scheme in {"http", "https", "ftp"}:
        request = Request(
            source_locator,
            headers={"User-Agent": "ProteoSphereV2-IntActSnapshot/0.1"},
        )
        request_opener = opener or urlopen
        with request_opener(request, timeout=30.0) as response:
            return _decode_payload(response.read())
    if parsed.scheme == "file":
        return Path(parsed.path).read_text(encoding="utf-8")
    path = Path(source_locator)
    if path.exists():
        return path.read_text(encoding="utf-8")
    request = Request(source_locator, headers={"User-Agent": "ProteoSphereV2-IntActSnapshot/0.1"})
    request_opener = opener or urlopen
    with request_opener(request, timeout=30.0) as response:
        return _decode_payload(response.read())


def _decode_payload(payload: bytes | str) -> str:
    return payload if isinstance(payload, str) else payload.decode("utf-8")


def _parse_records(
    raw_payload: str,
    *,
    normalized_manifest: IntActSnapshotManifest,
    source_locator: str,
) -> tuple[IntActInteractionRecord, ...]:
    rows = [
        line.rstrip("\n")
        for line in raw_payload.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not rows:
        return ()
    first_row = [column.strip() for column in rows[0].split("\t")]
    if _looks_like_header(first_row):
        header = tuple(_header_name(column) for column in first_row)
        return tuple(
            _parse_mapping_row(
                _row_mapping(header, line.split("\t")),
                raw_row=line,
                normalized_manifest=normalized_manifest,
                source_locator=source_locator,
            )
            for line in rows[1:]
            if line.strip()
        )
    return tuple(
        _parse_mitab_row(
            line.split("\t"),
            raw_row=line,
            normalized_manifest=normalized_manifest,
            source_locator=source_locator,
        )
        for line in rows
    )


def _parse_mapping_row(
    row: Mapping[str, Any],
    *,
    raw_row: str,
    normalized_manifest: IntActSnapshotManifest,
    source_locator: str,
) -> IntActInteractionRecord:
    interaction_ac = _mapping_text(row, "interaction_ac", default="")
    interaction_ids = _split_values(_mapping_text(row, "interaction_ids", default=interaction_ac))
    imex_id = _mapping_text(row, "imex_id", default="")
    if not interaction_ac and interaction_ids:
        interaction_ac = _interaction_ac_from_ids(interaction_ids)
    if not imex_id and interaction_ids:
        imex_id = _imex_id_from_ids(interaction_ids)
    participant_a_ids = _split_values(_mapping_text(row, "participant_a_ids", default=""))
    participant_b_ids = _split_values(_mapping_text(row, "participant_b_ids", default=""))
    participant_a_alt_ids = _split_values(_mapping_text(row, "participant_a_alt_ids", default=""))
    participant_b_alt_ids = _split_values(_mapping_text(row, "participant_b_alt_ids", default=""))
    if participant_a_alt_ids:
        participant_a_ids = tuple(dict.fromkeys((*participant_a_ids, *participant_a_alt_ids)))
    if participant_b_alt_ids:
        participant_b_ids = tuple(dict.fromkeys((*participant_b_ids, *participant_b_alt_ids)))
    participant_a_aliases = _split_values(_mapping_text(row, "participant_a_aliases", default=""))
    participant_b_aliases = _split_values(_mapping_text(row, "participant_b_aliases", default=""))
    participant_a_primary_namespace, participant_a_primary_id = _primary_join_id(participant_a_ids)
    participant_b_primary_namespace, participant_b_primary_id = _primary_join_id(participant_b_ids)
    participant_a_tax_id = _mapping_int(row, "participant_a_tax_id")
    participant_b_tax_id = _mapping_int(row, "participant_b_tax_id")
    interaction_type = _mapping_text(row, "interaction_type", default="")
    detection_method = _mapping_text(row, "detection_method", default="")
    source_database = _mapping_text(row, "source_database", default="")
    publication_ids = _split_values(_mapping_text(row, "publication_ids", default=""))
    confidence_values = _split_values(_mapping_text(row, "confidence_values", default=""))
    expansion_method = _mapping_text(row, "expansion_method", default="")
    expanded_from_complex = _mapping_bool(
        row,
        "expanded_from_complex",
        default=_is_expansion_method(expansion_method),
    )
    native_complex = _mapping_bool(
        row,
        "native_complex",
        default=_is_complex_interaction(interaction_type) and not expanded_from_complex,
    )
    interaction_representation = _mapping_text(
        row,
        "interaction_representation",
        default=_derive_representation(native_complex, expanded_from_complex),
    )
    lineage_state = _lineage_state(interaction_ac, imex_id)
    lineage_blockers = _lineage_blockers(interaction_ac, imex_id)
    return _build_record(
        interaction_ac=interaction_ac,
        imex_id=imex_id,
        participant_a_ids=participant_a_ids,
        participant_b_ids=participant_b_ids,
        participant_a_aliases=participant_a_aliases,
        participant_b_aliases=participant_b_aliases,
        participant_a_primary_namespace=participant_a_primary_namespace,
        participant_a_primary_id=participant_a_primary_id,
        participant_b_primary_namespace=participant_b_primary_namespace,
        participant_b_primary_id=participant_b_primary_id,
        participant_a_tax_id=participant_a_tax_id,
        participant_b_tax_id=participant_b_tax_id,
        interaction_type=interaction_type,
        detection_method=detection_method,
        source_database=source_database,
        publication_ids=publication_ids,
        confidence_values=confidence_values,
        interaction_ids=interaction_ids,
        expanded_from_complex=expanded_from_complex,
        native_complex=native_complex,
        interaction_representation=interaction_representation,
        lineage_state=lineage_state,
        lineage_blockers=lineage_blockers,
        normalized_manifest=normalized_manifest,
        source_locator=source_locator,
        raw_row=raw_row,
    )


def _parse_mitab_row(
    columns: Sequence[str],
    *,
    raw_row: str,
    normalized_manifest: IntActSnapshotManifest,
    source_locator: str,
) -> IntActInteractionRecord:
    padded = list(columns[: len(_MITAB_COLUMNS)])
    if len(padded) < len(_MITAB_COLUMNS):
        padded.extend("" for _ in range(len(_MITAB_COLUMNS) - len(padded)))
    return _parse_mapping_row(
        _row_mapping(_MITAB_COLUMNS, padded),
        raw_row=raw_row,
        normalized_manifest=normalized_manifest,
        source_locator=source_locator,
    )


def _build_record(
    *,
    interaction_ac: str,
    imex_id: str,
    participant_a_ids: tuple[str, ...],
    participant_b_ids: tuple[str, ...],
    participant_a_aliases: tuple[str, ...],
    participant_b_aliases: tuple[str, ...],
    participant_a_primary_namespace: str,
    participant_a_primary_id: str,
    participant_b_primary_namespace: str,
    participant_b_primary_id: str,
    participant_a_tax_id: int | None,
    participant_b_tax_id: int | None,
    interaction_type: str,
    detection_method: str,
    source_database: str,
    publication_ids: tuple[str, ...],
    confidence_values: tuple[str, ...],
    interaction_ids: tuple[str, ...],
    expanded_from_complex: bool,
    native_complex: bool,
    interaction_representation: str,
    lineage_state: str,
    lineage_blockers: tuple[str, ...],
    normalized_manifest: IntActSnapshotManifest,
    source_locator: str,
    raw_row: str,
) -> IntActInteractionRecord:
    return IntActInteractionRecord(
        interaction_ac=_text(interaction_ac),
        imex_id=_text(imex_id),
        participant_a_ids=participant_a_ids,
        participant_b_ids=participant_b_ids,
        participant_a_aliases=participant_a_aliases,
        participant_b_aliases=participant_b_aliases,
        participant_a_primary_id=participant_a_primary_id,
        participant_b_primary_id=participant_b_primary_id,
        participant_a_identity_namespace=participant_a_primary_namespace,
        participant_b_identity_namespace=participant_b_primary_namespace,
        participant_a_tax_id=participant_a_tax_id,
        participant_b_tax_id=participant_b_tax_id,
        interaction_type=_text(interaction_type),
        detection_method=_text(detection_method),
        source_database=_text(source_database),
        publication_ids=publication_ids,
        confidence_values=confidence_values,
        interaction_ids=interaction_ids,
        expanded_from_complex=expanded_from_complex,
        native_complex=native_complex,
        interaction_representation=interaction_representation,
        lineage_state=lineage_state,
        lineage_blockers=lineage_blockers,
        provenance={
            "source": "IntAct",
            "ecosystem": "IMEx",
            "manifest_id": normalized_manifest.manifest_id,
            "source_release_id": normalized_manifest.source_release.manifest_id,
            "source_locator": source_locator,
            "payload_format": normalized_manifest.payload_format,
            "projection_policy": normalized_manifest.projection_policy,
            "interaction_ac": _text(interaction_ac),
            "imex_id": _text(imex_id),
            "expanded_from_complex": expanded_from_complex,
            "native_complex": native_complex,
            "interaction_representation": interaction_representation,
            "lineage_state": lineage_state,
            "lineage_blockers": list(lineage_blockers),
        },
        raw_row=raw_row,
    )


def _is_expansion_method(value: str) -> bool:
    text = value.casefold()
    return bool(text) and text not in {"-", "none", "n/a"} and any(
        marker in text for marker in ("spoke", "matrix", "expand", "projection")
    )


def _is_complex_interaction(value: str) -> bool:
    text = value.casefold()
    return bool(text) and any(marker in text for marker in ("association", "complex", "co-complex"))


def _derive_representation(native_complex: bool, expanded_from_complex: bool) -> str:
    if expanded_from_complex:
        return "binary_projection"
    if native_complex:
        return "native_complex"
    return "direct_binary"


__all__ = [
    "IntActInteractionRecord",
    "IntActSnapshot",
    "IntActSnapshotManifest",
    "IntActSnapshotProvenance",
    "IntActSnapshotResult",
    "IntActSnapshotStatus",
    "acquire_intact_snapshot",
]
