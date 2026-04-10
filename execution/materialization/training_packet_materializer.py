from __future__ import annotations

import json
import shutil
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

PacketStatus = Literal["complete", "partial", "unresolved"]
LatestPromotionState = Literal["promoted", "held"]
PayloadValue = str | bytes | Path | Mapping[str, Any] | Sequence[Any]


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
    if isinstance(values, (str, bytes, Path)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _slug(value: str) -> str:
    text = _required_text(value, "slug value")
    cleaned = [
        character.lower()
        for character in text
        if character.isalnum() or character in {"-", "_", "."}
    ]
    slug = "".join(cleaned).strip("._-")
    return slug or "artifact"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _payload_suffix(payload: PayloadValue) -> str:
    if isinstance(payload, Path):
        return payload.suffix or ".dat"
    if isinstance(payload, bytes):
        return ".bin"
    if isinstance(payload, str):
        return ".txt"
    return ".json"


def _materialize_payload(
    payload: PayloadValue,
    *,
    destination: Path,
) -> tuple[str, int | None]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, Path):
        if not payload.exists():
            raise FileNotFoundError(f"missing source payload: {payload}")
        shutil.copy2(payload, destination)
        return "path_copy", destination.stat().st_size
    if isinstance(payload, bytes):
        destination.write_bytes(payload)
        return "bytes", len(payload)
    if isinstance(payload, str):
        candidate_path = Path(payload)
        if (
            ("\\" in payload or "/" in payload)
            and candidate_path.suffix
            and not payload.lstrip().startswith(("{", "["))
        ):
            raise TypeError(
                "ambiguous string payload looks like a file reference; "
                "use Path or a structured file_ref instead"
            )
        destination.write_text(payload, encoding="utf-8")
        return "text", len(payload.encode("utf-8"))
    destination.write_text(json.dumps(_json_ready(payload), indent=2), encoding="utf-8")
    return "json", destination.stat().st_size


@dataclass(frozen=True, slots=True)
class TrainingPacketRequest:
    packet_id: str
    accession: str
    canonical_id: str
    requested_modalities: tuple[str, ...] = ("sequence", "structure", "ligand", "ppi")
    modality_sources: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    planning_index_ref: str | None = None
    split_name: str | None = None
    raw_manifest_ids: tuple[str, ...] = field(default_factory=tuple)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", _required_text(self.packet_id, "packet_id"))
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        object.__setattr__(self, "requested_modalities", _dedupe_text(self.requested_modalities))
        normalized_sources: dict[str, tuple[str, ...]] = {}
        for modality, refs in dict(self.modality_sources).items():
            modality_name = _required_text(modality, "modality")
            normalized_sources[modality_name] = _dedupe_text(refs)
        object.__setattr__(self, "modality_sources", normalized_sources)
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "split_name", _optional_text(self.split_name))
        object.__setattr__(self, "raw_manifest_ids", _dedupe_text(self.raw_manifest_ids))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "requested_modalities": list(self.requested_modalities),
            "modality_sources": {
                modality: list(refs) for modality, refs in self.modality_sources.items()
            },
            "planning_index_ref": self.planning_index_ref,
            "split_name": self.split_name,
            "raw_manifest_ids": list(self.raw_manifest_ids),
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
            "metadata": _json_ready(dict(self.metadata)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TrainingPacketRequest:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        modality_sources = payload.get("modality_sources") or {}
        if not isinstance(modality_sources, Mapping):
            raise TypeError("modality_sources must be a mapping")
        return cls(
            packet_id=payload.get("packet_id") or payload.get("id") or "",
            accession=payload.get("accession") or "",
            canonical_id=payload.get("canonical_id") or payload.get("canonical") or "",
            requested_modalities=payload.get("requested_modalities") or (),
            modality_sources={
                _clean_text(modality): _dedupe_text(refs)
                for modality, refs in modality_sources.items()
            },
            planning_index_ref=payload.get("planning_index_ref"),
            split_name=payload.get("split_name") or payload.get("split"),
            raw_manifest_ids=payload.get("raw_manifest_ids") or (),
            provenance_refs=payload.get("provenance_refs") or (),
            notes=payload.get("notes") or (),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class MaterializedPacketArtifact:
    modality: str
    source_ref: str
    relative_path: str
    payload_kind: str
    size_bytes: int | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "modality", _required_text(self.modality, "modality"))
        object.__setattr__(self, "source_ref", _required_text(self.source_ref, "source_ref"))
        object.__setattr__(
            self,
            "relative_path",
            _required_text(self.relative_path, "relative_path"),
        )
        object.__setattr__(self, "payload_kind", _required_text(self.payload_kind, "payload_kind"))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "modality": self.modality,
            "source_ref": self.source_ref,
            "relative_path": self.relative_path,
            "payload_kind": self.payload_kind,
            "size_bytes": self.size_bytes,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class MaterializedTrainingPacket:
    packet_id: str
    accession: str
    canonical_id: str
    status: PacketStatus
    release_grade_ready: bool
    latest_promotion_state: LatestPromotionState
    packet_dir: str
    manifest_path: str
    requested_modalities: tuple[str, ...]
    present_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    modality_sources: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    artifacts: tuple[MaterializedPacketArtifact, ...] = field(default_factory=tuple)
    raw_manifest_ids: tuple[str, ...] = field(default_factory=tuple)
    provenance_refs: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", _required_text(self.packet_id, "packet_id"))
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        if self.status not in {"complete", "partial", "unresolved"}:
            raise ValueError(f"unsupported packet status: {self.status!r}")
        if not isinstance(self.release_grade_ready, bool):
            raise TypeError("release_grade_ready must be a boolean")
        if self.latest_promotion_state not in {"promoted", "held"}:
            raise ValueError(
                f"unsupported latest_promotion_state: {self.latest_promotion_state!r}"
            )
        object.__setattr__(self, "packet_dir", _required_text(self.packet_dir, "packet_dir"))
        object.__setattr__(
            self,
            "manifest_path",
            _required_text(self.manifest_path, "manifest_path"),
        )
        object.__setattr__(self, "requested_modalities", _dedupe_text(self.requested_modalities))
        object.__setattr__(self, "present_modalities", _dedupe_text(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        normalized_sources: dict[str, tuple[str, ...]] = {}
        for modality, refs in dict(self.modality_sources).items():
            modality_name = _required_text(modality, "modality")
            normalized_sources[modality_name] = _dedupe_text(refs)
        object.__setattr__(self, "modality_sources", normalized_sources)
        object.__setattr__(self, "raw_manifest_ids", _dedupe_text(self.raw_manifest_ids))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "status": self.status,
            "release_grade_ready": self.release_grade_ready,
            "latest_promotion_state": self.latest_promotion_state,
            "packet_dir": self.packet_dir,
            "manifest_path": self.manifest_path,
            "requested_modalities": list(self.requested_modalities),
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "modality_sources": {
                modality: list(refs) for modality, refs in self.modality_sources.items()
            },
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "raw_manifest_ids": list(self.raw_manifest_ids),
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class TrainingPacketMaterializationResult:
    run_id: str
    output_root: str
    status: PacketStatus
    release_grade_ready: bool
    latest_promotion_state: LatestPromotionState
    packet_count: int
    complete_count: int
    partial_count: int
    unresolved_count: int
    packets: tuple[MaterializedTrainingPacket, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        object.__setattr__(self, "output_root", _required_text(self.output_root, "output_root"))
        if self.status not in {"complete", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        if not isinstance(self.release_grade_ready, bool):
            raise TypeError("release_grade_ready must be a boolean")
        if self.latest_promotion_state not in {"promoted", "held"}:
            raise ValueError(
                f"unsupported latest_promotion_state: {self.latest_promotion_state!r}"
            )
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "output_root": self.output_root,
            "status": self.status,
            "release_grade_ready": self.release_grade_ready,
            "latest_promotion_state": self.latest_promotion_state,
            "packet_count": self.packet_count,
            "complete_count": self.complete_count,
            "partial_count": self.partial_count,
            "unresolved_count": self.unresolved_count,
            "packets": [packet.to_dict() for packet in self.packets],
            "notes": list(self.notes),
            "created_at": self.created_at,
        }


def _status_from_modalities(
    *,
    requested_modalities: Sequence[str],
    present_modalities: Sequence[str],
) -> PacketStatus:
    requested = _dedupe_text(requested_modalities)
    present_lookup = {modality.casefold() for modality in _dedupe_text(present_modalities)}
    if requested and all(modality.casefold() in present_lookup for modality in requested):
        return "complete"
    if present_lookup:
        return "partial"
    return "unresolved"


def _latest_promotion_state(status: PacketStatus) -> tuple[bool, LatestPromotionState, str]:
    if status == "complete":
        return True, "promoted", "complete packet run promoted as release-grade latest"
    if status == "partial":
        return False, "held", "partial packet run held from release-grade promotion"
    return False, "held", "unresolved packet run held from release-grade promotion"


def _status_rank(status: str) -> int:
    return {"unresolved": 0, "partial": 1, "complete": 2}.get(_clean_text(status), -1)


def _latest_quality_key(payload: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        _status_rank(_clean_text(payload.get("status"))),
        int(payload.get("complete_count") or 0),
        -int(payload.get("unresolved_count") or 0),
        -int(payload.get("partial_count") or 0),
        int(payload.get("packet_count") or 0),
    )


def _normalize_latest_payload_consistency(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _json_ready(dict(payload))
    top_level_status = _clean_text(normalized.get("status"))
    top_level_release_grade_ready = bool(normalized.get("release_grade_ready"))
    top_level_latest_promotion_state = _clean_text(
        normalized.get("latest_promotion_state")
    )
    packets = normalized.get("packets")
    if not isinstance(packets, list):
        return normalized

    run_is_promoted_latest = (
        top_level_status == "complete"
        and top_level_release_grade_ready
        and top_level_latest_promotion_state == "promoted"
    )
    normalized_packets: list[dict[str, Any]] = []
    for packet in packets:
        if not isinstance(packet, Mapping):
            normalized_packets.append(packet)
            continue
        packet_payload = _json_ready(dict(packet))
        packet_is_complete = _clean_text(packet_payload.get("status")) == "complete"
        packet_payload["latest_promotion_state"] = (
            "promoted" if run_is_promoted_latest and packet_is_complete else "held"
        )
        normalized_packets.append(packet_payload)
    normalized["packets"] = normalized_packets
    return normalized


def _should_replace_latest(candidate: Mapping[str, Any], current_latest_path: Path) -> bool:
    if not current_latest_path.exists():
        return True
    existing = _read_json(current_latest_path)
    if not isinstance(existing, Mapping):
        return True
    return _latest_quality_key(candidate) >= _latest_quality_key(
        _normalize_latest_payload_consistency(existing)
    )


def materialize_training_packets(
    requests: Iterable[TrainingPacketRequest | Mapping[str, Any]],
    *,
    available_payloads: Mapping[str, PayloadValue],
    output_root: Path,
    run_id: str | None = None,
) -> TrainingPacketMaterializationResult:
    normalized_requests = tuple(
        request
        if isinstance(request, TrainingPacketRequest)
        else TrainingPacketRequest.from_dict(request)
        for request in requests
    )
    resolved_run_id = _optional_text(run_id) or (
        f"training-packets-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    run_root = output_root / resolved_run_id
    run_root.mkdir(parents=True, exist_ok=True)

    packet_rows: list[dict[str, Any]] = []
    for request in normalized_requests:
        packet_root = run_root / _slug(request.packet_id)
        artifacts_root = packet_root / "artifacts"
        artifacts_root.mkdir(parents=True, exist_ok=True)

        present_modalities: list[str] = []
        artifacts: list[MaterializedPacketArtifact] = []
        notes: list[str] = []

        for modality in request.requested_modalities:
            source_refs = request.modality_sources.get(modality, ())
            modality_written = False
            if not source_refs:
                notes.append(f"no source refs declared for modality={modality}")
            for index, source_ref in enumerate(source_refs, start=1):
                payload = available_payloads.get(source_ref)
                if payload is None:
                    notes.append(f"missing payload for {modality}:{source_ref}")
                    continue
                suffix = _payload_suffix(payload)
                destination = artifacts_root / f"{_slug(modality)}-{index}{suffix}"
                payload_kind, size_bytes = _materialize_payload(payload, destination=destination)
                artifacts.append(
                    MaterializedPacketArtifact(
                        modality=modality,
                        source_ref=source_ref,
                        relative_path=str(destination.relative_to(packet_root)),
                        payload_kind=payload_kind,
                        size_bytes=size_bytes,
                    )
                )
                modality_written = True
            if modality_written:
                present_modalities.append(modality)

        missing_modalities = tuple(
            modality
            for modality in request.requested_modalities
            if modality.casefold() not in {item.casefold() for item in present_modalities}
        )
        packet_status = _status_from_modalities(
            requested_modalities=request.requested_modalities,
            present_modalities=present_modalities,
        )
        packet_rows.append(
            {
                "request": request,
                "packet_root": packet_root,
                "packet_status": packet_status,
                "artifacts": tuple(artifacts),
                "present_modalities": tuple(present_modalities),
                "missing_modalities": missing_modalities,
                "notes": _dedupe_text((*request.notes, *notes)),
            }
        )

    complete_count = sum(1 for row in packet_rows if row["packet_status"] == "complete")
    partial_count = sum(1 for row in packet_rows if row["packet_status"] == "partial")
    unresolved_count = sum(1 for row in packet_rows if row["packet_status"] == "unresolved")
    overall_status: PacketStatus
    if packet_rows and complete_count == len(packet_rows):
        overall_status = "complete"
    elif complete_count or partial_count:
        overall_status = "partial"
    else:
        overall_status = "unresolved"
    release_grade_ready, latest_promotion_state, latest_promotion_note = _latest_promotion_state(
        overall_status
    )

    packets: list[MaterializedTrainingPacket] = []
    for row in packet_rows:
        request = row["request"]
        packet_root = row["packet_root"]
        packet_status = row["packet_status"]
        artifacts = row["artifacts"]
        present_modalities = row["present_modalities"]
        missing_modalities = row["missing_modalities"]
        notes = row["notes"]
        packet_release_grade_ready = packet_status == "complete"
        packet_latest_promotion_state: LatestPromotionState = (
            "promoted" if release_grade_ready and packet_release_grade_ready else "held"
        )
        packet_manifest = {
            "packet_id": request.packet_id,
            "accession": request.accession,
            "canonical_id": request.canonical_id,
            "planning_index_ref": request.planning_index_ref,
            "split_name": request.split_name,
            "status": packet_status,
            "requested_modalities": list(request.requested_modalities),
            "present_modalities": list(_dedupe_text(present_modalities)),
            "missing_modalities": list(missing_modalities),
            "modality_sources": {
                modality: list(refs) for modality, refs in request.modality_sources.items()
            },
            "raw_manifest_ids": list(request.raw_manifest_ids),
            "provenance_refs": list(request.provenance_refs),
            "notes": list(_dedupe_text((*request.notes, *notes))),
            "metadata": _json_ready(dict(request.metadata)),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
        }
        packet_manifest["release_grade_ready"] = packet_release_grade_ready
        packet_manifest["latest_promotion_state"] = packet_latest_promotion_state
        manifest_path = packet_root / "packet_manifest.json"
        _write_json(manifest_path, packet_manifest)

        packets.append(
            MaterializedTrainingPacket(
                packet_id=request.packet_id,
                accession=request.accession,
                canonical_id=request.canonical_id,
                status=packet_status,
                release_grade_ready=packet_release_grade_ready,
                latest_promotion_state=packet_latest_promotion_state,
                packet_dir=str(packet_root),
                manifest_path=str(manifest_path),
                requested_modalities=request.requested_modalities,
                present_modalities=tuple(present_modalities),
                missing_modalities=missing_modalities,
                modality_sources=request.modality_sources,
                artifacts=tuple(artifacts),
                raw_manifest_ids=request.raw_manifest_ids,
                provenance_refs=request.provenance_refs,
                notes=_dedupe_text((*request.notes, *notes)),
            )
        )

    result = TrainingPacketMaterializationResult(
        run_id=resolved_run_id,
        output_root=str(run_root),
        status=overall_status,
        release_grade_ready=release_grade_ready,
        latest_promotion_state=latest_promotion_state,
        packet_count=len(packets),
        complete_count=complete_count,
        partial_count=partial_count,
        unresolved_count=unresolved_count,
        packets=tuple(packets),
        notes=(
            "manifest_driven_packet_materialization",
            latest_promotion_note,
        ),
    )
    result_payload = _normalize_latest_payload_consistency(result.to_dict())
    _write_json(run_root / "materialization_summary.json", result_payload)
    latest_path = output_root / "LATEST.json"
    if latest_path.exists():
        existing_latest = _read_json(latest_path)
        if isinstance(existing_latest, Mapping):
            normalized_existing_latest = _normalize_latest_payload_consistency(existing_latest)
            if normalized_existing_latest != _json_ready(dict(existing_latest)):
                _write_json(latest_path, normalized_existing_latest)
    if _should_replace_latest(result_payload, latest_path):
        _write_json(output_root / "LATEST.json", result_payload)
    if result.status == "complete":
        _write_json(output_root / "LATEST.release.json", result_payload)
    else:
        _write_json(output_root / "LATEST.partial.json", result_payload)
    return result


__all__ = [
    "MaterializedPacketArtifact",
    "MaterializedTrainingPacket",
    "LatestPromotionState",
    "PacketStatus",
    "TrainingPacketMaterializationResult",
    "TrainingPacketRequest",
    "materialize_training_packets",
]
