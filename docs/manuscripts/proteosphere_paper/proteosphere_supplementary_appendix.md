# Supplementary Appendix: ProteoSphere Manuscript Draft

## Appendix Overview

This appendix accompanies the main manuscript draft, **ProteoSphere: A Compact Evidence Warehouse and Dataset Reviewer for Biomolecular Interaction Machine Learning**. Its purpose is to make the paper easier to inspect and easier to revise toward submission. The appendix is intentionally practical. It records the evidence surfaces used in the draft, summarizes the Tier 1 proof set, and states the key truth boundaries that should remain in place during journal-facing revision.

## A. Core Claim Boundaries

The manuscript is currently strongest when it keeps the following boundaries explicit:

- ProteoSphere is **operationally effective for warehouse-first review**, but it is **not yet a full evidence-equivalent replacement** for every raw artifact surface.
- The paper supports a **proof-backed sample of recurring failure modes**, not a field-wide prevalence estimate.
- The strongest Tier 1 evidence is currently concentrated in **protein-ligand / DTA and PDBbind-style** benchmark families, with a smaller **protein-protein** subset.
- The flagship cases should remain separated into:
  - paper-specific split bugs;
  - inherited benchmark-family failures;
  - invalid external-validation cases;
  - mitigation-aware controls.

## B. Current Storage And Source-Estate Framing

The broader tracked source estate report currently records 53 tracked sources, of which 48 are present, 2 are partial, and 3 are missing, with 324,755,949,775 present bytes in that tracked set ([source_coverage_matrix.md](D:\documents\ProteoSphereV2\docs\reports\source_coverage_matrix.md)). The manuscript package also includes a current live storage ledger generated at build time, which measures the present local footprint of the warehouse root and selected raw or mirror roots in the active environment ([proteosphere_paper_storage_ledger.md](D:\documents\ProteoSphereV2\docs\reports\proteosphere_paper_storage_ledger.md)).

The manuscript should continue to avoid the unsupported exact phrase “more than 2 TB condensed to about 25 GB” unless a dedicated release-bound proof artifact is created for that exact number. The present draft instead uses a stronger and safer claim: ProteoSphere places a compact warehouse-first evidence surface in front of a multi-hundred-gigabyte to multi-terabyte local source estate.

## C. Tier 1 Paper Table

{{TIER1_TABLE}}

## D. Controls Included In The Current Review Package

The manuscript currently uses the following control papers to demonstrate that ProteoSphere is not merely a negative filter:

- RAPPPID
- GraphPPIS
- BatchDTA
- HGRL-DTA
- NHGNN-DTA
- PotentialNet
- Deep Fusion Inference
- DTA-OM
- TEFDTA
- DCGAN-DTA
- HAC-Net

These controls were carried forward from the local deep-review and recent-expansion artifacts and should remain visible in the paper because they make the narrative more scientifically fair.

## E. Figure Provenance Notes

The main manuscript uses generated figures rather than publisher-extracted paper figures as the primary visual surface. This is deliberate. The generated figures reflect the current local evidence more directly and avoid conflating the paper draft with copyrighted publisher layouts.

The only direct case-study structure visual currently used is the ProteoSphere-generated Struct2Graph overlay:

- [4EQ6_train_test_overlay.png](D:\documents\ProteoSphereV2\artifacts\status\struct2graph_overlap\4EQ6_train_test_overlay.png)

All other figures in the manuscript are generated from local machine-readable artifacts or local reports during the manuscript build.

## F. Strongest Figures For A Submission-Oriented Revision

The best figure set to preserve in later journal-facing versions is:

1. system overview;
2. source-estate / compact-warehouse footprint figure;
3. review-logic decision ladder;
4. Tier 1 landscape overview;
5. flagship case-study panel;
6. control/comparison panel.

## G. Recommended Revision Priorities Before External Submission

If this draft moves beyond PI review toward journal submission, the highest-value upgrades are:

- add 3 to 5 more direct hard-failure cases outside the current DTA and PDBbind concentration;
- add a short manual validation appendix for one or two flagship cases;
- convert local evidence citations into journal-style references and supplementary note labels;
- tighten the discussion so benchmark-family inheritance failures are clearly separated from paper-specific split bugs;
- preserve the positive, constructive tone toward audited papers.

## H. Manuscript Package Contents

The current manuscript package should include:

- main manuscript draft;
- supplementary appendix;
- PI briefing note;
- claim ledger;
- figure manifest;
- generated PDF outputs for the manuscript, supplement, and PI memo.
