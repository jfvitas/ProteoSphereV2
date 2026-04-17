from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

CorpusObjectKind = Literal[
    "raw_authoritative",
    "raw_duplicate",
    "derived_mirror",
    "derived_extract",
    "staging_output",
    "warehouse_output",
    "ignore",
]
SourceIntegrationStatus = Literal[
    "discovered",
    "planned",
    "partial",
    "promoted",
    "duplicate",
    "derived_only",
    "blocked",
    "corrupt",
    "out_of_scope",
]
SourceValidationStatus = Literal["passed", "warning", "failed", "unknown"]
WorkUnitStatus = Literal[
    "planned",
    "claimed",
    "extracting",
    "normalized_unvalidated",
    "validated_unpromoted",
    "promoted",
    "blocked",
    "failed",
]
LaneName = Literal[
    "identity_sequence",
    "structure",
    "interaction_network",
    "ligand_assay",
    "motif_annotation",
    "pathway_reference",
    "scrape_enrichment",
    "warehouse_validation_export",
]
WorkerStatus = Literal["idle", "active", "waiting", "failed", "stopped"]
ValidationDecision = Literal["passed", "warning", "failed"]
ScopeTier = Literal[
    "authoritative",
    "duplicate",
    "derived",
    "scraped",
    "project_adjacent",
    "warehouse_reconciliation",
    "out_of_scope",
]
ConsolidationStatus = Literal[
    "not_required",
    "pending",
    "planned",
    "copied",
    "verified",
    "superseded_pending_cleanup",
    "blocked",
]

_KIND_VALUES = {
    "raw_authoritative",
    "raw_duplicate",
    "derived_mirror",
    "derived_extract",
    "staging_output",
    "warehouse_output",
    "ignore",
}
_INTEGRATION_VALUES = {
    "discovered",
    "planned",
    "partial",
    "promoted",
    "duplicate",
    "derived_only",
    "blocked",
    "corrupt",
    "out_of_scope",
}
_VALIDATION_VALUES = {"passed", "warning", "failed", "unknown"}
_WORK_UNIT_VALUES = {
    "planned",
    "claimed",
    "extracting",
    "normalized_unvalidated",
    "validated_unpromoted",
    "promoted",
    "blocked",
    "failed",
}
_LANE_VALUES = {
    "identity_sequence",
    "structure",
    "interaction_network",
    "ligand_assay",
    "motif_annotation",
    "pathway_reference",
    "scrape_enrichment",
    "warehouse_validation_export",
}
_WORKER_VALUES = {"idle", "active", "waiting", "failed", "stopped"}
_DECISION_VALUES = {"passed", "warning", "failed"}
_SCOPE_TIER_VALUES = {
    "authoritative",
    "duplicate",
    "derived",
    "scraped",
    "project_adjacent",
    "warehouse_reconciliation",
    "out_of_scope",
}
_CONSOLIDATION_VALUES = {
    "not_required",
    "pending",
    "planned",
    "copied",
    "verified",
    "superseded_pending_cleanup",
    "blocked",
}


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


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_int(value: Any, field_name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer >= {minimum}")
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer >= {minimum}") from exc
    if normalized < minimum:
        raise ValueError(f"{field_name} must be an integer >= {minimum}")
    return normalized


def _normalize_literal(value: Any, field_name: str, allowed: set[str]) -> str:
    text = _required_text(value, field_name).replace("-", "_").replace(" ", "_").casefold()
    if text not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
    return text


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    text = _optional_text(value)
    if text is None:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()


def _normalize_json_value(value: Any, field_name: str) -> JSONValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, JSONValue] = {}
        for key, item in value.items():
            normalized_key = _required_text(key, f"{field_name} key")
            normalized[normalized_key] = _normalize_json_value(item, f"{field_name}[{normalized_key!r}]")
        return normalized
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return tuple(_normalize_json_value(item, field_name) for item in value)
    raise TypeError(f"{field_name} must contain JSON-serializable values")


def _normalize_json_mapping(value: Mapping[str, Any] | None, field_name: str) -> dict[str, JSONValue]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, JSONValue] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized[normalized_key] = _normalize_json_value(item, f"{field_name}[{normalized_key!r}]")
    return normalized


def _json_ready(value: JSONValue) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def extend_timestamp(timestamp: str | None, ttl_seconds: int) -> str:
    base = datetime.fromisoformat((timestamp or utc_now()).replace("Z", "+00:00"))
    return (base + timedelta(seconds=ttl_seconds)).isoformat()


@dataclass(frozen=True, slots=True)
class UnifiedSourceRecord:
    source_id: str
    source_family: str
    snapshot_id: str
    volume: str
    root_paths: tuple[str, ...]
    kind: CorpusObjectKind
    bytes: int
    fingerprint: str
    duplicate_of: str | None = None
    authoritative_root: str | None = None
    import_mode: str = "manual"
    integration_status: SourceIntegrationStatus = "discovered"
    validation_status: SourceValidationStatus = "unknown"
    file_count: int = 0
    duplicate_bytes: int = 0
    lane: LaneName | None = None
    location_verified: bool = False
    consolidation_target: str | None = None
    consolidation_status: ConsolidationStatus = "not_required"
    scope_tier: ScopeTier = "authoritative"
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "source_family", _required_text(self.source_family, "source_family"))
        object.__setattr__(self, "snapshot_id", _required_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(self, "volume", _required_text(self.volume, "volume"))
        roots = _normalize_text_tuple(self.root_paths)
        if not roots:
            raise ValueError("root_paths must not be empty")
        object.__setattr__(self, "root_paths", roots)
        object.__setattr__(self, "kind", _normalize_literal(self.kind, "kind", _KIND_VALUES))
        object.__setattr__(self, "bytes", _normalize_int(self.bytes, "bytes"))
        object.__setattr__(self, "fingerprint", _required_text(self.fingerprint, "fingerprint"))
        object.__setattr__(self, "duplicate_of", _optional_text(self.duplicate_of))
        object.__setattr__(self, "authoritative_root", _optional_text(self.authoritative_root) or roots[0])
        object.__setattr__(self, "import_mode", _required_text(self.import_mode, "import_mode"))
        object.__setattr__(self, "integration_status", _normalize_literal(self.integration_status, "integration_status", _INTEGRATION_VALUES))
        object.__setattr__(self, "validation_status", _normalize_literal(self.validation_status, "validation_status", _VALIDATION_VALUES))
        object.__setattr__(self, "file_count", _normalize_int(self.file_count, "file_count"))
        object.__setattr__(self, "duplicate_bytes", _normalize_int(self.duplicate_bytes, "duplicate_bytes"))
        normalized_lane = _optional_text(self.lane)
        if normalized_lane is not None:
            normalized_lane = _normalize_literal(normalized_lane, "lane", _LANE_VALUES)
        object.__setattr__(self, "lane", normalized_lane)
        object.__setattr__(self, "location_verified", bool(self.location_verified))
        object.__setattr__(self, "consolidation_target", _optional_text(self.consolidation_target))
        object.__setattr__(
            self,
            "consolidation_status",
            _normalize_literal(
                self.consolidation_status,
                "consolidation_status",
                _CONSOLIDATION_VALUES,
            ),
        )
        object.__setattr__(
            self,
            "scope_tier",
            _normalize_literal(self.scope_tier, "scope_tier", _SCOPE_TIER_VALUES),
        )
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_family": self.source_family,
            "snapshot_id": self.snapshot_id,
            "volume": self.volume,
            "root_paths": list(self.root_paths),
            "kind": self.kind,
            "bytes": self.bytes,
            "fingerprint": self.fingerprint,
            "duplicate_of": self.duplicate_of,
            "authoritative_root": self.authoritative_root,
            "import_mode": self.import_mode,
            "integration_status": self.integration_status,
            "validation_status": self.validation_status,
            "file_count": self.file_count,
            "duplicate_bytes": self.duplicate_bytes,
            "lane": self.lane,
            "location_verified": self.location_verified,
            "consolidation_target": self.consolidation_target,
            "consolidation_status": self.consolidation_status,
            "scope_tier": self.scope_tier,
            "notes": list(self.notes),
            "metadata": _json_ready(dict(self.metadata)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UnifiedSourceRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_id=payload.get("source_id") or "",
            source_family=payload.get("source_family") or "",
            snapshot_id=payload.get("snapshot_id") or "current",
            volume=payload.get("volume") or "",
            root_paths=payload.get("root_paths") or (),
            kind=payload.get("kind") or "ignore",
            bytes=payload.get("bytes") or 0,
            fingerprint=payload.get("fingerprint") or "",
            duplicate_of=payload.get("duplicate_of"),
            authoritative_root=payload.get("authoritative_root"),
            import_mode=payload.get("import_mode") or "manual",
            integration_status=payload.get("integration_status") or "discovered",
            validation_status=payload.get("validation_status") or "unknown",
            file_count=payload.get("file_count") or 0,
            duplicate_bytes=payload.get("duplicate_bytes") or 0,
            lane=payload.get("lane"),
            location_verified=bool(payload.get("location_verified", False)),
            consolidation_target=payload.get("consolidation_target"),
            consolidation_status=payload.get("consolidation_status") or "not_required",
            scope_tier=payload.get("scope_tier") or "authoritative",
            notes=payload.get("notes") or (),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class WorkUnit:
    work_unit_id: str
    lane: LaneName
    source_family: str
    snapshot_id: str
    shard_key: str
    inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    status: WorkUnitStatus = "planned"
    lease_owner: str | None = None
    lease_expires_at: str | None = None
    attempt: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_unit_id", _required_text(self.work_unit_id, "work_unit_id"))
        object.__setattr__(self, "lane", _normalize_literal(self.lane, "lane", _LANE_VALUES))
        object.__setattr__(self, "source_family", _required_text(self.source_family, "source_family"))
        object.__setattr__(self, "snapshot_id", _required_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(self, "shard_key", _required_text(self.shard_key, "shard_key"))
        inputs = _normalize_text_tuple(self.inputs)
        if not inputs:
            raise ValueError("inputs must not be empty")
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "expected_outputs", _normalize_text_tuple(self.expected_outputs))
        object.__setattr__(self, "depends_on", _normalize_text_tuple(self.depends_on))
        object.__setattr__(self, "status", _normalize_literal(self.status, "status", _WORK_UNIT_VALUES))
        object.__setattr__(self, "lease_owner", _optional_text(self.lease_owner))
        object.__setattr__(self, "lease_expires_at", _normalize_timestamp(self.lease_expires_at))
        object.__setattr__(self, "attempt", _normalize_int(self.attempt, "attempt"))
        object.__setattr__(self, "metadata", _normalize_json_mapping(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_unit_id": self.work_unit_id,
            "lane": self.lane,
            "source_family": self.source_family,
            "snapshot_id": self.snapshot_id,
            "shard_key": self.shard_key,
            "inputs": list(self.inputs),
            "expected_outputs": list(self.expected_outputs),
            "depends_on": list(self.depends_on),
            "status": self.status,
            "lease_owner": self.lease_owner,
            "lease_expires_at": self.lease_expires_at,
            "attempt": self.attempt,
            "metadata": _json_ready(dict(self.metadata)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WorkUnit:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            work_unit_id=payload.get("work_unit_id") or "",
            lane=payload.get("lane") or "warehouse_validation_export",
            source_family=payload.get("source_family") or "",
            snapshot_id=payload.get("snapshot_id") or "current",
            shard_key=payload.get("shard_key") or "all",
            inputs=payload.get("inputs") or (),
            expected_outputs=payload.get("expected_outputs") or (),
            depends_on=payload.get("depends_on") or (),
            status=payload.get("status") or "planned",
            lease_owner=payload.get("lease_owner"),
            lease_expires_at=payload.get("lease_expires_at"),
            attempt=payload.get("attempt") or 0,
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class WorkerHeartbeat:
    worker_id: str
    lane: LaneName
    lease_ids: tuple[str, ...] = field(default_factory=tuple)
    status: WorkerStatus = "idle"
    cpu: str | None = None
    memory: str | None = None
    disk_io: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _required_text(self.worker_id, "worker_id"))
        object.__setattr__(self, "lane", _normalize_literal(self.lane, "lane", _LANE_VALUES))
        object.__setattr__(self, "lease_ids", _normalize_text_tuple(self.lease_ids))
        object.__setattr__(self, "status", _normalize_literal(self.status, "status", _WORKER_VALUES))
        object.__setattr__(self, "cpu", _optional_text(self.cpu))
        object.__setattr__(self, "memory", _optional_text(self.memory))
        object.__setattr__(self, "disk_io", _optional_text(self.disk_io))
        object.__setattr__(self, "updated_at", _normalize_timestamp(self.updated_at) or utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "lane": self.lane,
            "lease_ids": list(self.lease_ids),
            "status": self.status,
            "cpu": self.cpu,
            "memory": self.memory,
            "disk_io": self.disk_io,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WorkerHeartbeat:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            worker_id=payload.get("worker_id") or "",
            lane=payload.get("lane") or "warehouse_validation_export",
            lease_ids=payload.get("lease_ids") or (),
            status=payload.get("status") or "idle",
            cpu=payload.get("cpu"),
            memory=payload.get("memory"),
            disk_io=payload.get("disk_io"),
            updated_at=payload.get("updated_at"),
        )


@dataclass(frozen=True, slots=True)
class ValidationReceipt:
    work_unit_id: str
    input_fingerprints: Mapping[str, Any]
    source_counts: Mapping[str, Any]
    staged_counts: Mapping[str, Any]
    checks: Mapping[str, Any]
    decision: ValidationDecision
    claim_surface_checks: Mapping[str, Any] = field(default_factory=dict)
    best_evidence_basis: Mapping[str, Any] = field(default_factory=dict)
    location_verification: Mapping[str, Any] = field(default_factory=dict)
    validated_at: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_unit_id", _required_text(self.work_unit_id, "work_unit_id"))
        object.__setattr__(self, "input_fingerprints", _normalize_json_mapping(self.input_fingerprints, "input_fingerprints"))
        object.__setattr__(self, "source_counts", _normalize_json_mapping(self.source_counts, "source_counts"))
        object.__setattr__(self, "staged_counts", _normalize_json_mapping(self.staged_counts, "staged_counts"))
        object.__setattr__(self, "checks", _normalize_json_mapping(self.checks, "checks"))
        object.__setattr__(self, "decision", _normalize_literal(self.decision, "decision", _DECISION_VALUES))
        object.__setattr__(
            self,
            "claim_surface_checks",
            _normalize_json_mapping(self.claim_surface_checks, "claim_surface_checks"),
        )
        object.__setattr__(
            self,
            "best_evidence_basis",
            _normalize_json_mapping(self.best_evidence_basis, "best_evidence_basis"),
        )
        object.__setattr__(
            self,
            "location_verification",
            _normalize_json_mapping(self.location_verification, "location_verification"),
        )
        object.__setattr__(self, "validated_at", _normalize_timestamp(self.validated_at) or utc_now())
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_unit_id": self.work_unit_id,
            "input_fingerprints": _json_ready(dict(self.input_fingerprints)),
            "source_counts": _json_ready(dict(self.source_counts)),
            "staged_counts": _json_ready(dict(self.staged_counts)),
            "checks": _json_ready(dict(self.checks)),
            "decision": self.decision,
            "claim_surface_checks": _json_ready(dict(self.claim_surface_checks)),
            "best_evidence_basis": _json_ready(dict(self.best_evidence_basis)),
            "location_verification": _json_ready(dict(self.location_verification)),
            "validated_at": self.validated_at,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ValidationReceipt:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            work_unit_id=payload.get("work_unit_id") or "",
            input_fingerprints=payload.get("input_fingerprints") or {},
            source_counts=payload.get("source_counts") or {},
            staged_counts=payload.get("staged_counts") or {},
            checks=payload.get("checks") or {},
            decision=payload.get("decision") or "failed",
            claim_surface_checks=payload.get("claim_surface_checks") or {},
            best_evidence_basis=payload.get("best_evidence_basis") or {},
            location_verification=payload.get("location_verification") or {},
            validated_at=payload.get("validated_at"),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class PromotionReceipt:
    promotion_id: str
    work_units: tuple[str, ...]
    families_updated: tuple[str, ...]
    warehouse_id: str
    manifest_version: str
    promoted_at: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "promotion_id", _required_text(self.promotion_id, "promotion_id"))
        work_units = _normalize_text_tuple(self.work_units)
        families_updated = _normalize_text_tuple(self.families_updated)
        if not work_units:
            raise ValueError("work_units must not be empty")
        if not families_updated:
            raise ValueError("families_updated must not be empty")
        object.__setattr__(self, "work_units", work_units)
        object.__setattr__(self, "families_updated", families_updated)
        object.__setattr__(self, "warehouse_id", _required_text(self.warehouse_id, "warehouse_id"))
        object.__setattr__(self, "manifest_version", _required_text(self.manifest_version, "manifest_version"))
        object.__setattr__(self, "promoted_at", _normalize_timestamp(self.promoted_at) or utc_now())
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "work_units": list(self.work_units),
            "families_updated": list(self.families_updated),
            "warehouse_id": self.warehouse_id,
            "manifest_version": self.manifest_version,
            "promoted_at": self.promoted_at,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PromotionReceipt:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            promotion_id=payload.get("promotion_id") or "",
            work_units=payload.get("work_units") or (),
            families_updated=payload.get("families_updated") or (),
            warehouse_id=payload.get("warehouse_id") or "",
            manifest_version=payload.get("manifest_version") or "",
            promoted_at=payload.get("promoted_at"),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class CorpusCompletionLedger:
    strict_validated_bytes: int
    partial_bytes: int
    duplicate_bytes: int
    blocked_bytes: int
    untouched_bytes: int
    source_counts_by_state: Mapping[str, Any]
    total_authoritative_bytes: int = 0
    duplicate_bytes_reconciled: int = 0
    widest_scope_bytes_captured_not_promoted: int = 0
    generated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strict_validated_bytes", _normalize_int(self.strict_validated_bytes, "strict_validated_bytes"))
        object.__setattr__(self, "partial_bytes", _normalize_int(self.partial_bytes, "partial_bytes"))
        object.__setattr__(self, "duplicate_bytes", _normalize_int(self.duplicate_bytes, "duplicate_bytes"))
        object.__setattr__(self, "blocked_bytes", _normalize_int(self.blocked_bytes, "blocked_bytes"))
        object.__setattr__(self, "untouched_bytes", _normalize_int(self.untouched_bytes, "untouched_bytes"))
        object.__setattr__(self, "source_counts_by_state", _normalize_json_mapping(self.source_counts_by_state, "source_counts_by_state"))
        object.__setattr__(self, "total_authoritative_bytes", _normalize_int(self.total_authoritative_bytes, "total_authoritative_bytes"))
        object.__setattr__(
            self,
            "duplicate_bytes_reconciled",
            _normalize_int(self.duplicate_bytes_reconciled, "duplicate_bytes_reconciled"),
        )
        object.__setattr__(
            self,
            "widest_scope_bytes_captured_not_promoted",
            _normalize_int(
                self.widest_scope_bytes_captured_not_promoted,
                "widest_scope_bytes_captured_not_promoted",
            ),
        )
        object.__setattr__(self, "generated_at", _normalize_timestamp(self.generated_at) or utc_now())

    def to_dict(self) -> dict[str, Any]:
        total = self.total_authoritative_bytes or (
            self.strict_validated_bytes + self.partial_bytes + self.blocked_bytes + self.untouched_bytes
        )
        denominator = total or 1
        return {
            "strict_validated_bytes": self.strict_validated_bytes,
            "partial_bytes": self.partial_bytes,
            "duplicate_bytes": self.duplicate_bytes,
            "blocked_bytes": self.blocked_bytes,
            "untouched_bytes": self.untouched_bytes,
            "total_authoritative_bytes": total,
            "authoritative_deduplicated_bytes_discovered": total,
            "fully_validated_promoted_bytes": self.strict_validated_bytes,
            "duplicate_bytes_reconciled": self.duplicate_bytes_reconciled,
            "widest_scope_bytes_captured_not_promoted": self.widest_scope_bytes_captured_not_promoted,
            "strict_validated_percent": round((self.strict_validated_bytes / denominator) * 100, 4),
            "partial_percent": round((self.partial_bytes / denominator) * 100, 4),
            "duplicate_percent_of_total": round((self.duplicate_bytes / denominator) * 100, 4),
            "blocked_percent": round((self.blocked_bytes / denominator) * 100, 4),
            "untouched_percent": round((self.untouched_bytes / denominator) * 100, 4),
            "source_counts_by_state": _json_ready(dict(self.source_counts_by_state)),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CorpusCompletionLedger:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            strict_validated_bytes=payload.get("strict_validated_bytes") or 0,
            partial_bytes=payload.get("partial_bytes") or 0,
            duplicate_bytes=payload.get("duplicate_bytes") or 0,
            blocked_bytes=payload.get("blocked_bytes") or 0,
            untouched_bytes=payload.get("untouched_bytes") or 0,
            source_counts_by_state=payload.get("source_counts_by_state") or {},
            total_authoritative_bytes=payload.get("total_authoritative_bytes") or 0,
            duplicate_bytes_reconciled=payload.get("duplicate_bytes_reconciled") or payload.get("duplicate_bytes") or 0,
            widest_scope_bytes_captured_not_promoted=payload.get("widest_scope_bytes_captured_not_promoted") or payload.get("partial_bytes") or 0,
            generated_at=payload.get("generated_at"),
        )


@dataclass(frozen=True, slots=True)
class LaneClaim:
    claim_id: str
    work_unit_id: str
    lane: LaneName
    source_family: str
    snapshot_id: str
    shard_key: str
    lease_owner: str
    lease_expires_at: str
    claimed_at: str | None = None
    inputs: tuple[str, ...] = field(default_factory=tuple)
    expected_outputs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _required_text(self.claim_id, "claim_id"))
        object.__setattr__(self, "work_unit_id", _required_text(self.work_unit_id, "work_unit_id"))
        object.__setattr__(self, "lane", _normalize_literal(self.lane, "lane", _LANE_VALUES))
        object.__setattr__(self, "source_family", _required_text(self.source_family, "source_family"))
        object.__setattr__(self, "snapshot_id", _required_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(self, "shard_key", _required_text(self.shard_key, "shard_key"))
        object.__setattr__(self, "lease_owner", _required_text(self.lease_owner, "lease_owner"))
        normalized_expiry = _normalize_timestamp(self.lease_expires_at)
        if normalized_expiry is None:
            raise ValueError("lease_expires_at must be an ISO-8601 timestamp")
        object.__setattr__(self, "lease_expires_at", normalized_expiry)
        object.__setattr__(self, "claimed_at", _normalize_timestamp(self.claimed_at) or utc_now())
        object.__setattr__(self, "inputs", _normalize_text_tuple(self.inputs))
        object.__setattr__(self, "expected_outputs", _normalize_text_tuple(self.expected_outputs))

    def expired(self, *, now: str | None = None) -> bool:
        current = datetime.fromisoformat((now or utc_now()).replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(self.lease_expires_at.replace("Z", "+00:00"))
        return expiry <= current

    def overlaps(self, other: LaneClaim) -> bool:
        return (
            self.lane == other.lane
            and self.source_family == other.source_family
            and self.snapshot_id == other.snapshot_id
            and self.shard_key == other.shard_key
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "work_unit_id": self.work_unit_id,
            "lane": self.lane,
            "source_family": self.source_family,
            "snapshot_id": self.snapshot_id,
            "shard_key": self.shard_key,
            "lease_owner": self.lease_owner,
            "lease_expires_at": self.lease_expires_at,
            "claimed_at": self.claimed_at,
            "inputs": list(self.inputs),
            "expected_outputs": list(self.expected_outputs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LaneClaim:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            claim_id=payload.get("claim_id") or "",
            work_unit_id=payload.get("work_unit_id") or "",
            lane=payload.get("lane") or "warehouse_validation_export",
            source_family=payload.get("source_family") or "",
            snapshot_id=payload.get("snapshot_id") or "current",
            shard_key=payload.get("shard_key") or "all",
            lease_owner=payload.get("lease_owner") or "",
            lease_expires_at=payload.get("lease_expires_at") or utc_now(),
            claimed_at=payload.get("claimed_at"),
            inputs=payload.get("inputs") or (),
            expected_outputs=payload.get("expected_outputs") or (),
        )


@dataclass(frozen=True, slots=True)
class CorpusProgramState:
    operating_mode: str
    milestone: str
    control_model: str
    cycle_index: int = 0
    active_workers: tuple[WorkerHeartbeat, ...] = field(default_factory=tuple)
    active_claim_count: int = 0
    resource_tokens: Mapping[str, Any] = field(default_factory=dict)
    stop_requested: bool = False
    resume_requested: bool = False
    last_cycle_summary: Mapping[str, Any] = field(default_factory=dict)
    updated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "operating_mode", _required_text(self.operating_mode, "operating_mode"))
        object.__setattr__(self, "milestone", _required_text(self.milestone, "milestone"))
        object.__setattr__(self, "control_model", _required_text(self.control_model, "control_model"))
        object.__setattr__(self, "cycle_index", _normalize_int(self.cycle_index, "cycle_index"))
        workers: list[WorkerHeartbeat] = []
        for worker in self.active_workers:
            if not isinstance(worker, WorkerHeartbeat):
                worker = WorkerHeartbeat.from_dict(worker)  # type: ignore[arg-type]
            workers.append(worker)
        object.__setattr__(self, "active_workers", tuple(workers))
        object.__setattr__(self, "active_claim_count", _normalize_int(self.active_claim_count, "active_claim_count"))
        object.__setattr__(self, "resource_tokens", _normalize_json_mapping(self.resource_tokens, "resource_tokens"))
        object.__setattr__(self, "last_cycle_summary", _normalize_json_mapping(self.last_cycle_summary, "last_cycle_summary"))
        object.__setattr__(self, "updated_at", _normalize_timestamp(self.updated_at) or utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating_mode": self.operating_mode,
            "milestone": self.milestone,
            "control_model": self.control_model,
            "cycle_index": self.cycle_index,
            "active_workers": [worker.to_dict() for worker in self.active_workers],
            "active_claim_count": self.active_claim_count,
            "resource_tokens": _json_ready(dict(self.resource_tokens)),
            "stop_requested": self.stop_requested,
            "resume_requested": self.resume_requested,
            "last_cycle_summary": _json_ready(dict(self.last_cycle_summary)),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CorpusProgramState:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            operating_mode=payload.get("operating_mode") or payload.get("mode") or "",
            milestone=payload.get("milestone") or "",
            control_model=payload.get("control_model") or "",
            cycle_index=payload.get("cycle_index") or 0,
            active_workers=tuple(
                WorkerHeartbeat.from_dict(item) if not isinstance(item, WorkerHeartbeat) else item
                for item in _iter_values(payload.get("active_workers") or ())
            ),
            active_claim_count=payload.get("active_claim_count") or 0,
            resource_tokens=payload.get("resource_tokens") or {},
            stop_requested=bool(payload.get("stop_requested", False)),
            resume_requested=bool(payload.get("resume_requested", False)),
            last_cycle_summary=payload.get("last_cycle_summary") or {},
            updated_at=payload.get("updated_at"),
        )


def compute_completion_ledger(
    records: Iterable[UnifiedSourceRecord],
    *,
    work_units: Iterable[WorkUnit] | None = None,
) -> CorpusCompletionLedger:
    strict_validated = 0.0
    partial = 0.0
    duplicate = 0
    blocked = 0.0
    total_authoritative = 0
    state_counts: dict[str, int] = {}
    work_units_by_source: dict[tuple[str, str], list[WorkUnit]] = {}
    if work_units is not None:
        for unit in work_units:
            work_units_by_source.setdefault((unit.source_family, unit.snapshot_id), []).append(unit)
    for record in records:
        duplicate += record.duplicate_bytes
        if record.integration_status == "duplicate":
            state_counts["duplicate"] = state_counts.get("duplicate", 0) + 1
            continue
        if record.kind in {"ignore", "staging_output", "warehouse_output"}:
            state_counts[record.integration_status] = state_counts.get(record.integration_status, 0) + 1
            continue
        total_authoritative += record.bytes
        source_units = work_units_by_source.get((record.source_family, record.snapshot_id), [])
        if source_units:
            promoted_count = sum(1 for unit in source_units if unit.status == "promoted")
            blocked_count = sum(1 for unit in source_units if unit.status in {"blocked", "failed"})
            total_units = len(source_units)
            strict_share = (record.bytes * promoted_count) / total_units
            blocked_share = (record.bytes * blocked_count) / total_units
            partial_share = max(record.bytes - strict_share - blocked_share, 0.0)
            strict_validated += strict_share
            blocked += blocked_share
            partial += partial_share
            if promoted_count == total_units:
                effective_state = "promoted"
            elif blocked_count == total_units:
                effective_state = "blocked"
            elif promoted_count > 0 or blocked_count > 0:
                effective_state = "partial"
            else:
                effective_state = "planned" if any(unit.status == "planned" for unit in source_units) else record.integration_status
            state_counts[effective_state] = state_counts.get(effective_state, 0) + 1
            continue
        state_counts[record.integration_status] = state_counts.get(record.integration_status, 0) + 1
        if record.integration_status == "promoted" and record.validation_status == "passed":
            strict_validated += record.bytes
        elif record.integration_status in {"planned", "discovered", "partial"}:
            partial += record.bytes
        elif record.integration_status in {"blocked", "corrupt"}:
            blocked += record.bytes
    rounded_strict = int(round(strict_validated))
    rounded_partial = int(round(partial))
    rounded_blocked = int(round(blocked))
    untouched = max(total_authoritative - rounded_strict - rounded_partial - rounded_blocked, 0)
    return CorpusCompletionLedger(
        strict_validated_bytes=rounded_strict,
        partial_bytes=rounded_partial,
        duplicate_bytes=duplicate,
        blocked_bytes=rounded_blocked,
        untouched_bytes=untouched,
        source_counts_by_state=state_counts,
        total_authoritative_bytes=total_authoritative,
        duplicate_bytes_reconciled=duplicate,
        widest_scope_bytes_captured_not_promoted=rounded_partial,
    )


def recover_active_claims(claims: Iterable[LaneClaim], *, now: str | None = None) -> tuple[LaneClaim, ...]:
    current = now or utc_now()
    return tuple(claim for claim in claims if not claim.expired(now=current))


def claim_work_units(
    work_units: Iterable[WorkUnit],
    active_claims: Iterable[LaneClaim],
    *,
    worker_id: str,
    lane: str,
    limit: int = 1,
    ttl_seconds: int = 3600,
    now: str | None = None,
) -> tuple[tuple[WorkUnit, ...], tuple[LaneClaim, ...]]:
    normalized_lane = _normalize_literal(lane, "lane", _LANE_VALUES)
    current = now or utc_now()
    live_claims = list(recover_active_claims(active_claims, now=current))
    occupied = {(claim.lane, claim.source_family, claim.snapshot_id, claim.shard_key) for claim in live_claims}
    selected_units: list[WorkUnit] = []
    selected_claims: list[LaneClaim] = []
    for unit in work_units:
        if unit.lane != normalized_lane or unit.status not in {"planned", "claimed"}:
            continue
        claim_key = (unit.lane, unit.source_family, unit.snapshot_id, unit.shard_key)
        if claim_key in occupied:
            continue
        lease_expires_at = extend_timestamp(current, ttl_seconds)
        selected_units.append(
            WorkUnit(
                work_unit_id=unit.work_unit_id,
                lane=unit.lane,
                source_family=unit.source_family,
                snapshot_id=unit.snapshot_id,
                shard_key=unit.shard_key,
                inputs=unit.inputs,
                expected_outputs=unit.expected_outputs,
                depends_on=unit.depends_on,
                status="claimed",
                lease_owner=worker_id,
                lease_expires_at=lease_expires_at,
                attempt=unit.attempt + 1,
                metadata=unit.metadata,
            )
        )
        selected_claims.append(
            LaneClaim(
                claim_id=f"claim:{unit.work_unit_id}",
                work_unit_id=unit.work_unit_id,
                lane=unit.lane,
                source_family=unit.source_family,
                snapshot_id=unit.snapshot_id,
                shard_key=unit.shard_key,
                lease_owner=worker_id,
                lease_expires_at=lease_expires_at,
                claimed_at=current,
                inputs=unit.inputs,
                expected_outputs=unit.expected_outputs,
            )
        )
        occupied.add(claim_key)
        if len(selected_units) >= limit:
            break
    return tuple(selected_units), tuple((*live_claims, *selected_claims))


__all__ = [
    "CorpusCompletionLedger",
    "CorpusProgramState",
    "LaneClaim",
    "LaneName",
    "PromotionReceipt",
    "UnifiedSourceRecord",
    "ValidationReceipt",
    "WorkUnit",
    "WorkerHeartbeat",
    "claim_work_units",
    "compute_completion_ledger",
    "extend_timestamp",
    "recover_active_claims",
    "utc_now",
]
