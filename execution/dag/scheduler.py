from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from execution.dag.node import DAGNode, DAGNodeState, DAGNodeStatus


def _default_state(node_id: str) -> DAGNodeState:
    return DAGNodeState(node_id=node_id)


@dataclass(frozen=True)
class DAGScheduler:
    """Stable DAG scheduler built on immutable node and state snapshots."""

    nodes: Sequence[DAGNode]
    _nodes_by_id: Mapping[str, DAGNode] = field(init=False, repr=False)
    _ordered_nodes: tuple[DAGNode, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        normalized_nodes = tuple(self.nodes)
        nodes_by_id: dict[str, DAGNode] = {}
        for node in normalized_nodes:
            if node.node_id in nodes_by_id:
                raise ValueError(f"duplicate node_id: {node.node_id}")
            nodes_by_id[node.node_id] = node

        for node in normalized_nodes:
            unknown_dependencies = [
                dependency
                for dependency in node.dependencies
                if dependency not in nodes_by_id
            ]
            if unknown_dependencies:
                missing = ", ".join(sorted(unknown_dependencies))
                raise ValueError(f"{node.node_id} has unknown dependencies: {missing}")

        object.__setattr__(self, "_nodes_by_id", nodes_by_id)
        object.__setattr__(self, "_ordered_nodes", self._topological_sort(normalized_nodes))

    @property
    def nodes_by_id(self) -> Mapping[str, DAGNode]:
        return self._nodes_by_id

    @property
    def ordered_nodes(self) -> tuple[DAGNode, ...]:
        return self._ordered_nodes

    def ready_nodes(self, states: Mapping[str, DAGNodeState] | None = None) -> tuple[DAGNode, ...]:
        state_map = states or {}
        completed = {
            node_id
            for node_id, state in state_map.items()
            if state.status == DAGNodeStatus.SUCCEEDED
        }
        ready: list[DAGNode] = []
        for node in self._ordered_nodes:
            state = state_map.get(node.node_id, _default_state(node.node_id))
            if state.status in {
                DAGNodeStatus.RUNNING,
                DAGNodeStatus.SUCCEEDED,
                DAGNodeStatus.BLOCKED,
            }:
                continue
            if state.status == DAGNodeStatus.FAILED and not state.can_retry(node):
                continue
            if self._has_terminal_dependency_failure(node, state_map):
                continue
            if node.is_ready(completed):
                ready.append(node)
        return tuple(ready)

    def blocked_nodes(self, states: Mapping[str, DAGNodeState]) -> tuple[DAGNode, ...]:
        blocked: list[DAGNode] = []
        for node in self._ordered_nodes:
            state = states.get(node.node_id, _default_state(node.node_id))
            if state.status in {
                DAGNodeStatus.SUCCEEDED,
                DAGNodeStatus.RUNNING,
                DAGNodeStatus.BLOCKED,
            }:
                continue
            if self._has_terminal_dependency_failure(node, states):
                blocked.append(node)
        return tuple(blocked)

    def _has_terminal_dependency_failure(
        self,
        node: DAGNode,
        states: Mapping[str, DAGNodeState],
    ) -> bool:
        for dependency in node.dependencies:
            dependency_node = self._nodes_by_id[dependency]
            dependency_state = states.get(dependency, _default_state(dependency))
            if dependency_state.status == DAGNodeStatus.BLOCKED:
                return True
            if (
                dependency_state.status == DAGNodeStatus.FAILED
                and not dependency_state.can_retry(dependency_node)
            ):
                return True
        return False

    def _topological_sort(self, nodes: Sequence[DAGNode]) -> tuple[DAGNode, ...]:
        indegree = {node.node_id: len(node.dependencies) for node in nodes}
        dependents: dict[str, list[str]] = {node.node_id: [] for node in nodes}
        insertion_order = {node.node_id: index for index, node in enumerate(nodes)}

        for node in nodes:
            for dependency in node.dependencies:
                dependents[dependency].append(node.node_id)

        queue = deque(
            node_id
            for node_id, degree in indegree.items()
            if degree == 0
        )
        ordered: list[DAGNode] = []

        while queue:
            node_id = queue.popleft()
            ordered.append(self._nodes_by_id[node_id])
            for dependent in sorted(dependents[node_id], key=insertion_order.__getitem__):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)

        if len(ordered) != len(nodes):
            raise ValueError("dependency cycle detected")
        return tuple(ordered)
