# Canonical / Execution Spec Reconciliation

## Scope

This note reconciles the authoritative spec set in `master_handoff_package/02_EXECUTION_AND_CANONICAL_SPEC` with the matching max-complete material in `master_handoff_package/03_MAX_COMPLETE_SPEC/03_execution_and_canonical_data_spec`, against the current bootstrap implementation and queue state. The new handoff package should now be treated as the authoritative baseline for canonical data and execution behavior.

## Canonical Schema

The authoritative canonical layer is broader than the current implementation. Required first-class records are `ProteinRecord`, `ChainRecord`, `LigandRecord`, `NucleicAcidRecord`, `ComplexRecord`, `AssayMeasurementRecord`, `AnnotationRecord`, `InteractionEvidenceRecord`, and `ProvenanceRecord`. All canonical records must carry the common control fields: stable internal identity, schema version, timestamps, provenance references, and quality flags. Cross-record references must always resolve to canonical objects or to explicit unresolved placeholders; dangling foreign keys are not allowed.

Current code only implements simplified bootstrap objects in [protein.py](/D:/documents/ProteoSphereV2/core/canonical/protein.py), [ligand.py](/D:/documents/ProteoSphereV2/core/canonical/ligand.py), and [assay.py](/D:/documents/ProteoSphereV2/core/canonical/assay.py). Those models are directionally useful, but they are not spec-complete and should not be treated as final canonical types. The largest schema gaps are the absence of chain, complex, nucleic acid, annotation, interaction-evidence, and full provenance records, plus the absence of uniform internal IDs, schema-version enforcement, canonical timestamps, and explicit placeholder records for unresolved mappings.

## Normalization Rules

The authoritative normalization model is conservative:

- protein is the preferred identity anchor
- chains may remain unmapped if evidence is insufficient
- all source observations must be preserved
- conflicts must not be silently overwritten or collapsed
- missing data must remain explicitly missing, masked, or imputed by policy, never coerced to zero
- downstream selection is a query-time policy decision, not an ingest-time destructive merge

This means the current lightweight canonical classes are too eager to look “resolved” without yet encoding the conflict-preservation and unresolved-reference semantics the spec requires. Queue coverage is partly aligned through `P1-T010`, `P1-T011`, and `P2-T003` through `P2-T006`, but there is still no explicit task for placeholder-record handling, no explicit task for canonical common-field enforcement, and no explicit task that guarantees all joins are performed strictly on canonical IDs after normalization.

## DAG And Recovery

The canonical execution spec requires a richer lifecycle than the current DAG implementation. Required node states include `created`, `queued`, `scheduled`, `running`, `paused`, `checkpointing`, `completed`, `failed_retryable`, `failed_nonretryable`, `cancelled`, and `stale_requires_rebuild`. The scheduler must be topological, dependency-aware, resource-aware, checkpoint-aware, retry-aware, and able to invalidate stale artifacts when upstream inputs or configs change. Recovery rules also require that resume logic never mixes incompatible schema or config versions.

Current bootstrap execution code in [node.py](/D:/documents/ProteoSphereV2/execution/dag/node.py) and [scheduler.py](/D:/documents/ProteoSphereV2/execution/dag/scheduler.py) only supports a reduced lifecycle (`pending`, `running`, `succeeded`, `failed`, `blocked`) and basic topological readiness. It does not yet model resource reservations, retry classes, checkpoint transitions, stale rebuild semantics, or schema/config compatibility gates. `P2-T007` and `P2-T008` should therefore be treated as provisional groundwork rather than completed alignment with the authoritative spec.

## Provenance

The new handoff package is explicit that provenance is mandatory on every canonical object and every execution run. Required lineage includes source identifiers, acquisition time, parser version, transformation chain, confidence, content hash, and parent references. Run provenance must also capture config snapshot, code revision or source hash, environment summary, library versions, hardware details, seeds, dataset or split IDs, and schema versions for features and models.

The current codebase does not yet implement this. The queue does point in the right direction with `P2-T001` and `P2-T002`, but those tasks are not enough by themselves unless they are expanded to cover object-level provenance refs, execution-run lineage, content hashing, and parent-child lineage traversal across canonical, feature, package, and training artifacts.

## Resource Management

The authoritative resource manager spec requires explicit scheduling decisions over CPU, GPU, VRAM, RAM, disk, and cache pressure, including max-jobs-per-GPU, packing policy, CPU fallback, and OOM-aware retry or resubmission behavior. Checkpoints are required at the major expensive boundaries: source acquisition, normalization and mapping, feature extraction, dataset build, long-running training, and export.

This is not currently represented in the execution core. `P2-T009`, `P2-T010`, and `P5-T010` cover pieces of checkpointing, retry, and GPU policy, but there is no single queue item that implements the required resource manager or connects it to DAG scheduling decisions. That is a material gap because the spec treats resource governance as core execution behavior, not optional optimization.

## Queue Gaps And Contradictions

The queue is broadly pointed in the right direction, but it is incomplete relative to the authoritative spec:

- no explicit task exists for `ChainRecord`, `ComplexRecord`, `NucleicAcidRecord`, `AnnotationRecord`, or `InteractionEvidenceRecord`
- no explicit task exists for canonical common metadata enforcement across all record types
- no explicit task exists for unresolved placeholder records and reference-resolution guarantees
- no explicit task exists for stale-artifact invalidation by input hash and config hash
- no explicit task exists for schema-compatibility enforcement during resume and recovery
- no explicit task exists for a resource manager that tracks CPU, GPU, VRAM, RAM, and disk pressure as first-class scheduler inputs
- completed tasks `P1-T007`, `P1-T008`, `P1-T009`, `P2-T007`, and `P2-T008` currently contradict the authoritative “implement exactly” standard if interpreted as final rather than bootstrap

## Implementation Direction

The correct interpretation is not to discard the existing bootstrap work, but to refactor it under the authoritative model. Immediate queue priority should be:

1. replace the simplified canonical record set with the full authoritative object family and shared control fields
2. add unresolved placeholder and canonical-reference enforcement before more ingestion logic lands
3. upgrade DAG state, retry classes, checkpoint boundaries, and stale rebuild semantics
4. implement provenance and lineage as mandatory infrastructure rather than optional metadata
5. add a real resource manager and bind scheduler decisions to it

Net: the handoff package resolves the canonical and execution ambiguity, but it also makes clear that the current implementation is only an initial skeleton. The existing queue direction is usable, yet it still needs targeted task expansion and a strict reclassification of several “done” items from final implementations to bootstrap placeholders awaiting spec-conformant replacement.
