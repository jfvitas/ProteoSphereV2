# P31 Worked Examples

This slice uses only current canonical, packet, and report artifacts to show where the summary library fuses cleanly and where it should stop short of forcing consensus.

## Strong example: P69905

P69905 is the cleanest multi-modal case in the current cohort. The packet is complete even though the cohort gate was conservative.

- [selected_cohort_materialization.current.json](/D:/documents/ProteoSphereV2/artifacts/status/selected_cohort_materialization.current.json) marks the accession as `rich_coverage` and keeps the planning estimate partial.
- [packet-p69905/packet_manifest.json](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p69905/packet_manifest.json) shows all four modalities present: sequence, structure, ligand, and ppi.
- [local_bridge_ligand_payloads.real.json](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json) resolves the ligand bridge to `CMO` with `InChIKey` and `SMILES`.
- [ppi-1.txt](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p69905/artifacts/ppi-1.txt) carries the IntAct pair rows and confidence evidence.

What is safe to fuse here is a single packet winner, because the current packet is complete and there is no competing claimant for the same field. The only dissent to retain is the conservative gap between cohort expectation and materialized packet status.

## PPI-rich example: P31749

P31749 is the best current example of a protein card that is strongly supported by PPI evidence and still has a large ligand payload attached.

- [intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json) gives the protein name, organism, sequence length, gene names, aliases, and a provenance pointer back to IntAct.
- [packet-p31749/packet_manifest.json](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p31749/packet_manifest.json) shows a complete packet with ligand, sequence, structure, and ppi present.
- [ppi-1.txt](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p31749/artifacts/ppi-1.txt) contains multiple IntAct rows, including direct interaction and physical association evidence with confidence values.
- [ligand-1.json](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p31749/artifacts/ligand-1.json) shows the BindingDB-backed ligand sweep with 3518 hits and a long affinity list.

This is a single-winner case for the core protein identity and packet shape. The remaining gaps are small but real: `taxon_id` is null, `sequence_checksum` is null, and the IntAct summary does not expose pathway references.

## Ligand-rich example: P00387

P00387 is the current example where ligand evidence is rich enough to matter, but it still should not be promoted into a fused ligand winner.

- [selected_cohort_materialization.current.json](/D:/documents/ProteoSphereV2/artifacts/status/selected_cohort_materialization.current.json) says the packet is partial and that ligand is the missing modality.
- [packet-p00387/packet_manifest.json](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p00387/packet_manifest.json) confirms the packet still lacks a ligand artifact.
- [local_chembl_rescue_brief.json](/D:/documents/ProteoSphereV2/artifacts/status/local_chembl_rescue_brief.json) gives the ChEMBL rescue signal: `CHEMBL2146`, 93 activities, 93 assays, `canonical_assay_resolution=false`, and `can_promote=false`.
- [ppi-1.txt](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-p00387/artifacts/ppi-1.txt) shows the packet is not empty overall, but the ligand claim still has no fused winner.

This is the right place to retain an alternate value instead of collapsing too early. The ChEMBL evidence is useful as a planning signal, but it should stay separate from a fused ligand field until the packet can materialize a promotable winner.

## Weak or blocked example: Q9UCM0

Q9UCM0 is the clear blocked case in the current materialization view.

- [q9ucm0_acquisition_proof.json](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_proof.json) says BindingDB hit count is zero, IntAct only yields alias-only rows, and RCSB/PDBe has no best-structure hit.
- [selected_cohort_materialization.current.json](/D:/documents/ProteoSphereV2/artifacts/status/selected_cohort_materialization.current.json) keeps only the sequence modality and marks structure, ligand, and ppi as missing.
- [packet-q9ucm0/packet_manifest.json](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-refresh/selected-cohort-refresh-20260323T1822Z/packet-q9ucm0/packet_manifest.json) matches that state exactly.

This record should stay retrieval-only. There is no safe consensus winner for the absent modalities, and the right downstream behavior is to preserve the nulls, keep the dissent markers, and trigger new acquisition.

## What These Examples Prove

The first slice is now concrete enough for implementation:

- Use a single winner when the packet is complete and the source evidence agrees.
- Keep an alternate planning signal when evidence exists but cannot yet be promoted into a fused field.
- Record dissent when the planning layer is more conservative than the materialized packet or when evidence is alias-only, empty, or missing.
- Attach provenance every time, even for the winners, so training packets can see both the fused value and the reason it was accepted.

