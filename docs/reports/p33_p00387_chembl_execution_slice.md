# P33 P00387 ChEMBL Execution Slice

Generated at: `2026-03-31T13:17:01.3425736-05:00`

This is the first concrete execution slice from the current packet-gap acquisition plan. The selected gap is the top-ranked actionable item, `P00387` ligand, and it can be advanced truthfully with the currently available local ChEMBL evidence.

## Current Inputs

- Dashboard: [`packet_deficit_dashboard.json`](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- Local registry: [`LATEST.json`](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json)
- Acquisition plan: [`p33_packet_gap_acquisition_plan.json`](/D:/documents/ProteoSphereV2/artifacts/status/p33_packet_gap_acquisition_plan.json)

The current dashboard and registry state still support this slice:

- Packet counts: `12` total, `7` complete, `5` partial.
- Remaining deficit count: `5`.
- Highest-leverage source fix remains `ligand:P00387`.
- The local registry keeps `chembl` present, so the ChEMBL lane is actually executable.

## What Was Materialized

- Plan rank: `1`
- Accession: `P00387`
- Modality: `ligand`
- Plan route: `ChEMBL rescue brief`
- Execution state: `executed_local_materialization`

## Evidence Used

- [p33_packet_gap_acquisition_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/p33_packet_gap_acquisition_plan.json)
- [p00387_ligand_extraction_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p00387_ligand_extraction_contract.json)
- [local_chembl_rescue_brief.json](/D:/documents/ProteoSphereV2/artifacts/status/local_chembl_rescue_brief.json)

The current local evidence is consistent across those artifacts:

- The packet already has sequence and structure.
- The ligand lane is the remaining gap.
- The local ChEMBL rescue brief reports one target hit.
- The extraction contract is `ready_for_next_step`.
- The selected target is `CHEMBL2146` for `NADH-cytochrome b5 reductase`.
- The activity count is `93`.

## Why This Slice Is Truthful

This slice does not claim packet completion or canonical assay resolution. It only materializes the top-ranked ligand rescue candidate from the current plan, using existing local ChEMBL evidence and the existing P00387 extraction contract.

## Next Step

Use this ligand evidence as the input to the next procurement and planning pass for the packet gap queue. Do not promote the packet based on this slice alone.
