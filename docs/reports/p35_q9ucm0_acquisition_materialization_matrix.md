# P35 Q9UCM0 Acquisition / Materialization Decision Matrix

- Generated at: `2026-03-31T15:02:53.2088237-05:00`
- Scope: `Q9UCM0` only
- Fresh-run-only: `yes`
- Basis: the blocker follow-up, Q9UCM0 acquisition proof/requirements, the current deficit dashboard, and the fresh-run payload surfaces

## Bottom Line

All three remaining Q9UCM0 lanes are acquisition-bound. None is truthfully transformation-bound from the current repo evidence, because the repo does not yet contain a canonical structure payload, a canonical PPI pair, or an accession-clean ligand/assay row for Q9UCM0.

## Ranking

1. `structure:Q9UCM0`
   - Plausibility: `medium_low`
   - Next-action cost: `low`
   - Most credible route: AlphaFold DB explicit accession probe, then RCSB/PDBe re-probe if needed
   - Why: this lane has the cleanest direct accession probe path, and the current evidence already tells us the local registry is sequence-only for Q9UCM0.

2. `ligand:Q9UCM0`
   - Plausibility: `low`
   - Next-action cost: `medium`
   - Most credible route: BindingDB/ChEMBL accession-safe probe, then fresh accession-safe acquisition only if still empty
   - Why: the repo has ligand source inventories, but the current BindingDB and ChEMBL evidence is empty for Q9UCM0.

3. `ppi:Q9UCM0`
   - Plausibility: `low`
   - Next-action cost: `high`
   - Most credible route: guarded BioGRID first-wave procurement, then STRING if BioGRID remains empty
   - Why: current IntAct evidence is alias-only, and BioGRID/STRING are not present in the local inventory.

## Acquisition-Bound vs Transformation-Bound

- `structure:Q9UCM0` is acquisition-bound.
- `ligand:Q9UCM0` is acquisition-bound.
- `ppi:Q9UCM0` is acquisition-bound.

None of the three is transformation-bound under current repo artifacts. Transformation can only happen later, after a truthful payload exists.

## Evidence Anchors

- [`p35_q9ucm0_blocker_followup.json`](/D:/documents/ProteoSphereV2/artifacts/status/p35_q9ucm0_blocker_followup.json)
- [`q9ucm0_acquisition_proof.json`](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_proof.json)
- [`q9ucm0_acquisition_requirements.json`](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_requirements.json)
- [`packet_deficit_dashboard.json`](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [`p35_packet_gap_priority_ranking.json`](/D:/documents/ProteoSphereV2/artifacts/status/p35_packet_gap_priority_ranking.json)
- [`available_payloads.generated.json`](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/available_payloads.generated.json)
- [`local_bridge_ligand_payloads.real.json`](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json)

## Decision Boundary

This matrix is not a rescue claim and does not touch the preserved latest snapshot. It only clarifies which Q9UCM0 lane should be attempted first, what route is most credible, and why each lane remains acquisition-bound for now.
