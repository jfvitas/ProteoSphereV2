# Execution Model

Topology:
- 1 planner
- 8 to 12 coding workers
- 2 to 4 data-analysis workers
- 1 reviewer
- CI / Git gates

Planner:
- decomposes work
- maintains dependency graph
- prevents file overlap
- reprioritizes tasks
- never writes production code directly

Workers:
- execute one task each
- only touch assigned files
- write tests
- stop if blocked

Reviewer:
- enforces specs
- rejects shortcuts
- verifies tests and branch hygiene

Why:
Open agent swarms drift. Hierarchical decomposition with hard gates is much more reliable.
