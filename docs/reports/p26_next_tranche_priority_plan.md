# P26 Next Tranche Priority Plan

Date: 2026-03-23

## Basis

This plan is anchored to the current selected-cohort packet state:

- `4` complete packets
- `8` partial packets
- remaining deficits: `7` ligand / `1` structure / `1` ppi

Primary evidence:

- `docs/reports/p26_selected_packet_materialization.md`
- `docs/reports/p26_packet_deficit_rerun.md`
- `docs/reports/p26_procurement_packet_readiness.md`
- `docs/reports/p26_source_priority_ranking.md`

## Next 5 Highest-Impact Tasks

### 1. Structure gap closure for `Q9UCM0`

- Proposed task: `P26-T013`
- Title: `Close the final single-accession structure deficit`
- Dependencies:
  - `P26-T003` corpus expansion registry builder
  - `P26-T005` training packet materializer
- Scope:
  - target `Q9UCM0` specifically
  - probe local `alphafold_db`, local `structures_rcsb`, and the `RCSB/PDBe` bridge for the best accession-clean structure payload
  - materialize the winning structure lane into the packet pipeline with provenance
- Expected payoff:
  - reduces structure deficit from `1` to `0`
  - removes the last structure-only blocker from the selected cohort
  - simplifies the next balanced-cohort plan by making remaining deficits mostly ligand-focused
- Main blocker:
  - must keep accession-to-structure lineage explicit and avoid role-ambiguous bridge rows

### 2. PPI gap closure for `P04637`

- Proposed task: `P26-T014`
- Title: `Resolve the final packet-level PPI deficit for P04637`
- Dependencies:
  - `P26-T002` source coverage matrix exporter
  - `P26-T003` corpus expansion registry builder
  - current IntAct packet path from `P26-T005`
- Scope:
  - audit why `P04637` still fails the non-self IntAct rule
  - test whether curated `IntAct`, local structural pair evidence, or a new `BioGRID` import can provide a truthful non-self pair lane
  - preserve the existing conservative rule if no valid pair exists
- Expected payoff:
  - reduces PPI deficit from `1` to `0`
  - gives the cohort a cleaner pair-aware floor for balanced multimodal selection
  - isolates ligand as the dominant remaining modality gap
- Main blocker:
  - the current rule is intentionally conservative, so this task must improve evidence, not just loosen validation

### 3. Seven-accession ligand expansion wave

- Proposed task: `P26-T015`
- Title: `Run targeted ligand bridge expansion for the remaining seven ligand-deficit accessions`
- Dependencies:
  - `P26-T003` corpus expansion registry builder
  - `P26-T005` training packet materializer
  - source priorities from `P26-I007`
- Scope:
  - target `P00387`, `P09105`, `P69892`, `P69905`, `Q2TAC2`, `Q9NZD4`, and `Q9UCM0`
  - search local `BindingDB`, `ChEMBL`, `BioLiP`, `PDBBind`, and bound-object extracts in that order
  - materialize only accession-clean, provenance-preserving ligand rows
- Expected payoff:
  - largest immediate coverage gain in the whole queue
  - if even `3-4` of the `7` accessions land cleanly, the cohort moves from mostly partial to mostly complete much faster than any other single task
  - directly improves balanced training coverage because ligand is the dominant remaining deficit
- Main blocker:
  - ligand joins are easy to overclaim; the task must prefer stable ligand identity and reject ambiguous bridge-only matches

### 4. Ligand-confidence ranking for packet-safe selection

- Proposed task: `P26-T016`
- Title: `Score candidate ligand rows for packet-safe materialization`
- Dependencies:
  - `P26-T004` balanced cohort scorer
  - `P26-T015` ligand expansion wave
- Scope:
  - add a ligand-selection policy layer for the remaining accession set
  - rank candidate ligand rows by evidence quality, structure linkage, assay support, and identifier stability
  - emit a top-choice-per-accession view that the packet materializer can consume
- Expected payoff:
  - converts raw ligand breadth into high-confidence training packets instead of noisy overlinked packets
  - improves the quality of balanced-set creation, not just the quantity of packets
  - reduces the chance that the next packet rerun looks better numerically but worse scientifically
- Main blocker:
  - multiple ligand rows may exist per accession, so the ranking policy has to stay conservative and testable

### 5. Rerun the balanced-cohort plan on post-expansion packets

- Proposed task: `P26-I017`
- Title: `Rerun balanced dataset planning on the expanded packet corpus`
- Dependencies:
  - `P26-T013`
  - `P26-T014`
  - `P26-T015`
  - `P26-T016`
  - `P26-T006` balanced dataset planning CLI
- Scope:
  - rerun packet deficit analysis after the structure, PPI, and ligand fixes
  - require explicit modality quotas in the plan:
    - zero structure deficits
    - zero PPI deficits
    - materially reduced ligand deficits
    - leakage-safe split diversity preserved
  - write an updated cohort recommendation for the next real training wave
- Expected payoff:
  - converts the expansion work into an actual go/no-go planning artifact
  - tells us whether we have enough complete packets to move beyond the current selected cohort
  - provides the cleanest bridge from procurement/materialization work into real training execution
- Main blocker:
  - success depends on the prior three closure tasks actually landing with conservative evidence

## Recommended Execution Order

1. `P26-T013` structure gap closure for `Q9UCM0`
2. `P26-T014` PPI gap closure for `P04637`
3. `P26-T015` seven-accession ligand expansion wave
4. `P26-T016` ligand-confidence ranking for packet-safe selection
5. `P26-I017` rerun balanced dataset planning on the expanded packet corpus

## Why This Order

- The structure and PPI gaps are single-accession closures, so they are the fastest truth-preserving wins.
- The ligand wave is the highest-yield coverage task, but it benefits from knowing that structure and PPI floors are already settled.
- The ligand scorer should follow the raw ligand expansion so it ranks actual candidates, not hypothetical ones.
- The balanced-plan rerun should happen only after the packet corpus changes materially.
