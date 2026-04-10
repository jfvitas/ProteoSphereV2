from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

StructurePacketState = Literal["packet_complete", "partial", "bridge_only", "unavailable"]
StructurePayloadState = Literal["available", "empty", "missing", "invalid"]
StructurePacketIssueKind = Literal[
    "missing_coordinate_payload",
    "empty_coordinate_payload",
    "invalid_coordinate_payload",
    "unbridged_accession",
]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _normalize_json_value(value: Any, field_name: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = _required_text(key, f"{field_name} key")
            normalized[normalized_key] = _normalize_json_value(
                item,
                f"{field_name}[{normalized_key!r}]",
            )
        return normalized
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return tuple(_normalize_json_value(item, field_name) for item in value)
    raise TypeError(f"{field_name} must contain only JSON-serializable values")


def _normalize_json_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized[normalized_key] = _normalize_json_value(
            item,
            f"{field_name}[{normalized_key!r}]",
        )
    return normalized


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("coordinate payload must be a JSON object")
    return dict(payload)


def _sha256_hex(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _normalize_path_roots(values: Iterable[str | Path]) -> tuple[Path, ...]:
    roots: list[Path] = []
    seen: set[str] = set()
    for value in values:
        path = Path(value)
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        roots.append(path)
    return tuple(roots)


def _candidate_payload_paths(root: Path, pdb_id: str) -> tuple[Path, ...]:
    cleaned = _required_text(pdb_id, "pdb_id").upper()
    return (
        root / f"{cleaned}.json",
        root / "rcsb" / f"{cleaned}.json",
    )


@dataclass(frozen=True, slots=True)
class StructurePacketIssue:
    accession: str
    kind: StructurePacketIssueKind
    message: str
    pdb_id: str | None = None
    payload_ref: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "pdb_id", _optional_text(self.pdb_id))
        object.__setattr__(self, "payload_ref", _optional_text(self.payload_ref))
        object.__setattr__(self, "details", _normalize_json_mapping(self.details, "details"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "kind": self.kind,
            "message": self.message,
            "pdb_id": self.pdb_id,
            "payload_ref": self.payload_ref,
            "details": _json_ready(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StructurePacketIssue:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            accession=payload.get("accession") or payload.get("id") or "",
            kind=payload.get("kind") or "missing_coordinate_payload",
            message=payload.get("message") or "",
            pdb_id=payload.get("pdb_id") or payload.get("pdb"),
            payload_ref=payload.get("payload_ref") or payload.get("ref") or payload.get("path"),
            details=payload.get("details") or payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class StructureCoordinatePayload:
    pdb_id: str
    payload_ref: str
    payload_state: StructurePayloadState
    byte_count: int
    payload_sha256: str | None = None
    task_type: str | None = None
    source_record_id: str | None = None
    payload_data: Mapping[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pdb_id", _required_text(self.pdb_id, "pdb_id").upper())
        object.__setattr__(self, "payload_ref", _required_text(self.payload_ref, "payload_ref"))
        if self.payload_state not in {"available", "empty", "missing", "invalid"}:
            raise ValueError(f"unsupported payload_state: {self.payload_state!r}")
        if self.byte_count < 0:
            raise ValueError("byte_count must be >= 0")
        object.__setattr__(self, "payload_sha256", _optional_text(self.payload_sha256))
        object.__setattr__(self, "task_type", _optional_text(self.task_type))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(
            self,
            "payload_data",
            _normalize_json_mapping(self.payload_data, "payload_data"),
        )
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def materialized(self) -> bool:
        return self.payload_state == "available"

    @property
    def packet_complete(self) -> bool:
        return self.materialized

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdb_id": self.pdb_id,
            "payload_ref": self.payload_ref,
            "payload_state": self.payload_state,
            "byte_count": self.byte_count,
            "payload_sha256": self.payload_sha256,
            "task_type": self.task_type,
            "source_record_id": self.source_record_id,
            "payload_data": _json_ready(dict(self.payload_data)),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StructureCoordinatePayload:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            pdb_id=payload.get("pdb_id") or payload.get("pdb") or "",
            payload_ref=(
                payload.get("payload_ref")
                or payload.get("ref")
                or payload.get("path")
                or ""
            ),
            payload_state=payload.get("payload_state") or "missing",
            byte_count=int(payload.get("byte_count") or 0),
            payload_sha256=payload.get("payload_sha256") or payload.get("checksum"),
            task_type=payload.get("task_type"),
            source_record_id=payload.get("source_record_id"),
            payload_data=payload.get("payload_data") or payload.get("payload") or {},
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class StructurePacketEnrichmentEntry:
    accession: str
    canonical_id: str
    split: str | None = None
    bucket: str | None = None
    judgment: str | None = None
    evidence_mode: str | None = None
    lane_depth: int | None = None
    source_lanes: tuple[str, ...] = field(default_factory=tuple)
    present_modalities: tuple[str, ...] = field(default_factory=tuple)
    missing_modalities: tuple[str, ...] = field(default_factory=tuple)
    coverage_notes: tuple[str, ...] = field(default_factory=tuple)
    bridge_state: str = "absent"
    bridge_kind: str | None = None
    packet_state: StructurePacketState = "unavailable"
    pdb_ids: tuple[str, ...] = field(default_factory=tuple)
    source_record_refs: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    coordinate_payloads: tuple[StructureCoordinatePayload, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[StructurePacketIssue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        object.__setattr__(self, "split", _optional_text(self.split))
        object.__setattr__(self, "bucket", _optional_text(self.bucket))
        object.__setattr__(self, "judgment", _optional_text(self.judgment))
        object.__setattr__(self, "evidence_mode", _optional_text(self.evidence_mode))
        object.__setattr__(
            self,
            "lane_depth",
            None if self.lane_depth is None else int(self.lane_depth),
        )
        object.__setattr__(self, "source_lanes", _dedupe_text(self.source_lanes))
        object.__setattr__(self, "present_modalities", _dedupe_text(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        object.__setattr__(self, "coverage_notes", _dedupe_text(self.coverage_notes))
        object.__setattr__(self, "bridge_state", _required_text(self.bridge_state, "bridge_state"))
        object.__setattr__(self, "bridge_kind", _optional_text(self.bridge_kind))
        if self.packet_state not in {"packet_complete", "partial", "bridge_only", "unavailable"}:
            raise ValueError(f"unsupported packet_state: {self.packet_state!r}")
        object.__setattr__(self, "pdb_ids", _dedupe_text(self.pdb_ids))
        object.__setattr__(self, "source_record_refs", _dedupe_text(self.source_record_refs))
        object.__setattr__(self, "evidence_refs", _dedupe_text(self.evidence_refs))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "coordinate_payloads", tuple(self.coordinate_payloads))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "issues", tuple(self.issues))

    @property
    def materialized_payload_count(self) -> int:
        return sum(1 for payload in self.coordinate_payloads if payload.materialized)

    @property
    def packet_complete_payload_count(self) -> int:
        return self.materialized_payload_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "split": self.split,
            "bucket": self.bucket,
            "judgment": self.judgment,
            "evidence_mode": self.evidence_mode,
            "lane_depth": self.lane_depth,
            "source_lanes": list(self.source_lanes),
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "coverage_notes": list(self.coverage_notes),
            "bridge_state": self.bridge_state,
            "bridge_kind": self.bridge_kind,
            "packet_state": self.packet_state,
            "pdb_ids": list(self.pdb_ids),
            "source_record_refs": list(self.source_record_refs),
            "evidence_refs": list(self.evidence_refs),
            "provenance_refs": list(self.provenance_refs),
            "coordinate_payloads": [payload.to_dict() for payload in self.coordinate_payloads],
            "notes": list(self.notes),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StructurePacketEnrichmentEntry:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            accession=payload.get("accession") or "",
            canonical_id=payload.get("canonical_id") or payload.get("canonical") or "",
            split=payload.get("split"),
            bucket=payload.get("bucket"),
            judgment=payload.get("judgment"),
            evidence_mode=payload.get("evidence_mode"),
            lane_depth=payload.get("lane_depth"),
            source_lanes=payload.get("source_lanes") or (),
            present_modalities=payload.get("present_modalities") or (),
            missing_modalities=payload.get("missing_modalities") or (),
            coverage_notes=payload.get("coverage_notes") or (),
            bridge_state=payload.get("bridge_state") or "absent",
            bridge_kind=payload.get("bridge_kind"),
            packet_state=(
                "packet_complete"
                if (payload.get("packet_state") or "unavailable") == "materialized"
                else payload.get("packet_state") or "unavailable"
            ),
            pdb_ids=payload.get("pdb_ids") or (),
            source_record_refs=payload.get("source_record_refs") or (),
            evidence_refs=payload.get("evidence_refs") or (),
            provenance_refs=payload.get("provenance_refs") or (),
            coordinate_payloads=tuple(
                item
                if isinstance(item, StructureCoordinatePayload)
                else StructureCoordinatePayload.from_dict(item)
                for item in _iter_values(payload.get("coordinate_payloads") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
            issues=tuple(
                item
                if isinstance(item, StructurePacketIssue)
                else StructurePacketIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or ())
            ),
        )


@dataclass(frozen=True, slots=True)
class StructurePacketEnrichmentResult:
    source_task_id: str
    source_slice_ref: str
    source_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    status: StructurePacketState = "unavailable"
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_accession_count: int = 0
    bridge_positive_accession_count: int = 0
    packet_complete_accession_count: int = 0
    bridge_only_accession_count: int = 0
    partial_accession_count: int = 0
    unavailable_accession_count: int = 0
    entries: tuple[StructurePacketEnrichmentEntry, ...] = field(default_factory=tuple)
    issues: tuple[StructurePacketIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_task_id",
            _required_text(self.source_task_id, "source_task_id"),
        )
        object.__setattr__(
            self,
            "source_slice_ref",
            _required_text(self.source_slice_ref, "source_slice_ref"),
        )
        if self.status not in {"packet_complete", "partial", "bridge_only", "unavailable"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        for field_name in (
            "source_accession_count",
            "bridge_positive_accession_count",
            "packet_complete_accession_count",
            "bridge_only_accession_count",
            "partial_accession_count",
            "unavailable_accession_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be >= 0")
        object.__setattr__(self, "source_artifact_refs", _dedupe_text(self.source_artifact_refs))
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def selected_accessions(self) -> tuple[str, ...]:
        return tuple(entry.accession for entry in self.entries)

    @property
    def bridge_positive_accessions(self) -> tuple[str, ...]:
        return tuple(
            entry.accession
            for entry in self.entries
            if entry.bridge_state == "positive_hit"
        )

    @property
    def materialized_accession_count(self) -> int:
        return self.packet_complete_accession_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_task_id": self.source_task_id,
            "source_slice_ref": self.source_slice_ref,
            "source_artifact_refs": list(self.source_artifact_refs),
            "status": self.status,
            "generated_at": self.generated_at,
            "source_accession_count": self.source_accession_count,
            "bridge_positive_accession_count": self.bridge_positive_accession_count,
            "packet_complete_accession_count": self.packet_complete_accession_count,
            "materialized_accession_count": self.packet_complete_accession_count,
            "bridge_only_accession_count": self.bridge_only_accession_count,
            "partial_accession_count": self.partial_accession_count,
            "unavailable_accession_count": self.unavailable_accession_count,
            "selected_accessions": list(self.selected_accessions),
            "bridge_positive_accessions": list(self.bridge_positive_accessions),
            "entries": [entry.to_dict() for entry in self.entries],
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StructurePacketEnrichmentResult:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_task_id=payload.get("source_task_id") or payload.get("task_id") or "",
            source_slice_ref=payload.get("source_slice_ref") or payload.get("source_ref") or "",
            source_artifact_refs=payload.get("source_artifact_refs") or (),
            status=(
                "packet_complete"
                if (payload.get("status") or "unavailable") == "materialized"
                else payload.get("status") or "unavailable"
            ),
            generated_at=payload.get("generated_at") or datetime.now(UTC).isoformat(),
            source_accession_count=int(payload.get("source_accession_count") or 0),
            bridge_positive_accession_count=int(
                payload.get("bridge_positive_accession_count") or 0
            ),
            packet_complete_accession_count=int(
                payload.get("packet_complete_accession_count")
                or payload.get("materialized_accession_count")
                or 0
            ),
            bridge_only_accession_count=int(payload.get("bridge_only_accession_count") or 0),
            partial_accession_count=int(payload.get("partial_accession_count") or 0),
            unavailable_accession_count=int(payload.get("unavailable_accession_count") or 0),
            entries=tuple(
                item
                if isinstance(item, StructurePacketEnrichmentEntry)
                else StructurePacketEnrichmentEntry.from_dict(item)
                for item in _iter_values(payload.get("entries") or ())
            ),
            issues=tuple(
                item
                if isinstance(item, StructurePacketIssue)
                else StructurePacketIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or ())
            ),
            notes=payload.get("notes") or payload.get("note") or (),
        )


def _load_protein_depth_slice(
    protein_depth_slice: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], str]:
    if isinstance(protein_depth_slice, (str, Path)):
        path = Path(protein_depth_slice)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise TypeError("protein_depth_slice must be a JSON object")
        return dict(payload), str(path)
    if not isinstance(protein_depth_slice, Mapping):
        raise TypeError("protein_depth_slice must be a mapping or path")
    return dict(protein_depth_slice), ""


def _bridge_positive_accessions(
    protein_depth_slice: Mapping[str, Any],
    *,
    include_unbridged: bool,
) -> dict[str, dict[str, Any]]:
    direct_rows = {
        _required_text(row.get("accession"), "accession"): dict(row)
        for row in _iter_values(protein_depth_slice.get("direct_evidence") or ())
        if isinstance(row, Mapping)
    }
    bridge_targets = protein_depth_slice.get("structure_bridge_targets") or {}
    if not isinstance(bridge_targets, Mapping):
        raise TypeError("structure_bridge_targets must be a mapping")

    selected: dict[str, dict[str, Any]] = {}
    for accession, row in direct_rows.items():
        pdb_ids = _dedupe_text(bridge_targets.get(accession) or ())
        if pdb_ids or include_unbridged:
            row["bridge_pdb_ids"] = pdb_ids
            selected[accession] = row
    return selected


def _group_bridge_records(
    protein_depth_slice: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    bridge_result = protein_depth_slice.get("structure_bridge_result") or {}
    if not isinstance(bridge_result, Mapping):
        raise TypeError("structure_bridge_result must be a mapping")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in _iter_values(bridge_result.get("records") or ()):
        if not isinstance(record, Mapping):
            continue
        accession = _optional_text(record.get("accession"))
        if accession is None:
            continue
        grouped.setdefault(accession, []).append(dict(record))
    return grouped


def _load_coordinate_payload(
    pdb_id: str,
    roots: tuple[Path, ...],
) -> StructureCoordinatePayload | None:
    for root in roots:
        for path in _candidate_payload_paths(root, pdb_id):
            if not path.is_file():
                continue
            byte_count = path.stat().st_size
            if byte_count == 0:
                return StructureCoordinatePayload(
                    pdb_id=pdb_id,
                    payload_ref=str(path),
                    payload_state="empty",
                    byte_count=0,
                    notes=("empty_coordinate_payload",),
                )
            payload_bytes = path.read_bytes()
            try:
                payload_data = _load_json(path)
            except Exception:
                return StructureCoordinatePayload(
                    pdb_id=pdb_id,
                    payload_ref=str(path),
                    payload_state="invalid",
                    byte_count=byte_count,
                    payload_sha256=_sha256_hex(payload_bytes),
                    notes=("invalid_coordinate_payload",),
                )
            return StructureCoordinatePayload(
                pdb_id=pdb_id,
                payload_ref=str(path),
                payload_state="available",
                byte_count=byte_count,
                payload_sha256=_sha256_hex(payload_bytes),
                task_type=payload_data.get("task_type"),
                source_record_id=payload_data.get("source_record_id"),
                payload_data=payload_data,
                notes=("packet_ready_coordinate_payload",),
            )
    return None


def _entry_state(
    payloads: tuple[StructureCoordinatePayload, ...],
    pdb_ids: tuple[str, ...],
) -> StructurePacketState:
    if not pdb_ids:
        return "unavailable"
    if not payloads:
        return "bridge_only"
    available = sum(1 for payload in payloads if payload.payload_state == "available")
    if available == len(pdb_ids):
        return "packet_complete"
    if available > 0:
        return "partial"
    return "bridge_only"


def enrich_structure_packets(
    protein_depth_slice: Mapping[str, Any] | str | Path,
    *,
    coordinate_payload_roots: Iterable[str | Path] = (),
    include_unbridged: bool = False,
    source_artifact_refs: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> StructurePacketEnrichmentResult:
    payload, source_slice_ref = _load_protein_depth_slice(protein_depth_slice)
    bridge_rows = _bridge_positive_accessions(payload, include_unbridged=include_unbridged)
    bridge_records = _group_bridge_records(payload)
    roots = _normalize_path_roots(coordinate_payload_roots)
    source_task_id = _required_text(payload.get("task_id") or "P15-T002", "source_task_id")
    selected_source_ref = (
        source_slice_ref
        or _optional_text(payload.get("source_slice_ref"))
        or source_task_id
    )
    source_refs = _dedupe_text(
        (
            source_slice_ref,
            *source_artifact_refs,
            payload.get("source_slice_ref"),
            payload.get("results_dir"),
        )
    )

    entries: list[StructurePacketEnrichmentEntry] = []
    issues: list[StructurePacketIssue] = []
    bridge_positive = materialized = bridge_only = partial = unavailable = 0

    for accession, row in bridge_rows.items():
        pdb_ids = _dedupe_text(row.get("bridge_pdb_ids") or ())
        accession_records = bridge_records.get(accession, [])
        if pdb_ids:
            bridge_positive += 1
        record_refs = _dedupe_text(
            record.get("source_record_id") or f"{accession}:{record.get('pdb_id')}"
            for record in accession_records
        )
        evidence_refs = _dedupe_text(
            evidence_ref
            for record in accession_records
            for evidence_ref in _iter_values(record.get("evidence_refs") or ())
        )
        payloads = tuple(
            payload_item
            for pdb_id in pdb_ids
            if (payload_item := _load_coordinate_payload(pdb_id, roots)) is not None
        )
        entry_issues: list[StructurePacketIssue] = []
        for pdb_id in pdb_ids:
            if any(
                payload_item.pdb_id == pdb_id
                and payload_item.payload_state == "available"
                for payload_item in payloads
            ):
                continue
            if any(
                payload_item.pdb_id == pdb_id
                and payload_item.payload_state == "empty"
                for payload_item in payloads
            ):
                entry_issues.append(
                    StructurePacketIssue(
                        accession=accession,
                        kind="empty_coordinate_payload",
                        message="coordinate payload file exists but is empty",
                        pdb_id=pdb_id,
                        payload_ref=next(
                            payload_item.payload_ref
                            for payload_item in payloads
                            if payload_item.pdb_id == pdb_id
                        ),
                    )
                )
                continue
            if any(
                payload_item.pdb_id == pdb_id
                and payload_item.payload_state == "invalid"
                for payload_item in payloads
            ):
                entry_issues.append(
                    StructurePacketIssue(
                        accession=accession,
                        kind="invalid_coordinate_payload",
                        message="coordinate payload file could not be parsed as JSON",
                        pdb_id=pdb_id,
                        payload_ref=next(
                            payload_item.payload_ref
                            for payload_item in payloads
                            if payload_item.pdb_id == pdb_id
                        ),
                    )
                )
                continue
            entry_issues.append(
                StructurePacketIssue(
                    accession=accession,
                    kind="missing_coordinate_payload",
                    message="no coordinate payload was available for the bridge-positive target",
                    pdb_id=pdb_id,
                    details={"pdb_id": pdb_id},
                )
            )

        packet_state = _entry_state(payloads, pdb_ids)
        bridge_state = "positive_hit" if pdb_ids else "absent"
        bridge_kind = "bridge_only" if pdb_ids else None
        if packet_state == "packet_complete":
            materialized += 1
        elif packet_state == "partial":
            partial += 1
        elif packet_state == "bridge_only":
            bridge_only += 1
        else:
            unavailable += 1
            if not pdb_ids:
                entry_issues.append(
                    StructurePacketIssue(
                        accession=accession,
                        kind="unbridged_accession",
                        message="accession had no bridge-positive structure target",
                    )
                )

        entry_notes = _dedupe_text(
            (
                *row.get("coverage_notes", ()),
                "bridge_only"
                if packet_state == "bridge_only"
                else "coordinate_payload_packet_complete"
                if packet_state == "packet_complete"
                else "coordinate_payload_partial"
                if packet_state == "partial"
                else "coordinate_payload_unavailable",
            )
        )
        entries.append(
            StructurePacketEnrichmentEntry(
                accession=accession,
                canonical_id=row.get("canonical_id") or f"protein:{accession}",
                split=row.get("split"),
                bucket=row.get("bucket"),
                judgment=row.get("judgment"),
                evidence_mode=row.get("evidence_mode"),
                lane_depth=row.get("lane_depth"),
                source_lanes=row.get("source_lanes") or (),
                present_modalities=row.get("present_modalities") or (),
                missing_modalities=row.get("missing_modalities") or (),
                coverage_notes=row.get("coverage_notes") or (),
                bridge_state=bridge_state,
                bridge_kind=bridge_kind,
                packet_state=packet_state,
                pdb_ids=pdb_ids,
                source_record_refs=record_refs,
                evidence_refs=evidence_refs,
                provenance_refs=(
                    *source_refs,
                    *record_refs,
                    *evidence_refs,
                ),
                coordinate_payloads=payloads,
                notes=entry_notes,
                issues=tuple(entry_issues),
            )
        )
        issues.extend(entry_issues)

    if entries and materialized and not bridge_only and not partial and not unavailable:
        status = "packet_complete"
    elif entries and materialized:
        status = "partial"
    elif entries and bridge_only:
        status = "bridge_only"
    else:
        status = "unavailable"

    return StructurePacketEnrichmentResult(
        source_task_id=source_task_id,
        source_slice_ref=selected_source_ref,
        source_artifact_refs=source_refs,
        status=status,
        source_accession_count=len(_iter_values(payload.get("direct_evidence") or ())),
        bridge_positive_accession_count=bridge_positive,
        packet_complete_accession_count=materialized,
        bridge_only_accession_count=bridge_only,
        partial_accession_count=partial,
        unavailable_accession_count=unavailable,
        entries=tuple(entries),
        issues=tuple(issues),
        notes=notes,
    )


__all__ = [
    "StructureCoordinatePayload",
    "StructurePacketEnrichmentEntry",
    "StructurePacketEnrichmentResult",
    "StructurePacketIssue",
    "StructurePacketIssueKind",
    "StructurePacketState",
    "StructurePayloadState",
    "enrich_structure_packets",
]
