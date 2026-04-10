from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CheckpointScope(StrEnum):
    RUN = "run"
    NODE = "node"


class CheckpointStoreError(Exception):
    """Base error for checkpoint store operations."""


class CheckpointNotFoundError(CheckpointStoreError, KeyError):
    """Raised when a requested checkpoint version does not exist."""


class CheckpointConflictError(CheckpointStoreError, ValueError):
    """Raised when a checkpoint write would overwrite an existing version."""


def _normalize_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _copy_mapping(value: Mapping[str, Any] | None, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return deepcopy(dict(value))


def _checkpoint_key(run_id: str, node_id: str | None) -> str:
    if node_id is None:
        return f"run:{run_id}"
    return f"run:{run_id}:node:{node_id}"


def _clone_record(record: CheckpointRecord) -> CheckpointRecord:
    return CheckpointRecord(
        run_id=record.run_id,
        node_id=record.node_id,
        version=record.version,
        checkpoint_state=record.checkpoint_state,
        provenance=record.provenance,
        metadata=record.metadata,
        schema_version=record.schema_version,
    )


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    """Immutable checkpoint snapshot for a run or node.

    The store keeps the record payload, provenance, and metadata intact so
    resume logic can compare the checkpoint against retry and recovery policy
    decisions without relying on implicit mutation.
    """

    run_id: str
    checkpoint_state: Mapping[str, Any] = field(default_factory=dict)
    version: int = 1
    node_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    checkpoint_key: str = field(init=False)
    scope: CheckpointScope = field(init=False)

    def __post_init__(self) -> None:
        run_id = _normalize_text(self.run_id, "run_id")
        node_id = None
        if self.node_id is not None:
            node_id = _normalize_text(self.node_id, "node_id")
        if self.version < 1:
            raise ValueError("version must be >= 1")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(
            self,
            "checkpoint_state",
            _copy_mapping(self.checkpoint_state, "checkpoint_state"),
        )
        object.__setattr__(self, "provenance", _copy_mapping(self.provenance, "provenance"))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata, "metadata"))
        object.__setattr__(self, "checkpoint_key", _checkpoint_key(run_id, node_id))
        scope = CheckpointScope.NODE if node_id is not None else CheckpointScope.RUN
        object.__setattr__(self, "scope", scope)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "node_id": self.node_id,
            "version": self.version,
            "checkpoint_state": deepcopy(dict(self.checkpoint_state)),
            "provenance": deepcopy(dict(self.provenance)),
            "metadata": deepcopy(dict(self.metadata)),
            "schema_version": self.schema_version,
            "checkpoint_key": self.checkpoint_key,
            "scope": self.scope.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CheckpointRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        record = cls(
            run_id=str(payload.get("run_id") or ""),
            node_id=payload.get("node_id"),
            version=int(payload.get("version") or 0),
            checkpoint_state=payload.get("checkpoint_state"),
            provenance=payload.get("provenance"),
            metadata=payload.get("metadata"),
            schema_version=int(payload.get("schema_version") or 0),
        )
        checkpoint_key = payload.get("checkpoint_key")
        if checkpoint_key is not None and (
            _normalize_text(str(checkpoint_key), "checkpoint_key") != record.checkpoint_key
        ):
            raise ValueError("checkpoint_key does not match the record identity")
        scope = payload.get("scope")
        if scope is not None and _normalize_text(str(scope), "scope") != record.scope.value:
            raise ValueError("scope does not match the record identity")
        return record


class CheckpointStore:
    """Deterministic in-memory checkpoint store with explicit versioning."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str | None], dict[int, CheckpointRecord]] = {}

    def save(self, checkpoint: CheckpointRecord, *, replace: bool = False) -> CheckpointRecord:
        """Persist a checkpoint record under its explicit version.

        The default behavior rejects collisions so callers cannot silently
        overwrite a published checkpoint version.
        """

        key = self._identity_key(checkpoint.run_id, checkpoint.node_id)
        versions = self._records.setdefault(key, {})
        if checkpoint.version in versions and not replace:
            raise CheckpointConflictError(
                "checkpoint "
                f"{checkpoint.checkpoint_key} version {checkpoint.version} already exists"
            )

        stored = _clone_record(checkpoint)
        versions[stored.version] = stored
        return _clone_record(stored)

    def write_run_checkpoint(
        self,
        run_id: str,
        checkpoint_state: Mapping[str, Any],
        *,
        provenance: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        version: int | None = None,
        schema_version: int = 1,
    ) -> CheckpointRecord:
        return self._write_checkpoint(
            run_id=run_id,
            checkpoint_state=checkpoint_state,
            provenance=provenance,
            metadata=metadata,
            version=version,
            schema_version=schema_version,
        )

    def write_node_checkpoint(
        self,
        run_id: str,
        node_id: str,
        checkpoint_state: Mapping[str, Any],
        *,
        provenance: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        version: int | None = None,
        schema_version: int = 1,
    ) -> CheckpointRecord:
        return self._write_checkpoint(
            run_id=run_id,
            node_id=node_id,
            checkpoint_state=checkpoint_state,
            provenance=provenance,
            metadata=metadata,
            version=version,
            schema_version=schema_version,
        )

    def load(
        self,
        run_id: str,
        node_id: str | None = None,
        version: int | None = None,
    ) -> CheckpointRecord:
        key = self._identity_key(run_id, node_id)
        versions = self._records.get(key)
        if not versions:
            raise CheckpointNotFoundError(self._missing_message(run_id, node_id, version))

        selected_version = self._select_version(versions, run_id, node_id, version)
        return _clone_record(versions[selected_version])

    def load_run_checkpoint(self, run_id: str, version: int | None = None) -> CheckpointRecord:
        return self.load(run_id, version=version)

    def load_node_checkpoint(
        self,
        run_id: str,
        node_id: str,
        version: int | None = None,
    ) -> CheckpointRecord:
        return self.load(run_id, node_id=node_id, version=version)

    def latest_version(self, run_id: str, node_id: str | None = None) -> int:
        versions = self._versions_for(run_id, node_id)
        if not versions:
            raise CheckpointNotFoundError(self._missing_message(run_id, node_id, None))
        return max(versions)

    def list_versions(self, run_id: str, node_id: str | None = None) -> tuple[int, ...]:
        versions = self._versions_for(run_id, node_id)
        return tuple(sorted(versions))

    def has_checkpoint(self, run_id: str, node_id: str | None = None) -> bool:
        return bool(self._versions_for(run_id, node_id))

    def _write_checkpoint(
        self,
        *,
        run_id: str,
        checkpoint_state: Mapping[str, Any],
        node_id: str | None = None,
        provenance: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        version: int | None = None,
        schema_version: int = 1,
    ) -> CheckpointRecord:
        key = self._identity_key(run_id, node_id)
        versions = self._records.setdefault(key, {})
        next_version = max(versions) + 1 if versions else 1
        selected_version = next_version if version is None else version
        record = CheckpointRecord(
            run_id=run_id,
            node_id=node_id,
            version=selected_version,
            checkpoint_state=checkpoint_state,
            provenance=provenance,
            metadata=metadata,
            schema_version=schema_version,
        )
        return self.save(record)

    def _versions_for(self, run_id: str, node_id: str | None) -> dict[int, CheckpointRecord]:
        key = self._identity_key(run_id, node_id)
        return self._records.get(key, {})

    @staticmethod
    def _identity_key(run_id: str, node_id: str | None) -> tuple[str, str | None]:
        normalized_run_id = _normalize_text(run_id, "run_id")
        normalized_node_id = None if node_id is None else _normalize_text(node_id, "node_id")
        return normalized_run_id, normalized_node_id

    @staticmethod
    def _select_version(
        versions: Mapping[int, CheckpointRecord],
        run_id: str,
        node_id: str | None,
        version: int | None,
    ) -> int:
        if version is None:
            return max(versions)
        if version not in versions:
            raise CheckpointNotFoundError(
                CheckpointStore._missing_message(run_id, node_id, version)
            )
        return version

    @staticmethod
    def _missing_message(run_id: str, node_id: str | None, version: int | None) -> str:
        normalized_run_id = _normalize_text(run_id, "run_id")
        normalized_node_id = None if node_id is None else _normalize_text(node_id, "node_id")
        checkpoint_key = _checkpoint_key(normalized_run_id, normalized_node_id)
        if version is None:
            return f"missing checkpoint: {checkpoint_key}"
        return f"missing checkpoint: {checkpoint_key} version {version}"
