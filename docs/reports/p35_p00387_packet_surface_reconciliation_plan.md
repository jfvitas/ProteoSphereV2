# P35 P00387 Packet Surface Reconciliation Plan

- Generated at: `2026-03-31T15:00:33.5307111-05:00`
- Selected gap: `ligand:P00387`
- Fresh-run-only: `yes`
- Basis: the current packet deficit dashboard, the fresh-run available payload registry, and the existing P00387 rescue artifacts

## Why This Is A Real Gap

`ligand:P00387` is already present in the fresh-run payload registry, but the preserved latest packet surface still treats it as missing. That means the evidence is real, yet the packet-surface layer has not been reconciled to it.

The important boundary is that this is not a promotion problem. It is a surface-projection problem.

## What The Repo Already Proves

- The fresh-run available payload registry contains `ligand:P00387`.
- The P00387 local ChEMBL rescue brief marks the lane as `local_rescue_candidate`.
- The P00387 extraction contract is `ready_for_next_step`.
- The latest-limited packet deficit dashboard still lists `ligand:P00387` among the unresolved refs.

## Concrete Reconciliation Step

The narrowest truthful next step is to add or reuse a fresh-run-only packet-surface projection that consumes the existing P00387 ligand payload artifacts and emits a run-scoped packet-surface overlay for `packet-P00387`.

That step must:

- read the existing P00387 ligand payload and rescue artifacts
- surface `ligand:P00387` in the fresh-run packet view
- leave `data/packages/LATEST.json` untouched
- keep the latest-promotion guard intact

## Success Criteria

- Fresh-run packet surfaces show `ligand:P00387` as present
- The preserved latest remains unchanged until a later guarded promotion
- Reports can clearly distinguish fresh-run payload presence from latest-preserved deficit state

## Not The Goal

- Do not weaken the latest-promotion guard
- Do not write a fake packet completion
- Do not claim the protected latest has changed
- Do not infer completion from the ChEMBL evidence alone

## Evidence Anchors

- [`packet_deficit_dashboard.json`](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [`available_payloads.generated.json`](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/available_payloads.generated.json)
- [`local_bridge_ligand_payloads.real.json`](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json)
- [`p34_p00387_fresh_run_ligand_blocker.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_p00387_fresh_run_ligand_blocker.json)
- [`p34_p00387_local_chembl_rescue_brief.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_p00387_local_chembl_rescue_brief.json)
- [`p34_p00387_ligand_extraction_contract.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_p00387_ligand_extraction_contract.json)

## Bottom Line

P00387 is evidence-complete for planning, but not yet surface-reconciled for the preserved latest view. The safe next move is a fresh-run-only packet-surface projection, not a latest rewrite.
