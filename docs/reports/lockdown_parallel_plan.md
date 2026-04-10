# Lockdown Parallel Plan

As of 2026-03-22, the authoritative order is still:
1. exact lockdown baseline
2. canonical / execution correctness
3. max-complete expansion

The current queue should be read through that lens. The baseline is close, but it is not release-green until the locked split work and exact-stack integration finish and prove out on real data.

## Next Tasks

1. `L1-T006` Implement MMseqs2 and Murcko split strategy. This is the last explicit lockdown primitive still open and should remain the top coding priority.
2. `L1-I007` / queue-equivalent `P1-I019` integrate the exact locked reference stack. Do not let this proceed as a generic bootstrap integration; it must validate the locked baseline end to end.
3. `P2-T001` Implement provenance record model. This starts the canonical / execution layer only after the baseline stack is green.
4. `P2-T002` Implement lineage links. This is the minimum structure needed for trustworthy canonical provenance.
5. `P2-T003` Implement protein conflict rules.
6. `P2-T004` Implement ligand conflict rules.
7. `P2-T005` Implement assay conflict rules.
8. `P2-T009` Implement checkpoint store. This should stay aligned with the retry policy already completed in `P2-T010`.
9. `P2-T011` Implement structure ingest to canonical layer.
10. `P2-T012` Implement sequence ingest to canonical layer.
11. `P2-T013` Implement assay ingest to canonical layer.
12. `P2-I014` Integrate canonical execution graph.
13. `P2-I015` Validate checkpoint restart behavior.
14. `P2-I016` Validate provenance integrity.

## Real-Data Procurement Gates

The summary-library and benchmark phases must wait on the full procurement chain:

- source analysis: `P3-A001` through `P3-A012`
- source compatibility: `P3-I013`
- join strategy and storage policy: `P3-I014` and `P3-I015`
- planning and selective materialization: `P4-T001` through `P4-I013`

Only after that chain can the summary library begin:

- `P6-T001` summary library schema
- `P6-T002` protein pair cross-reference index
- `P6-T003` summary library builder
- `P6-I004` real-corpus validation

The benchmark phase then requires the summary library plus the flagship model integration gate:

- `P5-I012`
- `P6-I007`

## Stale Or Deferred Items

- `P5-T010` should be deferred. The current orchestrator still has it active, but phase 5 is supposed to stay frozen until the lockdown baseline is green.
- `P6-T001` through `P6-I007` should remain blocked until the procurement chain above is complete.
- `P1-T010` is superseded by `L1-T001` and should not be revived as the primary mapping path.
- `P1-T012` and `P1-T013` are bootstrap-only feature tasks and should not be treated as release-grade until they are reconciled to the locked feature stack.
- The older `P1-T014` through `P1-I020` chain is not wrong in isolation, but it is now too bootstrap-shaped to outrun the authoritative lockdown / canonical ordering.

## Bottom Line

The next useful work is still narrow: finish the exact lockdown split and integration, then harden canonical provenance and execution correctness, while allowing source-analysis work to continue in parallel only when it does not pull the queue past the baseline.
