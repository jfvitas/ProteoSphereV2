# ProteoSphere Literature Hunt: Confirmed Dataset-Quality Failures

## Executive Summary

This hunt reviewed `19` candidate papers and promoted `15` to the confirmed shortlist. The shortlist includes `1` direct split failures, `1` blocked external-validation stories, and `13` benchmark-dependence cases where the paper is publishable and reproducible but still too weak for strong generalization claims under ProteoSphere logic.

The core pattern is that respected, peer-reviewed papers can still fail dataset review for different reasons. Some fail because the released split mechanism itself leaks. Others fail because the claimed external set overlaps biologically with training. A large third group fails more quietly: the paper reports large gains, but almost all evaluation remains trapped inside one inherited benchmark family.

## Best Examples For Publication

- `d2cp05644e_2023` (Physical Chemistry Chemical Physics, 2023): An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties — All three validation lanes fail clean external-benchmark expectations under ProteoSphere logic: the PDBbind panel shows direct protein reuse, the nanobody panel reuses a central antigen target, and the metadynamics panel contains severe exact or near-exact reuse.
- `baranwal2022struct2graph` (BMC Bioinformatics, 2022): Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions — Released split logic permits train/test reuse strongly enough that ProteoSphere would block the paper split for training claims.
- `meg_ppis2024` (Bioinformatics, 2024): MEG-PPIS: a fast protein-protein interaction site prediction method based on multi-scale graph information and equivariant graph neural network — Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- `agat_ppis2023` (Briefings in Bioinformatics, 2023): AGAT-PPIS — The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- `gte_ppis2025` (Briefings in Bioinformatics, 2025): GTE-PPIS — The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- `hssppi2025` (Briefings in Bioinformatics, 2025): HSSPPI — The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- `asce_ppis2025` (Bioinformatics, 2025): ASCE-PPIS — The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- `mvso_ppis2025` (Bioinformatics, 2025): MVSO-PPIS — The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.

## Confirmed Red Flag

### Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions

- DOI: https://doi.org/10.1186/s12859-022-04910-9
- Journal: BMC Bioinformatics (2022)
- Task family: `pair_level_ppi_prediction`
- Benchmark family: `struct2graph_public_pairs`
- Issue cluster: `direct_split_failure`
- Why it is flagged: Released split logic permits train/test reuse strongly enough that ProteoSphere would block the paper split for training claims.
- Claimed split: Balanced-set evaluation and fivefold cross-validation on an unbalanced set are claimed.
- Key evidence: ProteoSphere treats direct accession reuse, accession-root reuse, UniRef reuse, and shared partner/component reuse as leakage axes.
- Extra evidence: Without a paper roster, partner/component leakage cannot be enumerated concretely from the condensed warehouse.
- Consequence: Performance numbers can be inflated by direct structure or component reuse across partitions.
- ProteoSphere treatment: Do not use the paper-faithful split for training claims. Rebuild the benchmark under an accession-grouped or stronger structure-aware grouping policy before treating any performance comparison as canonical.
- Blockers: the repository exposes split-construction logic, but it does not provide a saved published split roster or seed-stable assignment artifact for the exact paper run

## Confirmed Blocked External Benchmark

### An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties

- DOI: https://doi.org/10.1039/D2CP05644E
- Journal: Physical Chemistry Chemical Physics (2023)
- Task family: `binding_affinity_regression`
- Benchmark family: `prodigy78_plus_external_panels`
- Issue cluster: `blocked_external_validation`
- Why it is flagged: All three validation lanes fail clean external-benchmark expectations under ProteoSphere logic: the PDBbind panel shows direct protein reuse, the nanobody panel reuses a central antigen target, and the metadynamics panel contains severe exact or near-exact reuse.
- Claimed split: Public materials reconstruct a 78-complex benchmark pool plus three claimed external validation panels: PDBbind-50, nanobody-47, and metadynamics-19.
- Key evidence: PDBbind-50 retains 4 direct protein overlaps against the recovered benchmark pool.
- Extra evidence: Nanobody-47 retains 1 direct protein overlaps, concentrated around reused antigen targets.
- Consequence: The paper's external validation story overstates independence and likely overstates generalization.
- ProteoSphere treatment: Treat the paper as a forensic case study. Recover the exact benchmark roster, re-split by accession or family, and keep the original external panels only as blocked audit examples.
- Blockers: The paper-internal benchmark split is still under-disclosed even though the effective benchmark pool was reconstructable from the public repository.

## Confirmed Audit-Only / Non-Canonical

### MEG-PPIS: a fast protein-protein interaction site prediction method based on multi-scale graph information and equivariant graph neural network

- DOI: https://doi.org/10.1093/bioinformatics/btae269
- Journal: Bioinformatics (2024)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- Claimed split: The paper appears to evaluate primarily on the `ppis_train335_family` benchmark family rather than on a newly released independent split.
- Key evidence: The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts.
- Extra evidence: In this study, benchmark datasets were the same as those in the previous work AGAT-PPIS, including training set (Train_335-1) and testing sets (Test_60, Test_315-28, Ubtest_31-6).
- Consequence: The paper may still be useful for within-family comparison, but not as strong evidence of external robustness.
- ProteoSphere treatment: Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence.

### AGAT-PPIS

- DOI: https://doi.org/10.1093/bib/bbad122
- Journal: Briefings in Bioinformatics (2023)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: Official repo ships explicit Train_335/Test_60/Test_315-28/UBtest_31-6 benchmark files.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### GTE-PPIS

- DOI: https://doi.org/10.1093/bib/bbaf290
- Journal: Briefings in Bioinformatics (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: Official repo releases the curated PPIS dataset files used in the paper.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### HSSPPI

- DOI: https://doi.org/10.1093/bib/bbaf079
- Journal: Briefings in Bioinformatics (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `hssppi_public_tasks`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: The paper and official release describe train/test datasets and trained models for two PPIS benchmark tasks.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Treat it as a `paper_faithful_external` audit lane or inherited benchmark family rather than a new canonical split.

### ASCE-PPIS

- DOI: https://doi.org/10.1093/bioinformatics/btaf423
- Journal: Bioinformatics (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: Official repo ships the full Train_335/Test_60/Test_315/UBtest benchmark lineage.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### MVSO-PPIS

- DOI: https://doi.org/10.1093/bioinformatics/btaf470
- Journal: Bioinformatics (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: Official repo provides the PPIS benchmark files plus processed PDB files.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### MGMA-PPIS: Predicting the protein-protein interaction site with multiview graph embedding and multiscale attention fusion

- DOI: https://doi.org/10.1093/gigascience/giaf114
- Journal: GigaScience (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- Claimed split: The paper appears to evaluate primarily on the `ppis_train335_family` benchmark family rather than on a newly released independent split.
- Key evidence: The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts.
- Extra evidence: The AGAT-PPIS dataset is derived from the GraphPPIS dataset, which includes the following subsets: 1 training set of Train_335-1 and 3 test sets of Test_315-28, Test_60-0, and Ubtest_31-6.
- Consequence: The paper may still be useful for within-family comparison, but not as strong evidence of external robustness.
- ProteoSphere treatment: Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence.

### EquiPPIS

- DOI: https://doi.org/10.1371/journal.pcbi.1011435
- Journal: PLOS Computational Biology (2023)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: EquiPPIS explicitly follows the public GraphPPIS train/test split rather than introducing a new benchmark family.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### EDG-PPIS: an equivariant and dual-scale graph network for protein-protein interaction site prediction

- DOI: https://doi.org/10.1186/s12864-025-12084-w
- Journal: BMC Genomics (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- Claimed split: The paper appears to evaluate primarily on the `ppis_train335_family` benchmark family rather than on a newly released independent split.
- Key evidence: The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts.
- Extra evidence: The dataset used in this study is the same as AGAT-PPIS, that is, Train_335 is used as the training set, and Test_60, Test_315-28, Btest_31-6, and UBtest_31-6 are used as the test sets.
- Consequence: The paper may still be useful for within-family comparison, but not as strong evidence of external robustness.
- ProteoSphere treatment: Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence.

### MIPPIS

- DOI: https://doi.org/10.1186/s12859-024-05964-7
- Journal: BMC Bioinformatics (2024)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: MIPPIS uses the public Train_335/Test_60 benchmark family; exact IDs are recoverable through the shared benchmark repos.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### EGCPPIS

- DOI: https://doi.org/10.1186/s12859-025-06328-5
- Journal: BMC Bioinformatics (2025)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: Official repo includes the train/test benchmark files together with associated dataset folders.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### GHGPR-PPIS

- DOI: https://doi.org/10.1016/j.compbiomed.2023.107683
- Journal: Computers in Biology and Medicine (2023)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: Official repo provides the shared PPIS benchmark files directly.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### GACT-PPIS

- DOI: https://doi.org/10.1016/j.ijbiomac.2024.137272
- Journal: International Journal of Biological Macromolecules (2024)
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Issue cluster: `benchmark_family_dependence`
- Why it is flagged: The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization.
- Claimed split: GACT-PPIS evaluates on the same public PPIS benchmark family rather than introducing a new split lineage.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.
- ProteoSphere treatment: Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

## Candidate Needing More Recovery

### HN-PPISP: a hybrid network based on MLP-Mixer for protein-protein interaction site prediction

- DOI: https://doi.org/10.1093/bib/bbac480
- Journal: Briefings in Bioinformatics (2023)
- Task family: `binding_site_prediction`
- Benchmark family: `dset_186_72_pdb164`
- Issue cluster: `legacy_benchmark_dependence`
- Why it is flagged: Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- Claimed split: The paper appears to evaluate primarily on the `dset_186_72_pdb164` benchmark family rather than on a newly released independent split.
- Key evidence: The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts.
- Extra evidence: These three benchmark datasets are fused as a dataset, same as the datasets in prior work, called Dset_186_72_PDB164 in this work.
- Consequence: The benchmark dependence is clear, but the exact split mechanics still need more recovery before the paper belongs on the confirmed shortlist.
- ProteoSphere treatment: Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence.
- Blockers: Exact split membership still needs local recovery or mirrored artifacts.

### DeepPPISP

- DOI: https://doi.org/10.1093/bioinformatics/btz699
- Journal: Bioinformatics (2019)
- Task family: `binding_site_prediction`
- Benchmark family: `deepppisp_186_72_164`
- Issue cluster: `legacy_benchmark_dependence`
- Why it is flagged: The paper exposes useful benchmark material, but the exact train/test membership is still not fixed enough to audit as a stable held-out split.
- Claimed split: Official repo ships the benchmark datasets and data_cache features, but the README still describes splitting the raw union yourself for the 350/70 partition.
- Key evidence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Extra evidence: The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Consequence: Any leakage or independence assessment remains partial until the exact roster is reconstructed.
- ProteoSphere treatment: Do not rely on the paper split alone. Reconstruct a fixed released roster and then reevaluate it under `accession_grouped`.
- Blockers: benchmark datasets are shipped, but the exact fixed 350/70 train/test membership is not exposed cleanly enough in the release surface

### DGCPPISP: a PPI site prediction model based on dynamic graph convolutional network and two-stage transfer learning

- DOI: https://doi.org/10.1186/s12859-024-05864-w
- Journal: BMC Bioinformatics (2024)
- Task family: `binding_site_prediction`
- Benchmark family: `dset_186_72_pdb164`
- Issue cluster: `legacy_benchmark_dependence`
- Why it is flagged: Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- Claimed split: The paper appears to evaluate primarily on the `dset_186_72_pdb164` benchmark family rather than on a newly released independent split.
- Key evidence: The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts.
- Extra evidence: To ascertain the performance of DGCPPISP at various stages of transfer learning, we perform an experiment on Dset_186_72_PDB164.
- Consequence: The benchmark dependence is clear, but the exact split mechanics still need more recovery before the paper belongs on the confirmed shortlist.
- ProteoSphere treatment: Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence.
- Blockers: Exact split membership still needs local recovery or mirrored artifacts.

### ProB-Site: Protein Binding Site Prediction Using Local Features

- DOI: https://doi.org/10.3390/cells11132117
- Journal: Cells (2022)
- Task family: `binding_site_prediction`
- Benchmark family: `dset_186_72_pdb164`
- Issue cluster: `legacy_benchmark_dependence`
- Why it is flagged: Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims.
- Claimed split: The paper appears to evaluate primarily on the `dset_186_72_pdb164` benchmark family rather than on a newly released independent split.
- Key evidence: The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts.
- Extra evidence: The study incorporated three benchmark datasets: Dset_72, Dset_186, and PDBset_164.
- Consequence: The benchmark dependence is clear, but the exact split mechanics still need more recovery before the paper belongs on the confirmed shortlist.
- ProteoSphere treatment: Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence.
- Blockers: Exact split membership still needs local recovery or mirrored artifacts.

## Benchmark-Family Clusters

- `deepppisp_186_72_164`: 1 papers
- `dset_186_72_pdb164`: 3 papers
- `hssppi_public_tasks`: 1 papers
- `ppis_train335_family`: 12 papers
- `prodigy78_plus_external_panels`: 1 papers
- `struct2graph_public_pairs`: 1 papers

## Non-Failure Controls

- `szymborski2022rapppid` (Bioinformatics, 2022): Published strict split artifacts and serves as a non-failure calibration case. Current ProteoSphere verdict: `faithful and acceptable as-is`.
- `graphppis2021` (Bioinformatics, 2021): Benchmark anchor and useful non-failure calibration case; later papers inherit its benchmark family. Current ProteoSphere verdict: `faithful and acceptable as-is`.

## Warehouse Sufficiency Notes

- The warehouse remains the governing read surface and is strong enough to contextualize benchmark-family reuse, source-family status, and canonical split-policy language.
- Exact paper roster overlap is still limited whenever a paper inherits a public benchmark but does not mirror the concrete split files into the local audit workspace.
- That limitation is precisely why benchmark-family dependence is reported separately from direct overlap: ProteoSphere should not over-claim what the evidence surface cannot yet prove.

## Raw / Archive Fallback Notes

- No raw or archive fallback was needed for the main shortlist in this run.
- The D2CP05644E case relies on previously recovered public artifacts already materialized into the audit workspace, not on an unrestricted crawl of raw source trees.
