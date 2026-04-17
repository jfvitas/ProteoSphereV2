# ProteoSphere Literature Hunt Addendum

## Summary

- New candidates reviewed: `17`
- New Tier 1 additions: `9`
- New Tier 2 additions: `4`
- New controls: `4`
- Combined Tier 1 total versus the original deep hunt: `29`

## Why This Addendum Matters

This pass broadens the existing deep hunt with newer 2022–2026 peer-reviewed papers, heavily prioritizing recent publications that still inherit known leaky benchmark families or use paper-specific row-level train/test designs that fail ProteoSphere independence logic.

## Tier 1 Additions

### TransVAE-DTA: Transformer and variational autoencoder network for drug-target binding affinity prediction

- `paper_id`: `transvaedta2024`
- DOI: [https://doi.org/10.1016/j.cmpb.2023.108003](https://doi.org/10.1016/j.cmpb.2023.108003)
- Journal/year: `Computer Methods and Programs in Biomedicine` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Split evidence: The official repo ships train_fold_setting1.txt and test_fold_setting1.txt under both Davis and KIBA.
- Failure: Warm-start split family blocks clean unseen-entity interpretation.
- Mitigation audit: The paper reuses the leaky fold family without countervailing mitigation.

### DEAttentionDTA: protein–ligand binding affinity prediction based on dynamic embedding and self-attention

- `paper_id`: `deattentiondta2024`
- DOI: [https://doi.org/10.1093/bioinformatics/btae319](https://doi.org/10.1093/bioinformatics/btae319)
- Journal/year: `Bioinformatics` / `2024`
- Benchmark family: `pdbbind_core_family`
- Split evidence: The official README names PDBbind 2020, core2016, and core2014.
- Failure: Nominal external evaluation is still protein-overlapped.
- Mitigation audit: The paper inherits the already-proven PDBbind core-family protein overlap without an effective mitigation layer.

### ImageDTA: A Simple Model for Drug–Target Binding Affinity Prediction

- `paper_id`: `imagedta2024`
- DOI: [https://doi.org/10.1021/acsomega.4c02308](https://doi.org/10.1021/acsomega.4c02308)
- Journal/year: `ACS Omega` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Split evidence: The official create_csv.py script explicitly says 'convert data from DeepDTA'.
- Failure: Generalization claims remain benchmark-family limited.
- Mitigation audit: No mitigation offsets the inherited DeepDTA setting1 leakage.

### 3DProtDTA: a deep learning model for drug-target affinity prediction based on residue-level protein graphs

- `paper_id`: `three_d_prot_dta2023`
- DOI: [https://doi.org/10.1039/D3RA00281K](https://doi.org/10.1039/D3RA00281K)
- Journal/year: `RSC Advances` / `2023`
- Benchmark family: `deepdta_setting1_family`
- Split evidence: The accompanying public repo contains Davis/KIBA fold files under data/*/folds/train_fold_setting1.txt and test_fold_setting1.txt.
- Failure: Benchmark saturation, not unseen-entity generalization, explains the evaluation lane.
- Mitigation audit: Inherited warm-start leakage remains unmitigated.

### AttentionDTA: Drug–Target Binding Affinity Prediction by Sequence-Based Deep Learning With Attention Mechanism

- `paper_id`: `attentiondta_tcbb2023`
- DOI: [https://doi.org/10.1109/TCBB.2022.3170365](https://doi.org/10.1109/TCBB.2022.3170365)
- Journal/year: `IEEE/ACM Transactions on Computational Biology and Bioinformatics` / `2023`
- Benchmark family: `attentiondta_random_row_cv`
- Split evidence: The official code shuffles the full pair table and slices folds by row index with get_kfold_data().
- Failure: Direct train/test reuse occurs at both the compound and target level because folds are built over interaction rows.
- Mitigation audit: No mitigation surfaced; the released evaluation remains a hard warm-start split.

### GraphscoreDTA: optimized graph neural network for protein–ligand binding affinity prediction

- `paper_id`: `graphscoredta2023`
- DOI: [https://doi.org/10.1093/bioinformatics/btad340](https://doi.org/10.1093/bioinformatics/btad340)
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Split evidence: The repo releases labels_train13851.csv, labels_test2016.csv, and labels_test2013.csv.
- Failure: Claims of broad external generalization are too strong for a protein-overlapped core-set benchmark.
- Mitigation audit: The paper inherits the leaky PDBbind core evaluation family as its headline external lane.

### DataDTA: a multi-feature and dual-interaction aggregation framework for drug–target binding affinity prediction

- `paper_id`: `datadta2023`
- DOI: [https://doi.org/10.1093/bioinformatics/btad560](https://doi.org/10.1093/bioinformatics/btad560)
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Split evidence: The official repo ships training_smi.csv, validation_smi.csv, test_smi.csv, test105_smi.csv, and test71_smi.csv together with affinity_data.csv keyed by pdbid.
- Failure: The benchmark remains unsuitable as a clean unseen-protein test.
- Mitigation audit: No mitigation strong enough to neutralize the PDBbind-family overlap was recovered.

### CAPLA: improved prediction of protein–ligand binding affinity by a deep learning approach based on a cross-attention mechanism

- `paper_id`: `capla2023`
- DOI: [https://doi.org/10.1093/bioinformatics/btad049](https://doi.org/10.1093/bioinformatics/btad049)
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Split evidence: The official README names Test2016_290 and Test2016_262 as the evaluation sets.
- Failure: Core-set evaluation remains unsafe as a clean external generalization test.
- Mitigation audit: The inherited core-family issue remains unresolved.

### MGraphDTA: deep multiscale graph neural network for explainable drug–target binding affinity prediction

- `paper_id`: `mgraphdta2022`
- DOI: [https://doi.org/10.1039/D1SC05180F](https://doi.org/10.1039/D1SC05180F)
- Journal/year: `Chemical Science` / `2022`
- Benchmark family: `deepdta_setting1_family`
- Split evidence: The official README states that Davis and KIBA data come from the DeepDTA benchmark family.
- Failure: This is a benchmark-family failure rather than a bespoke split bug.
- Mitigation audit: No paper-specific mitigation neutralizes the inherited DeepDTA warm-start leakage.

## Tier 2 Supporting Cases

- `btdhdta2025`: Insufficient official artifact recovery in this pass.
- `attentionmgtdta2024`: Exact fold roster recovery was incomplete in this pass.
- `mmfadta2024`: Split artifacts not fully recovered.
- `bicompdta2023`: Official split artifacts or repo evidence were not recovered in this run.

## Controls

- `dta_om2026`: Control_nonfailure unless a later audit shows the mitigation failed in practice.
- `tefdta2024`: This is a mitigation-aware control, not a Tier 1 failure.
- `dcgan_dta2024`: Control_nonfailure for this expansion because the paper releases colder options instead of only the leaky family.
- `hacnet2023`: Control_nonfailure.
