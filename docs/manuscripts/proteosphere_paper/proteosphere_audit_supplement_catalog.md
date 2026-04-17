# ProteoSphere Supplementary Literature Audit Catalog

This supplement backs the manuscript's literature-hunt claims with the full reviewed manuscript corpus.

## Corpus scope

- Reviewed manuscript corpus: `52` papers
- `tier1_hard_failure`: `29`
- `tier2_strong_supporting_case`: `9`
- `control_nonfailure`: `11`
- `candidate_needs_more_recovery`: `3`

## Benchmark-family proof artifacts

- DeepDTA setting1 family: `artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json`
- PDBbind core family: `artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json`
- AttentionDTA random-row CV: `artifacts/status/literature_hunt_recent_expansion_proofs/attentiondta_random_cv_family_audit.json`
- Struct2Graph direct reuse: `artifacts/status/struct2graph_overlap/struct2graph_reproduced_split_overlap.json`
- D2CP05644E external-panel audit: `artifacts/status/paper_d2cp05644e_detailed_audit.json`

## tier1_hard_failure

### GNNSeq: A Sequence-Based Graph Neural Network for Predicting Protein-Ligand Binding Affinity (gnnseq2025)

- DOI: `https://doi.org/10.3390/ph18030329`
- Journal/year: `Pharmaceuticals` / `2025`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3390/ph18030329
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The paper reports benchmark performance on the PDBbind refined/core lineage without an orthogonal cold-target or homology-aware split. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none surfaced in benchmark description
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/gnnseq2025.json

### GS-DTA: integrating graph and sequence models for predicting drug-target binding affinity (gsdta2025)

- DOI: `https://doi.org/10.1186/s12864-025-11234-4`
- Journal/year: `BMC Genomics` / `2025`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1186/s12864-025-11234-4 | https://github.com/zhuziguang/GS-DTA
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the Davis and KIBA data can be downloaded from the GraphDTA repository. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/gsdta2025.json

### MEGDTA: multi-modal drug-target affinity prediction based on protein three-dimensional structure and ensemble graph neural network (megdta2025)

- DOI: `https://doi.org/10.1186/s12864-025-11943-w`
- Journal/year: `BMC Genomics` / `2025`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1186/s12864-025-11943-w | https://github.com/liyijuncode/MEGDTA
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the Davis and KIBA datasets can be downloaded from the GraphDTA repository. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none for the headline Davis/KIBA evaluation
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/megdta2025.json

### DEAttentionDTA: protein–ligand binding affinity prediction based on dynamic embedding and self-attention (deattentiondta2024)

- DOI: `https://doi.org/10.1093/bioinformatics/btae319`
- Journal/year: `Bioinformatics` / `2024`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btae319 | https://github.com/whatamazing1/DEAttentionDTA | https://raw.githubusercontent.com/whatamazing1/DEAttentionDTA/main/README.md | https://raw.githubusercontent.com/whatamazing1/DEAttentionDTA/main/src/test.py
- Claimed split or evaluation design: The model evaluates on PDBbind general/refined training sets with core2016 and core2014 test sets.
- Recovered evidence: The official README names PDBbind 2020, core2016, and core2014. The released test script explicitly instantiates MyDataset('core2016', ...).
- What the paper said it did about bias, leakage, or split safety: No unseen-protein or source-family mitigation beyond the standard core-set evaluation is released.
- ProteoSphere mitigation reading: The paper inherits the already-proven PDBbind core-family protein overlap without an effective mitigation layer.
- Exact failure class: inherited_core_set_external_failure
- Overlap findings: PDBbind core-family proof shows 288/290 v2016 core complexes retain direct protein overlap with training-side complexes.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Nominal external evaluation is still protein-overlapped.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for unseen-protein claims; keep only as a paper-faithful PDBbind-core audit lane.
- Provenance notes: Recent 2024 Bioinformatics paper with explicit core-set references in the released repo.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/deattentiondta2024.json

### DeepTGIN: improving protein-ligand affinity prediction with a hybrid temporal and graph interaction network (deeptgin2024)

- DOI: `https://doi.org/10.1186/s13321-024-00938-6`
- Journal/year: `Journal of Cheminformatics` / `2024`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1186/s13321-024-00938-6
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says DeepTGIN uses the PDBbind 2016 core set as the primary test set and the PDBbind 2013 core set as an additional test set. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/deeptgin2024.json

### EMPDTA: An End-to-End Multimodal Representation Learning Framework with Pocket Online Detection for Drug-Target Affinity Prediction (empdta2024)

- DOI: `https://doi.org/10.3390/molecules29122912`
- Journal/year: `Molecules` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3390/molecules29122912 | https://github.com/BioCenter-SHU/EMPDTA | https://raw.githubusercontent.com/BioCenter-SHU/EMPDTA/main/README.md
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official README states that the sequence-based datasets and the split came from DeepDTA and MDeePred. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none for the headline Davis/KIBA results
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/empdta2024.json

### ImageDTA: A Simple Model for Drug–Target Binding Affinity Prediction (imagedta2024)

- DOI: `https://doi.org/10.1021/acsomega.4c02308`
- Journal/year: `ACS Omega` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1021/acsomega.4c02308 | https://github.com/neuhanli/ImageDTA | https://raw.githubusercontent.com/neuhanli/ImageDTA/main/README.md | https://raw.githubusercontent.com/neuhanli/ImageDTA/main/create_csv.py
- Claimed split or evaluation design: The model evaluates on Davis and KIBA after converting released benchmark artifacts.
- Recovered evidence: The official create_csv.py script explicitly says 'convert data from DeepDTA'. It reads train_fold_setting1.txt and test_fold_setting1.txt from the Davis and KIBA benchmark folders.
- What the paper said it did about bias, leakage, or split safety: No released cold-drug, cold-target, or novel-pair setting is used for the main results.
- ProteoSphere mitigation reading: No mitigation offsets the inherited DeepDTA setting1 leakage.
- Exact failure class: script_proven_inherited_fold_family_failure
- Overlap findings: The official data-conversion script ties the paper directly to the DeepDTA warm-start folds.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Generalization claims remain benchmark-family limited.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for generalization claims; preserve as a paper-faithful warm-start benchmark only.
- Provenance notes: Recent 2024 paper with explicit benchmark-conversion code.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/imagedta2024.json

### TransVAE-DTA: Transformer and variational autoencoder network for drug-target binding affinity prediction (transvaedta2024)

- DOI: `https://doi.org/10.1016/j.cmpb.2023.108003`
- Journal/year: `Computer Methods and Programs in Biomedicine` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1016/j.cmpb.2023.108003 | https://github.com/HPC-NEAU/TransVAE-DTA | https://raw.githubusercontent.com/HPC-NEAU/TransVAE-DTA/main/README.md
- Claimed split or evaluation design: Davis and KIBA performance is reported using released fold files.
- Recovered evidence: The official repo ships train_fold_setting1.txt and test_fold_setting1.txt under both Davis and KIBA. Those files place the paper directly inside the already-proven DeepDTA setting1 warm-start family.
- What the paper said it did about bias, leakage, or split safety: No cold split or unseen-target split is surfaced in the released package.
- ProteoSphere mitigation reading: The paper reuses the leaky fold family without countervailing mitigation.
- Exact failure class: released_inherited_fold_family_failure
- Overlap findings: Released fold artifacts map directly to the DeepDTA setting1 family.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Warm-start split family blocks clean unseen-entity interpretation.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for broad generalization; acceptable only as a paper-faithful warm-start audit lane.
- Provenance notes: Recent 2024 journal paper with official fold artifacts.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/transvaedta2024.json

### 3DProtDTA: a deep learning model for drug-target affinity prediction based on residue-level protein graphs (three_d_prot_dta2023)

- DOI: `https://doi.org/10.1039/D3RA00281K`
- Journal/year: `RSC Advances` / `2023`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1039/D3RA00281K | https://github.com/HySonLab/Ligand_Generation | https://raw.githubusercontent.com/HySonLab/Ligand_Generation/main/README.md
- Claimed split or evaluation design: The paper reports Davis and KIBA benchmark performance for residue-level protein graphs.
- Recovered evidence: The accompanying public repo contains Davis/KIBA fold files under data/*/folds/train_fold_setting1.txt and test_fold_setting1.txt. That places the paper in the same DeepDTA setting1 family already proven to be a hard warm-start split.
- What the paper said it did about bias, leakage, or split safety: No stronger held-out entity split is released for the core paper benchmark.
- ProteoSphere mitigation reading: Inherited warm-start leakage remains unmitigated.
- Exact failure class: inherited_warm_start_benchmark_failure
- Overlap findings: Released fold layout matches the DeepDTA setting1 family.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Benchmark saturation, not unseen-entity generalization, explains the evaluation lane.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for generalization claims based only on the inherited Davis/KIBA setting1 family.
- Provenance notes: Recent 2023 paper with public benchmark files in the companion repo.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/three_d_prot_dta2023.json

### An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties (d2cp05644e_2023)

- DOI: `https://doi.org/10.1039/D2CP05644E`
- Journal/year: `Physical Chemistry Chemical Physics` / `2023`
- Benchmark family: `prodigy78_plus_external_panels`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1039/D2CP05644E | https://www.rsc.org/suppdata/d2/cp/d2cp05644e/d2cp05644e1.pdf | https://github.com/DSIMB/PPSUS
- Claimed split or evaluation design: Recovered public materials reconstruct a 78-complex benchmark pool plus three claimed external panels: PDBbind-50, nanobody-47, and metadynamics-19.
- Recovered evidence: ProteoSphere recovered the benchmark pool and three validation panels; all three external panels fail independence checks. The benchmark pool was reconstructed from the public repository rather than from a warehouse-native split artifact.
- What the paper said it did about bias, leakage, or split safety: No release-date, accession-group, or family-aware mitigation is evident in the recovered training/external panel design.
- ProteoSphere mitigation reading: failed. The PDBbind panel retains direct protein overlap against the recovered benchmark pool. The nanobody panel reuses a central antigen target. The metadynamics panel shows severe direct reuse and cannot count as independent external validation
- Exact failure class: direct_protein_overlap, exact_sequence_reuse, invalid_external_validation, shared_partner_context
- Overlap detail fields: prodigy78_vs_pdbbind50: overall_decision=blocked, coverage_fraction=0.9766, covered_structure_count=125, total_structure_count=128, direct_protein_overlap_count=4, exact_sequence_overlap_count=4, mutation_like_pair_count=0, flagged_structure_pair_count=16, top_recommendation=Re-split the dataset before training use. | prodigy78_vs_nanobody47: overall_decision=blocked, coverage_fraction=0.84, covered_structure_count=105, total_structure_count=125, direct_protein_overlap_count=1, exact_sequence_overlap_count=1, mutation_like_pair_count=0, flagged_structure_pair_count=24, top_recommendation=Re-split the dataset before training use. | prodigy78_vs_metadynamics19: overall_decision=blocked, coverage_fraction=0.9691, covered_structure_count=94, total_structure_count=97, direct_protein_overlap_count=26, exact_sequence_overlap_count=26, mutation_like_pair_count=0, flagged_structure_pair_count=24, top_recommendation=Re-split the dataset before training use.
- Contamination or control reading: PDBbind-50 retains 4 direct protein overlaps. Nanobody-47 retains 1 direct protein overlaps. Metadynamics-19 retains 26 direct protein overlaps and repeated exact complexes.
- Blockers or remaining uncertainties: The paper-internal benchmark split is under-disclosed even though the effective benchmark pool was reconstructable.
- PDBbind-derived 50-complex panel: direct protein overlap 4, accession-root overlap 4, UniRef100 overlap 4, shared partner overlap 110, flagged structure-pair count 16, verdict high_direct_protein_overlap.
- Exact direct-overlap map: Lysozyme C (P00698): train 1BVK, 1DQJ, 1MLC, 1P2C, 1VFB, 2I25; test 4CJ2, 6JB2 | GTPase HRas (P01112): train 1HE8, 1LFD; test 5E95 | Beta-2-microglobulin (P61769): train 1AKJ; test 3VFN | Actin, alpha skeletal muscle (P68135): train 1ATN; test 4B1Y.
- Nanobody 47-complex panel: direct protein overlap 1, accession-root overlap 1, UniRef100 overlap 1, shared partner overlap 16, flagged structure-pair count 24, verdict high_direct_protein_overlap.
- Exact direct-overlap map: Lysozyme C (P00698): train 1BVK, 1DQJ, 1MLC, 1P2C, 1VFB, 2I25; test 1RI8, 1RJC, 1ZV5, 1ZVH.
- Metadynamics 19-complex panel: direct protein overlap 26, accession-root overlap 26, UniRef100 overlap 26, shared partner overlap 75, flagged structure-pair count 24, verdict high_direct_protein_overlap.
- Exact direct-overlap map: Pancreatic alpha-amylase (P00690): train 1BVN, 1KXQ; test 1BVN | Serine protease 1 {ECO:0000250|UniProtKB:P07477} (P00760): train 1PPE, 2TGP; test 2PTC, 2UUY | Chymotrypsinogen A (P00766): train 1ACB, 1CBW; test 1ACB | Streptogrisin-B (P00777): train 3SGB; test 3SGB | Subtilisin Carlsberg {ECO:0000303|PubMed:4967581} (P00780): train 1R0R; test 1R0R | Pancreatic trypsin inhibitor (P00974): train 1CBW, 2TGP; test 2PTC | Eglin C (P01051): train 1ACB; test 1ACB | Alpha-amylase inhibitor HOE-467A (P01092): train 1BVN; test 1BVN | ATP-dependent molecular chaperone HSP82 (P02829): train 1US7; test 1US7 | T-cell surface antigen CD2 (P06729): train 1QA9; test 1QA9 | Chemotaxis protein CheA (P07363): train 1FFW; test 1FFW | Colicin-E9 (P09883): train 1EMV, 2WPT; test 1EMV | Enterotoxin type C-3 (P0A0L5): train 2AQ3, 3BZD; test 3BZD | Chemotaxis protein CheY (P0AE67): train 1FFW; test 1FFW | Polyubiquitin-C (P0CH28): train 2OOB; test 2OOB | Transforming growth factor beta-3 proprotein (P10600): train 1KTZ; test 1KTZ | Colicin-E9 immunity protein (P13479): train 1EMV; test 1EMV | Lymphocyte function-associated antigen 3 (P19256): train 1QA9; test 1QA9 | Sterol carrier protein 2 (P22307): train 2C0L; test 2C0L | Fiber protein (P36711): train 1KAC; test 1KAC | TGF-beta receptor type-2 (P37173): train 1KTZ; test 1KTZ | Peroxisomal targeting signal 1 receptor {ECO:0000305} (P50542): train 2C0L; test 2C0L | Ovomucoid (P68390): train 1R0R, 3SGB; test 1R0R, 3SGB | Coxsackievirus and adenovirus receptor (P78310): train 1KAC; test 1KAC | E3 ubiquitin-protein ligase CBL-B (Q13191): train 2OOB; test 2OOB | Hsp90 co-chaperone Cdc37 (Q16543): train 1US7; test 1US7.
- Detailed flagship proof artifact: artifacts/status/paper_d2cp05644e_detailed_audit.json
- Recommended ProteoSphere treatment: Treat this paper as a flagship forensic case study and do not accept any of its validation lanes as canonical without a re-split.
- Provenance notes: This record relies on previously recovered public artifacts materialized in the local audit workspace. It is one of the clearest examples of why paper prose about an 'external test set' is not enough.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/d2cp05644e_2023.json

### AttentionDTA: Drug–Target Binding Affinity Prediction by Sequence-Based Deep Learning With Attention Mechanism (attentiondta_tcbb2023)

- DOI: `https://doi.org/10.1109/TCBB.2022.3170365`
- Journal/year: `IEEE/ACM Transactions on Computational Biology and Bioinformatics` / `2023`
- Benchmark family: `attentiondta_random_row_cv`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1109/TCBB.2022.3170365 | https://github.com/zhaoqichang/AttentionDTA_TCBB | https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/AttentionDTA_main.py | https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/datasets/Davis.txt | https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/datasets/KIBA.txt | https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/datasets/Metz.txt
- Claimed split or evaluation design: Five-fold cross-validation on released Davis, KIBA, and Metz pair tables.
- Recovered evidence: The official code shuffles the full pair table and slices folds by row index with get_kfold_data(). Recovered first-fold overlap counts: Davis shares 68/68 test drugs and 367/367 test targets with training. KIBA shares 2054/2054 test drugs and 229/229 test targets with training.
- What the paper said it did about bias, leakage, or split safety: No cold-drug, cold-target, or cold-pair mitigation is released.
- ProteoSphere mitigation reading: No mitigation surfaced; the released evaluation remains a hard warm-start split.
- Exact failure class: code_proven_random_row_cv_leakage
- Overlap findings: The released train/test logic guarantees shared drugs and shared targets across folds. This invalidates unseen-entity generalization claims.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Direct train/test reuse occurs at both the compound and target level because folds are built over interaction rows.
- Underlying family proof: AttentionDTA shuffles full interaction rows and slices folds by row index, preserving drug and target reuse across folds.
- Davis: 68/68 test drugs and 367/367 test targets also appear in training.
- KIBA: 2054/2054 test drugs and 229/229 test targets also appear in training.
- Metz: 1206/1214 test drugs and 169/169 test targets also appear in training.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_recent_expansion_proofs/attentiondta_random_cv_family_audit.json
- Recommended ProteoSphere treatment: Audit-only Tier 1 failure; treat as paper-specific evidence that row-level CV can collapse entity independence.
- Provenance notes: Proof computed from the released repository datasets and main training script.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/attentiondta_tcbb2023.json

### CAPLA: improved prediction of protein–ligand binding affinity by a deep learning approach based on a cross-attention mechanism (capla2023)

- DOI: `https://doi.org/10.1093/bioinformatics/btad049`
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btad049 | https://github.com/lennylv/CAPLA | https://raw.githubusercontent.com/lennylv/CAPLA/main/README.md
- Claimed split or evaluation design: CAPLA evaluates on PDBbind-derived Test2016_290 and Test2016_262 sets.
- Recovered evidence: The official README names Test2016_290 and Test2016_262 as the evaluation sets. These are direct descendants of the PDBbind core-set evaluation family already proven to retain protein overlap with training.
- What the paper said it did about bias, leakage, or split safety: No stronger unseen-protein mitigation is released for the headline benchmark.
- ProteoSphere mitigation reading: The inherited core-family issue remains unresolved.
- Exact failure class: inherited_core_set_external_failure
- Overlap findings: PDBbind core-family reuse is explicit in the official benchmark naming.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Core-set evaluation remains unsafe as a clean external generalization test.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for general externality claims; retain only as a PDBbind-core audit lane.
- Provenance notes: Recent 2023 paper with official core-set naming in the repo.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/capla2023.json

### CurvAGN: curvatures-based Adaptive Graph Neural Network for protein-ligand binding affinity prediction (curvagn2023)

- DOI: `https://doi.org/10.1186/s12859-023-05503-w`
- Journal/year: `BMC Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1186/s12859-023-05503-w
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the model was trained on the standard PDBbind-v2016 dataset and evaluated on the PDBbind v2016 core set. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/curvagn2023.json

### DGDTA: dynamic graph attention network for predicting drug-target binding affinity (dgdta2023)

- DOI: `https://doi.org/10.1186/s12859-023-05497-5`
- Journal/year: `BMC Bioinformatics` / `2023`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1186/s12859-023-05497-5 | https://github.com/luojunwei/DGDTA
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official article says the Davis and KIBA data can be downloaded from the GraphDTA repository, which inherits the DeepDTA setting1 split. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/dgdta2023.json

### DataDTA: a multi-feature and dual-interaction aggregation framework for drug–target binding affinity prediction (datadta2023)

- DOI: `https://doi.org/10.1093/bioinformatics/btad560`
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btad560 | https://github.com/YanZhu06/DataDTA | https://raw.githubusercontent.com/YanZhu06/DataDTA/main/README.md
- Claimed split or evaluation design: The repo releases training, validation, test, test105, and test71 affinity surfaces keyed by PDB identifiers.
- Recovered evidence: The official repo ships training_smi.csv, validation_smi.csv, test_smi.csv, test105_smi.csv, and test71_smi.csv together with affinity_data.csv keyed by pdbid. That is consistent with a PDBbind-derived training/test family rather than a newly mitigated unseen-protein split.
- What the paper said it did about bias, leakage, or split safety: No explicit cold-protein or source-family separation is released for the headline benchmark package.
- ProteoSphere mitigation reading: No mitigation strong enough to neutralize the PDBbind-family overlap was recovered.
- Exact failure class: released_pdbbind_family_without_effective_mitigation
- Overlap findings: Released PDB-ID keyed benchmark files keep the paper inside the protein-overlapped PDBbind family.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: The benchmark remains unsuitable as a clean unseen-protein test.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for externality claims, with a note that the paper package is still useful for paper-faithful PDBbind-family auditing.
- Provenance notes: Recent 2023 paper with a released benchmark package but no convincing mitigation layer.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/datadta2023.json

### GraphscoreDTA: optimized graph neural network for protein–ligand binding affinity prediction (graphscoredta2023)

- DOI: `https://doi.org/10.1093/bioinformatics/btad340`
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btad340 | https://github.com/CSUBioGroup/GraphscoreDTA | https://raw.githubusercontent.com/CSUBioGroup/GraphscoreDTA/main/README.md
- Claimed split or evaluation design: The model reports performance on training, test2016, and test2013 sets distributed with the official repo.
- Recovered evidence: The repo releases labels_train13851.csv, labels_test2016.csv, and labels_test2013.csv. Those released files place the paper directly inside the proven PDBbind core-set family.
- What the paper said it did about bias, leakage, or split safety: No released cold-protein or scaffold-split mitigation neutralizes the inherited core-set overlap.
- ProteoSphere mitigation reading: The paper inherits the leaky PDBbind core evaluation family as its headline external lane.
- Exact failure class: released_core_set_family_failure
- Overlap findings: Official test2016/test2013 labels align with the core-set family already proven protein-overlapped.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Claims of broad external generalization are too strong for a protein-overlapped core-set benchmark.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for externality claims; acceptable only as a paper-faithful core-set benchmark lane.
- Provenance notes: Recent 2023 Bioinformatics paper with released core-family labels.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/graphscoredta2023.json

### SS-GNN: A Simple-Structured Graph Neural Network for Affinity Prediction (ss_gnn2023)

- DOI: `https://doi.org/10.1021/acsomega.3c00085`
- Journal/year: `ACS Omega` / `2023`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1021/acsomega.3c00085
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official paper describes results on the standard PDBbind v2016 core test set without a homology- or time-based mitigation layer. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none surfaced in benchmark description
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/ss_gnn2023.json

### iEdgeDTA: integrated edge information and 1D graph convolutional neural networks for binding affinity prediction (iedgedta2023)

- DOI: `https://doi.org/10.1039/D3RA03796G`
- Journal/year: `RSC Advances` / `2023`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1039/D3RA03796G | https://github.com/cucpbioinfo/iEdgeDTA | https://raw.githubusercontent.com/cucpbioinfo/iEdgeDTA/main/core/data_processing.py
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official iEdgeDTA code loads `original/folds/train_fold_setting1.txt` and `original/folds/test_fold_setting1.txt`, and the README points back to DeepDTA for training-dataset information. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/iedgedta2023.json

### CSatDTA: Prediction of Drug-Target Binding Affinity Using Convolution Model with Self-Attention (csatdta2022)

- DOI: `https://doi.org/10.3390/ijms23158453`
- Journal/year: `International Journal of Molecular Sciences` / `2022`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3390/ijms23158453 | https://github.com/aashutoshghimire/CSatDTA | https://raw.githubusercontent.com/aashutoshghimire/CSatDTA/main/data/README.md
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The vendored data README exposes `test_fold_setting1.txt` and `train_fold_setting1.txt` and points back to the DeepDTA data article. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/csatdta2022.json

### MGraphDTA: deep multiscale graph neural network for explainable drug–target binding affinity prediction (mgraphdta2022)

- DOI: `https://doi.org/10.1039/D1SC05180F`
- Journal/year: `Chemical Science` / `2022`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1039/D1SC05180F | https://github.com/guaguabujianle/MGraphDTA | https://raw.githubusercontent.com/guaguabujianle/MGraphDTA/master/README.md
- Claimed split or evaluation design: Performance is reported on Davis and KIBA benchmark splits inherited from earlier DTA work.
- Recovered evidence: The official README states that Davis and KIBA data come from the DeepDTA benchmark family. The inherited DeepDTA setting1 family is already proven to share 68/68 Davis test drugs and 2027/2027 KIBA test drugs with training in ProteoSphere's benchmark proof.
- What the paper said it did about bias, leakage, or split safety: No cold-drug or cold-target split is released in the official repo.
- ProteoSphere mitigation reading: No paper-specific mitigation neutralizes the inherited DeepDTA warm-start leakage.
- Exact failure class: inherited_warm_start_benchmark_failure
- Overlap findings: Inherited DeepDTA setting1 retains complete test-drug reuse and complete/near-complete target reuse.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: This is a benchmark-family failure rather than a bespoke split bug.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 1 hard failure for generalization claims built on DeepDTA setting1 only.
- Provenance notes: Recent peer-reviewed DTA paper that still inherits the warm-start family.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/mgraphdta2022.json

### Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions (baranwal2022struct2graph)

- DOI: `https://doi.org/10.1186/s12859-022-04910-9`
- Journal/year: `BMC Bioinformatics` / `2022`
- Benchmark family: `struct2graph_public_pairs`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1186/s12859-022-04910-9 | https://github.com/baranwa2/Struct2Graph | https://raw.githubusercontent.com/baranwa2/Struct2Graph/master/create_examples.py
- Claimed split or evaluation design: Balanced-set evaluation and fivefold cross-validation on an unbalanced set are claimed.
- Recovered evidence: ProteoSphere already reproduced the released split logic and found 643 shared PDB IDs between train and test. The released `create_examples.py` logic uses example-level random shuffling and fixed slicing rather than a group-aware split.
- What the paper said it did about bias, leakage, or split safety: No cold-family or accession-group mitigation surfaced in the released split-generation logic.
- ProteoSphere mitigation reading: failed. The released split mechanism itself is the source of the leakage. No published mitigation neutralizes the direct train/test structure reuse
- Exact failure class: direct_structure_overlap, pair_level_random_split, shared_component_leakage
- Overlap detail fields: shared_pdb_count: 643
- Contamination or control reading: ProteoSphere reproduced the released split logic and found 643 shared PDB IDs between train and test. This is a direct split failure, not a subtle family-similarity issue.
- ProteoSphere reproduced the released example-shuffle split logic with seed 1337 and found 643 shared PDB IDs between train and test.
- Representative shared-PDB sample: 1A4E, 1A5E, 1AOJ, 1AY0, 1B6U, 1BI7, 1BMP, 1BOR, 1BUO, 1CI6, 1D5R, 1DZF, 1EFX, 1EG3, 1EH2, 1EJP, 1EK0, 1EKX, 1EOT, 1F4J, 1F9Q, 1FNT, 1FOS, 1FOT, 1G5J.
- Highlight structure 4EQ6 was reused in 78 reproduced train examples and 9 reproduced test examples.
- Highlight chain grounding: chain A -> protein:P40465; chain B -> protein:Q12318.
- Detailed flagship proof artifact: artifacts/status/struct2graph_overlap/struct2graph_reproduced_split_overlap.json
- Recommended ProteoSphere treatment: Keep the original split only as a forensic audit example and rebuild any canonical version with accession- or structure-group-aware partitioning.
- Provenance notes: Primary proof came from the local Struct2Graph forensic artifact and reproduced overlap analysis. No raw/archive fallback was required for this paper in the current run.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/baranwal2022struct2graph.json

### GraphDTA: predicting drug-target binding affinity with graph neural networks (graphdta2021)

- DOI: `https://doi.org/10.1093/bioinformatics/btaa921`
- Journal/year: `Bioinformatics` / `2021`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btaa921 | https://github.com/thinng/GraphDTA | https://raw.githubusercontent.com/thinng/GraphDTA/master/README.md
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official GraphDTA README says the Davis/KIBA `test_fold_setting1.txt` and `train_fold_setting1.txt` files were downloaded from DeepDTA. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/graphdta2021.json

### OnionNet-2: A Convolutional Neural Network Model for Predicting Protein-Ligand Binding Affinity Based on Residue-Atom Contacting Shells (onionnet2_2021)

- DOI: `https://doi.org/10.3389/fchem.2021.753002`
- Journal/year: `Frontiers in Chemistry` / `2021`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3389/fchem.2021.753002
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official Frontiers article says OnionNet-2 was trained on the PDBbind database and evaluated primarily on CASF-2016. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/onionnet2_2021.json

### SAG-DTA: Prediction of Drug-Target Affinity Using Self-Attention Graph Network (sagdta2021)

- DOI: `https://doi.org/10.3390/ijms22168993`
- Journal/year: `International Journal of Molecular Sciences` / `2021`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3390/ijms22168993 | https://github.com/ShugangZhang/SAG-DTA | https://raw.githubusercontent.com/ShugangZhang/SAG-DTA/master/prepare_data.py
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official data-preparation script says `convert data from DeepDTA` and reads `train_fold_setting1.txt` plus `test_fold_setting1.txt`. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/sagdta2021.json

### SE-OnionNet: A Convolution Neural Network for Protein-Ligand Binding Affinity Prediction (se_onionnet2021)

- DOI: `https://doi.org/10.3389/fgene.2020.607824`
- Journal/year: `Frontiers in Genetics` / `2021`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3389/fgene.2020.607824
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official Frontiers article says the model was tested using scoring functions on PDBbind and the CASF-2016 benchmark. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/se_onionnet2021.json

### GANsDTA: Predicting Drug-Target Binding Affinity Using GANs (gansdta2020)

- DOI: `https://doi.org/10.3389/fgene.2019.01243`
- Journal/year: `Frontiers in Genetics` / `2020`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.3389/fgene.2019.01243
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official Frontiers article states that the Davis and KIBA experiments used the same setting as DeepDTA, with 80% training and 20% testing. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, benchmark_inheritance_without_mitigation
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/gansdta2020.json

### OnionNet: a Multiple-Layer Intermolecular-Contact-Based Convolutional Neural Network for Protein-Ligand Binding Affinity Prediction (onionnet2019)

- DOI: `https://doi.org/10.1021/acsomega.9b01997`
- Journal/year: `ACS Omega` / `2019`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1021/acsomega.9b01997 | https://github.com/zhenglz/onionnet | https://raw.githubusercontent.com/zhenglz/onionnet/master/README.md
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The official OnionNet README says the testing set is the CASF-2013 benchmark and the PDBbind v2016 core set. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/onionnet2019.json

### DeepDTA: deep drug-target binding affinity prediction (deepdta2018)

- DOI: `https://doi.org/10.1093/bioinformatics/bty593`
- Journal/year: `Bioinformatics` / `2018`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/bty593 | https://raw.githubusercontent.com/hkmztrk/DeepDTA/master/data/README.md
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: DeepDTA ships `train_fold_setting1.txt` and `test_fold_setting1.txt`; ProteoSphere re-computed overlap directly from the official files. The official setting1 split is a hard warm-start failure for unseen-entity evaluation: Davis shares every test drug and every test target with training, and KIBA shares almost all.
- What the paper said it did about bias, leakage, or split safety: none
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: shared_drug_identity_between_train_test, shared_target_identity_between_train_test, warm_start_split
- Overlap detail fields: davis: shared_drug_count=68, test_unique_drug_count=68, shared_target_count=442, test_unique_target_count=442 | kiba: shared_drug_count=2027, test_unique_drug_count=2027, shared_target_count=229, test_unique_target_count=229
- Contamination or control reading: ProteoSphere re-computed overlap directly from the official DeepDTA split files. Davis is a full warm-start failure: every test drug and every test target also appear in training. KIBA is nearly the same: 1938 of 2027 test drugs and 228 of 229 test targets also appear in training.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Do not use the released split as evidence of unseen-drug or unseen-target generalization. Keep it only as a paper-faithful audit lane and pair it with cold-drug, cold-target, or cold-drug+target splits.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/deepdta2018.json

### Development and evaluation of a deep learning model for protein-ligand binding affinity prediction (pafnucy2018)

- DOI: `https://doi.org/10.1093/bioinformatics/bty374`
- Journal/year: `Bioinformatics` / `2018`
- Benchmark family: `pdbbind_core_family`
- Manuscript role: `Flagship or primary proof-set paper`
- Official evidence links: https://doi.org/10.1093/bioinformatics/bty374
- Claimed split or evaluation design: The paper's headline benchmark inherits a released benchmark family whose split is recoverable and evaluable under ProteoSphere.
- Recovered evidence: The paper's widely reused benchmark story is training on PDBbind and evaluating on CASF/core-set scoring power; ProteoSphere's direct overlap audit shows the core-set family is not independent at the protein level. The standard PDBbind core-set evaluation family is not a clean unseen-protein benchmark: v2016 core retains direct protein overlap for 288 of 290 test complexes against the remaining general set, and v2013 core retains overlap for all 108 test complexes.
- What the paper said it did about bias, leakage, or split safety: no homology-aware split surfaced in headline benchmark
- ProteoSphere mitigation reading: failed. No meaningful mitigation strategy was surfaced in the official evidence for the headline benchmark result. The benchmark family itself remains block-worthy under ProteoSphere once the split is reconstructed
- Exact failure class: direct_protein_identity_overlap_between_training_and_test, legacy_core_set_external_evaluation, receptor_reuse
- Overlap detail fields: v2016_core: test_count=290, training_pool_count=18747, test_complexes_with_direct_protein_overlap=288, shared_accession_count=77, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool | v2013_core: test_count=108, training_pool_count=18929, test_complexes_with_direct_protein_overlap=108, shared_accession_count=50, failure_class=core_set_retains_direct_protein_identity_overlap_against_training_pool
- Contamination or control reading: ProteoSphere resolved the official core-set ID lists and compared them against the remaining local PDBbind general pool through SIFTS accessions. The v2016 core set retains direct protein overlap for 288 of 290 test complexes against the remaining general pool. The v2013 core set retains direct protein overlap for all 108 test complexes.
- Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool.
- v2016 core: 288/290 test complexes retain direct protein overlap with training.
- v2013 core: 108/108 test complexes retain direct protein overlap with training.
- Illustrative v2016 conflicts: 3AO4 shares Q72498 with train-side examples 3AO1, 3AO5, 3OVN, 5WLO; 3GV9 shares P00811 with train-side examples 1C3B, 1FSW, 1FSY, 1GA9; 1UTO shares P00760 with train-side examples 1AQ7, 1AUJ, 1BJU, 1BJV.
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/pdbbind_core_family_audit.json
- Recommended ProteoSphere treatment: Do not treat refined/general-to-core evaluation as a clean external benchmark. Use time-split, homology-cluster, or cold-target validation for governing claims.
- Provenance notes: The benchmark-family proof was computed in this run from official released artifacts and local audit data where required. The paper was promoted to Tier 1 only because it inherits that proven failure without a mitigation layer strong enough to neutralize it.
- Raw or archive fallback required in this paper-level artifact: yes.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/pafnucy2018.json

## tier2_strong_supporting_case

### Deep Drug–Target Binding Affinity Prediction Base on Multiple Feature Extraction and Fusion (btdhdta2025)

- DOI: `https://doi.org/10.1021/acsomega.4c08048`
- Journal/year: `ACS Omega` / `2025`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1021/acsomega.4c08048
- Claimed split or evaluation design: The paper reports recent DTA benchmark results in the DeepDTA/Davis/KIBA ecosystem.
- Recovered evidence: The publication is recent and relevant, but official split artifacts or repository files were not recovered strongly enough for Tier 1 promotion.
- What the paper said it did about bias, leakage, or split safety: No verifiable mitigation package recovered in this pass.
- ProteoSphere mitigation reading: Held at Tier 2 because proof of the exact split lineage is incomplete.
- Exact failure class: likely_warm_start_family_but_under_recovered
- Overlap findings: Likely benchmark-family exposure, but proof strength is incomplete.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: This paper helps show the issue is current, but not yet as a flagship proof case.
- Blockers or remaining uncertainties: Insufficient official artifact recovery in this pass.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 2 supporting case pending deeper recovery.
- Provenance notes: Recent 2025 paper kept as a supporting example rather than over-promoted.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/btdhdta2025.json

### GTE-PPIS (gte_ppis2025)

- DOI: `https://doi.org/10.1093/bib/bbaf290`
- Journal/year: `Briefings in Bioinformatics` / `2025`
- Benchmark family: `ppis_train335_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1093/bib/bbaf290
- Claimed split or evaluation design: Official repo releases the curated PPIS dataset files used in the paper.
- Recovered evidence: Another strong within-family PPIS benchmark paper that is better framed as a supporting saturation case than a Tier 1 failure. The paper is strongly benchmarked and audit-friendly, but the key problem is benchmark-family saturation rather than a recovered hard split failure.
- What the paper said it did about bias, leakage, or split safety: No extra out-of-family validation was mirrored into the warehouse for this run.
- ProteoSphere mitigation reading: insufficient for tier1. This paper is better treated as a strong supporting case than as a flagship hard failure. The current evidence does not prove a paper-specific split failure at the same level as Struct2Graph or the benchmark families above
- Exact failure class: benchmark_family_saturation, insufficient_out_of_family_validation
- Overlap detail fields: direct_overlap: status=published_not_mirrored | accession_root_overlap: status=published_not_mirrored | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers. Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization.
- Blockers or remaining uncertainties: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run
- Recommended ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/gte_ppis2025.json

### MVSO-PPIS (mvso_ppis2025)

- DOI: `https://doi.org/10.1093/bioinformatics/btaf470`
- Journal/year: `Bioinformatics` / `2025`
- Benchmark family: `ppis_train335_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btaf470 | https://github.com/Edwardblue282/MVSO-PPIS
- Claimed split or evaluation design: Official repo provides the PPIS benchmark files plus processed PDB files.
- Recovered evidence: Shares the same benchmark-family dependence story as other late PPIS papers in the Train_335 lineage. The paper is strongly benchmarked and audit-friendly, but the key problem is benchmark-family saturation rather than a recovered hard split failure.
- What the paper said it did about bias, leakage, or split safety: No extra out-of-family validation was mirrored into the warehouse for this run.
- ProteoSphere mitigation reading: insufficient for tier1. This paper is better treated as a strong supporting case than as a flagship hard failure. The current evidence does not prove a paper-specific split failure at the same level as Struct2Graph or the benchmark families above
- Exact failure class: benchmark_family_saturation, insufficient_out_of_family_validation
- Overlap detail fields: direct_overlap: status=published_not_mirrored | accession_root_overlap: status=published_not_mirrored | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers. Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization.
- Blockers or remaining uncertainties: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run
- Recommended ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/mvso_ppis2025.json

### AttentionMGT-DTA: A multi-modal drug-target affinity prediction using graph transformer and attention mechanism (attentionmgtdta2024)

- DOI: `https://doi.org/10.1016/j.neunet.2023.11.018`
- Journal/year: `Neural Networks` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1016/j.neunet.2023.11.018 | https://github.com/JK-Liu7/AttentionMGT-DTA | https://raw.githubusercontent.com/JK-Liu7/AttentionMGT-DTA/main/README.md | https://raw.githubusercontent.com/JK-Liu7/AttentionMGT-DTA/main/train_DTA.py
- Claimed split or evaluation design: The model trains and tests on Davis/KIBA processed folds in the public repo.
- Recovered evidence: The training script points to data/Davis/processed/train/fold/* and matching test fold paths. The repo context strongly suggests inherited Davis/KIBA fold evaluation, but the exact raw fold membership was not re-materialized in this pass.
- What the paper said it did about bias, leakage, or split safety: No explicit cold split was surfaced in the official training script.
- ProteoSphere mitigation reading: Likely inherited DeepDTA-family evaluation, but not elevated to Tier 1 because the exact released fold lineage was not fully reconstructed here.
- Exact failure class: likely_inherited_warm_start_family
- Overlap findings: The repo structure is consistent with a warm-start Davis/KIBA fold family.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Strong supporting case, but held below Tier 1 pending one more recovery pass.
- Blockers or remaining uncertainties: Exact fold roster recovery was incomplete in this pass.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 2 supporting case pending explicit fold lineage confirmation.
- Provenance notes: Recent 2024 paper retained to broaden the evidence surface without overstating proof.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/attentionmgtdta2024.json

### MIPPIS (mippis2024)

- DOI: `https://doi.org/10.1186/s12859-024-05964-7`
- Journal/year: `BMC Bioinformatics` / `2024`
- Benchmark family: `ppis_train335_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1186/s12859-024-05964-7 | https://pmc.ncbi.nlm.nih.gov/articles/PMC11536593/
- Claimed split or evaluation design: MIPPIS uses the public Train_335/Test_60 benchmark family; exact IDs are recoverable through the shared benchmark repos.
- Recovered evidence: Good supporting example of repeated benchmark-family reuse without enough out-of-family validation. The paper is strongly benchmarked and audit-friendly, but the key problem is benchmark-family saturation rather than a recovered hard split failure.
- What the paper said it did about bias, leakage, or split safety: No extra out-of-family validation was mirrored into the warehouse for this run.
- ProteoSphere mitigation reading: insufficient for tier1. This paper is better treated as a strong supporting case than as a flagship hard failure. The current evidence does not prove a paper-specific split failure at the same level as Struct2Graph or the benchmark families above
- Exact failure class: benchmark_family_saturation, insufficient_out_of_family_validation
- Overlap detail fields: direct_overlap: status=published_not_mirrored | accession_root_overlap: status=published_not_mirrored | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers. Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization. This paper inherits a strong public benchmark rather than releasing a new one, so its main audit value is comparability, not novel split design.
- Blockers or remaining uncertainties: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run
- Recommended ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/mippis2024.json

### MMFA-DTA: Multimodal Feature Attention Fusion Network for Drug-Target Affinity Prediction for Drug Repurposing Against SARS-CoV-2 (mmfadta2024)

- DOI: `https://doi.org/10.1021/acs.jctc.4c00663`
- Journal/year: `Journal of Chemical Theory and Computation` / `2024`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1021/acs.jctc.4c00663
- Claimed split or evaluation design: The paper uses the common DTA benchmark stack for SARS-CoV-2 repurposing work.
- Recovered evidence: Article-level evidence suggests standard Davis/KIBA-style benchmarking, but the released split surface was not recovered deeply enough here.
- What the paper said it did about bias, leakage, or split safety: No verified mitigation package recovered in this pass.
- ProteoSphere mitigation reading: Remains Tier 2 until split artifacts are reconstructed.
- Exact failure class: likely_benchmark_family_dependence
- Overlap findings: Likely benchmark-family exposure, pending stronger artifact recovery.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Supporting case only.
- Blockers or remaining uncertainties: Split artifacts not fully recovered.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 2 supporting case.
- Provenance notes: Recent 2024 paper kept below Tier 1 to preserve evidentiary discipline.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/mmfadta2024.json

### AGAT-PPIS (agat_ppis2023)

- DOI: `https://doi.org/10.1093/bib/bbad122`
- Journal/year: `Briefings in Bioinformatics` / `2023`
- Benchmark family: `ppis_train335_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1093/bib/bbad122 | https://github.com/AILBC/AGAT-PPIS
- Claimed split or evaluation design: Official repo ships explicit Train_335/Test_60/Test_315-28/UBtest_31-6 benchmark files.
- Recovered evidence: Useful PPIS benchmark paper, but not a hard failure because exact chain-level overlap was not mirrored and the issue is benchmark saturation rather than proven leakage. The paper is strongly benchmarked and audit-friendly, but the key problem is benchmark-family saturation rather than a recovered hard split failure.
- What the paper said it did about bias, leakage, or split safety: No extra out-of-family validation was mirrored into the warehouse for this run.
- ProteoSphere mitigation reading: insufficient for tier1. This paper is better treated as a strong supporting case than as a flagship hard failure. The current evidence does not prove a paper-specific split failure at the same level as Struct2Graph or the benchmark families above
- Exact failure class: benchmark_family_saturation, insufficient_out_of_family_validation
- Overlap detail fields: direct_overlap: status=published_not_mirrored | accession_root_overlap: status=published_not_mirrored | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers. Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization.
- Blockers or remaining uncertainties: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run
- Recommended ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/agat_ppis2023.json

### BiComp-DTA: Drug-target binding affinity prediction through complementary biological-related and compression-based featurization approach (bicompdta2023)

- DOI: `https://doi.org/10.1371/journal.pcbi.1011036`
- Journal/year: `PLOS Computational Biology` / `2023`
- Benchmark family: `deepdta_setting1_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1371/journal.pcbi.1011036
- Claimed split or evaluation design: The paper reports Davis and KIBA benchmark results.
- Recovered evidence: The journal paper clearly uses the same DTA benchmark family, but the official split artifacts were not recovered in this pass.
- What the paper said it did about bias, leakage, or split safety: No released countervailing cold split was recovered.
- ProteoSphere mitigation reading: Remains a strong supporting case, not Tier 1, because split artifacts were not fully recovered.
- Exact failure class: likely_benchmark_family_dependence
- Overlap findings: Benchmark choice strongly suggests warm-start exposure.
- Overlap detail fields: direct_entity_overlap: True
- Contamination or control reading: Needs one more evidence pass before Tier 1 promotion.
- Blockers or remaining uncertainties: Official split artifacts or repo evidence were not recovered in this run.
- Underlying family proof: DeepDTA setting1 releases warm-start folds. Davis reuses 68/68 test drugs and 442/442 test targets across train/test.
- KIBA reuses 2027/2027 test drugs and 229/229 test targets.
- Sample shared entity indices preserved in the proof artifact: Davis drugs [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], Davis targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], KIBA drugs [0, 1, 2, 3, 4, 5, 6, 7, 9, 10], KIBA targets [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].
- Benchmark-family proof artifact: artifacts/status/literature_hunt_deep_proofs/dta_setting1_family_audit.json
- Recommended ProteoSphere treatment: Tier 2 supporting case.
- Provenance notes: Recent 2023 peer-reviewed DTA paper retained for breadth.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/bicompdta2023.json

### EquiPPIS (equippis2023)

- DOI: `https://doi.org/10.1371/journal.pcbi.1011435`
- Journal/year: `PLOS Computational Biology` / `2023`
- Benchmark family: `ppis_train335_family`
- Manuscript role: `Supporting breadth paper retained below Tier 1`
- Official evidence links: https://doi.org/10.1371/journal.pcbi.1011435
- Claimed split or evaluation design: EquiPPIS explicitly follows the public GraphPPIS train/test split rather than introducing a new benchmark family.
- Recovered evidence: Strong PPIS paper that still lives inside the Train_335/Test_60 benchmark family rather than proving out-of-family generalization. The paper is strongly benchmarked and audit-friendly, but the key problem is benchmark-family saturation rather than a recovered hard split failure.
- What the paper said it did about bias, leakage, or split safety: No extra out-of-family validation was mirrored into the warehouse for this run.
- ProteoSphere mitigation reading: insufficient for tier1. This paper is better treated as a strong supporting case than as a flagship hard failure. The current evidence does not prove a paper-specific split failure at the same level as Struct2Graph or the benchmark families above
- Exact failure class: benchmark_family_saturation, insufficient_out_of_family_validation
- Overlap detail fields: direct_overlap: status=published_not_mirrored | accession_root_overlap: status=published_not_mirrored | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers. Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization. This paper inherits a strong public benchmark rather than releasing a new one, so its main audit value is comparability, not novel split design.
- Blockers or remaining uncertainties: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run
- Recommended ProteoSphere treatment: Keep as an audit-only comparison lane and demand at least one additional out-of-family benchmark before treating the paper as a strong generalization result.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/equippis2023.json

## control_nonfailure

### An artificial intelligence model for accurate drug-target affinity prediction in medicinal chemistry (dta_om2026)

- DOI: `https://doi.org/10.1016/j.ejmech.2026.118840`
- Journal/year: `European Journal of Medicinal Chemistry` / `2026`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1016/j.ejmech.2026.118840 | https://github.com/MiJia-ID/DTA-OM | https://raw.githubusercontent.com/MiJia-ID/DTA-OM/main/README.md
- Claimed split or evaluation design: The paper reports novel-pair and novel-drug evaluations.
- Recovered evidence: The official README explicitly advertises novel-pair and novel-drug settings.
- What the paper said it did about bias, leakage, or split safety: Novel-pair and novel-drug holdouts are central to the released evaluation story.
- ProteoSphere mitigation reading: Control_nonfailure unless a later audit shows the mitigation failed in practice.
- Exact failure class: none_control
- Overlap findings: The claimed mitigation directly targets warm-start bias.
- Overlap detail fields: direct_entity_overlap: False
- Contamination or control reading: Strong recent control demonstrating the field can ship colder evaluation surfaces.
- Recommended ProteoSphere treatment: Control_nonfailure.
- Provenance notes: Very recent 2026 control, useful for the 'still relevant' narrative because it shows better practice exists now.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/dta_om2026.json

### DCGAN-DTA: Predicting drug-target binding affinity with deep convolutional generative adversarial networks (dcgan_dta2024)

- DOI: `https://doi.org/10.1186/s12864-024-10326-x`
- Journal/year: `BMC Genomics` / `2024`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1186/s12864-024-10326-x | https://github.com/mojtabaze7/DCGAN-DTA | https://raw.githubusercontent.com/mojtabaze7/DCGAN-DTA/main/README.md
- Claimed split or evaluation design: The repo exposes multiple fold settings, including colder settings for some datasets.
- Recovered evidence: The official repo includes setting1, setting2, and setting3 split files for some benchmarks.
- What the paper said it did about bias, leakage, or split safety: Multiple settings imply the paper is not restricted to the warm-start setting only.
- ProteoSphere mitigation reading: Control_nonfailure for this expansion because the paper releases colder options instead of only the leaky family.
- Exact failure class: none_control
- Overlap findings: Released colder settings keep this paper out of the Tier 1 bucket.
- Overlap detail fields: direct_entity_overlap: False
- Contamination or control reading: Useful mitigation-aware control.
- Recommended ProteoSphere treatment: Control_nonfailure.
- Provenance notes: Recent 2024 control retained to show the analyzer is fair.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/dcgan_dta2024.json

### TEFDTA: a transformer encoder and fingerprint representation combined prediction method for bonded and non-bonded drug–target affinities (tefdta2024)

- DOI: `https://doi.org/10.1093/bioinformatics/btad778`
- Journal/year: `Bioinformatics` / `2024`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btad778 | https://github.com/RefDawn-XD/TEFDTA | https://raw.githubusercontent.com/RefDawn-XD/TEFDTA/master/README.md
- Claimed split or evaluation design: The repo releases both standard train/test and cold evaluation files for Davis and KIBA.
- Recovered evidence: The official repo ships Davis_train/test/cold.csv and KIBA_train/test/cold.csv.
- What the paper said it did about bias, leakage, or split safety: Cold evaluation surfaces are released for both Davis and KIBA.
- ProteoSphere mitigation reading: This is a mitigation-aware control, not a Tier 1 failure.
- Exact failure class: none_control
- Overlap findings: A cold split is explicitly released, which is exactly the kind of mitigation the analyzer wants to see.
- Overlap detail fields: direct_entity_overlap: False
- Contamination or control reading: Useful control showing the tool can validate better benchmark design.
- Recommended ProteoSphere treatment: Control_nonfailure.
- Provenance notes: Recent 2024 control paper with released cold splits.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/tefdta2024.json

### HAC-Net: A Hybrid Attention-Based Convolutional Neural Network for Highly Accurate Protein–Ligand Binding Affinity Prediction (hacnet2023)

- DOI: `https://doi.org/10.1021/acs.jcim.3c00251`
- Journal/year: `Journal of Chemical Information and Modeling` / `2023`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1021/acs.jcim.3c00251 | https://github.com/gregory-kyro/HAC-Net | https://raw.githubusercontent.com/gregory-kyro/HAC-Net/main/README.md
- Claimed split or evaluation design: The paper reports multiple train/test splits maximizing differences in proteins or ligands.
- Recovered evidence: The official README says the paper evaluates under splits maximizing differences in protein structure, sequence, or ligand fingerprint.
- What the paper said it did about bias, leakage, or split safety: The evaluation is explicitly designed to counter common protein/ligand leakage channels.
- ProteoSphere mitigation reading: Control_nonfailure.
- Exact failure class: none_control
- Overlap findings: This is the kind of mitigation-aware design ProteoSphere wants to encourage.
- Overlap detail fields: direct_entity_overlap: False
- Contamination or control reading: Useful control for fairness.
- Recommended ProteoSphere treatment: Control_nonfailure.
- Provenance notes: Recent 2023 control paper that strengthens the adoption narrative by contrast.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_recent_expansion/hacnet2023.json

### NHGNN-DTA: a node-adaptive hybrid graph neural network for interpretable drug-target binding affinity prediction (nhgnn_dta2023)

- DOI: `https://doi.org/10.1093/bioinformatics/btad355`
- Journal/year: `Bioinformatics` / `2023`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btad355 | https://github.com/hehh77/NHGNN-DTA | https://raw.githubusercontent.com/hehh77/NHGNN-DTA/main/Code/split.py
- Claimed split or evaluation design: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The released split utility explicitly implements cold-target, cold-drug, and cold target+drug settings.
- What the paper said it did about bias, leakage, or split safety: The released split utility explicitly implements cold-target, cold-drug, and cold target+drug settings.
- ProteoSphere mitigation reading: passes control check. This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt
- Exact failure class: 
- Contamination or control reading: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Recommended ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.
- Provenance notes: This control was kept intentionally to avoid turning the review into a one-sided takedown.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/nhgnn_dta2023.json

### BatchDTA: implicit batch alignment enhances deep learning-based drug-target affinity estimation (batchdta2022)

- DOI: `https://doi.org/10.1093/bib/bbac260`
- Journal/year: `Briefings in Bioinformatics` / `2022`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1093/bib/bbac260 | https://raw.githubusercontent.com/PaddlePaddle/PaddleHelix/dev/apps/drug_target_interaction/batchdta/README.md
- Claimed split or evaluation design: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The official README says the Davis/KIBA benchmark is split based on unseen protein sequence, which directly addresses the warm-start failure seen in DeepDTA-style setting1.
- What the paper said it did about bias, leakage, or split safety: The official README says the Davis/KIBA benchmark is split based on unseen protein sequence, which directly addresses the warm-start failure seen in DeepDTA-style setting1.
- ProteoSphere mitigation reading: passes control check. This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt
- Exact failure class: 
- Contamination or control reading: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Recommended ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.
- Provenance notes: This control was kept intentionally to avoid turning the review into a one-sided takedown.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/batchdta2022.json

### Hierarchical graph representation learning for the prediction of drug-target binding affinity (hgrldta2022)

- DOI: `https://doi.org/10.1016/j.ins.2022.09.043`
- Journal/year: `Information Sciences` / `2022`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1016/j.ins.2022.09.043 | https://github.com/Zhaoyang-Chu/HGRL-DTA | https://raw.githubusercontent.com/Zhaoyang-Chu/HGRL-DTA/main/README.md
- Claimed split or evaluation design: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The official repository exposes S1/S2/S3/S4 training and testing settings, which is mitigation-aware rather than a single warm-start benchmark.
- What the paper said it did about bias, leakage, or split safety: The official repository exposes S1/S2/S3/S4 training and testing settings, which is mitigation-aware rather than a single warm-start benchmark.
- ProteoSphere mitigation reading: passes control check. This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt
- Exact failure class: 
- Contamination or control reading: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Recommended ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.
- Provenance notes: This control was kept intentionally to avoid turning the review into a one-sided takedown.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/hgrldta2022.json

### RAPPPID: towards generalizable protein interaction prediction with AWD-LSTM twin networks (szymborski2022rapppid)

- DOI: `https://doi.org/10.1093/bioinformatics/btac429`
- Journal/year: `Bioinformatics` / `2022`
- Benchmark family: `rapppid_c123`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btac429 | https://doi.org/10.5281/zenodo.6817258
- Claimed split or evaluation design: Official Zenodo package ships strict train/val/test comparative splits (C1/C2/C3) with explicit pair files and sequence dictionaries.
- Recovered evidence: Strict C1/C2/C3 split design and explicit release artifacts make this a good fairness check for the analyzer.
- What the paper said it did about bias, leakage, or split safety: uniref_grouped
- ProteoSphere mitigation reading: passes control check. This paper is useful because the analyzer can validate it as comparatively well-designed instead of flagging everything
- Exact failure class: 
- Overlap detail fields: direct_overlap: status=mapping_blocked_after_roster_recovery | accession_root_overlap: status=mapping_blocked_after_roster_recovery | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.
- Blockers or remaining uncertainties: released split artifacts are published, but the identifiers are not bridged into warehouse-native protein refs
- Recommended ProteoSphere treatment: Keep this as a `uniref_grouped` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/szymborski2022rapppid.json

### GraphPPIS (graphppis2021)

- DOI: `https://doi.org/10.1093/bioinformatics/btab643`
- Journal/year: `Bioinformatics` / `2021`
- Benchmark family: `ppis_train335_family`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btab643
- Claimed split or evaluation design: GraphPPIS is the anchor PPIS benchmark paper for the Train_335/Test_60/Test_315/UBtest_31 family and the official release ships the exact datasets.
- Recovered evidence: Benchmark anchor for the PPIS family; useful as a control because it is paper-faithful and the main concern is later family saturation, not a proven split failure here.
- What the paper said it did about bias, leakage, or split safety: paper_faithful_external
- ProteoSphere mitigation reading: passes control check. This paper is useful because the analyzer can validate it as comparatively well-designed instead of flagging everything
- Exact failure class: 
- Overlap detail fields: direct_overlap: status=published_not_mirrored | accession_root_overlap: status=published_not_mirrored | uniref_overlap: status=theoretically_supported
- Contamination or control reading: This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits. The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers. Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization.
- Blockers or remaining uncertainties: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run
- Recommended ProteoSphere treatment: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred.
- Provenance notes: Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code. Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available. No raw/archive fallback was used.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/graphppis2021.json

### Improved Protein-Ligand Binding Affinity Prediction with Structure-Based Deep Fusion Inference (deep_fusion_inference2021)

- DOI: `https://doi.org/10.1021/acs.jcim.0c01306`
- Journal/year: `Journal of Chemical Information and Modeling` / `2021`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1021/acs.jcim.0c01306 | https://github.com/LLNL/fast
- Claimed split or evaluation design: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: The paper keeps the standard core-set comparison for literature continuity but also adds a temporal plus 3D structure-clustered holdout for novel protein targets.
- What the paper said it did about bias, leakage, or split safety: The paper keeps the standard core-set comparison for literature continuity but also adds a temporal plus 3D structure-clustered holdout for novel protein targets.
- ProteoSphere mitigation reading: passes control check. This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt
- Exact failure class: 
- Contamination or control reading: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Recommended ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.
- Provenance notes: This control was kept intentionally to avoid turning the review into a one-sided takedown.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/deep_fusion_inference2021.json

### PotentialNet for Molecular Property Prediction (potentialnet2018)

- DOI: `https://doi.org/10.1021/acscentsci.8b00507`
- Journal/year: `ACS Central Science` / `2018`
- Benchmark family: `mitigation_aware_control`
- Manuscript role: `Fairness control showing that ProteoSphere does not over-flag`
- Official evidence links: https://doi.org/10.1021/acscentsci.8b00507
- Claimed split or evaluation design: The paper explicitly adds a mitigation-aware split or clustering strategy aimed at measuring genuine generalization.
- Recovered evidence: PotentialNet explicitly proposes sequence- and structure-homology-clustered cross-validation to measure generalizability more honestly.
- What the paper said it did about bias, leakage, or split safety: PotentialNet explicitly proposes sequence- and structure-homology-clustered cross-validation to measure generalizability more honestly.
- ProteoSphere mitigation reading: passes control check. This paper is a useful fairness control because the mitigation directly addresses one of the failure modes highlighted elsewhere in the hunt
- Exact failure class: 
- Contamination or control reading: No Tier 1 promotion was attempted because the paper includes a meaningful mitigation strategy.
- Recommended ProteoSphere treatment: Use as a fairness control in the review paper to show that the analyzer distinguishes better split design from leakage-prone benchmarking.
- Provenance notes: This control was kept intentionally to avoid turning the review into a one-sided takedown.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/potentialnet2018.json

## candidate_needs_more_recovery

### AttentionDTA: drug-target binding affinity prediction by sequence-based deep learning with attention mechanism (attentiondta2024)

- DOI: `https://doi.org/10.1109/TCBB.2022.3170365`
- Journal/year: `IEEE/ACM Transactions on Computational Biology and Bioinformatics` / `2024`
- Benchmark family: `needs_more_recovery`
- Manuscript role: `Transparency-only recovery backlog entry`
- Official evidence links: https://doi.org/10.1109/TCBB.2022.3170365 | https://github.com/zhaoqichang/AttentionDTA_TCBB
- Claimed split or evaluation design: The paper is relevant, but the current run did not recover enough split evidence to classify it fairly.
- What the paper said it did about bias, leakage, or split safety: no explicit mitigation claim was recovered.
- ProteoSphere mitigation reading: unknown. This candidate stays out of the flagship argument until the split lineage or mitigation story is clearer
- Exact failure class: 
- Blockers or remaining uncertainties: The repository exposes the datasets but not enough split provenance to prove whether the paper inherits a warm-start split or uses something colder.
- Recommended ProteoSphere treatment: Do not use in the main review narrative until the split is reconstructed or the mitigation story is verified.
- Provenance notes: Kept as backlog to remain truthful rather than guessing from an incomplete public trail.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/attentiondta2024.json

### Predicting Drug-Target Affinity by Learning Protein Knowledge From Biological Networks (msf_dta2023)

- DOI: `https://doi.org/10.1109/JBHI.2023.3240305`
- Journal/year: `IEEE Journal of Biomedical and Health Informatics` / `2023`
- Benchmark family: `needs_more_recovery`
- Manuscript role: `Transparency-only recovery backlog entry`
- Official evidence links: https://doi.org/10.1109/JBHI.2023.3240305
- Claimed split or evaluation design: The paper is relevant, but the current run did not recover enough split evidence to classify it fairly.
- What the paper said it did about bias, leakage, or split safety: no explicit mitigation claim was recovered.
- ProteoSphere mitigation reading: unknown. This candidate stays out of the flagship argument until the split lineage or mitigation story is clearer
- Exact failure class: 
- Blockers or remaining uncertainties: The paper is interesting, but the public evidence located in this run is still too weak to prove whether the headline split is warm-start or mitigation-aware.
- Recommended ProteoSphere treatment: Do not use in the main review narrative until the split is reconstructed or the mitigation story is verified.
- Provenance notes: Kept as backlog to remain truthful rather than guessing from an incomplete public trail.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/msf_dta2023.json

### NerLTR-DTA: drug-target binding affinity prediction based on neighbor relationship and learning to rank (nerltr_dta2022)

- DOI: `https://doi.org/10.1093/bioinformatics/btac048`
- Journal/year: `Bioinformatics` / `2022`
- Benchmark family: `needs_more_recovery`
- Manuscript role: `Transparency-only recovery backlog entry`
- Official evidence links: https://doi.org/10.1093/bioinformatics/btac048 | https://github.com/Li-Hongmin/NerLTR-DTA
- Claimed split or evaluation design: The paper is relevant, but the current run did not recover enough split evidence to classify it fairly.
- What the paper said it did about bias, leakage, or split safety: no explicit mitigation claim was recovered.
- ProteoSphere mitigation reading: unknown. This candidate stays out of the flagship argument until the split lineage or mitigation story is clearer
- Exact failure class: 
- Blockers or remaining uncertainties: The current repo and landing-page evidence are not yet strong enough to prove which split family underlies the headline results.
- Recommended ProteoSphere treatment: Do not use in the main review narrative until the split is reconstructed or the mitigation story is verified.
- Provenance notes: Kept as backlog to remain truthful rather than guessing from an incomplete public trail.
- Raw or archive fallback required in this paper-level artifact: no.
- Primary per-paper artifact: artifacts/status/literature_hunt_deep_review/nerltr_dta2022.json

