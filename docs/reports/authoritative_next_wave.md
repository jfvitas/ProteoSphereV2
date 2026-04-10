# Authoritative Next Wave

## Baseline Order

The master handoff package is now authoritative. Execution order is:

1. Lockdown baseline first
2. Canonical and execution correctness second
3. Max-complete expansion third

No task should bypass that ordering. Existing bootstrap implementations may remain useful, but they are not release-grade if they fall short of the lockdown or canonical contracts.

## Immediate Priorities

### 1. Finish the lockdown reference pipeline exactly

Promote these as the highest-priority ready tasks:

- `L1-T001` MMseqs2 chain-to-UniProt alignment mapping
- `L1-T002` atom and residue graph extraction
- `L1-T003` frozen ESM2 embedding extraction
- `L1-T004` RDKit ligand descriptor extraction
- `L1-T005` KD-tree interface contact features

Gate the next lockdown tasks behind those outputs:

- `L1-T006` MMseqs2 protein split + Murcko scaffold split
- `L1-I007` integration of the locked reference stack

`P1-T010` should be treated as superseded by `L1-T001`, because exact-match mapping is below the authoritative baseline. `P1-T012` and `P1-T013` should be treated as bootstrap-only until they are reconciled to the locked feature stack.

### 2. Harden canonical correctness immediately after lockdown parity

Continue only the Phase 2 work that strengthens canonical integrity and runtime correctness without redefining the baseline:

- `P2-T003` protein conflict rules
- `P2-T004` ligand conflict rules
- `P2-T005` assay conflict rules
- `P2-T006` canonical entity registry
- `P2-T009` checkpoint store
- `P2-T010` retry policy

The next wave after lockdown parity must close the known canonical gaps:

- richer canonical record families and strict cross-references
- unresolved placeholders instead of silent drops
- common control and provenance fields across records
- stronger DAG lifecycle, stale rebuild handling, and checkpoint-resume semantics
- resource-aware execution controls

### 3. Keep research breadth moving, but do not let it outrun the baseline

The Phase 3 source-analysis tasks are useful and can continue in parallel because they inform the release-grade data strategy:

- `P3-A003`
- `P3-A005`
- `P3-A006`
- `P3-A007`
- `P3-A008`
- `P3-A009`
- `P3-A010`
- `P3-A011`
- `P3-A012`

Phase 5 and Phase 6 expansion work should stay effectively frozen, except for minimal scaffolding that is directly required for lockdown execution, validation, or canonical hardening.

## Release-Grade Validation Gates

Before broader expansion, the system must demonstrate all of the following on real data:

- end-to-end execution of the exact lockdown stack
- explicit unresolved-mapping handling for chain-to-protein canonicalization
- leakage-safe MMseqs2 and Murcko split validation
- provenance and lineage checks across canonical records
- checkpoint, retry, and resume validation
- baseline metrics reporting for the locked reference model

## Planner Decision

The next wave is therefore:

1. Complete the lockdown feature and split primitives
2. Integrate the exact locked reference pipeline and prove it on real data
3. Immediately harden canonical/provenance/runtime correctness to release-grade behavior
4. Only then expand source breadth, storage/indexing depth, UI breadth, and multimodal scope
