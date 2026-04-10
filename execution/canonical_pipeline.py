from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from core.canonical.registry import CanonicalEntityRegistry
from execution.checkpoints.store import (
    CheckpointNotFoundError,
    CheckpointRecord,
    CheckpointStore,
)
from execution.dag.node import DAGNode, DAGNodeState, DAGNodeStatus
from execution.dag.scheduler import DAGScheduler
from execution.ingest.assays import AssayIngestResult, ingest_bindingdb_assays
from execution.ingest.sequences import (
    DEFAULT_PARSER_VERSION,
    SequenceIngestResult,
    ingest_sequence_records,
)
from execution.ingest.structures import StructureIngestResult, ingest_structure_records
from execution.retries.policy import FailureClass, FailureSignal, RetryDecision, RetryPolicy

CanonicalPipelineStatus = Literal["ready", "partial", "conflict", "unresolved", "failed"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _pipeline_graph() -> DAGScheduler:
    return DAGScheduler(
        nodes=(
            DAGNode(
                node_id="ingest_sequences",
                operation="execution.ingest.sequences.ingest_sequence_records",
                outputs=("sequence_result", "canonical_proteins"),
            ),
            DAGNode(
                node_id="ingest_structures",
                operation="execution.ingest.structures.ingest_structure_records",
                dependencies=("ingest_sequences",),
                outputs=("structure_result",),
            ),
            DAGNode(
                node_id="ingest_assays",
                operation="execution.ingest.assays.ingest_bindingdb_assays",
                dependencies=("ingest_sequences",),
                outputs=("assay_result",),
            ),
            DAGNode(
                node_id="assemble_canonical_layer",
                operation="execution.canonical_pipeline.assemble_canonical_layer",
                dependencies=("ingest_sequences", "ingest_structures", "ingest_assays"),
                outputs=("pipeline_result",),
            ),
        )
    )


def _checkpoint_provenance(
    *,
    run_id: str,
    node_id: str,
    attempt: int,
    node_status: str,
    completed_nodes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "node_id": node_id,
        "attempt": attempt,
        "node_status": node_status,
        "completed_nodes": list(completed_nodes),
    }


def _run_checkpoint_state(
    *,
    status: CanonicalPipelineStatus,
    reason: str,
    completed_nodes: tuple[str, ...],
    blocked_nodes: tuple[str, ...],
    sequence_result: SequenceIngestResult | None,
    structure_result: StructureIngestResult | None,
    assay_result: AssayIngestResult | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "completed_nodes": list(completed_nodes),
        "blocked_nodes": list(blocked_nodes),
        "sequence": (
            None
            if sequence_result is None
            else {
                "status": sequence_result.status,
                "reason": sequence_result.reason,
                "canonical_ids": list(sequence_result.canonical_ids),
                "unresolved": len(sequence_result.unresolved_references),
                "conflicts": len(sequence_result.conflicts),
            }
        ),
        "structure": (
            None
            if structure_result is None
            else {
                "status": structure_result.status,
                "canonical_records": len(structure_result.canonical_records),
                "unresolved": len(structure_result.unresolved_references),
                "conflicts": len(structure_result.conflicts),
            }
        ),
        "assay": (
            None
            if assay_result is None
            else {
                "status": assay_result.status,
                "canonical_assays": len(assay_result.canonical_assays),
                "unresolved_cases": len(assay_result.unresolved_cases),
                "conflicts": len(assay_result.conflicts),
            }
        ),
    }


def _summarize_sequence_result(result: SequenceIngestResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "status": result.status,
        "reason": result.reason,
        "canonical_ids": list(result.canonical_ids),
        "conflicts": len(result.conflicts),
        "unresolved_references": len(result.unresolved_references),
    }


def _summarize_structure_result(result: StructureIngestResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "status": result.status,
        "proteins": len(result.proteins),
        "chains": len(result.chains),
        "complexes": len(result.complexes),
        "conflicts": len(result.conflicts),
        "unresolved_references": len(result.unresolved_references),
        "graph_edges": len(result.graph_edges),
    }


def _summarize_assay_result(result: AssayIngestResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "status": result.status,
        "reason": result.reason,
        "canonical_assays": len(result.canonical_assays),
        "conflicts": len(result.conflicts),
        "unresolved_cases": len(result.unresolved_cases),
    }


def _collect_unresolved_cases(
    sequence_result: SequenceIngestResult | None,
    structure_result: StructureIngestResult | None,
    assay_result: AssayIngestResult | None,
) -> tuple[Any, ...]:
    unresolved: list[Any] = []
    if sequence_result is not None:
        unresolved.extend(sequence_result.unresolved_references)
    if structure_result is not None:
        unresolved.extend(structure_result.unresolved_references)
    if assay_result is not None:
        unresolved.extend(assay_result.unresolved_cases)
    return tuple(unresolved)


def _collect_conflicts(
    sequence_result: SequenceIngestResult | None,
    structure_result: StructureIngestResult | None,
    assay_result: AssayIngestResult | None,
) -> tuple[Any, ...]:
    conflicts: list[Any] = []
    if sequence_result is not None:
        conflicts.extend(sequence_result.conflicts)
    if structure_result is not None:
        conflicts.extend(structure_result.conflicts)
    if assay_result is not None:
        conflicts.extend(assay_result.conflicts)
    return tuple(conflicts)


def _derive_status(
    *,
    failure: str | None,
    sequence_result: SequenceIngestResult | None,
    structure_result: StructureIngestResult | None,
    assay_result: AssayIngestResult | None,
) -> tuple[CanonicalPipelineStatus, str]:
    if failure is not None:
        return "failed", failure

    statuses = [
        sequence_result.status if sequence_result is not None else None,
        structure_result.status if structure_result is not None else None,
        assay_result.status if assay_result is not None else None,
    ]
    if any(status == "conflict" for status in statuses if status is not None):
        return "conflict", "one_or_more_ingest_slices_reported_conflicts"

    has_unresolved = any(
        status in {"partial", "unresolved", "ambiguous"}
        for status in statuses
        if status is not None
    )
    has_success = any(status in {"ready", "resolved"} for status in statuses if status is not None)
    if has_unresolved:
        if has_success:
            return "partial", "one_or_more_ingest_slices_preserved_unresolved_cases"
        return "unresolved", "no_canonical_records_were_resolved"
    return "ready", "all_canonical_ingest_slices_resolved"


def _failure_signal_for_exception(
    *,
    node: DAGNode,
    exc: Exception,
    checkpoint_available: bool,
) -> FailureSignal:
    if isinstance(exc, TimeoutError):
        failure_class = FailureClass.TRANSIENT_IO
    elif isinstance(exc, OSError):
        failure_class = FailureClass.EXTERNAL_DEPENDENCY
    elif isinstance(exc, TypeError):
        failure_class = FailureClass.SCHEMA_MISMATCH
    elif isinstance(exc, ValueError):
        failure_class = FailureClass.INPUT_VALIDATION
    else:
        failure_class = FailureClass.UNKNOWN
    return FailureSignal(
        failure_class=failure_class,
        message=str(exc),
        node_type=node.operation,
        checkpoint_available=checkpoint_available,
        checkpoint_valid=True,
        alternate_source_available=False,
    )


def _failure_message(node_id: str, exc: Exception) -> str:
    return f"{node_id} failed: {exc.__class__.__name__}: {exc}"


def _blocked_state(node_id: str, reason: str) -> DAGNodeState:
    return DAGNodeState(node_id=node_id, status=DAGNodeStatus.BLOCKED, attempt=0, last_error=reason)


@dataclass(frozen=True, slots=True)
class CanonicalPipelineConfig:
    run_id: str
    sequence_records: object | None = None
    structure_records: object | None = None
    assay_records: object | None = None
    registry: CanonicalEntityRegistry = field(default_factory=CanonicalEntityRegistry)
    checkpoint_store: CheckpointStore = field(default_factory=CheckpointStore)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    acquired_at: str | None = None
    parser_version: str = DEFAULT_PARSER_VERSION

    def __post_init__(self) -> None:
        run_id = _clean_text(self.run_id)
        if not run_id:
            raise ValueError("run_id must be a non-empty string")
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(
            self,
            "parser_version",
            _clean_text(self.parser_version) or DEFAULT_PARSER_VERSION,
        )


@dataclass(frozen=True, slots=True)
class CanonicalPipelineResult:
    run_id: str
    status: CanonicalPipelineStatus
    reason: str
    scheduler: DAGScheduler
    node_states: dict[str, DAGNodeState]
    run_checkpoints: tuple[CheckpointRecord, ...]
    node_checkpoints: tuple[CheckpointRecord, ...]
    sequence_result: SequenceIngestResult | None
    structure_result: StructureIngestResult | None
    assay_result: AssayIngestResult | None
    unresolved_cases: tuple[Any, ...]
    conflicts: tuple[Any, ...]
    registry: CanonicalEntityRegistry
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def blocked_nodes(self) -> tuple[str, ...]:
        return tuple(
            node.node_id for node in self.scheduler.blocked_nodes(self.node_states)
        )

    @property
    def ready_nodes(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self.scheduler.ready_nodes(self.node_states))

    @property
    def run_checkpoint(self) -> CheckpointRecord | None:
        return self.run_checkpoints[-1] if self.run_checkpoints else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "reason": self.reason,
            "scheduler": {
                "nodes": [node.to_record() for node in self.scheduler.ordered_nodes],
                "ready_nodes": list(self.ready_nodes),
                "blocked_nodes": list(self.blocked_nodes),
            },
            "node_states": {
                node_id: {
                    "node_id": state.node_id,
                    "status": state.status,
                    "attempt": state.attempt,
                    "last_error": state.last_error,
                }
                for node_id, state in sorted(self.node_states.items())
            },
            "run_checkpoints": [record.to_dict() for record in self.run_checkpoints],
            "node_checkpoints": [record.to_dict() for record in self.node_checkpoints],
            "sequence_result": (
                None if self.sequence_result is None else self.sequence_result.to_dict()
            ),
            "structure_result": (
                None if self.structure_result is None else self.structure_result.to_dict()
            ),
            "assay_result": None if self.assay_result is None else self.assay_result.to_dict(),
            "unresolved_cases": [_json_ready(item) for item in self.unresolved_cases],
            "conflicts": [_json_ready(item) for item in self.conflicts],
            "registry": {
                "proteins": [entity.to_dict() for entity in self.registry.list_entities("protein")],
                "ligands": [entity.to_dict() for entity in self.registry.list_entities("ligand")],
                "assays": [entity.to_dict() for entity in self.registry.list_entities("assay")],
            },
            "summary": _json_ready(self.summary),
        }


@dataclass(frozen=True, slots=True)
class CanonicalPipeline:
    config: CanonicalPipelineConfig
    scheduler: DAGScheduler = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "scheduler", _pipeline_graph())

    def run(self) -> CanonicalPipelineResult:
        registry = self.config.registry
        store = self.config.checkpoint_store

        sequence_result: SequenceIngestResult | None = None
        structure_result: StructureIngestResult | None = None
        assay_result: AssayIngestResult | None = None
        run_checkpoints: list[CheckpointRecord] = []
        node_checkpoints: list[CheckpointRecord] = []
        node_states: dict[str, DAGNodeState] = {}
        completed_nodes: list[str] = []
        failure_reason: str | None = None

        for node in self.scheduler.ordered_nodes:
            if failure_reason is not None:
                break

            node_output: dict[str, Any] = {}
            attempt = 0
            while True:
                attempt += 1
                try:
                    if node.node_id == "ingest_sequences":
                        sequence_result = ingest_sequence_records(
                            (
                                self.config.sequence_records
                                if self.config.sequence_records is not None
                                else ()
                            ),
                            registry=registry,
                            parser_version=self.config.parser_version,
                        )
                        node_output = _summarize_sequence_result(sequence_result)
                    elif node.node_id == "ingest_structures":
                        structure_result = self._run_structure_ingest(
                            registry=registry,
                            sequence_result=sequence_result,
                        )
                        node_output = _summarize_structure_result(structure_result)
                    elif node.node_id == "ingest_assays":
                        assay_result = ingest_bindingdb_assays(
                            (
                                self.config.assay_records
                                if self.config.assay_records is not None
                                else ()
                            ),
                            registry=registry,
                            acquired_at=self.config.acquired_at
                            or datetime.now(UTC).isoformat(),
                            parser_version=self.config.parser_version,
                            run_id=self.config.run_id,
                        )
                        node_output = _summarize_assay_result(assay_result)
                    elif node.node_id == "assemble_canonical_layer":
                        node_output = self._assemble_summary(
                            sequence_result=sequence_result,
                            structure_result=structure_result,
                            assay_result=assay_result,
                            completed_nodes=tuple(completed_nodes),
                        )
                    else:
                        raise ValueError(f"unsupported pipeline node: {node.node_id}")

                    node_state = DAGNodeState(
                        node_id=node.node_id,
                        status=DAGNodeStatus.SUCCEEDED,
                        attempt=attempt,
                    )
                    node_states[node.node_id] = node_state
                    completed_nodes.append(node.node_id)
                    node_checkpoints.append(
                        store.write_node_checkpoint(
                            self.config.run_id,
                            node.node_id,
                            {
                                "status": node_state.status,
                                "attempt": node_state.attempt,
                                "output": node_output,
                            },
                            provenance=_checkpoint_provenance(
                                run_id=self.config.run_id,
                                node_id=node.node_id,
                                attempt=attempt,
                                node_status=node_state.status.value,
                                completed_nodes=tuple(completed_nodes),
                            ),
                            metadata={
                                "operation": node.operation,
                                "dependencies": list(node.dependencies),
                                "retry_limit": node.retry_limit,
                            },
                        )
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    signal = _failure_signal_for_exception(
                        node=node,
                        exc=exc,
                        checkpoint_available=store.has_checkpoint(self.config.run_id, node.node_id),
                    )
                    decision = self.config.retry_policy.evaluate(
                        signal,
                        attempt=attempt,
                        node_retry_limit=node.retry_limit,
                    )
                    node_state = DAGNodeState(
                        node_id=node.node_id,
                        status=DAGNodeStatus.FAILED,
                        attempt=attempt,
                        last_error=_failure_message(node.node_id, exc),
                    )
                    node_states[node.node_id] = node_state
                    node_checkpoints.append(
                        store.write_node_checkpoint(
                            self.config.run_id,
                            node.node_id,
                            {
                                "status": node_state.status,
                                "attempt": node_state.attempt,
                                "error": node_state.last_error,
                            },
                            provenance=_checkpoint_provenance(
                                run_id=self.config.run_id,
                                node_id=node.node_id,
                                attempt=attempt,
                                node_status=node_state.status.value,
                                completed_nodes=tuple(completed_nodes),
                            ),
                            metadata={
                                "operation": node.operation,
                                "retry_decision": self._retry_decision_to_dict(decision),
                                "failure_class": signal.failure_class.value,
                            },
                        )
                    )
                    if decision.should_retry:
                        continue
                    failure_reason = node_state.last_error
                    for blocked_node in self.scheduler.blocked_nodes(node_states):
                        node_states.setdefault(
                            blocked_node.node_id,
                            _blocked_state(
                                blocked_node.node_id,
                                f"blocked_by:{node.node_id}",
                            ),
                        )
                    break

            run_status, run_reason = _derive_status(
                failure=failure_reason,
                sequence_result=sequence_result,
                structure_result=structure_result,
                assay_result=assay_result,
            )
            run_checkpoints.append(
                store.write_run_checkpoint(
                    self.config.run_id,
                    _run_checkpoint_state(
                        status=run_status,
                        reason=run_reason,
                        completed_nodes=tuple(completed_nodes),
                        blocked_nodes=tuple(
                            node.node_id for node in self.scheduler.blocked_nodes(node_states)
                        ),
                        sequence_result=sequence_result,
                        structure_result=structure_result,
                        assay_result=assay_result,
                    ),
                    provenance={
                        "run_id": self.config.run_id,
                        "node_id": node.node_id,
                        "completed_nodes": list(completed_nodes),
                        "status": run_status,
                    },
                    metadata={
                        "completed_nodes": list(completed_nodes),
                        "node_count": len(self.scheduler.ordered_nodes),
                    },
                )
            )
            if failure_reason is not None:
                break

        status, reason = _derive_status(
            failure=failure_reason,
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
        )
        summary = self._final_summary(
            status=status,
            reason=reason,
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
            completed_nodes=tuple(completed_nodes),
            node_states=node_states,
            run_checkpoints=tuple(run_checkpoints),
            node_checkpoints=tuple(node_checkpoints),
        )
        return CanonicalPipelineResult(
            run_id=self.config.run_id,
            status=status,
            reason=reason,
            scheduler=self.scheduler,
            node_states=node_states,
            run_checkpoints=tuple(run_checkpoints),
            node_checkpoints=tuple(node_checkpoints),
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
            unresolved_cases=_collect_unresolved_cases(
                sequence_result,
                structure_result,
                assay_result,
            ),
            conflicts=_collect_conflicts(
                sequence_result,
                structure_result,
                assay_result,
            ),
            registry=registry,
            summary=summary,
        )

    def resume(self) -> CanonicalPipelineResult:
        resume_state = _load_resume_state(self)
        if resume_state.run_checkpoint is None and not resume_state.node_checkpoints:
            return self.run()

        registry = self.config.registry
        store = self.config.checkpoint_store
        sequence_result = resume_state.sequence_result
        structure_result = resume_state.structure_result
        assay_result = resume_state.assay_result
        node_states = dict(resume_state.node_states)
        completed_nodes = list(resume_state.completed_nodes)
        completed_node_ids = set(completed_nodes)
        failure_reason = resume_state.failure_reason
        run_checkpoints = (
            [resume_state.run_checkpoint] if resume_state.run_checkpoint is not None else []
        )
        node_checkpoints = list(resume_state.node_checkpoints)

        for node in self.scheduler.ordered_nodes:
            state = node_states.get(node.node_id)
            if state is not None and state.status == DAGNodeStatus.SUCCEEDED:
                continue
            if state is not None and state.status == DAGNodeStatus.BLOCKED:
                continue
            if state is not None and state.status == DAGNodeStatus.FAILED and not state.can_retry(
                node
            ):
                continue

            ready_node_ids = {
                ready_node.node_id for ready_node in self.scheduler.ready_nodes(node_states)
            }
            if node.node_id not in ready_node_ids:
                continue

            attempt = 1 if state is None else state.attempt + 1
            (
                sequence_result,
                structure_result,
                assay_result,
                node_output,
            ) = _execute_pipeline_node(
                self,
                node,
                sequence_result=sequence_result,
                structure_result=structure_result,
                assay_result=assay_result,
                completed_nodes=tuple(completed_nodes),
            )
            node_state = DAGNodeState(
                node_id=node.node_id,
                status=DAGNodeStatus.SUCCEEDED,
                attempt=attempt,
            )
            node_states[node.node_id] = node_state
            if node.node_id not in completed_node_ids:
                completed_nodes.append(node.node_id)
                completed_node_ids.add(node.node_id)
            node_checkpoints.append(
                store.write_node_checkpoint(
                    self.config.run_id,
                    node.node_id,
                    {
                        "status": node_state.status,
                        "attempt": node_state.attempt,
                        "output": node_output,
                    },
                    provenance=_checkpoint_provenance(
                        run_id=self.config.run_id,
                        node_id=node.node_id,
                        attempt=attempt,
                        node_status=node_state.status.value,
                        completed_nodes=tuple(completed_nodes),
                    ),
                    metadata={
                        "operation": node.operation,
                        "dependencies": list(node.dependencies),
                        "retry_limit": node.retry_limit,
                    },
                )
            )
            failure_reason = _resume_failure_reason(self.scheduler, node_states)
            run_status, run_reason = _derive_status(
                failure=failure_reason,
                sequence_result=sequence_result,
                structure_result=structure_result,
                assay_result=assay_result,
            )
            run_checkpoints.append(
                store.write_run_checkpoint(
                    self.config.run_id,
                    _run_checkpoint_state(
                        status=run_status,
                        reason=run_reason,
                        completed_nodes=tuple(completed_nodes),
                        blocked_nodes=tuple(
                            node.node_id for node in self.scheduler.blocked_nodes(node_states)
                        ),
                        sequence_result=sequence_result,
                        structure_result=structure_result,
                        assay_result=assay_result,
                    ),
                    provenance={
                        "run_id": self.config.run_id,
                        "node_id": node.node_id,
                        "completed_nodes": list(completed_nodes),
                        "status": run_status,
                    },
                    metadata={
                        "completed_nodes": list(completed_nodes),
                        "node_count": len(self.scheduler.ordered_nodes),
                    },
                )
            )

        failure_reason = _resume_failure_reason(self.scheduler, node_states) or failure_reason

        status, reason = _derive_status(
            failure=failure_reason,
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
        )
        summary = self._final_summary(
            status=status,
            reason=reason,
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
            completed_nodes=tuple(completed_nodes),
            node_states=node_states,
            run_checkpoints=tuple(record for record in run_checkpoints if record is not None),
            node_checkpoints=tuple(node_checkpoints),
        )
        return CanonicalPipelineResult(
            run_id=self.config.run_id,
            status=status,
            reason=reason,
            scheduler=self.scheduler,
            node_states=node_states,
            run_checkpoints=tuple(record for record in run_checkpoints if record is not None),
            node_checkpoints=tuple(node_checkpoints),
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
            unresolved_cases=_collect_unresolved_cases(
                sequence_result,
                structure_result,
                assay_result,
            ),
            conflicts=_collect_conflicts(
                sequence_result,
                structure_result,
                assay_result,
            ),
            registry=registry,
            summary=summary,
        )

    def _run_structure_ingest(
        self,
        *,
        registry: CanonicalEntityRegistry,
        sequence_result: SequenceIngestResult | None,
    ) -> StructureIngestResult:
        provenance = () if sequence_result is None else sequence_result.provenance_records
        return ingest_structure_records(
            self.config.structure_records if self.config.structure_records is not None else (),
            provenance=provenance,
            registry=registry,
        )

    def _assemble_summary(
        self,
        *,
        sequence_result: SequenceIngestResult | None,
        structure_result: StructureIngestResult | None,
        assay_result: AssayIngestResult | None,
        completed_nodes: tuple[str, ...],
    ) -> dict[str, Any]:
        status, reason = _derive_status(
            failure=None,
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
        )
        return {
            "status": status,
            "reason": reason,
            "completed_nodes": list(completed_nodes),
            "sequence": _summarize_sequence_result(sequence_result),
            "structure": _summarize_structure_result(structure_result),
            "assay": _summarize_assay_result(assay_result),
        }

    @staticmethod
    def _retry_decision_to_dict(decision: RetryDecision) -> dict[str, Any]:
        return {
            "failure_class": decision.failure_class.value,
            "failure_disposition": decision.failure_disposition.value,
            "task_state": decision.task_state.value,
            "should_retry": decision.should_retry,
            "is_terminal": decision.is_terminal,
            "retry_limit": decision.retry_limit,
            "remaining_attempts": decision.remaining_attempts,
            "next_delay_seconds": decision.next_delay_seconds,
            "checkpoint_disposition": decision.checkpoint_disposition.value,
            "alternate_source_allowed": decision.alternate_source_allowed,
        }

    @staticmethod
    def _final_summary(
        *,
        status: CanonicalPipelineStatus,
        reason: str,
        sequence_result: SequenceIngestResult | None,
        structure_result: StructureIngestResult | None,
        assay_result: AssayIngestResult | None,
        completed_nodes: tuple[str, ...],
        node_states: dict[str, DAGNodeState],
        run_checkpoints: tuple[CheckpointRecord, ...],
        node_checkpoints: tuple[CheckpointRecord, ...],
    ) -> dict[str, Any]:
        return {
            "status": status,
            "reason": reason,
            "completed_nodes": list(completed_nodes),
            "blocked_nodes": [
                node_id
                for node_id, state in sorted(node_states.items())
                if state.status == DAGNodeStatus.BLOCKED
            ],
            "run_checkpoint_versions": [record.version for record in run_checkpoints],
            "node_checkpoint_versions": {
                record.node_id or "<run>": record.version for record in node_checkpoints
            },
            "sequence": _summarize_sequence_result(sequence_result),
            "structure": _summarize_structure_result(structure_result),
            "assay": _summarize_assay_result(assay_result),
        }


@dataclass(frozen=True, slots=True)
class _CanonicalPipelineResumeState:
    run_checkpoint: CheckpointRecord | None
    node_checkpoints: tuple[CheckpointRecord, ...]
    node_states: dict[str, DAGNodeState]
    completed_nodes: tuple[str, ...]
    sequence_result: SequenceIngestResult | None
    structure_result: StructureIngestResult | None
    assay_result: AssayIngestResult | None
    failure_reason: str | None


def _execute_pipeline_node(
    pipeline: CanonicalPipeline,
    node: DAGNode,
    *,
    sequence_result: SequenceIngestResult | None,
    structure_result: StructureIngestResult | None,
    assay_result: AssayIngestResult | None,
    completed_nodes: tuple[str, ...] = (),
) -> tuple[
    SequenceIngestResult | None,
    StructureIngestResult | None,
    AssayIngestResult | None,
    dict[str, Any],
]:
    registry = pipeline.config.registry
    if node.node_id == "ingest_sequences":
        sequence_result = ingest_sequence_records(
            (
                pipeline.config.sequence_records
                if pipeline.config.sequence_records is not None
                else ()
            ),
            registry=registry,
            parser_version=pipeline.config.parser_version,
        )
        return sequence_result, structure_result, assay_result, _summarize_sequence_result(
            sequence_result
        )
    if node.node_id == "ingest_structures":
        structure_result = pipeline._run_structure_ingest(
            registry=registry,
            sequence_result=sequence_result,
        )
        return sequence_result, structure_result, assay_result, _summarize_structure_result(
            structure_result
        )
    if node.node_id == "ingest_assays":
        assay_result = ingest_bindingdb_assays(
            (
                pipeline.config.assay_records if pipeline.config.assay_records is not None else ()
            ),
            registry=registry,
            acquired_at=pipeline.config.acquired_at or datetime.now(UTC).isoformat(),
            parser_version=pipeline.config.parser_version,
            run_id=pipeline.config.run_id,
        )
        return sequence_result, structure_result, assay_result, _summarize_assay_result(
            assay_result
        )
    if node.node_id == "assemble_canonical_layer":
        return (
            sequence_result,
            structure_result,
            assay_result,
            pipeline._assemble_summary(
                sequence_result=sequence_result,
                structure_result=structure_result,
                assay_result=assay_result,
                completed_nodes=completed_nodes,
            ),
        )
    raise ValueError(f"unsupported pipeline node: {node.node_id}")


def _resume_failure_reason(
    scheduler: DAGScheduler,
    node_states: dict[str, DAGNodeState],
) -> str | None:
    for node in scheduler.ordered_nodes:
        state = node_states.get(node.node_id)
        if state is None or state.status != DAGNodeStatus.FAILED:
            continue
        if state.can_retry(node):
            continue
        return state.last_error or f"{node.node_id} failed"
    return None


def _load_resume_state(pipeline: CanonicalPipeline) -> _CanonicalPipelineResumeState:
    store = pipeline.config.checkpoint_store
    try:
        run_checkpoint = store.load_run_checkpoint(pipeline.config.run_id)
    except CheckpointNotFoundError:
        return _CanonicalPipelineResumeState(
            run_checkpoint=None,
            node_checkpoints=(),
            node_states={},
            completed_nodes=(),
            sequence_result=None,
            structure_result=None,
            assay_result=None,
            failure_reason=None,
        )

    node_checkpoints: list[CheckpointRecord] = []
    node_states: dict[str, DAGNodeState] = {}
    sequence_result: SequenceIngestResult | None = None
    structure_result: StructureIngestResult | None = None
    assay_result: AssayIngestResult | None = None
    completed_nodes: list[str] = []

    for node in pipeline.scheduler.ordered_nodes:
        if not store.has_checkpoint(pipeline.config.run_id, node.node_id):
            continue
        checkpoint = store.load_node_checkpoint(pipeline.config.run_id, node.node_id)
        node_checkpoints.append(checkpoint)
        state = DAGNodeState(
            node_id=node.node_id,
            status=DAGNodeStatus(str(checkpoint.checkpoint_state.get("status") or "pending")),
            attempt=int(checkpoint.checkpoint_state.get("attempt") or 0),
            last_error=_clean_text(checkpoint.checkpoint_state.get("error")) or None,
        )
        node_states[node.node_id] = state
        if state.status != DAGNodeStatus.SUCCEEDED:
            continue
        (
            sequence_result,
            structure_result,
            assay_result,
            _,
        ) = _execute_pipeline_node(
            pipeline,
            node,
            sequence_result=sequence_result,
            structure_result=structure_result,
            assay_result=assay_result,
            completed_nodes=tuple(completed_nodes),
        )
        completed_nodes.append(node.node_id)

    checkpoint_status = _clean_text(run_checkpoint.checkpoint_state.get("status")).casefold()
    checkpoint_reason = _clean_text(run_checkpoint.checkpoint_state.get("reason")) or None

    return _CanonicalPipelineResumeState(
        run_checkpoint=run_checkpoint,
        node_checkpoints=tuple(node_checkpoints),
        node_states=node_states,
        completed_nodes=tuple(completed_nodes),
        sequence_result=sequence_result,
        structure_result=structure_result,
        assay_result=assay_result,
        failure_reason=(
            _resume_failure_reason(pipeline.scheduler, node_states)
            or (checkpoint_reason if checkpoint_status == "failed" else None)
        ),
    )


def run_canonical_pipeline(
    config: CanonicalPipelineConfig,
) -> CanonicalPipelineResult:
    return CanonicalPipeline(config).run()


def resume_canonical_pipeline(
    config: CanonicalPipelineConfig,
) -> CanonicalPipelineResult:
    return CanonicalPipeline(config).resume()


__all__ = [
    "CanonicalPipeline",
    "CanonicalPipelineConfig",
    "CanonicalPipelineResult",
    "CanonicalPipelineStatus",
    "resume_canonical_pipeline",
    "run_canonical_pipeline",
]
