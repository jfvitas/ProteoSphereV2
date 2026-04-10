# Initial Task Decomposition

## Scope Basis

This decomposition is derived from the packaged specs under `specs/parallel_build` and `specs/autotask`.

The packages define the orchestration model, phase order, source-analysis mission, storage mission, branch policy, and agent topology. They do not include the "existing master handoff package and specs already created" referenced in the parallel build README, so the queue below treats missing baseline architecture detail as an explicit blocker rather than filling in gaps by invention.

## Operating Assumptions

- Topology: 1 planner, 10 coding workers, 3 data-analysis workers, 1 reviewer.
- Concurrency target: no overlapping active file ownership.
- Branch rule: one task per branch, reviewer approval required, CI must stay green.
- Phase order is fixed: locked baseline, canonical plus execution, source acquisition plus analysis, storage plus indexing plus packaging, multimodal expansion.

## Queue Shape

- Total tasks: 64
- Coding tasks: 45
- Data-analysis tasks: 12
- Integration tasks: 7

## Explicit Blockers

1. Missing master handoff package.
   The parallel build package says it should be used with an already-created master handoff package and existing specs, but those files are not present in the repository.

2. Missing exact baseline reference pipeline contract.
   The packages identify required baseline components, but they do not define the exact reference model architecture, target metrics, dataset inclusion rules, or canonical split policy. Tasks that depend on those details should proceed only until ambiguity appears, then write a blocker report and stop.

3. Missing canonical schema authority.
   Phase 2 requires canonical records, provenance, conflict handling, and lineage, but there is no detailed canonical schema document in the repository. Entity-level implementation tasks are still decomposed, but schema disputes must be escalated rather than guessed.

4. Missing flagship multimodal success definition.
   Phase 5 calls for a flagship multimodal model, but the repository does not define the exact modality mix, benchmark task, or acceptance threshold. Multimodal tasks should build adapters and infrastructure first, then stop on unresolved product-level choices.

## Recommended Initial Waves

### Wave 1

- `P1-T001` to `P1-T008`
- `P3-A001` to `P3-A003`

Reason: establishes repo discipline and minimal baseline primitives while starting the three highest-value source reports.

### Wave 2

- `P1-T009` to `P1-T013`
- `P2-T017` to `P2-T023`
- `P3-A004` to `P3-A006`

Reason: opens normalization, provenance, and identifier work without file overlap while keeping analysis workers busy on high-priority sources.

### Wave 3

- `P1-T014` to `P1-T016`
- `P2-T024` to `P2-T030`
- `P3-A007` to `P3-A012`

Reason: converges the baseline pipeline and canonical execution while finishing the source-analysis surface required for storage design.

### Wave 4

- `P3-I013` to `P3-I014`
- `P4-T001` to `P4-T010`

Reason: turns source analysis into concrete storage and packaging decisions.

### Wave 5

- `P5-T001` to `P5-T010`

Reason: begins only after the baseline, canonical layer, source strategy, and packaging path exist.

## Planner Notes

- Keep `P1-T014` to `P1-T016`, `P2-T024` to `P2-T030`, and `P5-T006` to `P5-T010` under tighter review because they are the most likely to hit missing-spec blockers.
- Treat source reports as prerequisites for storage-layer decisions. Do not launch Phase 4 implementation broadly until `P3-I013` and `P3-I014` are done.
- If reviewer findings or blocker reports expose hidden file overlap, split tasks further instead of allowing concurrent edits in the same subtree.
