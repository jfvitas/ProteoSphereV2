from __future__ import annotations

import pytest

from execution.dag.node import DAGNode, DAGNodeState, DAGNodeStatus
from execution.dag.scheduler import DAGScheduler


def test_scheduler_orders_nodes_topologically():
    fetch = DAGNode(node_id="fetch", operation="fetch")
    normalize = DAGNode(
        node_id="normalize",
        operation="normalize",
        dependencies=("fetch",),
    )
    package = DAGNode(
        node_id="package",
        operation="package",
        dependencies=("normalize",),
    )

    scheduler = DAGScheduler((package, normalize, fetch))

    assert [node.node_id for node in scheduler.ordered_nodes] == [
        "fetch",
        "normalize",
        "package",
    ]


def test_scheduler_rejects_unknown_dependencies():
    with pytest.raises(ValueError, match="unknown dependencies"):
        DAGScheduler(
            (
                DAGNode(node_id="package", operation="package", dependencies=("missing",)),
            )
        )


def test_scheduler_rejects_cycles():
    with pytest.raises(ValueError, match="dependency cycle"):
        DAGScheduler(
            (
                DAGNode(node_id="a", operation="a", dependencies=("b",)),
                DAGNode(node_id="b", operation="b", dependencies=("a",)),
            )
        )


def test_scheduler_reports_ready_nodes_from_completed_dependencies():
    fetch = DAGNode(node_id="fetch", operation="fetch")
    normalize = DAGNode(
        node_id="normalize",
        operation="normalize",
        dependencies=("fetch",),
    )
    package = DAGNode(
        node_id="package",
        operation="package",
        dependencies=("normalize",),
    )
    scheduler = DAGScheduler((fetch, normalize, package))

    assert [node.node_id for node in scheduler.ready_nodes()] == ["fetch"]

    ready_after_fetch = scheduler.ready_nodes(
        {
            "fetch": DAGNodeState(node_id="fetch", status=DAGNodeStatus.SUCCEEDED),
        }
    )
    assert [node.node_id for node in ready_after_fetch] == ["normalize"]


def test_scheduler_skips_failed_nodes_without_retry_budget():
    fetch = DAGNode(node_id="fetch", operation="fetch")
    scheduler = DAGScheduler((fetch,))

    ready = scheduler.ready_nodes(
        {
            "fetch": DAGNodeState(
                node_id="fetch",
                status=DAGNodeStatus.FAILED,
                attempt=0,
            )
        }
    )
    assert ready == ()


def test_scheduler_marks_nodes_blocked_when_dependency_failed_terminally():
    fetch = DAGNode(node_id="fetch", operation="fetch", retry_limit=1)
    normalize = DAGNode(
        node_id="normalize",
        operation="normalize",
        dependencies=("fetch",),
    )
    scheduler = DAGScheduler((fetch, normalize))

    blocked = scheduler.blocked_nodes(
        {
            "fetch": DAGNodeState(
                node_id="fetch",
                status=DAGNodeStatus.FAILED,
                attempt=1,
            )
        }
    )
    assert [node.node_id for node in blocked] == ["normalize"]
