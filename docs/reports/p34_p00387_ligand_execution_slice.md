# P34 P00387 Ligand Execution Slice

- Generated at: `2026-03-31T14:41:05.9810046-05:00`
- Basis: [`p34_packet_gap_current_state_ranking.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_packet_gap_current_state_ranking.json)
- Selected gap: `ligand:P00387`

## Why This Slice

P00387 is the most realistic next local ligand rescue among the current local candidates. The local ChEMBL evidence is accession-scoped, the rescue brief already names a concrete target hit, and the lane can be executed without speculative procurement.

## Exact Local Sources

- [`p00387_local_chembl_rescue.json`](/D:/documents/ProteoSphereV2/artifacts/status/p00387_local_chembl_rescue.json)
- [`local_chembl_rescue_brief.json`](/D:/documents/ProteoSphereV2/artifacts/status/local_chembl_rescue_brief.json)
- [`manifest.json`](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/chembl/manifest.json)
- [`inventory.json`](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/chembl/inventory.json)
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`

## Execution Shape

1. Read the P00387 rescue summary and confirm the lane is ligand-only.
2. Materialize the ligand payload from the local ChEMBL sqlite source.
3. Refresh the run-scoped packet materialization and available-payload surfaces only.
4. Record the result in the packet deficit and reporting surfaces.

## Expected `source_ref`

`ligand:P00387`

## Success Criteria

- A provenance-safe P00387 ligand payload appears, or a truthful null result is recorded with the same evidence trail.
- The output stays accession-scoped and tied to the local ChEMBL hit.
- Only the freshest run-scoped surfaces change.
- [`LATEST.json`](/D:/documents/ProteoSphereV2/data/packages/LATEST.json) is not rewritten by this slice.
- Any later promotion must still pass the existing latest-promotion guard and release-grade checks.

## Promotion Boundary

This slice updates the freshest run only. It could only qualify for latest promotion later if downstream work produces a release-grade-ready packet and the normal promotion guard passes. The slice itself does not promote anything.
