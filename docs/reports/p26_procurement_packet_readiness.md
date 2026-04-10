# P26 Procurement And Packet Readiness

Date: 2026-03-23  
Task: `P26-I007`

## Verdict

Procurement breadth is now strong enough to support a serious expansion wave, and packet readiness is materially better than the earlier thin-slice state, but the remaining gaps are now very specific rather than broad.

The strongest current truth is:

- source procurement is no longer the main blocker by itself
- corpus expansion and packet materialization are now implemented as code paths
- actual materialized packet quality in the selected cohort is now `7` complete / `5` partial
- the next urgent step is to close the remaining targeted packet gaps while expanding beyond the frozen 12-accession cohort

## What Is Live Right Now

### Source Procurement

The generated source coverage matrix in `artifacts/status/source_coverage_matrix.json` shows:

- `42` tracked sources
- `33` present
- `2` partial
- `7` missing
- `34` online-downloaded raw files
- `186826` locally present files
- about `153.6 GB` already present in the local registry

The highest-coverage sources are currently:

- `bindingdb`
- `uniprot`
- `alphafold`
- `alphafold_db`
- `biolip`
- `chembl`

The strongest procurement-priority gaps from the matrix and the source-priority ranking are:

1. `BioGRID`
2. `STRING`
3. `PDBBind` completion / exploitation
4. motif and pattern gaps such as `ELM` and `PROSITE`

### Corpus Expansion Readiness

The new corpus registry builder is code-complete and test-verified. A direct read from the registry summary shows:

- `25` candidate rows across the currently wired source landscape
- candidate kinds:
  - `8` protein
  - `5` pair
  - `9` ligand
  - `3` annotation
- effective status by candidate kind:
  - protein: `8 present`
  - pair: `3 present`, `2 missing`
  - ligand: `7 present`, `2 partial`
  - annotation: `3 present`

This is an important improvement over the older repo state because we now have a planning surface that separates protein, pair, ligand, and annotation candidate supply instead of treating procurement as one undifferentiated bucket.

### Packet Readiness

The current operator-facing packet truth is now the selected cohort under `data/packages/LATEST.json` and `artifacts/status/packet_deficit_dashboard.json`:

- `12` packets total
- `7` complete
- `5` partial
- `0` unresolved

Missing-modality counts remain the core issue:

- missing `ligand`: `5`
- missing `structure`: `1`
- missing `ppi`: `1`
- missing `sequence`: `0`

That means the packet materializer is no longer just code-complete; it is already producing a mostly-usable selected cohort, and the remaining work is a bounded closure wave rather than a ground-up packet rebuild.

### Fresh Targeted Procurement Read

The newest accession-scoped procurement read tightens the remaining story for three of the five partial rows:

- `P09105`
  - RCSB/PDBe remained empty as a direct target-bound rescue lane
  - BindingDB remained empty / zero-hit
  - IntAct is the only lane that moved, but only to a weak summary-grade `ppi` state
  - result: still `partial`, with `ligand` as the only missing modality
- `Q2TAC2`
  - RCSB/PDBe remained empty as a direct target-bound rescue lane
  - BindingDB remained empty / zero-hit
  - IntAct is the only lane that moved, but only to a weak summary-grade `ppi` state
  - result: still `partial`, with `ligand` as the only missing modality
- `Q9UCM0`
  - RCSB/PDBe remained empty
  - BindingDB remained empty / zero-hit
  - IntAct remained the only changing lane in scope, but it is still non-resolving at the curated cohort level
  - result: still `partial`, with `structure`, `ligand`, and `ppi` all missing

That is important because it narrows the next wave: `P09105` and `Q2TAC2` are no longer broad mystery rows, while `Q9UCM0` remains the only row in this subset that still needs full multi-modality rescue.

### Canonical Traceability

The canonical layer now has enough top-level traceability to surface directly in operator reporting:

- canonical run id: `raw-canonical-20260323T181726Z`
- canonical created at: `2026-03-23T18:17:27.433108+00:00`
- canonical status / reason: `ready` / `all_manifest_driven_lanes_resolved`
- bootstrap summary path: `data\raw\bootstrap_runs\LATEST.json`
- canonical root: `data\canonical`
- canonical output paths:
  - `data\canonical\runs\raw-canonical-20260323T181726Z\canonical_store.json`
  - `data\canonical\runs\raw-canonical-20260323T181726Z\sequence_result.json`
  - `data\canonical\runs\raw-canonical-20260323T181726Z\structure_result.json`
  - `data\canonical\runs\raw-canonical-20260323T181726Z\assay_result.json`

## Capability Matrix

| Area | Current state | Honest read |
| --- | --- | --- |
| Source coverage matrix | implemented and generated | usable now for procurement planning |
| Corpus registry builder | implemented and test-verified | ready to drive expansion planning |
| Balanced cohort scorer | implemented and test-verified | scoring logic exists, but no persisted large-cohort execution artifact was found in-tree yet |
| Training packet materializer | implemented and test-verified | writes `data/packages` conservatively and now yields a live `7` complete / `5` partial selected cohort |
| Source priority ranking | written and grounded in current audits | gives a credible next-source order |

That distinction matters. We now have the tooling needed to move fast, but not all of the corresponding large real-data outputs have been run and committed yet.

## Balanced-Cohort Read

The new balanced cohort scorer is directionally sane on the current frozen packet audit. A direct scoring read over the existing packet rows ranked:

1. `P69905`
2. `P68871`
3. `P00387`
4. `P04637`
5. `P31749`

That ranking is useful as a sanity check, but it should not be mistaken for a release-grade balanced cohort. It is still bounded by the same thin live packet slice:

- `P69905` leads because it is the only multilane row with meaningful depth
- `P68871` remains mixed-evidence
- the rest of the top five are still thin single-lane or near-thin rows

So the scoring system is ready, but the candidate pool still needs to widen materially before the output can be called robust.

## What Is Actually Blocking Well-Balanced Training Sets

1. The canonical store is now traceable and assay-stable, but still structurally narrow.
   `data/canonical/LATEST.json` currently contains `11` proteins, `4124` ligands, `5138` assays, and `0` structures with `0` assay unresolved cases. That is a real improvement, but it still means structure-ready canonical breadth is lagging procurement breadth.

2. The remaining packet gaps are concentrated in one multi-modality row plus a few ligand-only rows.
   `Q9UCM0` still lacks `structure`, `ligand`, and `ppi`, while `P00387`, `P09105`, and `Q2TAC2` each need only ligand closure.

3. Structure and ligand breadth are present in local corpora but under-materialized into packets.
   This is now more of an execution and bridging problem than a raw storage problem.

4. `data/packages` is real, but not yet broad enough to call release-grade.
   The selected cohort latest is useful and mostly complete, but it is still only a 12-packet slice.

## Priority Order

Using the current procurement matrix together with `p26_source_priority_ranking.md`, the best next execution order is:

1. close the bounded selected-cohort packet gaps first
   Resolve ligand coverage for `P00387`, `P09105`, and `Q2TAC2`, then treat `Q9UCM0` as the only remaining scoped multi-modality closure target. The fresh procurement read now makes that prioritization more confident: RCSB and BindingDB are not the active movers on this trio, while IntAct only changed the pair side.

2. exploit local structure and ligand corpora second
   Use the existing `structures_rcsb`, `PDBBind`, `BioLiP`, `ChEMBL`, and `BindingDB` local assets instead of waiting on more raw-download volume.

3. expand curated `PPI` coverage third
   Target `IntAct` exploitation and `BioGRID` procurement before broad low-confidence network widening.

4. deepen annotation support after that
   `InterPro`, `Pfam`, and `Reactome` are already strong leverage for diversity and balanced scoring.

5. fill motif and residual sequence-family gaps after that
   `ELM`, `PROSITE`, and deeper evolutionary lanes help quality, but they are not the first bottleneck compared with `PPI`, structure, and ligand coverage.

## Next Balanced-Cohort Execution Wave

The next wave should be concrete and bounded:

1. export a persisted corpus-registry artifact from the current raw and local manifests
2. close the next-wave selected-cohort rows:
   - `P00387` -> ligand
   - `P09105` -> ligand
   - `Q2TAC2` -> ligand
   - `Q9UCM0` -> structure + ligand + ppi
3. score the expanded registry for a target cohort requiring:
   - `sequence` mandatory
   - at least one of `structure`, `ligand`, or `ppi`
   - leakage-safe diversity across evidence modes and buckets
4. materialize packets for the top tranche into `data/packages`
5. rerun packet audit on those new package outputs, not just on the legacy benchmark sidecars
6. only then widen benchmark or training claims

## Bottom Line

The project is in a much better place than it was before `P26`.

We now have:

- a real source procurement matrix
- a real corpus expansion registry builder
- a real balanced cohort scorer
- a real packet materializer
- a ranked source-priority strategy
- a traceable canonical latest with explicit run id, bootstrap path, and output paths

What we do **not** yet have is a broad repo-persisted expanded packet corpus proving that those new capabilities have already produced strong balanced multimodal training sets at scale.

So the immediate recommendation is simple: stop treating procurement as the sole blocker, and aggressively execute the new expansion -> scoring -> packet-materialization loop on real corpora next.
