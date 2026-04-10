# P26 Source Priority Ranking

Date: 2026-03-23  
Task: `P26-A008`

## Fastest Path

The fastest route to stronger balanced multimodal training sets is not to fetch every missing source first. It is:

1. fill the curated protein-protein interaction gaps
2. exploit the large local structure, ligand, and annotation corpora that are already present but underused

## Ranked Priorities

1. `IntAct`
   Best immediate `PPI` value. It is already reachable and provides curated pair evidence that improves training usefulness faster than broad low-confidence network expansion.
2. `BioGRID`
   Next best `PPI` breadth source. It addresses the same dominant packet deficit as `IntAct` and remains missing in the local mirror.
3. `RCSB/PDBe` accession-to-structure bridge plus local `structures_rcsb`
   Best immediate `structure` uplift. The local structure mirror is already large, so the main need is honest accession and chain bridging, not raw file volume alone.
4. Local ligand stack: `PDBbind`, `BioLiP`, `ChEMBL`, `BindingDB`
   Best immediate `ligand` uplift. These are already present locally and are underused rather than absent.
5. Local annotation depth: `InterPro`, `Pfam`, `Reactome`
   Best immediate `annotation` uplift. These are the cheapest way to improve depth and balanced cohort scoring for protein-only rows.
6. `Evolutionary / MSA`
   Best next `sequence-family depth` lane once the core PPI/structure/ligand deficits are improved.
7. `DisProt`
   Useful selective disorder and functional annotation lane, but accession coverage is uneven.
8. `STRING`
   Useful contextual `PPI` breadth, but lower priority than curated `IntAct` and `BioGRID` for canonical training evidence.

## Why This Order

- Current packet deficits are dominated by missing `PPI`, missing `structure`, and missing `ligand`.
- Curated `PPI` expansion improves pair-aware training breadth fastest.
- Structure and ligand breadth are already partly available in local corpora, so exploitation is higher leverage than new procurement there.
- Annotation depth helps balanced scoring and cohort diversity, but it does not replace missing `PPI` and `ligand` lanes.

## References

- [training_packet_audit.md](/D:/documents/ProteoSphereV2/docs/reports/training_packet_audit.md)
- [data_inventory_audit.md](/D:/documents/ProteoSphereV2/docs/reports/data_inventory_audit.md)
- [bio_agent_lab_source_inventory.md](/D:/documents/ProteoSphereV2/docs/reports/bio_agent_lab_source_inventory.md)
- [local_online_join_expansion.md](/D:/documents/ProteoSphereV2/docs/reports/local_online_join_expansion.md)
- [missing_source_live_probe_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/missing_source_live_probe_matrix.md)
- [p13_remaining_corpus_gaps.md](/D:/documents/ProteoSphereV2/docs/reports/p13_remaining_corpus_gaps.md)
