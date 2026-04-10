# P29 Next Acquisition Queue

- Generated at: `2026-03-30T00:49:28.4244984-05:00`
- Queue file: [`artifacts/status/p29_next_acquisition_queue.json`](/D:/documents/ProteoSphereV2/artifacts/status/p29_next_acquisition_queue.json)

## Queue Summary

This queue turns the scope audit into an execution order. The first priority is to restore the missing curated interaction-network class, then fill the absent motif and metadata lanes, and only after that spend effort on lazy sequence expansion or packet-level rescues.

## Phases

### Phase 1: Curated interaction-network coverage

- `BioGRID` guarded procurement first wave.
- `STRING` guarded procurement first wave.
- `IntAct` authoritative intake or refresh.

Why this comes first: the registry has no present `interaction_network` source, and this is the largest breadth hole in the scope.

### Phase 2: Motif and metadata breadth

- `PROSITE` acquisition refresh.
- `ELM` acquisition refresh.
- `SABIO-RK` acquisition.

Why this comes second: motif coverage is entirely missing, and `SABIO-RK` is the only missing metadata lane.

### Phase 3: Sequence depth and packet rescues

- `UniProt` TrEMBL expansion or equivalent sequence-depth lane.
- `Q9UCM0` AlphaFold explicit accession probe.
- `Q9UCM0` curated PPI rescue via `BioGRID` / `STRING` validation.
- Ligand rescue bundle for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`.

Why this comes last: the reviewed sequence spine should stay stable, while the packet-specific work can be indexed against the sources already in hand.

## Acquisition Modes

- `BioGRID`, `STRING`, `IntAct`, `ELM`, `SABIO-RK`, and `Q9UCM0` AlphaFold are queued as `download`.
- `PROSITE` is queued as `copy_from_bio_agent_lab` because it already exists in the promoted procurement mirror.
- `UniProt` TrEMBL is queued as `kept_lazy` so the reviewed Swiss-Prot spine stays stable.
- `Q9UCM0` PPI validation and the ligand rescue bundle are `indexed_only` because they are downstream validation/extraction steps over already available local sources.

## Deferred

- `Mega Motif Base` and `Motivated Proteins` are deferred as lazy motif gaps.

## Readout

The queue is breadth-first at the top, then depth-focused at the packet level. If we execute in this order, the next gains should come from restoring missing source classes before trying to squeeze more value out of the already-heavy structure and ligand lanes.
