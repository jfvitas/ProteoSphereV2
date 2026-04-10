from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DAGNodeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


def _normalize_unique_strings(values: Collection[str], field_name: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = raw_value.strip()
        if not value:
            raise ValueError(f"{field_name} entries must be non-empty strings")
        if value in seen:
            raise ValueError(f"{field_name} entries must be unique")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


@dataclass(frozen=True)
class DAGNode:
    """Immutable description of a single execution unit in the DAG."""

    node_id: str
    operation: str
    dependencies: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    params: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    retry_limit: int = 0
    checkpoint_key: str | None = None

    def __post_init__(self) -> None:
        node_id = self.node_id.strip()
        operation = self.operation.strip()
        if not node_id:
            raise ValueError("node_id must be a non-empty string")
        if not operation:
            raise ValueError("operation must be a non-empty string")
        if self.retry_limit < 0:
            raise ValueError("retry_limit must be >= 0")

        dependencies = _normalize_unique_strings(self.dependencies, "dependencies")
        if node_id in dependencies:
            raise ValueError("node cannot depend on itself")

        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "inputs", _normalize_unique_strings(self.inputs, "inputs"))
        object.__setattr__(self, "outputs", _normalize_unique_strings(self.outputs, "outputs"))
        object.__setattr__(self, "params", dict(self.params))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "checkpoint_key", self.checkpoint_key or node_id)

    def is_ready(self, completed_nodes: Collection[str]) -> bool:
        return set(self.dependencies).issubset(set(completed_nodes))

    def to_record(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "operation": self.operation,
            "dependencies": list(self.dependencies),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "params": dict(self.params),
            "metadata": dict(self.metadata),
            "retry_limit": self.retry_limit,
            "checkpoint_key": self.checkpoint_key,
        }


@dataclass(frozen=True)
class DAGNodeState:
    """Mutable execution data is modeled as immutable snapshots for checkpointing."""

    node_id: str
    status: DAGNodeStatus = DAGNodeStatus.PENDING
    attempt: int = 0
    last_error: str | None = None

    def __post_init__(self) -> None:
        node_id = self.node_id.strip()
        if not node_id:
            raise ValueError("node_id must be a non-empty string")
        if self.attempt < 0:
            raise ValueError("attempt must be >= 0")
        object.__setattr__(self, "node_id", node_id)

    def can_retry(self, node: DAGNode) -> bool:
        return self.status == DAGNodeStatus.FAILED and self.attempt < node.retry_limit
