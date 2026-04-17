# Paper Split Evaluation

- Generated at: 2026-04-13T17:48:40.296757+00:00
- Warehouse root: `D:\ProteoSphere\reference_library`
- Default view: `best_evidence`

## Summary Table

| Paper | Verdict | Project status | Recommended policy |
| --- | --- | --- | --- |
| `zhang2012preppi` | incomplete because required evidence is missing | `blocked_pending_mapping` | `paper_faithful_external` |
| `sun2017sequence` | misleading / leakage-prone | `unsafe_for_training` | `accession_grouped` |
| `du2017deepppi` | incomplete because required evidence is missing | `blocked_pending_mapping` | `accession_grouped` |
| `hashemifar2018dppi` | incomplete because required evidence is missing | `blocked_pending_mapping` | `accession_grouped` |
| `chen2019siamese_rcnn` | incomplete because required evidence is missing | `blocked_pending_mapping` | `accession_grouped` |
| `sledzieski2021dscript` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |
| `szymborski2022rapppid` | audit-useful but non-canonical | `audit_only` | `uniref_grouped` |
| `baranwal2022struct2graph` | misleading / leakage-prone | `unsafe_for_training` | `accession_grouped` |
| `gainza2020masif` | incomplete because required evidence is missing | `blocked_pending_mapping` | `paper_faithful_external` |
| `dai2021geometric_interface` | incomplete because required evidence is missing | `blocked_pending_mapping` | `paper_faithful_external` |
| `xie2022interprotein_contacts` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |
| `tubiana2022scannet` | audit-useful but non-canonical | `audit_only` | `uniref_grouped` |
| `krapp2023pesto` | incomplete because required evidence is missing | `blocked_pending_mapping` | `paper_faithful_external` |
| `yugandhar2014affinity` | misleading / leakage-prone | `unsafe_for_training` | `accession_grouped` |
| `rodrigues2019mcsm_ppi2` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |
| `wang2020nettree` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |
| `zhang2020mutabind2` | incomplete because required evidence is missing | `blocked_pending_mapping` | `accession_grouped` |
| `zhou2024ddmut_ppi` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |
| `bryant2022af2_ppi` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |
| `gao2022af2complex` | audit-useful but non-canonical | `audit_only` | `paper_faithful_external` |

## audit-useful but non-canonical

- `sledzieski2021dscript`: Keep the paper in a `paper_faithful_external` audit lane. Build an Ensembl/FlyBase-to-UniProt bridge before comparing it with ProteoSphere-native accession- or UniRef-grouped evaluations. Blockers: published D-SCRIPT split files are keyed by Ensembl/FlyBase protein identifiers that the condensed warehouse does not currently bridge to `protein_ref` or UniProt accessions. Warnings: none.
- `szymborski2022rapppid`: Keep the released C1/C2/C3 splits as audit lanes and rebuild any governing comparison under `uniref_grouped` once STRING/Ensembl identifiers are bridged into warehouse proteins. Blockers: published RAPPPID split artifacts are keyed by STRING/Ensembl protein identifiers that the condensed warehouse does not currently bridge to canonical `protein_ref` rows. Warnings: STRING is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `xie2022interprotein_contacts`: Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `tubiana2022scannet`: Keep the paper split as a `paper_faithful_external` audit lane and compare it against a ProteoSphere-native `uniref_grouped` rebuild when roster evidence becomes available. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `rodrigues2019mcsm_ppi2`: Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `wang2020nettree`: Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `zhou2024ddmut_ppi`: Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `bryant2022af2_ppi`: Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `gao2022af2complex`: Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.

## misleading / leakage-prone

- `sun2017sequence`: Do not accept the reported split as training-governing. Re-express the benchmark under `accession_grouped` before any comparison is treated as meaningful. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: STRING is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `baranwal2022struct2graph`: Do not use the paper-faithful split for training claims. Rebuild the benchmark under an accession-grouped or stronger structure-aware grouping policy before treating any performance comparison as canonical. Blockers: the repository exposes split-construction logic, but it does not provide a saved published split roster or seed-stable assignment artifact for the exact paper run. Warnings: PDBBind is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `yugandhar2014affinity`: Do not accept the reported split as training-governing. Re-express the benchmark under `accession_grouped` before any comparison is treated as meaningful. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: PDBBind is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..

## incomplete because required evidence is missing

- `zhang2012preppi`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `paper_faithful_external` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: STRING is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `du2017deepppi`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `accession_grouped` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: STRING is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `hashemifar2018dppi`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `accession_grouped` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: STRING is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `chen2019siamese_rcnn`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `accession_grouped` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: STRING is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing..
- `gainza2020masif`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `paper_faithful_external` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `dai2021geometric_interface`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `paper_faithful_external` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `krapp2023pesto`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `paper_faithful_external` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.
- `zhang2020mutabind2`: Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `accession_grouped` rather than trusting the paper split verbatim. Blockers: paper-specific train/test membership roster is absent from the condensed warehouse. Warnings: none.

## Warehouse Sufficiency Notes

- The condensed warehouse does not expose a DOI-indexed paper benchmark membership surface, so paper-specific train/test rosters could not be reconstructed from best_evidence alone.
- IntAct and STRING are present as promoted sources, but the current best_evidence `protein_protein_edges` table only materializes `pdbbind` and `elm_interaction_domains` rows.
- Structure families are well represented, but interface/contact benchmark labels such as CASP-CAPRI and PPDB5 are not materialized as paper-membership tables.
- Mutation support exists in `protein_variants`, but named cohorts such as AB-Bind S645 and SM1124 are not represented as explicit warehouse splits.
- Even when paper supplements were recovered, some released rosters were keyed by Ensembl/FlyBase or other non-warehouse identifiers, so overlap and admissibility checks remain blocked until identifier bridges are materialized.

## Raw/Archive Fallback

- No raw/archive fallback was required for this report.
- If future roster reconstruction is needed, any raw/archive path must be resolved through `source_registry.json` and remain non-governing until validated.
- Supplemental GitHub or Zenodo release artifacts were used for selected papers, but these were treated as audit-supporting evidence rather than governing warehouse truth.
