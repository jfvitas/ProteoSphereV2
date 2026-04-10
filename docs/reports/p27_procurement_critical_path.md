# P27 Procurement Critical Path

## Current state

- `protein_data_scope` is now a ProteoSphere-native seed downloader:
  - default destination is inside `data/raw/protein_data_scope_seed`
  - manual-review sources are skipped by default
  - HTML landing-page placeholders are skipped by default
  - each run emits a structured JSON manifest with checksums and file sizes
  - archive extraction is path-sanitized
- Current verified seed run:
  - `prosite`
  - `pdb_chemical_component_dictionary`
- Current packet library truth:
  - `12` packets
  - `7` complete
  - `5` partial
  - deficits: `ligand 5`, `ppi 1`, `structure 1`
- Current canonical traceability truth:
  - canonical run id: `raw-canonical-20260323T181726Z`
  - canonical created at: `2026-03-23T18:17:27.433108+00:00`
  - canonical status / reason: `ready` / `all_manifest_driven_lanes_resolved`
  - bootstrap summary path: `data\raw\bootstrap_runs\LATEST.json`
- Tier 1 direct promotion truth:
  - direct pipeline status: `passed`
  - promotion status: `promoted`
  - promotion id: `protein-data-scope-seed:20260323T174627`
- Scoped post-Tier1 regression truth:
  - scoped rerun packet counts: `7` complete / `5` partial
  - scoped latest promotion state: `held`
  - scoped release-grade ready: `false`
  - race-condition caveat: older scoped artifacts under `runs/tier1_direct_validation/20260323T175411Z` still show the stale pre-fallback `3` complete / `9` partial view
  - interpretation: the current scoped Tier 1 slice is materially stronger after the bridge-ligand fallback fix, but still not complete enough to remove ligand procurement from the critical path
- Next-wave accession focus:
  - `P00387`: close `ligand`
  - `P09105`: close `ligand`
  - `Q2TAC2`: close `ligand`
  - `Q9UCM0`: close `structure`, `ligand`, and `ppi`
- Fresh targeted procurement outcome:
  - `P09105`: RCSB/PDBe remained empty as a direct rescue lane, BindingDB remained zero-hit, and IntAct was the only lane that moved, but only to a weak summary-grade `ppi` state; packet status is still `partial` because `ligand` is missing.
  - `Q2TAC2`: RCSB/PDBe remained empty as a direct rescue lane, BindingDB remained zero-hit, and IntAct was the only lane that moved, but only to a weak summary-grade `ppi` state; packet status is still `partial` because `ligand` is missing.
  - `Q9UCM0`: RCSB/PDBe remained empty, BindingDB remained zero-hit, and IntAct still resolves only to a reachable-empty/non-resolving lane, so this row remains the only scoped multi-modality hard gap.

## Remaining steps before full procurement

### 1. Tier 1 direct adapters

These are safe to automate first:

- `reactome`
- `sifts`
- `uniprot`
- `chebi`
- `prosite`
- `pdb_chemical_component_dictionary`

Required implementation before a full Tier 1 run:

- define required core files per source
- capture release stamp and retrieval metadata
- record checksums and file sizes for every artifact
- validate gzip/archive integrity where relevant
- add one parser/header smoke check per source
- publish only if required core files pass

### 2. Tier 2 guarded adapters

These are automatable, but only with snapshot pinning:

- `string`
- `biogrid`

Required implementation:

- explicit local release freeze metadata
- no direct canonical use of mutable `latest` endpoints
- fail closed on version drift or archive-name changes
- sample parser/header validation before publish

### 3. Tier 3 resolver/manual-first adapters

These cannot be bulk-procured safely yet:

- `alphafold_db`
- `intact`
- `bindingdb`
- `chembl`
- `complex_portal`
- `rnacentral`
- `interpro`

Required implementation:

- source-specific resolver step to produce concrete pinned URLs
- release-token discovery and recording
- stop conditions for landing-page drift or FTP-layout drift
- no publish unless a resolver manifest exists

### 4. Publish gate integration

Before calling procurement "finished", every source run must emit:

- `status`
- `reason`
- `release_version`
- `retrieval_mode`
- local artifact paths
- checksums
- validation summary

And every source must be classified as one of:

- `ready_for_raw_publish`
- `guarded_publish_only`
- `resolver_required`
- `manual_review_required`

### 5. Downstream validation

After Tier 1 and Tier 2 procurement stabilize:

- rebuild canonical store from frozen raw procurement
- regenerate available payload registry
- rerun selected packet materialization
- rerun packet deficit dashboard
- verify that procurement closes real modality gaps, not just disk mirrors

## Estimated development time

- Tier 1 adapter hardening and first broad run: `1-2 days`
- Tier 2 guarded adapters and freeze logic: `1 day`
- Tier 3 resolver layer: `2-4 days`
- downstream validation and packet/canonical reruns: `1-2 days`

Expected total to a trustworthy full-procurement state: `5-8 focused engineering days`, plus download wall-clock for large sources.

## Recommended execution order

1. Finish Tier 1 adapter contracts and validation gates.
2. Run Tier 1 procurement into frozen raw snapshots.
3. Build Tier 2 guarded snapshot logic.
4. Run Tier 2 guarded procurement and freeze metadata capture.
5. Build Tier 3 resolvers.
6. Resolve concrete URLs for Tier 3 sources.
7. Run downstream canonical and packet regeneration from frozen raw snapshots.
8. Recompute coverage and packet deficits.

## Immediate priority

The main blocker is not packet logic anymore; it is trustworthy raw procurement breadth and direct-source depth.
The highest-priority execution lane is:

1. Tier 1 production-safe procurement
2. Tier 2 guarded procurement
3. Tier 3 resolvers
4. packet/canonical reruns after each tranche

For the currently targeted rows, that means:

- do not spend another cycle expecting RCSB/PDBe to rescue `P09105`, `Q2TAC2`, or `Q9UCM0` without a newly pinned bridge hit
- treat BindingDB as explicitly zero-hit for these three rows until a fresh accession-scoped assay pull proves otherwise
- keep IntAct as the only moving lane in this trio, and keep its truth boundary explicit: weak summary-grade movement for `P09105` and `Q2TAC2`, reachable-empty for `Q9UCM0`
