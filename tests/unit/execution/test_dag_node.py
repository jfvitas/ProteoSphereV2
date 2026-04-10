from __future__ import annotations

import pytest

from execution.dag.node import DAGNode, DAGNodeState, DAGNodeStatus


def test_dag_node_normalizes_fields_and_defaults_checkpoint_key():
    node = DAGNode(
        node_id=" ingest-structures ",
        operation=" normalize ",
        dependencies=("fetch-sequences",),
        inputs=(" raw/structures.json ",),
        outputs=("canonical/structures.parquet",),
        params={"batch_size": 32},
        metadata={"phase": 2},
        retry_limit=2,
    )

    assert node.node_id == "ingest-structures"
    assert node.operation == "normalize"
    assert node.dependencies == ("fetch-sequences",)
    assert node.inputs == ("raw/structures.json",)
    assert node.outputs == ("canonical/structures.parquet",)
    assert node.checkpoint_key == "ingest-structures"
    assert node.to_record()["retry_limit"] == 2


def test_dag_node_rejects_duplicate_or_self_dependencies():
    with pytest.raises(ValueError):
        DAGNode(node_id="build", operation="work", dependencies=("a", "a"))

    with pytest.raises(ValueError):
        DAGNode(node_id="build", operation="work", dependencies=("build",))


def test_dag_node_readiness_tracks_completed_dependencies():
    node = DAGNode(
        node_id="package",
        operation="package",
        dependencies=("normalize", "index"),
    )

    assert not node.is_ready({"normalize"})
    assert node.is_ready({"normalize", "index", "report"})


def test_dag_node_state_can_retry_only_for_failed_nodes_with_budget():
    node = DAGNode(node_id="index", operation="index", retry_limit=2)
    failed_once = DAGNodeState(node_id="index", status=DAGNodeStatus.FAILED, attempt=1)
    failed_twice = DAGNodeState(node_id="index", status=DAGNodeStatus.FAILED, attempt=2)
    running = DAGNodeState(node_id="index", status=DAGNodeStatus.RUNNING, attempt=1)

    assert failed_once.can_retry(node)
    assert not failed_twice.can_retry(node)
    assert not running.can_retry(node)
