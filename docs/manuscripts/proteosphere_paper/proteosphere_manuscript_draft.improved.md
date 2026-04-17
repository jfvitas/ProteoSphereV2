# ProteoSphere: A Compact Evidence Warehouse and Dataset Reviewer for Biomolecular Interaction Machine Learning

## Abstract

**Motivation.** Machine learning benchmarks for protein–protein and protein–ligand interaction are increasingly difficult to interpret. Train/test partitions can look independent at the row level while reusing the same entity, structure, partner, or benchmark family across lanes, and nominally external panels are often not independent of training data once accessions and chains are resolved. Auditing these conditions is expensive, so most groups rely on the split artifacts distributed with each paper.

**Results.** We present **ProteoSphere**, a warehouse-first dataset reviewer for biomolecular interaction ML. A release-pinned reference library materializes thirteen compact record families — proteins, variants, PDB entries, structure units, ligands, protein–ligand and protein–protein edges, site/domain annotations, pathway roles, provenance claims, materialization routes, leakage groups, and similarity signatures — and exposes a default `best_evidence` logical view in front of a much larger raw estate. A code-driven audit layer resolves split policies, computes overlap at the accession, sequence, UniRef-cluster, structure, and shared-partner levels, and assigns one of six admissibility verdicts. In a proof-backed literature hunt we confirmed **29 Tier 1 hard-failure papers**, 18 of them published in 2023 or later, spanning four recurring failure classes: direct cross-partition reuse, warm-start benchmark inheritance, protein-overlapped "external" panels, and row-level random cross-validation leakage. Flagship cases include Struct2Graph (643 shared PDB IDs across released train/test), Silva *et al.* 2023 (all three external panels contaminated by direct-protein, exact-sequence, and shared-partner overlap), the DeepDTA setting-1 lineage (all test drugs and targets shared with training on both Davis and KIBA), the PDBbind core-set family (288 of 290 complexes in v2016 carry direct protein overlap), and AttentionDTA (all drug and target entities retained on Davis and KIBA, and 1,206 of 1,214 drugs plus all targets retained on Metz).

**Conclusions.** Compact, provenance-aware dataset review can be run as a routine part of biomolecular interaction ML evaluation rather than as an exceptional forensic exercise. ProteoSphere identifies unsafe generalization claims, preserves paper-faithful audit lanes, and certifies mitigation-aware benchmarks; it is a dataset reviewer, not a takedown tool.

**Availability.** Warehouse, runtime, audit reports, and the full Tier 1 proof bundle are released with the manuscript.

## 1. Introduction

Biomolecular interaction prediction — protein–protein interaction (PPI), drug–target affinity (DTA), interface-site prediction, mutation-effect estimation — has made rapid progress, but benchmark interpretation has not kept pace. Leakage in these domains is multidimensional. A partition can be row-disjoint yet reuse the same drug, target, chain, epitope, or benchmark family across lanes. An "external" panel can share its accessions with training once chains and sequences are resolved. A random cross-validation split, applied after shuffling an interaction table, can allow every compound and target to recur on both sides of each fold. None of these conditions is visible from reported metrics, and only some are visible from the paper text.

Two forces have made audits more, not less, necessary over the past five years. First, public benchmark families (PDBbind core, Davis, KIBA, DeepDTA setting-1) are inherited verbatim by downstream papers, so a single upstream design choice propagates into dozens of later claims. Second, released artifact trails are often partial: split CSVs without their generating code, generating code without their source tables, or supplementary panels whose provenance is cited only narratively. A reviewer who wants to check a single paper's split logic frequently has to reconstruct it from three or four sources spanning hundreds of gigabytes.

ProteoSphere is built around the observation that most of this reconstruction is repetitive. The same accession joins, structure lookups, UniRef cluster queries, and partner-graph walks are needed across audits. A compact, release-pinned evidence warehouse — small enough to keep hot, rich enough to answer overlap questions deterministically — removes most of that cost. The same warehouse then supports a code-driven audit layer that maps each paper to a canonical split policy, computes overlap at multiple biological levels, and assigns a verdict under an explicit reason-code catalog.

This paper makes three contributions.

1. A **systems** contribution: a warehouse-first reference library, a `best_evidence` claim surface, and a runtime that keeps dataset review tractable without demanding the full raw source estate at each call.
2. A **methodological** contribution: a canonical set of split policies, overlap measurements, reason codes, and verdict classes that make interaction-ML dataset review reproducible across papers and labs.
3. An **empirical** contribution: a proof-backed audit of 29 recent hard-failure papers in PPI and DTA, organized into four failure classes and grounded in recoverable artifacts.

We present the empirical results constructively. Several of the audited papers address real scientific problems; what our audit narrows is the *scope of the generalization claim* each paper can support, not the value of the underlying work.

![Figure 1. ProteoSphere system overview.]({{FIGURE_1_PATH}})

## 2. Background: why interaction-ML dataset review is hard

Independence, in this domain, has at least five distinguishable layers:

- **Row identity.** The same (drug, target) or (chain-a, chain-b) pair recurs across partitions.
- **Accession identity.** Row tuples differ, but one or both components are the same UniProt accession or PDB chain.
- **Family similarity.** Accessions differ but share a UniRef cluster, a SCOP superfamily, or a Pfam domain architecture.
- **Structural context.** Accessions differ but the complexes share partners, binding modes, or conformational ensembles.
- **Benchmark-family inheritance.** A split's biological entities are determined upstream, by a public split distributed with an earlier paper.

A convincing audit must address all five, and no single artifact contains the information needed to do so. Sequence identity requires UniProt; family similarity requires UniRef; structural context requires RCSB/PDBe/AlphaFold; partner overlap requires IntAct/BioGRID; benchmark-family inheritance requires the original split manifest plus the generating code. ProteoSphere's warehouse materializes these surfaces jointly so an overlap query can be answered from one place.

## 3. System design

### 3.1 Release-pinned source contract

The source contract is release-aware rather than live-web aware, and is organized at two scopes. The **warehouse scope** — the twelve sources whose records are directly resolved through the warehouse manifest — anchors identity, structure, and interaction evidence: UniProt and UniParc for sequence identity; RCSB/PDBe and AlphaFold DB for structure; BindingDB, IntAct, and SABIO-RK for interaction and assay evidence; PDBbind for protein–ligand affinity; STRING for interaction edges; ELM for short linear motifs; and two curated motif corpora (MEGA Motif Base, Motivated Proteins) for structural-site context. The **broader tracked-estate scope** — recorded in the repository's source-coverage matrix — currently enumerates 53 sources used at any point in recovery or audit, including BioGRID, InterPro, DisProt, Reactome, EMDB, SIFTS, BioLiP, Pfam, and SCOP. An evolutionary-profile lane is explicitly pending for the warehouse scope.

Governance is strict. The warehouse manifest's public-export policy names only five sources as publicly redistributable (UniProt, RCSB/PDBe, AlphaFold, IntAct, ELM). All other warehouse sources — including BindingDB, PDBbind, STRING, UniParc, SABIO-RK, and the two motif corpora — are held `internal_only` and excluded from public bundles. Every downstream claim is traceable to one release-stamped source entry at whichever scope it applies.

### 3.2 Warehouse and `best_evidence` view

The warehouse is rooted at a pinned filesystem path and materializes thirteen record families (Table 1). Each record preserves three claim surfaces — `raw`, `derived_or_scraped`, and `best_evidence` — and a conflict summary that reports disagreement across surfaces. The default projection is `best_evidence`: alternative claims remain inspectable when a workflow opts in, but the default query answers with the most defensible single value.

Storage is organized in six tiers: pinned manifest, planning index, canonical store, feature cache, deferred materialization, and a narrow scrape-only enrichment lane. Heavy payloads — raw mmCIF, map volumes, full PSI-MI/XML, multiple-sequence alignments — stay deferred until a candidate is selected. Compactness comes from this separation, not from dropping provenance.

**Table 1.** Warehouse families currently materialized.

| Family | Role |
|---|---|
| proteins | canonical sequence identity spine |
| protein_variants | allelic and mutational variants |
| pdb_entries | PDB header, release, and experimental metadata |
| structure_units | chains, assemblies, and biological units |
| ligands | small-molecule identity and chemotype |
| protein_ligand_edges | affinity and binding assertions |
| protein_protein_edges | PPI assertions with evidence tags |
| motif_domain_site_annotations | InterPro, ELM, DisProt sites |
| pathway_roles | Reactome and related context |
| provenance_claims | source release stamps per record |
| materialization_routes | registry-anchored retrieval routes |
| leakage_groups | precomputed identity and family cohorts |
| similarity_signatures | sequence and structure signatures |

### 3.3 Runtime and audit layer

The runtime exposes the warehouse as a first-class training-set gate. Candidate rows carry their accession grounding, custom-manifest identifiers, and UniRef cluster hints; the split compiler computes accession-level overlap between train-plus-validation and test, and blocks any split with direct protein overlap. Materialization routes are resolved through the source registry rather than through mutable local paths, so release stamps propagate end-to-end.

The audit layer wraps the warehouse in a policy-resolution step and an overlap-measurement step. Each paper is mapped to one of six canonical split policies (`paper_faithful_external`, `accession_grouped`, `uniref_grouped`, `protein_ligand_component_grouped`, `unresolved_policy`, or a paper-specific variant). Overlap is computed at row, accession, exact-sequence, UniRef-cluster, and shared-partner levels. A reason-code catalog — including DIRECT_OVERLAP, ACCESSION_ROOT_OVERLAP, UNIREF_CLUSTER_OVERLAP, SHARED_PARTNER_LEAKAGE, POLICY_MISMATCH, UNRESOLVED_SPLIT_MEMBERSHIP, and WAREHOUSE_COVERAGE_GAP — combines with the policy to yield one of six verdicts: `usable`, `usable_with_caveats`, `audit_only`, `blocked_pending_mapping`, `blocked_pending_cleanup`, or `unsafe_for_training`.

![Figure 2. Source estate versus warehouse-first evidence surface.]({{FIGURE_2_PATH}})

### 3.4 Footprint in the current environment

The tracked source estate in the current build records 53 sources with 324,755,949,775 present bytes (≈302 GiB, or 324.8 decimal GB); the manuscript's live storage ledger measures the active warehouse root at 74.2 GB, `data/raw` at 1.6 TB, and the incoming-mirror path at 1.5 TB. These are environment measurements rather than release-bound package sizes, but they illustrate why a warehouse-first review surface is practical in day-to-day use: a routine audit touches tens of gigabytes, not terabytes.

## 4. Audit logic

### 4.1 Red-flag taxonomy

A red flag in ProteoSphere does not assert that a model is useless. It asserts that the split or validation design is too entangled to support the specific generalization claim the paper makes. We classify entanglement into six failure classes:

1. direct structure or entity reuse across train/test;
2. accession-root or exact-sequence reuse across nominally independent lanes;
3. benchmark-family reuse preserving biological entities across partitions;
4. partner, receptor, antigen, or ligand-core reuse narrowing the effective claim;
5. invalid external validation, where an "external" panel overlaps substantially with the training pool;
6. under-documented or incompletely recoverable splits, held as audit-only rather than canonical.

### 4.2 Verdicts

The verdict space is deliberately narrow and monotonic (Figure 3). `usable` requires a resolved policy, no unmapped entities, and no overlap at any audited level. `usable_with_caveats` retains usability subject to a declared caveat (e.g., retained shared-partner overlap with documented mitigation). `audit_only` reserves a split as a paper-faithful reproduction lane without endorsing it as governing evidence. `blocked_pending_mapping` and `blocked_pending_cleanup` are recoverable states. `unsafe_for_training` is terminal.

![Figure 3. Audit decision ladder.]({{FIGURE_3_PATH}})

### 4.3 Human-review gate

Human review is triggered only for genuine ambiguity: conflicting provenance claims that the `best_evidence` view cannot reconcile, split manifests whose generating code is missing, or panels whose external status depends on an unverified assertion. Deterministic failures — a policy mismatch, an observed direct overlap, an unresolved cohort — do not escalate; they resolve to their verdict immediately.

## 5. Literature hunt: design and evidence standards

We assembled a Tier 1 proof set under a conservative admission standard: a paper was promoted only when its split or external panel could be recovered from a local artifact or an official source and then re-evaluated under ProteoSphere's policy and overlap logic. When evidence was partial, mitigation could not be falsified, or the generating code was unavailable, the paper was held in a supporting tier rather than promoted.

For every Tier 1 paper, the local bundle contains the article PDF and the supplementary or supporting files needed to reproduce the audit. The current bundle contains all 29 article PDFs and 119 supplemental items. The manuscript and its claim ledger are anchored to these artifacts rather than to narrative summaries.

## 6. Results

### 6.1 Yield and composition

The Tier 1 proof set contains 29 hard-failure papers; 18 were published in 2023 or later. By issue family, 14 papers inherit warm-start benchmark liabilities, 12 inherit protein-overlapped external panels, and the remaining three are distributed across direct cross-partition reuse, row-level random-CV leakage, and invalid external validation. By domain, 93% are protein–ligand / DTA and 7% are protein–protein. That concentration reflects where benchmark inheritance is densest; it is a scope boundary, not a claim about the field as a whole.

![Figure 4. Tier 1 landscape.]({{FIGURE_4_PATH}})

### 6.2 Flagship cases

**Table 2.** Flagship cases and their governing overlap measurements.

| Paper / family | Class | Key overlap | Verdict |
|---|---|---|---|
| Struct2Graph (Baranwal *et al.*, 2022) | paper-specific direct reuse | 643 shared PDB IDs across reproduced 8,003 train / 1,000 test; 4EQ6 appears 78× in train, 9× in test | `unsafe_for_training` |
| Silva *et al.*, 2023 (D2CP05644E) | invalid external validation | PDBbind test: 4 direct / 4 exact-sequence / 110 shared-partner; nanobody: 1 / 1 / 16 on P00698; metadynamics: 26 / 26 / 75 | all three panels `blocked_pending_cleanup` |
| DeepDTA setting-1 lineage | warm-start benchmark family | Davis: all 68 test drugs, all 442 test targets shared; KIBA: all 2,027 / 229 shared | `unsafe_for_training` (inherited by 14 Tier 1 papers) |
| PDBbind core-set family | protein-overlapped external family | v2016: 288/290 test complexes overlap, 77 shared accessions; v2013: 108/108, 50 shared | `audit_only` as governing evidence (inherited by 12 Tier 1 papers) |
| AttentionDTA (Zhao *et al.*, 2023) | paper-specific random-CV leakage | Davis: 68/68 test drugs, 367/367 test targets shared; KIBA: 2,054/2,054 and 229/229; Metz: 1,206/1,214 drugs and 169/169 targets | `unsafe_for_training` |

**Struct2Graph** is the clearest paper-specific case. Reproducing the released `create_examples.py` with the published seed yields 8,003 train and 1,000 test rows and 643 PDB IDs shared across the partition; the highlighted 4EQ6 structure occurs 78 times in train and 9 times in test. The leakage lives in the pair-level split mechanism itself rather than in the downstream model.

**Silva *et al.* 2023** is the strongest invalid-external-validation case. A 78-structure benchmark pool reconstructed from the authors' notebook (81 rows with the notebook's explicit drops at indices 12, 14, 28) is evaluated against three external panels. All three are contaminated. The PDBbind panel (50 test structures) shares four accessions (P00698, P01112, P61769, P68135) directly, four exact sequences, and retains 110 shared-partner overlap relations against the benchmark pool. The nanobody panel (47 test structures) centers on lysozyme C (P00698), with one direct-protein and 16 shared-partner overlap relations. The metadynamics panel (19 test structures) is the most compromised: against the joint 97-structure benchmark+panel audit set, ProteoSphere records 26 direct-protein, 26 exact-sequence, and 75 shared-partner overlap relations. Under ProteoSphere logic, none of the three panels is an independent external benchmark.

**DeepDTA setting-1** is the benchmark-family exemplar. Every test drug and every test target on Davis and KIBA appears in training under the released split. This is not a criticism of DeepDTA as a modeling contribution; it is a statement about a reusable lineage that 14 later Tier 1 papers inherit.

**PDBbind core** is the parallel benchmark-family proof on the protein–ligand side. The "core" set is widely read as an external test set; under ProteoSphere's policy resolution it is a refined-to-core transfer inside a single release, and 288 of 290 complexes in v2016 carry direct protein overlap with the remaining pool. The family remains usable as a historical scoring benchmark; it is not a valid proxy for unseen-target generalization.

**AttentionDTA** shows a protocol-level failure. Shuffling the interaction table before slicing folds produces row-disjoint partitions that preserve nearly every entity across folds: all drug and target identities on Davis (68 / 367) and KIBA (2,054 / 229), and all 169 targets plus 1,206 of 1,214 drugs on Metz.

![Figure 5. Flagship case studies.]({{FIGURE_5_PATH}})

### 6.3 Controls

ProteoSphere is not a one-sided filter. Eleven papers in the current review package pass or downgrade cleanly under its logic: RAPPPID, GraphPPIS, BatchDTA, HGRL-DTA, NHGNN-DTA, PotentialNet, Deep Fusion Inference, DTA-OM, TEFDTA, DCGAN-DTA, and HAC-Net. Each either presents a mitigation-aware split (UniRef-grouped, time-split, cold-target) or restricts its claim scope to what its evaluation supports. Keeping these visible in the review package is what distinguishes a reviewer from a filter.

![Figure 6. Controls and constructive use of the reviewer.]({{FIGURE_6_PATH}})

## 7. Discussion

The empirical finding is that multiple distinct, current, and reproducible benchmark failures continue to appear across recent PPI and DTA papers, and that the same compact warehouse can separate those failures from carefully designed evaluations. Both halves matter. A reviewer that only flagged problems would be adopted reluctantly; a reviewer that also validated better practice is useful during benchmark construction, not only during post-hoc criticism.

Three boundaries deserve emphasis. First, concentration in DTA and PDBbind-style families reflects where benchmark inheritance is densest, not where audit coverage ends; antibody, peptide, protein–RNA, and protein–DNA settings are the natural next expansion. Second, the warehouse is operationally effective but not yet fully evidence-equivalent to every raw surface: top-level outcomes on the current validation set match, but deep forensic recovery still occasionally requires the raw estate. Third, this work reports a proof-backed sample of failure modes, not a field-wide prevalence estimate; a properly powered prevalence study is future work.

## 8. Limitations

1. **Scope concentration.** The Tier 1 set is dominated by protein–ligand / DTA and PDBbind-family papers. The 7% protein–protein share is real but small.
2. **Heterogeneity of failure.** The five flagship cases represent four distinct failure classes; they should not be flattened into a single "leakage" bucket.
3. **Warehouse vs. raw equivalence.** Twenty-of-twenty top-level outcomes match between the warehouse and the broader downloaded collection, but identifier-bridge-heavy and full-structure overlap cases retain a fallback to the raw estate.
4. **Prevalence vs. sample.** This is a sample of recurring modes; we do not claim field-wide prevalence.

## 9. Methods

**Warehouse.** The warehouse is rooted at a pinned filesystem path with `best_evidence` as the default logical view. The manifest materializes thirteen record families (Table 1) in a `full-local-backbone` snapshot. Runtime validation reports `status: passed` across all thirteen families in the current build.

**Audit pipeline.** Each paper is mapped to a canonical split policy; overlap is computed at row, accession, exact-sequence, UniRef-cluster, and shared-partner levels; reason codes and verdicts are assigned under a fixed catalog. An LLM bridge reviews only deterministically ambiguous cases and may only override five fields (`resolved_split_policy`, `verdict`, `reason_codes`, `needs_human_review`, `llm_rationale`); it does not run unbounded review.

**Literature hunt.** Candidate papers were harvested from recent PPI and DTA literature, prioritizing strong journals and recoverable artifact trails. Promotion to Tier 1 required that the split or external panel be reproducible from a local artifact or an official source and that the recovered evidence support a hard-failure conclusion under ProteoSphere logic.

**Reproducibility.** The manuscript package includes the warehouse manifest, source registry, runtime-validation snapshot, Tier 1 master summary, flagship proof artifacts, the claim ledger, and the figure manifest. Figures are regenerated from the same artifact bundle during the manuscript build.

## 10. Data and code availability

The warehouse, source registry, runtime, audit pipeline, Tier 1 proof bundle (article PDFs and supplemental items), claim ledger, figure manifest, and the PDFs generated from this draft are released with the manuscript. A public mirror excludes `internal_only` (STRING) and `restricted` (PDBbind) payloads; all other sources are redistributed under their upstream licenses.

## References

1. Baranwal M, *et al.* Struct2Graph: a graph attention network for structure-based prediction of protein–protein interactions. *BMC Bioinformatics* 23, 370 (2022). https://doi.org/10.1186/s12859-022-04910-9
2. Silva D-A, *et al.* An artificial neural network model to predict structure-based protein–protein free energy of binding from Rosetta-calculated properties. *Phys. Chem. Chem. Phys.* (2023). https://doi.org/10.1039/D2CP05644E
3. Öztürk H, Özgür A, Ozkirimli E. DeepDTA: deep drug–target binding affinity prediction. *Bioinformatics* 34, i821–i829 (2018). https://doi.org/10.1093/bioinformatics/bty593
4. Nguyen T, *et al.* GraphDTA: predicting drug–target binding affinity with graph neural networks. *Bioinformatics* 37, 1140–1147 (2021). https://doi.org/10.1093/bioinformatics/btaa921
5. Zhao Q, *et al.* AttentionDTA: drug–target binding affinity prediction by sequence-based deep learning with attention. *IEEE/ACM Trans. Comput. Biol. Bioinform.* (2023). https://doi.org/10.1109/TCBB.2022.3170365
6. Davis MI, *et al.* Comprehensive analysis of kinase inhibitor selectivity. *Nat. Biotechnol.* 29, 1046–1051 (2011). https://doi.org/10.1038/nbt.1990
7. Tang J, *et al.* Making sense of large-scale kinase inhibitor bioactivity data sets: a comparative and integrative analysis. *J. Chem. Inf. Model.* 54, 735–743 (2014). https://doi.org/10.1021/ci400709d
8. Wang R, *et al.* The PDBbind database: methodologies and updates. *J. Med. Chem.* 48, 4111–4119 (2005). https://doi.org/10.1021/jm048957q
9. Su M, *et al.* Comparative assessment of scoring functions: the CASF-2016 update. *J. Chem. Inf. Model.* 59, 895–913 (2019). https://doi.org/10.1021/acs.jcim.8b00545
10. Szymborski J, Emad A. RAPPPID: a deep-learning approach for protein–protein interaction prediction. *Bioinformatics* 38, 3603–3610 (2022). https://doi.org/10.1093/bioinformatics/btac429
11. Sledzieski S, *et al.* D-SCRIPT: structure-aware prediction of protein–protein interactions. *Cell Syst.* 12, 969–982 (2021). https://doi.org/10.1016/j.cels.2021.08.010
12. UniProt Consortium. UniProt: the universal protein knowledgebase in 2023. *Nucleic Acids Res.* 51, D523–D531 (2023). https://doi.org/10.1093/nar/gkac1052
13. Suzek BE, *et al.* UniRef clusters: a comprehensive and scalable alternative for improving sequence similarity searches. *Bioinformatics* 31, 926–932 (2015). https://doi.org/10.1093/bioinformatics/btu739
14. Burley SK, *et al.* RCSB Protein Data Bank: powerful new tools. *Nucleic Acids Res.* 49, D437–D451 (2021). https://doi.org/10.1093/nar/gkaa1038
15. Varadi M, *et al.* AlphaFold Protein Structure Database. *Nucleic Acids Res.* 50, D439–D444 (2022). https://doi.org/10.1093/nar/gkab1061
16. Gilson MK, *et al.* BindingDB in 2015: a public database for medicinal chemistry, computational chemistry, and systems pharmacology. *Nucleic Acids Res.* 44, D1045–D1053 (2016). https://doi.org/10.1093/nar/gkv1072
17. Oughtred R, *et al.* The BioGRID interaction database: 2021 update. *Nucleic Acids Res.* 49, D605–D612 (2021). https://doi.org/10.1093/nar/gkaa1141
18. del Toro N, *et al.* The IntAct database: efficient access to fine-grained molecular interaction data. *Nucleic Acids Res.* 50, D648–D653 (2022). https://doi.org/10.1093/nar/gkab1006
19. Blum M, *et al.* InterPro in 2022. *Nucleic Acids Res.* 51, D418–D427 (2023). https://doi.org/10.1093/nar/gkac993
20. Kulmanov M, Hoehndorf R. Evaluating the effect of data-split strategies on the offset between evaluation and deployment of machine-learning models in biology. *Brief. Bioinform.* 24, bbad065 (2023). https://doi.org/10.1093/bib/bbad065
