from __future__ import annotations

import pytest

from execution.checkpoints.store import (
    CheckpointConflictError,
    CheckpointNotFoundError,
    CheckpointRecord,
    CheckpointStore,
)
from execution.retries.policy import CheckpointDisposition, FailureClass


def test_checkpoint_store_saves_and_loads_run_and_node_snapshots() -> None:
    store = CheckpointStore()

    run_record = store.write_run_checkpoint(
        run_id="run-001",
        checkpoint_state={"stage": "queued", "attempt": 0},
        provenance={"source_ids": ("raw/run.json",), "code_version": "abc123"},
    )
    node_record = store.write_node_checkpoint(
        run_id="run-001",
        node_id="normalize",
        checkpoint_state={"offset": 128, "status": "checkpointing"},
        provenance={"source_ids": ("raw/node.json",), "code_version": "abc123"},
    )

    assert store.load_run_checkpoint("run-001") == run_record
    assert store.load_node_checkpoint("run-001", "normalize") == node_record
    assert run_record.scope.value == "run"
    assert node_record.scope.value == "node"
    assert node_record.checkpoint_key == "run:run-001:node:normalize"


def test_checkpoint_store_raises_for_missing_checkpoint() -> None:
    store = CheckpointStore()

    with pytest.raises(CheckpointNotFoundError, match="missing checkpoint: run:missing-run"):
        store.load_run_checkpoint("missing-run")

    with pytest.raises(
        CheckpointNotFoundError,
        match="missing checkpoint: run:missing-run:node:normalize version 2",
    ):
        store.load_node_checkpoint("missing-run", "normalize", version=2)


def test_checkpoint_store_versions_new_writes_without_overwriting_existing_checkpoint() -> None:
    store = CheckpointStore()

    first = store.write_node_checkpoint(
        run_id="run-001",
        node_id="feature_extract",
        checkpoint_state={"cursor": 10},
    )
    second = store.write_node_checkpoint(
        run_id="run-001",
        node_id="feature_extract",
        checkpoint_state={"cursor": 20},
    )

    assert first.version == 1
    assert second.version == 2
    assert store.list_versions("run-001", "feature_extract") == (1, 2)
    assert store.latest_version("run-001", "feature_extract") == 2
    assert store.load_node_checkpoint("run-001", "feature_extract", version=1).checkpoint_state == {
        "cursor": 10
    }
    assert store.load_node_checkpoint("run-001", "feature_extract").checkpoint_state == {
        "cursor": 20
    }

    with pytest.raises(
        CheckpointConflictError,
        match="checkpoint run:run-001:node:feature_extract version 2 already exists",
    ):
        store.save(
            CheckpointRecord(
                run_id="run-001",
                node_id="feature_extract",
                version=2,
                checkpoint_state={"cursor": 99},
            )
        )


def test_checkpoint_store_preserves_resume_metadata_and_provenance() -> None:
    store = CheckpointStore()
    provenance = {
        "source_ids": ("raw/normalize.tsv",),
        "parser_version": "2.3.1",
        "transformation_chain": ("raw_validate", "normalize"),
        "content_hash": "sha256:bead",
    }
    metadata = {
        "retry": {
            "attempt": 2,
            "failure_class": FailureClass.TRANSIENT_IO.value,
            "checkpoint_disposition": CheckpointDisposition.RESUME_FROM_CHECKPOINT.value,
            "remaining_attempts": 1,
        },
        "resume_gate": {
            "inputs_hash": "sha256:inputs",
            "config_hash": "sha256:config",
            "code_version": "git:deadbeef",
        },
    }

    record = store.write_node_checkpoint(
        run_id="run-001",
        node_id="export",
        checkpoint_state={"artifact": "export.tar", "status": "checkpointing"},
        provenance=provenance,
        metadata=metadata,
    )
    loaded = store.load_node_checkpoint("run-001", "export")

    assert loaded == record
    assert loaded.provenance == provenance
    assert loaded.metadata == metadata
    assert loaded.metadata["retry"]["checkpoint_disposition"] == (
        CheckpointDisposition.RESUME_FROM_CHECKPOINT.value
    )
    assert loaded.metadata["retry"]["failure_class"] == FailureClass.TRANSIENT_IO.value


def test_checkpoint_record_round_trips_through_dict_and_store_identity() -> None:
    payload = {
        "run_id": "run-identity",
        "node_id": None,
        "version": 1,
        "checkpoint_state": {
            "run_id": "run-identity",
            "checkpoint_tag": "tag-1",
            "checkpoint_ref": "checkpoint://run-identity/tag-1",
            "checkpoint_path": "artifacts/runtime_checkpoints/tag-1.json",
            "processed_examples": 2,
            "completed_example_ids": ["example-1", "example-2"],
            "processable_example_ids": ["example-1", "example-2"],
            "deterministic_seed": 7,
            "plan_signature": "plan-123",
            "dataset_signature": "dataset-123",
            "feature_bundle_signature": "bundle-123",
            "head_weights": [0.1, 0.2],
            "head_bias": 0.3,
            "loss_history": [0.4, 0.5],
            "resumed_from": None,
            "provenance": {"checkpoint_kind": "runtime", "inputs": []},
        },
        "provenance": {},
        "metadata": {},
        "schema_version": 1,
        "checkpoint_key": "run:run-identity",
        "scope": "run",
    }

    record = CheckpointRecord.from_dict(payload)
    assert record.provenance == {}
    assert record.metadata == {}
    assert record.checkpoint_state["checkpoint_ref"] == "checkpoint://run-identity/tag-1"
    assert record.checkpoint_key == "run:run-identity"
    assert record.scope.value == "run"

    store = CheckpointStore()
    stored = store.save(record)
    loaded = store.load_run_checkpoint("run-identity")

    assert stored == record
    assert loaded == record
    assert loaded.checkpoint_state["provenance"]["checkpoint_kind"] == "runtime"

    record_dict = loaded.to_dict()
    assert record_dict["checkpoint_key"] == "run:run-identity"
    assert record_dict["scope"] == "run"
