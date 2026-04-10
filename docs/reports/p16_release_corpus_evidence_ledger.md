# P16 Release Corpus Evidence Ledger

Date: 2026-03-22
Task: `P16-I007`
Status: `completed`

## Summary

- registry id: `release-cohort:prototype-frozen-12`
- release version: `0.9.0-prototype`
- entries: `12`
- included rows: `12`
- blocked rows: `12`
- release-ready rows: `0`
- grade counts: `{"blocked": 12}`

## Evidence Waves

- PPI wave plan: `release-ppi-wave-d529696142eb2135` with `11` direct-covered accessions, `0` breadth-covered accessions, and `1` unresolved accessions
- ligand wave plan: `release-ligand-wave:v1` with `1` assay-linked, `2` structure-linked, and `9` held sparse-gap accessions

## Top Rows

- `protein:P69905` scored `69` as `blocked`; blockers=['packet_not_materialized', 'modalities_incomplete'] evidence_lanes=['UniProt', 'InterPro', 'Reactome', 'AlphaFold DB', 'Evolutionary / MSA', 'ppi:direct_single_source', 'ligand:structure_linked']
- `protein:P68871` scored `53` as `blocked`; blockers=['packet_not_materialized', 'modalities_incomplete', 'mixed_evidence'] evidence_lanes=['UniProt', 'protein-protein summary library', 'ppi:direct_single_source', 'ligand:structure_linked']
- `protein:P31749` scored `46` as `blocked`; blockers=['packet_not_materialized', 'modalities_incomplete', 'thin_coverage'] evidence_lanes=['BindingDB', 'ppi:direct_single_source', 'ligand:assay_linked']
- `protein:P04637` scored `42` as `blocked`; blockers=['packet_not_materialized', 'modalities_incomplete', 'thin_coverage', 'ligand_gap'] evidence_lanes=['IntAct', 'ppi:direct_single_source']
- `protein:Q9NZD4` scored `40` as `blocked`; blockers=['packet_not_materialized', 'modalities_incomplete', 'thin_coverage', 'ligand_gap'] evidence_lanes=['UniProt', 'ppi:direct_single_source']

## Blocker Themes

- packet partials block all `12` rows because the current benchmark packets are still partial rather than release-grade materializations
- thin coverage remains on `10` blocked rows
- ligand gaps remain on `9` blocked rows
- PPI gaps remain on `1` blocked rows

## Truth Boundary

- This ledger is evidence-backed, but it is not a release-capable corpus declaration.
- The strongest accession remains `protein:P69905`, yet it is still blocked by packet incompleteness and missing requested modalities.
- The ledger intentionally keeps weak, thin, mixed, and sparse ligand rows blocked instead of upgrading them by inference.
