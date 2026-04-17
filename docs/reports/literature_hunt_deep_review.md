# Deep ProteoSphere Literature Hunt: Tier 1 ML Dataset Failures

## Executive Summary

This deep hunt reviewed `35` journal papers and retained `20` as proof-backed Tier 1 hard failures. It also kept `5` Tier 2 supporting cases, `7` mitigation-aware controls, and `3` backlog candidates that stayed unresolved on purpose.

The flagship story is now much stronger than the earlier hunt. The Tier 1 set is anchored by two local forensic cases and two reusable benchmark-family proofs: the DeepDTA warm-start family and the PDBbind core-set family. Papers only entered Tier 1 when the benchmark failure itself was proven and the paper did not add a mitigation strong enough to neutralize it.

## Evidence Standard

- Tier 1 means the failure is proof-backed: released split files, code-level split logic, or recovered benchmark-vs-external contamination strong enough that ProteoSphere would block the claim.
- Tier 2 means the paper still matters, but the current evidence is better framed as benchmark saturation or incomplete validation rather than a direct hard failure.
- Controls are included so the analyzer can show when a paper used a mitigation strategy that actually addresses the failure mode.

## Flagship Proof Set

- `deepdta2018` (Bioinformatics, 2018): DeepDTA: deep drug-target binding affinity prediction — ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- `graphdta2021` (Bioinformatics, 2021): GraphDTA: predicting drug-target binding affinity with graph neural networks — ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- `pafnucy2018` (Bioinformatics, 2018): Development and evaluation of a deep learning model for protein-ligand binding affinity prediction — ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- `d2cp05644e_2023` (Physical Chemistry Chemical Physics, 2023): An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties — PDBbind-50 retains 4 direct protein overlaps.
- `baranwal2022struct2graph` (BMC Bioinformatics, 2022): Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions — ProteoSphere reproduced the released split logic and found 643 shared PDB IDs between train and test.
- `onionnet2019` (ACS Omega, 2019): OnionNet: a Multiple-Layer Intermolecular-Contact-Based Convolutional Neural Network for Protein-Ligand Binding Affinity Prediction — ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- `ss_gnn2023` (ACS Omega, 2023): SS-GNN: A Simple-Structured Graph Neural Network for Affinity Prediction — ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- `dgdta2023` (BMC Bioinformatics, 2023): DGDTA: dynamic graph attention network for predicting drug-target binding affinity — ProteoSphere re-computed overlap directly from the official DeepDTA split files.

## Benchmark-Family Proofs

- `deepdta_setting1_family`: Davis shares `68/68` test drugs and `442/442` test targets with training; KIBA shares `2027/2027` test drugs and `229/229` test targets with training.
- `pdbbind_core_family`: the v2016 core set retains direct protein overlap for `288/290` test complexes against the remaining general pool; the v2013 core set retains overlap for `108/108`.

## Tier1 Hard Failure

### DeepDTA: deep drug-target binding affinity prediction

- DOI: https://doi.org/10.1093/bioinformatics/bty593
- Journal: Bioinformatics (2018)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: DeepDTA ships `train_fold_setting1.txt` and `test_fold_setting1.txt`; ProteoSphere re-computed overlap directly from the official files.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### GraphDTA: predicting drug-target binding affinity with graph neural networks

- DOI: https://doi.org/10.1093/bioinformatics/btaa921
- Journal: Bioinformatics (2021)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official GraphDTA README says the Davis/KIBA `test_fold_setting1.txt` and `train_fold_setting1.txt` files were downloaded from DeepDTA.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### Development and evaluation of a deep learning model for protein-ligand binding affinity prediction

- DOI: https://doi.org/10.1093/bioinformatics/bty374
- Journal: Bioinformatics (2018)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The paper's widely reused benchmark story is training on PDBbind and evaluating on CASF/core-set scoring power; ProteoSphere's direct overlap audit shows the core-set family is not independent at the protein level.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties

- DOI: https://doi.org/10.1039/D2CP05644E
- Journal: Physical Chemistry Chemical Physics (2023)
- Domain: `protein_protein`
- Task family: `binding_affinity_regression`
- Benchmark family: `prodigy78_plus_external_panels`
- Claimed split: Recovered public materials reconstruct a 78-complex benchmark pool plus three claimed external panels: PDBbind-50, nanobody-47, and metadynamics-19.
- Recovered evidence: ProteoSphere recovered the benchmark pool and three validation panels; all three external panels fail independence checks.
- Key consequence: PDBbind-50 retains 4 direct protein overlaps.
- Mitigation audit: The PDBbind panel retains direct protein overlap against the recovered benchmark pool.
- ProteoSphere treatment: Treat this paper as a flagship forensic case study and do not accept any of its validation lanes as canonical without a re-split.
- Blockers: The paper-internal benchmark split is under-disclosed even though the effective benchmark pool was reconstructable.

### Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions

- DOI: https://doi.org/10.1186/s12859-022-04910-9
- Journal: BMC Bioinformatics (2022)
- Domain: `protein_protein`
- Task family: `pair_level_ppi_prediction`
- Benchmark family: `struct2graph_public_pairs`
- Claimed split: Balanced-set evaluation and fivefold cross-validation on an unbalanced set are claimed.
- Recovered evidence: ProteoSphere already reproduced the released split logic and found 643 shared PDB IDs between train and test.
- Key consequence: ProteoSphere reproduced the released split logic and found 643 shared PDB IDs between train and test.
- Mitigation audit: The released split mechanism itself is the source of the leakage.
- ProteoSphere treatment: Keep the original split only as a forensic audit example and rebuild any canonical version with accession- or structure-group-aware partitioning.

### OnionNet: a Multiple-Layer Intermolecular-Contact-Based Convolutional Neural Network for Protein-Ligand Binding Affinity Prediction

- DOI: https://doi.org/10.1021/acsomega.9b01997
- Journal: ACS Omega (2019)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official OnionNet README says the testing set is the CASF-2013 benchmark and the PDBbind v2016 core set.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### SS-GNN: A Simple-Structured Graph Neural Network for Affinity Prediction

- DOI: https://doi.org/10.1021/acsomega.3c00085
- Journal: ACS Omega (2023)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official paper describes results on the standard PDBbind v2016 core test set without a homology- or time-based mitigation layer.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### DGDTA: dynamic graph attention network for predicting drug-target binding affinity

- DOI: https://doi.org/10.1186/s12859-023-05497-5
- Journal: BMC Bioinformatics (2023)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the Davis and KIBA data can be downloaded from the GraphDTA repository, which inherits the DeepDTA setting1 split.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### CurvAGN: curvatures-based Adaptive Graph Neural Network for protein-ligand binding affinity prediction

- DOI: https://doi.org/10.1186/s12859-023-05503-w
- Journal: BMC Bioinformatics (2023)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the model was trained on the standard PDBbind-v2016 dataset and evaluated on the PDBbind v2016 core set.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### GS-DTA: integrating graph and sequence models for predicting drug-target binding affinity

- DOI: https://doi.org/10.1186/s12864-025-11234-4
- Journal: BMC Genomics (2025)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the Davis and KIBA data can be downloaded from the GraphDTA repository.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### MEGDTA: multi-modal drug-target affinity prediction based on protein three-dimensional structure and ensemble graph neural network

- DOI: https://doi.org/10.1186/s12864-025-11943-w
- Journal: BMC Genomics (2025)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the Davis and KIBA datasets can be downloaded from the GraphDTA repository.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### DeepTGIN: improving protein-ligand affinity prediction with a hybrid temporal and graph interaction network

- DOI: https://doi.org/10.1186/s13321-024-00938-6
- Journal: Journal of Cheminformatics (2024)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says DeepTGIN uses the PDBbind 2016 core set as the primary test set and the PDBbind 2013 core set as an additional test set.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### EMPDTA: An End-to-End Multimodal Representation Learning Framework with Pocket Online Detection for Drug-Target Affinity Prediction

- DOI: https://doi.org/10.3390/molecules29122912
- Journal: Molecules (2024)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official README states that the sequence-based datasets and the split came from DeepDTA and MDeePred.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### GANsDTA: Predicting Drug-Target Binding Affinity Using GANs

- DOI: https://doi.org/10.3389/fgene.2019.01243
- Journal: Frontiers in Genetics (2020)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official Frontiers article states that the Davis and KIBA experiments used the same setting as DeepDTA, with 80% training and 20% testing.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### CSatDTA: Prediction of Drug-Target Binding Affinity Using Convolution Model with Self-Attention

- DOI: https://doi.org/10.3390/ijms23158453
- Journal: International Journal of Molecular Sciences (2022)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The vendored data README exposes `test_fold_setting1.txt` and `train_fold_setting1.txt` and points back to the DeepDTA data article.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### SAG-DTA: Prediction of Drug-Target Affinity Using Self-Attention Graph Network

- DOI: https://doi.org/10.3390/ijms22168993
- Journal: International Journal of Molecular Sciences (2021)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official data-preparation script says `convert data from DeepDTA` and reads `train_fold_setting1.txt` plus `test_fold_setting1.txt`.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### GNNSeq: A Sequence-Based Graph Neural Network for Predicting Protein-Ligand Binding Affinity

- DOI: https://doi.org/10.3390/ph18030329
- Journal: Pharmaceuticals (2025)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The paper reports benchmark performance on the PDBbind refined/core lineage without an orthogonal cold-target or homology-aware split.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### OnionNet-2: A Convolutional Neural Network Model for Predicting Protein-Ligand Binding Affinity Based on Residue-Atom Contacting Shells

- DOI: https://doi.org/10.3389/fchem.2021.753002
- Journal: Frontiers in Chemistry (2021)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official Frontiers article says OnionNet-2 was trained on the PDBbind database and evaluated primarily on CASF-2016.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### SE-OnionNet: A Convolution Neural Network for Protein-Ligand Binding Affinity Prediction

- DOI: https://doi.org/10.3389/fgene.2020.607824
- Journal: Frontiers in Genetics (2021)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official Frontiers article says the model was tested using scoring functions on PDBbind and the CASF-2016 benchmark.
- Key consequence: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### iEdgeDTA: integrated edge information and 1D graph convolutional neural networks for binding affinity prediction

- DOI: https://doi.org/10.1039/D3RA03796G
- Journal: RSC Advances (2023)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Claimed split: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official iEdgeDTA code loads `original/folds/train_fold_setting1.txt` and `original/folds/test_fold_setting1.txt`, and the README points back to DeepDTA for training-dataset information.
- Key consequence: ProteoSphere re-computed overlap directly from the official DeepDTA split files.
- Mitigation audit: No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.
- ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

## Tier2 Strong Supporting Case

### AGAT-PPIS

- DOI: https://doi.org/10.1093/bib/bbad122
- Journal: Briefings in Bioinformatics (2023)
- Domain: `protein_protein`
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Claimed split: Official repo ships explicit Train_335/Test_60/Test_315-28/UBtest_31-6 benchmark files.
- Recovered evidence: Useful PPIS benchmark paper, but not a hard failure because exact chain-level overlap was not mirrored and the issue is benchmark saturation rather than proven leakage.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is better treated as a strong supporting case than as a flagship hard failure.
- ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### GTE-PPIS

- DOI: https://doi.org/10.1093/bib/bbaf290
- Journal: Briefings in Bioinformatics (2025)
- Domain: `protein_protein`
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Claimed split: Official repo releases the curated PPIS dataset files used in the paper.
- Recovered evidence: Another strong within-family PPIS benchmark paper that is better framed as a supporting saturation case than a Tier 1 failure.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is better treated as a strong supporting case than as a flagship hard failure.
- ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### MVSO-PPIS

- DOI: https://doi.org/10.1093/bioinformatics/btaf470
- Journal: Bioinformatics (2025)
- Domain: `protein_protein`
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Claimed split: Official repo provides the PPIS benchmark files plus processed PDB files.
- Recovered evidence: Shares the same benchmark-family dependence story as other late PPIS papers in the Train_335 lineage.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is better treated as a strong supporting case than as a flagship hard failure.
- ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### MIPPIS

- DOI: https://doi.org/10.1186/s12859-024-05964-7
- Journal: BMC Bioinformatics (2024)
- Domain: `protein_protein`
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Claimed split: MIPPIS uses the public Train_335/Test_60 benchmark family; exact IDs are recoverable through the shared benchmark repos.
- Recovered evidence: Good supporting example of repeated benchmark-family reuse without enough out-of-family validation.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is better treated as a strong supporting case than as a flagship hard failure.
- ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### EquiPPIS

- DOI: https://doi.org/10.1371/journal.pcbi.1011435
- Journal: PLOS Computational Biology (2023)
- Domain: `protein_protein`
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Claimed split: EquiPPIS explicitly follows the public GraphPPIS train/test split rather than introducing a new benchmark family.
- Recovered evidence: Strong PPIS paper that still lives inside the Train_335/Test_60 benchmark family rather than proving out-of-family generalization.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is better treated as a strong supporting case than as a flagship hard failure.
- ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

## Control Nonfailure

### PotentialNet for Molecular Property Prediction

- DOI: https://doi.org/10.1021/acscentsci.8b00507
- Journal: ACS Central Science (2018)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `mitigation_aware_control`
- Claimed split: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: PotentialNet explicitly proposes sequence- and structure-homology-clustered cross-validation to measure generalizability more honestly.
- Key consequence: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Mitigation audit: This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt.
- ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.

### Improved Protein-Ligand Binding Affinity Prediction with Structure-Based Deep Fusion Inference

- DOI: https://doi.org/10.1021/acs.jcim.0c01306
- Journal: Journal of Chemical Information and Modeling (2021)
- Domain: `protein_ligand`
- Task family: `binding_affinity_prediction`
- Benchmark family: `mitigation_aware_control`
- Claimed split: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The paper keeps the standard core-set comparison for literature continuity but also adds a temporal plus 3D structure-clustered holdout for novel protein targets.
- Key consequence: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Mitigation audit: This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt.
- ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.

### BatchDTA: implicit batch alignment enhances deep learning-based drug-target affinity estimation

- DOI: https://doi.org/10.1093/bib/bbac260
- Journal: Briefings in Bioinformatics (2022)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `mitigation_aware_control`
- Claimed split: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The official README says the Davis/KIBA benchmark is split based on unseen protein sequence, which directly addresses the warm-start failure seen in DeepDTA-style setting1.
- Key consequence: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Mitigation audit: This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt.
- ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.

### GraphPPIS

- DOI: https://doi.org/10.1093/bioinformatics/btab643
- Journal: Bioinformatics (2021)
- Domain: `protein_protein`
- Task family: `binding_site_prediction`
- Benchmark family: `ppis_train335_family`
- Claimed split: GraphPPIS is the anchor PPIS benchmark paper for the Train_335/Test_60/Test_315/UBtest_31 family and the official release ships the exact datasets.
- Recovered evidence: Benchmark anchor for the PPIS family; useful as a control because it is paper-faithful and the main concern is later family saturation, not a proven split failure here.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is useful because the analyzer can validate it as comparatively well-designed instead of flagging everything.
- ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run

### NHGNN-DTA: a node-adaptive hybrid graph neural network for interpretable drug-target binding affinity prediction

- DOI: https://doi.org/10.1093/bioinformatics/btad355
- Journal: Bioinformatics (2023)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `mitigation_aware_control`
- Claimed split: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The released split utility explicitly implements cold-target, cold-drug, and cold target+drug settings.
- Key consequence: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Mitigation audit: This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt.
- ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.

### RAPPPID: towards generalizable protein interaction prediction with AWD-LSTM twin networks

- DOI: https://doi.org/10.1093/bioinformatics/btac429
- Journal: Bioinformatics (2022)
- Domain: `protein_protein`
- Task family: `ppi_prediction`
- Benchmark family: `rapppid_c123`
- Claimed split: Official Zenodo package ships strict train/val/test comparative splits (C1/C2/C3) with explicit pair files and sequence dictionaries.
- Recovered evidence: Strict C1/C2/C3 split design and explicit release artifacts make this a good fairness check for the analyzer.
- Key consequence: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.
- Mitigation audit: This paper is useful because the analyzer can validate it as comparatively well-designed instead of flagging everything.
- ProteoSphere treatment: Keep this as a `uniref_grouped` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Blockers: released split artifacts are published, but the identifiers are not bridged into warehouse-native protein refs

### Hierarchical graph representation learning for the prediction of drug-target binding affinity

- DOI: https://doi.org/10.1016/j.ins.2022.09.043
- Journal: Information Sciences (2022)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `mitigation_aware_control`
- Claimed split: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The official repository exposes S1/S2/S3/S4 training and testing settings, which is mitigation-aware rather than a single warm-start benchmark.
- Key consequence: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Mitigation audit: This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt.
- ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.

## Candidate Needs More Recovery

### NerLTR-DTA: drug-target binding affinity prediction based on neighbor relationship and learning to rank

- DOI: https://doi.org/10.1093/bioinformatics/btac048
- Journal: Bioinformatics (2022)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `needs_more_recovery`
- Claimed split: The paper is relevant, but the current run did not recover enough split evidence to classify it fairly.
- Mitigation audit: This candidate stays out of the flagship argument until the split lineage or mitigation story is clearer.
- ProteoSphere treatment: Do not use in the main review narrative until the split is reconstructed or the mitigation story is verified.
- Blockers: The current repo and landing-page evidence are not yet strong enough to prove which split family underlies the headline results.

### Predicting Drug-Target Affinity by Learning Protein Knowledge From Biological Networks

- DOI: https://doi.org/10.1109/JBHI.2023.3240305
- Journal: IEEE Journal of Biomedical and Health Informatics (2023)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `needs_more_recovery`
- Claimed split: The paper is relevant, but the current run did not recover enough split evidence to classify it fairly.
- Mitigation audit: This candidate stays out of the flagship argument until the split lineage or mitigation story is clearer.
- ProteoSphere treatment: Do not use in the main review narrative until the split is reconstructed or the mitigation story is verified.
- Blockers: The paper is interesting, but the public evidence located in this run is still too weak to prove whether the headline split is warm-start or mitigation-aware.

### AttentionDTA: drug-target binding affinity prediction by sequence-based deep learning with attention mechanism

- DOI: https://doi.org/10.1109/TCBB.2022.3170365
- Journal: IEEE/ACM Transactions on Computational Biology and Bioinformatics (2024)
- Domain: `protein_ligand`
- Task family: `drug_target_affinity_prediction`
- Benchmark family: `needs_more_recovery`
- Claimed split: The paper is relevant, but the current run did not recover enough split evidence to classify it fairly.
- Mitigation audit: This candidate stays out of the flagship argument until the split lineage or mitigation story is clearer.
- ProteoSphere treatment: Do not use in the main review narrative until the split is reconstructed or the mitigation story is verified.
- Blockers: The repository exposes the datasets but not enough split provenance to prove whether the paper inherits a warm-start split or uses something colder.

## Domain Coverage

- `protein_ligand`: 26 papers
- `protein_protein`: 9 papers

## Raw / Archive Fallback Notes

- This run stayed warehouse-first for policy and provenance, but it used registry-mediated local fallback for the PDBbind core-family proof because the exact benchmark-family overlap still lives outside the condensed best_evidence surface.
- The D2CP05644E forensic case relies on previously recovered public artifacts materialized in the audit workspace.
- No unrestricted crawl of raw source trees was used for normal evaluation; fallback only served split reconstruction where the warehouse could not yet express the benchmark directly.

## Publication Use Notes

- The Tier 1 set is strong enough to anchor a paper about why dataset review tools matter, but the argument will be strongest if the write-up clearly separates local forensic failures from benchmark-family failures.
- The controls matter almost as much as the failures: they show that the analyzer can validate better split design and does not merely downgrade papers indiscriminately.
