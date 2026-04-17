# ProteoSphere Tier 1 Master Summary

## Executive Summary

- Total confirmed Tier 1 papers: `29`
- Tier 1 papers from 2023 or later: `18`
- Quality score for the review paper: `8.4/10`
- Novelty score for the review paper: `8.1/10`
- Publishability score for the review paper: `7.8/10`
- Overall verdict: `strong_if_carefully_framed`

## Why This Story Is Convincing

- There are now 29 proof-backed Tier 1 failures rather than just a few anecdotal examples.
- The package includes both spectacular paper-specific failures and benchmark-family failures that many later papers inherit.
- The evidence is machine-readable, reproducible, and paired with mitigation-aware controls so the analyzer looks fair rather than indiscriminately negative.
- The story is current: 18 of the Tier 1 papers are from 2023 or later.

## Main Risks

- Over-claiming that all Tier 1 papers are equally broken.
- Not separating direct leakage failures from inherited benchmark-family failures.
- Not including enough controls to prove the analyzer can also validate good practice.

## Tier 1 Papers

### GS-DTA: integrating graph and sequence models for predicting drug-target binding affinity

- `paper_id`: `gsdta2025`
- DOI: [https://doi.org/10.1186/s12864-025-11234-4](https://doi.org/10.1186/s12864-025-11234-4)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: GS-DTA: integrating graph and sequence models for predicting drug-target binding affinity (BMC Genomics, 2025) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official article says the Davis and KIBA data can be downloaded from the GraphDTA repository. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### MEGDTA: multi-modal drug-target affinity prediction based on protein three-dimensional structure and ensemble graph neural network

- `paper_id`: `megdta2025`
- DOI: [https://doi.org/10.1186/s12864-025-11943-w](https://doi.org/10.1186/s12864-025-11943-w)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: MEGDTA: multi-modal drug-target affinity prediction based on protein three-dimensional structure and ensemble graph neural network (BMC Genomics, 2025) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official article says the Davis and KIBA datasets can be downloaded from the GraphDTA repository. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### GNNSeq: A Sequence-Based Graph Neural Network for Predicting Protein-Ligand Binding Affinity

- `paper_id`: `gnnseq2025`
- DOI: [https://doi.org/10.3390/ph18030329](https://doi.org/10.3390/ph18030329)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: GNNSeq: A Sequence-Based Graph Neural Network for Predicting Protein-Ligand Binding Affinity (Pharmaceuticals, 2025) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The paper reports benchmark performance on the PDBbind refined/core lineage without an orthogonal cold-target or homology-aware split. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### DeepTGIN: improving protein-ligand affinity prediction with a hybrid temporal and graph interaction network

- `paper_id`: `deeptgin2024`
- DOI: [https://doi.org/10.1186/s13321-024-00938-6](https://doi.org/10.1186/s13321-024-00938-6)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: DeepTGIN: improving protein-ligand affinity prediction with a hybrid temporal and graph interaction network (Journal of Cheminformatics, 2024) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The official article says DeepTGIN uses the PDBbind 2016 core set as the primary test set and the PDBbind 2013 core set as an additional test set. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### EMPDTA: An End-to-End Multimodal Representation Learning Framework with Pocket Online Detection for Drug-Target Affinity Prediction

- `paper_id`: `empdta2024`
- DOI: [https://doi.org/10.3390/molecules29122912](https://doi.org/10.3390/molecules29122912)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: EMPDTA: An End-to-End Multimodal Representation Learning Framework with Pocket Online Detection for Drug-Target Affinity Prediction (Molecules, 2024) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official README states that the sequence-based datasets and the split came from DeepDTA and MDeePred. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### DEAttentionDTA: protein–ligand binding affinity prediction based on dynamic embedding and self-attention

- `paper_id`: `deattentiondta2024`
- DOI: [https://doi.org/10.1093/bioinformatics/btae319](https://doi.org/10.1093/bioinformatics/btae319)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: DEAttentionDTA: protein–ligand binding affinity prediction based on dynamic embedding and self-attention (Bioinformatics, 2024) is a Tier 1 hard failure because nominal external evaluation is still protein-overlapped. Evidence: The official README names PDBbind 2020, core2016, and core2014. Mitigation audit: The paper inherits the already-proven PDBbind core-family protein overlap without an effective mitigation layer. ProteoSphere treatment: Tier 1 hard failure for unseen-protein claims; keep only as a paper-faithful PDBbind-core audit lane.

### ImageDTA: A Simple Model for Drug–Target Binding Affinity Prediction

- `paper_id`: `imagedta2024`
- DOI: [https://doi.org/10.1021/acsomega.4c02308](https://doi.org/10.1021/acsomega.4c02308)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: ImageDTA: A Simple Model for Drug–Target Binding Affinity Prediction (ACS Omega, 2024) is a Tier 1 hard failure because generalization claims remain benchmark-family limited. Evidence: The official create_csv.py script explicitly says 'convert data from DeepDTA'. Mitigation audit: No mitigation offsets the inherited DeepDTA setting1 leakage. ProteoSphere treatment: Tier 1 hard failure for generalization claims; preserve as a paper-faithful warm-start benchmark only.

### TransVAE-DTA: Transformer and variational autoencoder network for drug-target binding affinity prediction

- `paper_id`: `transvaedta2024`
- DOI: [https://doi.org/10.1016/j.cmpb.2023.108003](https://doi.org/10.1016/j.cmpb.2023.108003)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: TransVAE-DTA: Transformer and variational autoencoder network for drug-target binding affinity prediction (Computer Methods and Programs in Biomedicine, 2024) is a Tier 1 hard failure because warm-start split family blocks clean unseen-entity interpretation. Evidence: The official repo ships train_fold_setting1.txt and test_fold_setting1.txt under both Davis and KIBA. Mitigation audit: The paper reuses the leaky fold family without countervailing mitigation. ProteoSphere treatment: Tier 1 hard failure for broad generalization; acceptable only as a paper-faithful warm-start audit lane.

### An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties

- `paper_id`: `d2cp05644e_2023`
- DOI: [https://doi.org/10.1039/D2CP05644E](https://doi.org/10.1039/D2CP05644E)
- Domain/task: `protein_protein` / `binding_affinity_regression`
- Benchmark family: `prodigy78_plus_external_panels`
- Issue family: `invalid_external_validation`
- Explanation: An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties (Physical Chemistry Chemical Physics, 2023) is a Tier 1 hard failure because pdbbind-50 retains 4 direct protein overlaps. Evidence: ProteoSphere recovered the benchmark pool and three validation panels; all three external panels fail independence checks. Mitigation audit: {'status': 'failed', 'notes': ['The PDBbind panel retains direct protein overlap against the recovered benchmark pool.', 'The nanobody panel reuses a central antigen target.', 'The metadynamics panel shows severe direct reuse and cannot count as independent external validation.']} ProteoSphere treatment: Treat this paper as a flagship forensic case study and do not accept any of its validation lanes as canonical without a re-split.

### SS-GNN: A Simple-Structured Graph Neural Network for Affinity Prediction

- `paper_id`: `ss_gnn2023`
- DOI: [https://doi.org/10.1021/acsomega.3c00085](https://doi.org/10.1021/acsomega.3c00085)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: SS-GNN: A Simple-Structured Graph Neural Network for Affinity Prediction (ACS Omega, 2023) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The official paper describes results on the standard PDBbind v2016 core test set without a homology- or time-based mitigation layer. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### DGDTA: dynamic graph attention network for predicting drug-target binding affinity

- `paper_id`: `dgdta2023`
- DOI: [https://doi.org/10.1186/s12859-023-05497-5](https://doi.org/10.1186/s12859-023-05497-5)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: DGDTA: dynamic graph attention network for predicting drug-target binding affinity (BMC Bioinformatics, 2023) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official article says the Davis and KIBA data can be downloaded from the GraphDTA repository, which inherits the DeepDTA setting1 split. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### CurvAGN: curvatures-based Adaptive Graph Neural Network for protein-ligand binding affinity prediction

- `paper_id`: `curvagn2023`
- DOI: [https://doi.org/10.1186/s12859-023-05503-w](https://doi.org/10.1186/s12859-023-05503-w)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: CurvAGN: curvatures-based Adaptive Graph Neural Network for protein-ligand binding affinity prediction (BMC Bioinformatics, 2023) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The official article says the model was trained on the standard PDBbind-v2016 dataset and evaluated on the PDBbind v2016 core set. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### iEdgeDTA: integrated edge information and 1D graph convolutional neural networks for binding affinity prediction

- `paper_id`: `iedgedta2023`
- DOI: [https://doi.org/10.1039/D3RA03796G](https://doi.org/10.1039/D3RA03796G)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: iEdgeDTA: integrated edge information and 1D graph convolutional neural networks for binding affinity prediction (RSC Advances, 2023) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official iEdgeDTA code loads `original/folds/train_fold_setting1.txt` and `original/folds/test_fold_setting1.txt`, and the README points back to DeepDTA for training-dataset information. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### AttentionDTA: Drug–Target Binding Affinity Prediction by Sequence-Based Deep Learning With Attention Mechanism

- `paper_id`: `attentiondta_tcbb2023`
- DOI: [https://doi.org/10.1109/TCBB.2022.3170365](https://doi.org/10.1109/TCBB.2022.3170365)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `attentiondta_random_row_cv`
- Issue family: `paper_specific_random_cv_leakage`
- Explanation: AttentionDTA: Drug–Target Binding Affinity Prediction by Sequence-Based Deep Learning With Attention Mechanism (IEEE/ACM Transactions on Computational Biology and Bioinformatics, 2023) is a Tier 1 hard failure because direct train/test reuse occurs at both the compound and target level because folds are built over interaction rows. Evidence: The official code shuffles the full pair table and slices folds by row index with get_kfold_data(). Mitigation audit: No mitigation surfaced; the released evaluation remains a hard warm-start split. ProteoSphere treatment: Audit-only Tier 1 failure; treat as paper-specific evidence that row-level CV can collapse entity independence.

### GraphscoreDTA: optimized graph neural network for protein–ligand binding affinity prediction

- `paper_id`: `graphscoredta2023`
- DOI: [https://doi.org/10.1093/bioinformatics/btad340](https://doi.org/10.1093/bioinformatics/btad340)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: GraphscoreDTA: optimized graph neural network for protein–ligand binding affinity prediction (Bioinformatics, 2023) is a Tier 1 hard failure because claims of broad external generalization are too strong for a protein-overlapped core-set benchmark. Evidence: The repo releases labels_train13851.csv, labels_test2016.csv, and labels_test2013.csv. Mitigation audit: The paper inherits the leaky PDBbind core evaluation family as its headline external lane. ProteoSphere treatment: Tier 1 hard failure for externality claims; acceptable only as a paper-faithful core-set benchmark lane.

### CAPLA: improved prediction of protein–ligand binding affinity by a deep learning approach based on a cross-attention mechanism

- `paper_id`: `capla2023`
- DOI: [https://doi.org/10.1093/bioinformatics/btad049](https://doi.org/10.1093/bioinformatics/btad049)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: CAPLA: improved prediction of protein–ligand binding affinity by a deep learning approach based on a cross-attention mechanism (Bioinformatics, 2023) is a Tier 1 hard failure because core-set evaluation remains unsafe as a clean external generalization test. Evidence: The official README names Test2016_290 and Test2016_262 as the evaluation sets. Mitigation audit: The inherited core-family issue remains unresolved. ProteoSphere treatment: Tier 1 hard failure for general externality claims; retain only as a PDBbind-core audit lane.

### DataDTA: a multi-feature and dual-interaction aggregation framework for drug–target binding affinity prediction

- `paper_id`: `datadta2023`
- DOI: [https://doi.org/10.1093/bioinformatics/btad560](https://doi.org/10.1093/bioinformatics/btad560)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: DataDTA: a multi-feature and dual-interaction aggregation framework for drug–target binding affinity prediction (Bioinformatics, 2023) is a Tier 1 hard failure because the benchmark remains unsuitable as a clean unseen-protein test. Evidence: The official repo ships training_smi.csv, validation_smi.csv, test_smi.csv, test105_smi.csv, and test71_smi.csv together with affinity_data.csv keyed by pdbid. Mitigation audit: No mitigation strong enough to neutralize the PDBbind-family overlap was recovered. ProteoSphere treatment: Tier 1 hard failure for externality claims, with a note that the paper package is still useful for paper-faithful PDBbind-family auditing.

### 3DProtDTA: a deep learning model for drug-target affinity prediction based on residue-level protein graphs

- `paper_id`: `three_d_prot_dta2023`
- DOI: [https://doi.org/10.1039/D3RA00281K](https://doi.org/10.1039/D3RA00281K)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: 3DProtDTA: a deep learning model for drug-target affinity prediction based on residue-level protein graphs (RSC Advances, 2023) is a Tier 1 hard failure because benchmark saturation, not unseen-entity generalization, explains the evaluation lane. Evidence: The accompanying public repo contains Davis/KIBA fold files under data/*/folds/train_fold_setting1.txt and test_fold_setting1.txt. Mitigation audit: Inherited warm-start leakage remains unmitigated. ProteoSphere treatment: Tier 1 hard failure for generalization claims based only on the inherited Davis/KIBA setting1 family.

### Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions

- `paper_id`: `baranwal2022struct2graph`
- DOI: [https://doi.org/10.1186/s12859-022-04910-9](https://doi.org/10.1186/s12859-022-04910-9)
- Domain/task: `protein_protein` / `pair_level_ppi_prediction`
- Benchmark family: `struct2graph_public_pairs`
- Issue family: `paper_specific_direct_reuse`
- Explanation: Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions (BMC Bioinformatics, 2022) is a Tier 1 hard failure because proteosphere reproduced the released split logic and found 643 shared pdb ids between train and test. Evidence: ProteoSphere already reproduced the released split logic and found 643 shared PDB IDs between train and test. Mitigation audit: {'status': 'failed', 'notes': ['The released split mechanism itself is the source of the leakage.', 'No published mitigation neutralizes the direct train/test structure reuse.']} ProteoSphere treatment: Keep the original split only as a forensic audit example and rebuild any canonical version with accession- or structure-group-aware partitioning.

### CSatDTA: Prediction of Drug-Target Binding Affinity Using Convolution Model with Self-Attention

- `paper_id`: `csatdta2022`
- DOI: [https://doi.org/10.3390/ijms23158453](https://doi.org/10.3390/ijms23158453)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: CSatDTA: Prediction of Drug-Target Binding Affinity Using Convolution Model with Self-Attention (International Journal of Molecular Sciences, 2022) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The vendored data README exposes `test_fold_setting1.txt` and `train_fold_setting1.txt` and points back to the DeepDTA data article. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### MGraphDTA: deep multiscale graph neural network for explainable drug–target binding affinity prediction

- `paper_id`: `mgraphdta2022`
- DOI: [https://doi.org/10.1039/D1SC05180F](https://doi.org/10.1039/D1SC05180F)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: MGraphDTA: deep multiscale graph neural network for explainable drug–target binding affinity prediction (Chemical Science, 2022) is a Tier 1 hard failure because this is a benchmark-family failure rather than a bespoke split bug. Evidence: The official README states that Davis and KIBA data come from the DeepDTA benchmark family. Mitigation audit: No paper-specific mitigation neutralizes the inherited DeepDTA warm-start leakage. ProteoSphere treatment: Tier 1 hard failure for generalization claims built on DeepDTA setting1 only.

### GraphDTA: predicting drug-target binding affinity with graph neural networks

- `paper_id`: `graphdta2021`
- DOI: [https://doi.org/10.1093/bioinformatics/btaa921](https://doi.org/10.1093/bioinformatics/btaa921)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: GraphDTA: predicting drug-target binding affinity with graph neural networks (Bioinformatics, 2021) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official GraphDTA README says the Davis/KIBA `test_fold_setting1.txt` and `train_fold_setting1.txt` files were downloaded from DeepDTA. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### SAG-DTA: Prediction of Drug-Target Affinity Using Self-Attention Graph Network

- `paper_id`: `sagdta2021`
- DOI: [https://doi.org/10.3390/ijms22168993](https://doi.org/10.3390/ijms22168993)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: SAG-DTA: Prediction of Drug-Target Affinity Using Self-Attention Graph Network (International Journal of Molecular Sciences, 2021) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official data-preparation script says `convert data from DeepDTA` and reads `train_fold_setting1.txt` plus `test_fold_setting1.txt`. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### OnionNet-2: A Convolutional Neural Network Model for Predicting Protein-Ligand Binding Affinity Based on Residue-Atom Contacting Shells

- `paper_id`: `onionnet2_2021`
- DOI: [https://doi.org/10.3389/fchem.2021.753002](https://doi.org/10.3389/fchem.2021.753002)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: OnionNet-2: A Convolutional Neural Network Model for Predicting Protein-Ligand Binding Affinity Based on Residue-Atom Contacting Shells (Frontiers in Chemistry, 2021) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The official Frontiers article says OnionNet-2 was trained on the PDBbind database and evaluated primarily on CASF-2016. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### SE-OnionNet: A Convolution Neural Network for Protein-Ligand Binding Affinity Prediction

- `paper_id`: `se_onionnet2021`
- DOI: [https://doi.org/10.3389/fgene.2020.607824](https://doi.org/10.3389/fgene.2020.607824)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: SE-OnionNet: A Convolution Neural Network for Protein-Ligand Binding Affinity Prediction (Frontiers in Genetics, 2021) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The official Frontiers article says the model was tested using scoring functions on PDBbind and the CASF-2016 benchmark. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### GANsDTA: Predicting Drug-Target Binding Affinity Using GANs

- `paper_id`: `gansdta2020`
- DOI: [https://doi.org/10.3389/fgene.2019.01243](https://doi.org/10.3389/fgene.2019.01243)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: GANsDTA: Predicting Drug-Target Binding Affinity Using GANs (Frontiers in Genetics, 2020) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: The official Frontiers article states that the Davis and KIBA experiments used the same setting as DeepDTA, with 80% training and 20% testing. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### OnionNet: a Multiple-Layer Intermolecular-Contact-Based Convolutional Neural Network for Protein-Ligand Binding Affinity Prediction

- `paper_id`: `onionnet2019`
- DOI: [https://doi.org/10.1021/acsomega.9b01997](https://doi.org/10.1021/acsomega.9b01997)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: OnionNet: a Multiple-Layer Intermolecular-Contact-Based Convolutional Neural Network for Protein-Ligand Binding Affinity Prediction (ACS Omega, 2019) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The official OnionNet README says the testing set is the CASF-2013 benchmark and the PDBbind v2016 core set. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

### DeepDTA: deep drug-target binding affinity prediction

- `paper_id`: `deepdta2018`
- DOI: [https://doi.org/10.1093/bioinformatics/bty593](https://doi.org/10.1093/bioinformatics/bty593)
- Domain/task: `protein_ligand` / `drug_target_affinity_prediction`
- Benchmark family: `deepdta_setting1_family`
- Issue family: `warm_start_benchmark_family`
- Explanation: DeepDTA: deep drug-target binding affinity prediction (Bioinformatics, 2018) is a Tier 1 hard failure because proteosphere re-computed overlap directly from the official deepdta split files. Evidence: DeepDTA ships `train_fold_setting1.txt` and `test_fold_setting1.txt`; ProteoSphere re-computed overlap directly from the official files. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.

### Development and evaluation of a deep learning model for protein-ligand binding affinity prediction

- `paper_id`: `pafnucy2018`
- DOI: [https://doi.org/10.1093/bioinformatics/bty374](https://doi.org/10.1093/bioinformatics/bty374)
- Domain/task: `protein_ligand` / `binding_affinity_prediction`
- Benchmark family: `pdbbind_core_family`
- Issue family: `protein_overlapped_external_family`
- Explanation: Development and evaluation of a deep learning model for protein-ligand binding affinity prediction (Bioinformatics, 2018) is a Tier 1 hard failure because proteosphere resolved the official core-set id lists and compared them against the remaining local pdbbind general pool through sifts accessions. Evidence: The paper's widely reused benchmark story is training on PDBbind and evaluating on CASF/core-set scoring power; ProteoSphere's direct overlap audit shows the core-set family is not independent at the protein level. Mitigation audit: {'status': 'failed', 'notes': ['No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result.', 'The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed.']} ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.

## Publishability Assessment

This is publishable if framed as a rigorous dataset-audit and benchmark-governance paper rather than a blanket criticism of a field. The strongest venues are likely methods- or bioinformatics-oriented journals that value reproducibility, benchmark critique, and practical tooling.

### Best Target Venues
- Bioinformatics
- Briefings in Bioinformatics
- Journal of Chemical Information and Modeling
- Patterns
- PLOS Computational Biology

### Highest-Value Next Steps
- Add 3 to 5 more direct paper-specific failures outside the current DTA/PDBbind clusters.
- Add a short manual validation appendix with one or two independently re-run case studies.
- Turn the methods section into an explicit decision ladder: warehouse-first, official artifacts second, fallback only when necessary.
- Keep the narrative tiered: flagship proofs, supporting breadth, then controls.
