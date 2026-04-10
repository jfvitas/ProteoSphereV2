from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from core.storage.package_manifest import PackageManifest
from execution.materialization.selective_materializer import (
    SelectiveMaterializationExample,
    SelectiveMaterializationResult,
)

PacketChecksumAuditStatus = Literal["consistent", "partial", "unresolved"]
PacketChecksumState = Literal["consistent", "partial", "unavailable"]
PacketChecksumDriftState = Literal["same", "drifted", "unavailable"]
PacketChecksumIssueKind = Literal[
    "missing_materialized_artifact",
    "missing_canonical_record",
    "checksum_drift",
    "partial_packet",
    "unavailable_packet",
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
    if isinstance(values, Sequence):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


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


def _stable_digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def _coerce_package_manifest(
    value: PackageManifest | Mapping[str, Any],
) -> PackageManifest:
    if isinstance(value, PackageManifest):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("package_manifest must be a PackageManifest or mapping")
    return PackageManifest.from_dict(value)


def _coerce_selective_result(
    value: SelectiveMaterializationResult | Mapping[str, Any],
) -> SelectiveMaterializationResult:
    if isinstance(value, SelectiveMaterializationResult):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("selective_result must be a SelectiveMaterializationResult or mapping")
    return SelectiveMaterializationResult.from_dict(value)


def _example_lookup(
    selective_result: SelectiveMaterializationResult,
) -> dict[str, SelectiveMaterializationExample]:
    return {example.example_id: example for example in selective_result.selected_examples}


def _materialized_pointer_map(
    example: SelectiveMaterializationExample,
) -> dict[str, dict[str, Any]]:
    return {
        artifact.artifact_pointer.pointer: {
            "artifact_kind": artifact.artifact_pointer.artifact_kind,
            "pointer": artifact.artifact_pointer.pointer,
            "selector": artifact.artifact_pointer.selector,
            "source_name": artifact.artifact_pointer.source_name,
            "source_record_id": artifact.artifact_pointer.source_record_id,
            "materialized_ref": artifact.materialized_ref,
            "checksum": artifact.checksum,
            "provenance_refs": list(artifact.provenance_refs),
            "notes": list(artifact.notes),
        }
        for artifact in example.materialized_artifacts
    }


def _asset_identity_payload(
    package_manifest: PackageManifest,
    example: SelectiveMaterializationExample,
) -> dict[str, Any]:
    return {
        "package_id": package_manifest.package_id,
        "package_manifest_id": package_manifest.manifest_id,
        "example_id": example.example_id,
        "planning_index_ref": example.planning_index_ref,
        "source_record_refs": list(example.source_record_refs),
        "canonical_ids": list(example.canonical_ids),
        "artifact_pointers": [
            {
                "artifact_kind": pointer.artifact_kind,
                "pointer": pointer.pointer,
                "selector": pointer.selector,
                "source_name": pointer.source_name,
                "source_record_id": pointer.source_record_id,
            }
            for pointer in example.artifact_pointers
        ],
        "materialized_artifacts": _materialized_pointer_map(example),
        "raw_manifest_ids": [
            manifest.raw_manifest_id for manifest in package_manifest.raw_manifests
        ],
        "planning_index_refs": list(package_manifest.planning_index_refs),
        "provenance": list(package_manifest.provenance),
    }


def _entry_state(example: SelectiveMaterializationExample) -> PacketChecksumState:
    if example.status == "materialized" and example.materialized_artifacts:
        return "consistent"
    if example.materialized_artifacts:
        return "partial"
    return "unavailable"


def _entry_issues(
    *,
    example: SelectiveMaterializationExample,
    packet_state: PacketChecksumState,
    drift_state: PacketChecksumDriftState,
    reference_checksum: str | None,
) -> tuple[dict[str, Any], ...]:
    issues: list[dict[str, Any]] = []
    if packet_state == "partial":
        issues.append(
            {
                "kind": "partial_packet",
                "message": "selected example only rebuilt a subset of its pinned artifacts",
            }
        )
    if packet_state == "unavailable":
        issues.append(
            {
                "kind": "unavailable_packet",
                "message": "selected example has no materialized artifacts in the rebuild output",
            }
        )
    for issue in example.issues:
        issues.append(
            {
                "kind": issue.kind,
                "message": issue.message,
                "artifact_pointer": issue.artifact_pointer,
                "canonical_id": issue.canonical_id,
                "details": _json_ready(dict(issue.details)),
            }
        )
    if drift_state == "drifted":
        issues.append(
            {
                "kind": "checksum_drift",
                "message": "rebuild checksum differs from the reference audit",
                "details": {
                    "reference_checksum": reference_checksum,
                },
            }
        )
    return tuple(issues)


@dataclass(frozen=True, slots=True)
class PacketChecksumAuditEntry:
    example_id: str
    packet_state: PacketChecksumState
    drift_state: PacketChecksumDriftState
    asset_identity_checksum: str
    expected_artifact_count: int
    materialized_artifact_count: int
    expected_artifact_pointers: tuple[str, ...] = ()
    materialized_artifact_pointers: tuple[str, ...] = ()
    missing_artifact_pointers: tuple[str, ...] = ()
    planning_index_ref: str | None = None
    canonical_ids: tuple[str, ...] = ()
    source_record_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    issues: tuple[dict[str, Any], ...] = ()
    reference_checksum: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        if self.packet_state not in {"consistent", "partial", "unavailable"}:
            raise ValueError(f"unsupported packet_state: {self.packet_state!r}")
        if self.drift_state not in {"same", "drifted", "unavailable"}:
            raise ValueError(f"unsupported drift_state: {self.drift_state!r}")
        object.__setattr__(
            self,
            "asset_identity_checksum",
            _required_text(self.asset_identity_checksum, "asset_identity_checksum"),
        )
        object.__setattr__(self, "expected_artifact_count", int(self.expected_artifact_count))
        object.__setattr__(
            self,
            "materialized_artifact_count",
            int(self.materialized_artifact_count),
        )
        object.__setattr__(
            self,
            "expected_artifact_pointers",
            _dedupe_text(self.expected_artifact_pointers),
        )
        object.__setattr__(
            self,
            "materialized_artifact_pointers",
            _dedupe_text(self.materialized_artifact_pointers),
        )
        object.__setattr__(
            self,
            "missing_artifact_pointers",
            _dedupe_text(self.missing_artifact_pointers),
        )
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "canonical_ids", _dedupe_text(self.canonical_ids))
        object.__setattr__(self, "source_record_refs", _dedupe_text(self.source_record_refs))
        object.__setattr__(self, "provenance_refs", _dedupe_text(self.provenance_refs))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "issues", tuple(dict(item) for item in self.issues))
        object.__setattr__(self, "reference_checksum", _optional_text(self.reference_checksum))

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "packet_state": self.packet_state,
            "drift_state": self.drift_state,
            "asset_identity_checksum": self.asset_identity_checksum,
            "expected_artifact_count": self.expected_artifact_count,
            "materialized_artifact_count": self.materialized_artifact_count,
            "expected_artifact_pointers": list(self.expected_artifact_pointers),
            "materialized_artifact_pointers": list(self.materialized_artifact_pointers),
            "missing_artifact_pointers": list(self.missing_artifact_pointers),
            "planning_index_ref": self.planning_index_ref,
            "canonical_ids": list(self.canonical_ids),
            "source_record_refs": list(self.source_record_refs),
            "provenance_refs": list(self.provenance_refs),
            "notes": list(self.notes),
            "issues": [_json_ready(item) for item in self.issues],
            "reference_checksum": self.reference_checksum,
        }


@dataclass(frozen=True, slots=True)
class PacketChecksumAuditResult:
    package_id: str
    package_manifest_id: str
    status: PacketChecksumAuditStatus
    entries: tuple[PacketChecksumAuditEntry, ...]
    reference_audit_id: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_id", _required_text(self.package_id, "package_id"))
        object.__setattr__(
            self,
            "package_manifest_id",
            _required_text(self.package_manifest_id, "package_manifest_id"),
        )
        if self.status not in {"consistent", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(self, "reference_audit_id", _optional_text(self.reference_audit_id))
        object.__setattr__(self, "summary", dict(self.summary))

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "package_manifest_id": self.package_manifest_id,
            "status": self.status,
            "entry_count": self.entry_count,
            "reference_audit_id": self.reference_audit_id,
            "entries": [entry.to_dict() for entry in self.entries],
            "summary": _json_ready(dict(self.summary)),
        }


def audit_packet_checksums(
    package_manifest: PackageManifest | Mapping[str, Any],
    selective_result: SelectiveMaterializationResult | Mapping[str, Any],
    *,
    reference_audit: PacketChecksumAuditResult | Mapping[str, Any] | None = None,
) -> PacketChecksumAuditResult:
    manifest = _coerce_package_manifest(package_manifest)
    selective = _coerce_selective_result(selective_result)
    reference_lookup: dict[str, str] = {}
    reference_audit_id = None
    if reference_audit is not None:
        if isinstance(reference_audit, PacketChecksumAuditResult):
            reference_audit_id = reference_audit.package_manifest_id
            reference_lookup = {
                entry.example_id: entry.asset_identity_checksum for entry in reference_audit.entries
            }
        elif isinstance(reference_audit, Mapping):
            reference_audit_id = _clean_text(reference_audit.get("package_manifest_id"))
            for item in _iter_values(reference_audit.get("entries") or ()):
                if not isinstance(item, Mapping):
                    continue
                example_id = _clean_text(item.get("example_id"))
                checksum = _clean_text(item.get("asset_identity_checksum"))
                if example_id and checksum:
                    reference_lookup[example_id] = checksum
        else:
            raise TypeError("reference_audit must be a PacketChecksumAuditResult or mapping")

    selective_lookup = _example_lookup(selective)
    entries: list[PacketChecksumAuditEntry] = []
    for example in manifest.selected_examples:
        selected_example = selective_lookup.get(example.example_id)
        if selected_example is None:
            payload = {
                "example_id": example.example_id,
                "package_manifest_id": manifest.manifest_id,
                "selected_example": example.to_dict(),
                "materialized_example": None,
            }
            checksum = _stable_digest(payload)
            entries.append(
                PacketChecksumAuditEntry(
                    example_id=example.example_id,
                    packet_state="unavailable",
                    drift_state="unavailable",
                    asset_identity_checksum=checksum,
                    expected_artifact_count=len(example.artifact_pointers),
                    materialized_artifact_count=0,
                    expected_artifact_pointers=tuple(
                        pointer.pointer for pointer in example.artifact_pointers
                    ),
                    missing_artifact_pointers=tuple(
                        pointer.pointer for pointer in example.artifact_pointers
                    ),
                    planning_index_ref=example.planning_index_ref,
                    canonical_ids=example.canonical_ids,
                    source_record_refs=example.source_record_refs,
                    provenance_refs=manifest.provenance,
                    notes=("selected example was not materialized",),
                    issues=(
                        {
                            "kind": "unavailable_packet",
                            "message": "selected example was not materialized",
                        },
                    ),
                    reference_checksum=reference_lookup.get(example.example_id),
                )
            )
            continue

        packet_state = _entry_state(selected_example)
        checksum_payload = _asset_identity_payload(manifest, selected_example)
        checksum = _stable_digest(checksum_payload)
        reference_checksum = reference_lookup.get(example.example_id)
        if reference_checksum is None:
            drift_state: PacketChecksumDriftState = "unavailable"
        elif reference_checksum == checksum:
            drift_state = "same"
        else:
            drift_state = "drifted"
        expected_pointers = tuple(pointer.pointer for pointer in example.artifact_pointers)
        materialized_pointers = tuple(
            artifact.artifact_pointer.pointer
            for artifact in selected_example.materialized_artifacts
        )
        missing_pointers = tuple(
            pointer for pointer in expected_pointers if pointer not in materialized_pointers
        )
        entries.append(
            PacketChecksumAuditEntry(
                example_id=example.example_id,
                packet_state=packet_state,
                drift_state=drift_state,
                asset_identity_checksum=checksum,
                expected_artifact_count=len(expected_pointers),
                materialized_artifact_count=len(materialized_pointers),
                expected_artifact_pointers=expected_pointers,
                materialized_artifact_pointers=materialized_pointers,
                missing_artifact_pointers=missing_pointers,
                planning_index_ref=example.planning_index_ref,
                canonical_ids=example.canonical_ids,
                source_record_refs=example.source_record_refs,
                provenance_refs=(
                    manifest.provenance
                    + selected_example.provenance_refs
                    + selected_example.notes
                ),
                notes=selected_example.notes,
                issues=_entry_issues(
                    example=selected_example,
                    packet_state=packet_state,
                    drift_state=drift_state,
                    reference_checksum=reference_checksum,
                ),
                reference_checksum=reference_checksum,
            )
        )

    if not entries:
        status: PacketChecksumAuditStatus = "unresolved"
    elif any(
        entry.packet_state != "consistent" or entry.drift_state == "drifted"
        for entry in entries
    ):
        status = "partial"
    else:
        status = "consistent"

    summary = {
        "entry_count": len(entries),
        "consistent_count": sum(1 for entry in entries if entry.packet_state == "consistent"),
        "partial_count": sum(1 for entry in entries if entry.packet_state == "partial"),
        "unavailable_count": sum(1 for entry in entries if entry.packet_state == "unavailable"),
        "drifted_count": sum(1 for entry in entries if entry.drift_state == "drifted"),
        "same_count": sum(1 for entry in entries if entry.drift_state == "same"),
        "missing_artifact_count": sum(len(entry.missing_artifact_pointers) for entry in entries),
    }
    return PacketChecksumAuditResult(
        package_id=manifest.package_id,
        package_manifest_id=manifest.manifest_id,
        status=status,
        entries=tuple(entries),
        reference_audit_id=reference_audit_id,
        summary=summary,
    )


def audit_packet_checksum_payload(payload: Mapping[str, Any]) -> PacketChecksumAuditResult:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return PacketChecksumAuditResult(
        package_id=payload.get("package_id") or "",
        package_manifest_id=payload.get("package_manifest_id") or "",
        status=payload.get("status") or "unresolved",
        entries=tuple(
            item if isinstance(item, PacketChecksumAuditEntry) else PacketChecksumAuditEntry(**item)
            for item in _iter_values(payload.get("entries") or ())
        ),
        reference_audit_id=payload.get("reference_audit_id"),
        summary=dict(payload.get("summary") or {}),
    )


__all__ = [
    "PacketChecksumAuditEntry",
    "PacketChecksumAuditResult",
    "PacketChecksumAuditStatus",
    "PacketChecksumDriftState",
    "PacketChecksumIssueKind",
    "PacketChecksumState",
    "audit_packet_checksum_payload",
    "audit_packet_checksums",
]
