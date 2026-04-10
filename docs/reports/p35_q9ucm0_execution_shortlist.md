# P35 Q9UCM0 Execution Shortlist

- Generated at: `2026-03-31T15:06:18.1099704-05:00`
- Scope: next repo-local acquisition or transformation actions for `Q9UCM0`
- Fresh-run-only: `yes`
- Basis: the Q9UCM0 blocker follow-up and the acquisition/materialization matrix

## Shortlist

1. `structure:Q9UCM0`
   - Action type: acquisition
   - Expected payoff: high
   - Evidence quality: medium-high
   - Truth-safety: high
   - Most credible route: AlphaFold DB explicit accession probe, then RCSB/PDBe re-probe if AlphaFold stays empty
   - Why first: it is the cheapest truthful test of whether Q9UCM0 can gain a structure anchor at all.

2. `ligand:Q9UCM0`
   - Action type: acquisition
   - Expected payoff: medium
   - Evidence quality: medium
   - Truth-safety: high
   - Most credible route: BindingDB/ChEMBL accession-safe probe, then fresh accession-safe acquisition only if the local probe stays empty
   - Why second: the repo has ligand inventories, but current Q9UCM0 probes are empty.

3. `ppi:Q9UCM0`
   - Action type: acquisition
   - Expected payoff: medium-low
   - Evidence quality: low
   - Truth-safety: high
   - Most credible route: guarded BioGRID first-wave procurement, then STRING if BioGRID remains empty
   - Why third: this is the highest-cost lane and the current evidence is the weakest.

4. `packet-surface projection for Q9UCM0`
   - Action type: transformation
   - Expected payoff: high if a payload lands
   - Evidence quality: contingent
   - Truth-safety: high
   - Most credible route: reconcile a fresh-run payload overlay into packet views once a canonical Q9UCM0 payload exists
   - Why fourth: it is the first useful local transformation, but it is blocked until an accession-clean payload appears.

## What This Is Not

- It is not a rescue claim.
- It does not touch the canonical or packet latest surfaces.
- It does not promote alias-only or empty-source evidence to truth.

## Evidence Anchors

- [`p35_q9ucm0_acquisition_materialization_matrix.json`](/D:/documents/ProteoSphereV2/artifacts/status/p35_q9ucm0_acquisition_materialization_matrix.json)
- [`p35_q9ucm0_blocker_followup.json`](/D:/documents/ProteoSphereV2/artifacts/status/p35_q9ucm0_blocker_followup.json)
- [`q9ucm0_acquisition_proof.json`](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_proof.json)
- [`q9ucm0_acquisition_requirements.json`](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_requirements.json)
- [`available_payloads.generated.json`](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/available_payloads.generated.json)
- [`local_bridge_ligand_payloads.real.json`](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json)

## Boundary

This shortlist is fresh-run-only and report-only. It ranks only truthful next steps and keeps the latest-promotion guardrails untouched.
no latest promotion is attempted here.
