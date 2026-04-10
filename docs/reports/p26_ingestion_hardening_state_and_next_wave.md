# P26 Ingestion Hardening State And Next Wave

Date: 2026-03-23  
Scope: current ingestion hardening state, truthful packet and library deficits, and the highest-yield next coding wave.

## Current Hardening State

The ingestion stack is materially stronger than it was before the latest `P26` tranche.

- Raw acquisition is manifest-driven for the currently wired online sources, with `6/6` online source lanes mirrored and `39` local `bio-agent-lab` sources registered in [data_inventory_audit.md](/D:/documents/ProteoSphereV2/docs/reports/data_inventory_audit.md).
- Corpus expansion and balanced planning are no longer just ideas. The registry and balanced-plan surfaces are now real implementation paths, and selected-cohort packets are materialized under [data/packages/LATEST.json](/D:/documents/ProteoSphereV2/data/packages/LATEST.json).
- Packet truthfulness improved: the current selected cohort is explicitly reported as `7` complete and `5` partial in [p26_selected_packet_materialization.md](/D:/documents/ProteoSphereV2/docs/reports/p26_selected_packet_materialization.md) and [packet_deficit_dashboard.md](/D:/documents/ProteoSphereV2/docs/reports/packet_deficit_dashboard.md).
- Canonical traceability is now operator-usable at the top level: [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) exposes canonical `run_id`, `created_at`, `bootstrap_summary_path`, `canonical_root`, and `output_paths`.
- Local summary-library enrichment is now real for at least two lanes:
  - Reactome pathway summaries in [reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json)
  - IntAct probe and pair summaries in [intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json)

## Truthful Remaining Deficits

The current bottleneck is no longer raw file presence. It is the gap between available corpora and robust packet/library materialization.

### Packet Deficits

The current selected-cohort packet truth is:

- `12` packets total
- `7` complete
- `5` partial
- missing modalities:
  - `ligand`: `5`
  - `structure`: `1`
  - `ppi`: `1`

Highest-leverage remaining packet gaps from [packet_deficit_dashboard.md](/D:/documents/ProteoSphereV2/docs/reports/packet_deficit_dashboard.md):

- `Q9UCM0` is still missing `structure`, `ligand`, and `ppi`
- `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4` are still missing `ligand`
- the remaining packet layer is materially stronger than before; the next wave should focus on these bounded closure targets rather than reopening broad assay-truth concerns

### Canonical / Ingestion Deficits

The canonical layer is still much narrower than the procurement layer, even though the top-level traceability is now much better.

- [data/canonical/LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) currently reports `11` proteins, `4124` ligands, `5138` assays, and `0` structures, with `0` assay unresolved cases.
- The canonical latest is now directly traceable as run `raw-canonical-20260323T181726Z`, created `2026-03-23T18:17:27.433108+00:00`, sourced from `data\raw\bootstrap_runs\LATEST.json`, and written under `data\canonical\runs\raw-canonical-20260323T181726Z\...`.
- That means the ingestion stack is materially stronger on the assay lane, and the remaining under-materialization pressure is now more concentrated in structure and packet-ready modality exploitation.
- The main architecture gap remains the missing extracted/query tier between raw manifests and canonical materialization, as summarized in [p26_bio_agent_lab_ingestion_pattern_map.md](/D:/documents/ProteoSphereV2/docs/reports/p26_bio_agent_lab_ingestion_pattern_map.md).

### Library Deficits

The summary-library layer is real, but still thin and lane-specific.

- Reactome local summaries currently cover `4` protein records in [reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json).
- IntAct local summaries currently cover `4` records total in [intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json), with `P04637` still only `reachable_empty` under the current non-self rule.
- Ligand, motif, and broader pair/library views are still not materialized at comparable depth.

## Recommended Next Coding Wave

The next wave should be a single focused ingestion-to-packet exploitation wave, not another broad audit.

### Priority 1: Build the ingestion control plane

Add the missing control artifacts first:

- unified source lifecycle and query-readiness artifact
- raw acquisition ledger keyed by accession, pair, ligand, and source record id
- extracted/query tier ahead of canonical materialization

This is the shortest path to turning the existing local corpora into packet-safe inputs.

### Priority 2: Exploit the current corpora to close the remaining packet gaps

Target the exact remaining deficits:

- `P00387` ligand closure
- `P09105` ligand closure
- `Q2TAC2` ligand closure
- `Q9UCM0` structure + ligand + `ppi` closure

These are the highest-yield real-data wins still left in the selected cohort.

### Priority 3: Publish package and release-grade readiness artifacts

After the above lands, add:

- package/training manifest for `data/packages`
- split diagnostics for the materialized cohort
- one release-bundle manifest tying canonical, source state, packet state, and split state together

## Bottom Line

ProteoSphere is now past the "do we have enough data at all?" stage. The truthful state is:

- procurement is strong enough
- packet materialization is working, but still incomplete
- summary-library materialization is real, but still narrow
- the next win comes from better ingestion control artifacts plus targeted exploitation of the already-present corpora

That is the best next wave because it improves both actual packet completeness and the trust surface around how those packets were built.
