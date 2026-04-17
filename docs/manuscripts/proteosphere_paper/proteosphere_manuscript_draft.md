# ProteoSphere: A Compact Evidence Warehouse and Dataset Reviewer for Biomolecular Interaction Machine Learning

## Abstract

Reliable machine-learning benchmarks in biomolecular interaction research depend on train/test partitions that remain independent at the level of biological identity, family similarity, structure context, and provenance. In practice, those conditions are difficult to verify because many papers inherit benchmark families, recover only partial split artifacts, or evaluate on nominally external panels whose biological overlap is not obvious from paper prose alone. We present ProteoSphere, a warehouse-first dataset reviewer built around a compact, release-pinned evidence library, a `best_evidence` logical view, and code-driven audit routines for overlap, provenance, admissibility, and mitigation review. ProteoSphere is designed to keep the evidence surface small enough for routine evaluation while preserving lineage to richer raw and archive sources when deeper forensic recovery is required. The current library exposes a validated warehouse rooted at `D:\ProteoSphere\reference_library`, defaulting to `best_evidence`, with 13 materialized record families spanning proteins, variants, structures, ligands, interaction edges, site/domain annotations, pathway roles, provenance, materialization routes, leakage groups, and similarity signatures. In a proof-backed literature hunt, ProteoSphere confirmed 29 Tier 1 hard-failure papers, including 18 published in 2023 or later, and recovered complete local article bundles for all 29 papers together with 119 supplemental or supporting evidence files. The strongest cases include direct split reuse, invalid external validation, warm-start benchmark inheritance, and protein-overlapped “external” benchmark families. We present these results constructively: many audited papers address important scientific problems, but their reported generalization is often narrower than the benchmark framing suggests. ProteoSphere therefore functions as a dataset reviewer rather than a takedown tool: it can flag unsafe evaluation claims, preserve paper-faithful audit lanes, and also validate stronger, mitigation-aware benchmark practice. The manuscript argues that compact, provenance-aware dataset review should become a routine part of biomolecular interaction ML evaluation.

## Introduction

Machine learning for biomolecular interactions has matured quickly across protein-protein interaction prediction, protein-ligand affinity modeling, interface-site prediction, mutation-effect estimation, and multimodal structure-aware learning. That growth has been scientifically productive, but it has also made benchmark interpretation harder. Modern papers often inherit public splits, release only partial artifact trails, or frame external panels as independent even when the underlying biological entities, partners, or structural contexts are not actually cleanly separated. These problems rarely look dramatic at the level of headline metrics, yet they materially affect what a result means.

The practical challenge is that dataset review is expensive. A convincing audit usually requires accession-aware joins, structure grounding, benchmark-family recovery, released-code inspection, and a governed distinction between direct evidence, derived evidence, and scrape-derived enrichment. Many research groups therefore do not run a dedicated review pass at all, or they perform one only for especially controversial benchmarks. ProteoSphere was built to reduce that cost by putting a compact, release-pinned evidence warehouse in front of a much larger raw estate, then pairing that warehouse with explicit audit logic for leakage, provenance sufficiency, and admissibility.

This paper makes two linked contributions. First, it describes ProteoSphere as a practical systems contribution: a warehouse-first reference library and runtime that support dataset review without requiring every workflow to reopen the full upstream corpus. Second, it presents ProteoSphere as a scientific review tool: a positive, evidence-backed audit of recent biomolecular interaction ML papers showing that serious dataset-design failures remain current and consequential. The central message is not that the field is careless. It is that benchmark interpretation still needs better tooling, and that such tooling can be rigorous without being adversarial.

![Figure 1. ProteoSphere system overview.]({{FIGURE_1_PATH}})

## Why Dataset Review Is Still Needed In Interaction ML

Dataset review remains difficult because independence is multidimensional. A train/test boundary can look reasonable at the row level while still reusing the same drug, target, chain, antigen, receptor, protein family, structural context, or interaction neighborhood across partitions. Likewise, an “external” panel may look independent by source name while still overlapping heavily with the training pool once accessions, chains, or partner identities are resolved. These are not hypothetical concerns in ProteoSphere’s current audit corpus. They are recurring failure modes recovered from released code, released split files, supplementary tables, and benchmark lineages that continue to appear in recent papers.

The challenge is compounded by the fact that many papers are not directly comparable. Some fail because their released split logic is leakage-prone. Others inherit a benchmark family that was already unsafe for the claim being made. Still others are scientifically interesting but under-documented, meaning the correct scientific action is to soften interpretation rather than to declare the work invalid. A useful reviewer must therefore separate different failure classes rather than flattening them into a single bucket.

ProteoSphere treats these distinctions as first-class. Its results are strongest when framed in three layers: paper-specific split bugs, inherited benchmark-family failures, and mitigation-aware controls. That framing is central to the manuscript because it makes the review more scientifically fair and more useful to researchers who want to improve benchmarks rather than merely criticize them.

## ProteoSphere Architecture And Evidence Model

{{METHODS_SYSTEMS}}

![Figure 2. Large source estate and compact warehouse-first evidence surface.]({{FIGURE_2_PATH}})

The compactness claim can also be stated concretely in the current environment. The checked-in source-coverage matrix records 53 tracked sources and 324,755,949,775 present bytes in the broader tracked source estate, while the manuscript build's live storage ledger measures the active warehouse root at 74.2 GB, the repository `data/raw` path at 1.6 TB, and the incoming-mirror path at 1.5 TB ([source_coverage_matrix.md](D:\documents\ProteoSphereV2\docs\reports\source_coverage_matrix.md) and [proteosphere_paper_storage_ledger.md](D:\documents\ProteoSphereV2\docs\reports\proteosphere_paper_storage_ledger.md)). These measurements are intentionally described as current local footprints rather than release-bound package sizes, but they still show why a warehouse-first review surface is practical in day-to-day research use.

## Audit Logic: What Constitutes A Red Flag

ProteoSphere’s decision logic is deliberately conservative. A red flag does not require proof that a published result is useless; it requires proof that the split or validation design is too entangled to support the specific generalization claim being made. The main failure classes used in the current manuscript are:

- direct structure or entity reuse across train/test;
- accession-root or exact-sequence reuse across nominally independent lanes;
- family or benchmark-level reuse that preserves the same biological entities across partitions;
- partner, receptor, antigen, or ligand-core reuse that narrows the effective generalization claim;
- invalid external validation, where a panel presented as external still overlaps substantially with the training pool;
- under-documented or incompletely recoverable splits that should remain audit-only rather than canonical.

These classes are intentionally broader than “duplicate rows.” The goal is to reflect how biomolecular ML claims are actually made. A model that sees the same target repeatedly under different pair rows is not being tested in the same way as a model evaluated on a truly unseen target family. Similarly, a structure-based model evaluated on an “external” set with direct protein overlap is not being tested in the same way as one evaluated on a cold-target or time-split design.

![Figure 3. ProteoSphere review logic and red-flag taxonomy.]({{FIGURE_3_PATH}})

## Literature Hunt And Evidence Standards

The literature hunt was designed to favor strong journals, explicit split artifacts, and recoverable evidence surfaces. Papers were promoted to the current Tier 1 proof set only when official or recoverable evidence supported a hard-failure conclusion under ProteoSphere logic. If evidence was incomplete or mitigation could not be falsified, the paper remained in a supporting or backlog tier. This matters for credibility: the paper is not claiming that every suspicious benchmark is broken, only that the recovered proof set is large enough and recent enough to justify adoption of a dedicated reviewer.

The current audit package includes the local paper corpus, supplemental bundles, and machine-readable proof artifacts needed to reproduce the headline claims. For the Tier 1 set, all 29 article PDFs are locally available and paired with 119 supplemental or supporting evidence items. This makes the current manuscript unusually inspectable for a benchmark-review paper: the strongest claims are attached to local, re-openable artifacts rather than to one-off notes or unverifiable anecdotes.

## Results

{{RESULTS_CASES}}

![Figure 4. Tier 1 landscape across years, domains, and issue families.]({{FIGURE_4_PATH}})

![Figure 5. Flagship case studies.]({{FIGURE_5_PATH}})

![Figure 6. Controls and constructive use of the reviewer.]({{FIGURE_6_PATH}})

## Discussion

The main result of this study is not simply that leakage exists. It is that a compact, warehouse-first reviewer can recover multiple distinct and currently relevant benchmark failures in a reproducible way, while also distinguishing those failures from stronger or more carefully mitigated evaluation designs. That combination matters for adoption. Researchers are unlikely to use a tool that only tells them that everything is bad. They are more likely to use a tool that helps them decide what a benchmark can and cannot support.

The paper also suggests a constructive reinterpretation of many audited results. Several benchmark families remain useful as paper-faithful audit lanes, ablation environments, or historical comparators even when they are not safe as governing evidence for unseen-entity or clean external generalization. Likewise, papers that address important scientific questions should not be discarded simply because their evaluation lanes are narrower than their prose implies. The reviewer’s role is to clarify scope, not to erase value.

The compactness story is similarly important when stated carefully. ProteoSphere demonstrates that a release-pinned, warehouse-first evidence surface can support routine dataset review without carrying every raw payload into every workflow. In the current local environment, the tracked source estate is already large by any practical standard, and the warehouse root is much smaller than the combined raw and incoming-mirror footprints. That difference is scientifically useful because it makes repeated review feasible. At the same time, the current evidence still supports only a bounded claim: the compact warehouse is operationally effective for warehouse-first review, but not yet a full evidence-equivalent replacement for every raw artifact surface.

This distinction is healthy rather than problematic. It means the reviewer can remain honest about what is fast, what is canonical, and when a deeper forensic recovery lane is still needed. In practice, that is exactly how a review system should behave in a live research environment.

## Limitations

This manuscript has four important limits.

First, the strongest Tier 1 proof set remains concentrated in protein-ligand / DTA and PDBbind-style benchmark families, with a smaller but still important protein-protein subset. That concentration reflects the currently recovered evidence, not a claim about the entire biomolecular interaction literature.

Second, not every Tier 1 paper represents the same kind of failure. Struct2Graph and AttentionDTA expose paper-specific split logic problems. DeepDTA-setting-1 and PDBbind-core show inherited benchmark-family liabilities. D2CP05644E demonstrates overlap-contaminated external panels. The paper is strongest when these are treated as distinct categories rather than as interchangeable faults.

Third, the warehouse is not yet fully evidence-equivalent to every raw artifact surface. The local equivalence review shows that top-level outcomes match across the current validation set, but deeper roster reconstruction, structure-level overlap reproduction, and some identifier-bridge-heavy cases still require broader artifacts.

Fourth, the current manuscript is intentionally conservative about prevalence. It presents a proof-backed sample of recurring failure modes, not a field-wide prevalence estimate.

## Methods

ProteoSphere was evaluated in a warehouse-first configuration rooted at `D:\ProteoSphere\reference_library`, using `best_evidence` as the default logical view. The governing inputs for this manuscript were the warehouse summary, warehouse manifest, source registry, release/storage strategy reports, runtime/library code, the Tier 1 literature-hunt summaries, the paper-source bundle, and the flagship proof artifacts for Struct2Graph, D2CP05644E, DeepDTA-setting-1, PDBbind-core, and AttentionDTA. Quantitative claims were included only when they could be traced to a local artifact or to a report generated from local filesystem measurements during this manuscript build.

The systems section was written from the release/storage and runtime/library artifacts. The results section was written from the machine-readable Tier 1 review summaries and flagship proof artifacts. A skeptical review pass was then used to remove or soften overstatements, especially around compression claims, field-wide prevalence, and distinctions between paper-specific and benchmark-family failures. Figure generation and manuscript packaging were performed locally from the same evidence bundle so the PDF package and the claim ledger share a common source base.

## Data And Code Availability

The manuscript package produced in this workspace includes:

- a main manuscript draft;
- a supplementary appendix with the Tier 1 paper table and evidence notes;
- a PI-oriented briefing memo;
- a claim ledger;
- a figure manifest and generated figure set;
- PDF renderings of the main draft, supplement, and briefing note.

The local evidence surfaces used for the manuscript are listed explicitly in the figure manifest and claim ledger. The Tier 1 paper corpus is locally bundled under the source-bundle output, and the flagship proof artifacts are preserved as machine-readable JSON or report files within the repository outputs.

## References

1. ProteoSphere source release matrix. [source_release_matrix.md](D:\documents\ProteoSphereV2\docs\reports\source_release_matrix.md)
2. ProteoSphere source storage strategy. [source_storage_strategy.md](D:\documents\ProteoSphereV2\docs\reports\source_storage_strategy.md)
3. Lightweight reference library master plan. [lightweight_reference_library_master_plan.md](D:\documents\ProteoSphereV2\docs\reports\lightweight_reference_library_master_plan.md)
4. Warehouse summary. [warehouse_summary.json](D:\ProteoSphere\reference_library\warehouse_summary.json)
5. Warehouse manifest. [warehouse_manifest.json](D:\ProteoSphere\reference_library\warehouse_manifest.json)
6. Source registry. [source_registry.json](D:\ProteoSphere\reference_library\control\source_registry.json)
7. Library versus broad collection equivalence review. [library_vs_broad_collection_equivalence.md](D:\documents\ProteoSphereV2\docs\reports\library_vs_broad_collection_equivalence.md)
8. Source coverage matrix. [source_coverage_matrix.md](D:\documents\ProteoSphereV2\docs\reports\source_coverage_matrix.md)
9. Tier 1 master summary. [literature_hunt_tier1_master_summary.json](D:\documents\ProteoSphereV2\artifacts\status\literature_hunt_tier1_master_summary.json)
10. Tier 1 source bundle summary. [literature_hunt_tier1_source_bundle.md](D:\documents\ProteoSphereV2\docs\reports\literature_hunt_tier1_source_bundle.md)
11. Struct2Graph reproduced overlap report. [struct2graph_reproduced_overlap.md](D:\documents\ProteoSphereV2\docs\reports\struct2graph_reproduced_overlap.md)
12. D2CP05644E quality assessment. [paper_d2cp05644e_quality_assessment.md](D:\documents\ProteoSphereV2\docs\reports\paper_d2cp05644e_quality_assessment.md)
13. DeepDTA-setting-1 family audit. [dta_setting1_family_audit.json](D:\documents\ProteoSphereV2\artifacts\status\literature_hunt_deep_proofs\dta_setting1_family_audit.json)
14. PDBbind core-family audit. [pdbbind_core_family_audit.json](D:\documents\ProteoSphereV2\artifacts\status\literature_hunt_deep_proofs\pdbbind_core_family_audit.json)
15. AttentionDTA random-CV family audit. [attentiondta_random_cv_family_audit.json](D:\documents\ProteoSphereV2\artifacts\status\literature_hunt_recent_expansion_proofs\attentiondta_random_cv_family_audit.json)
16. Baranwal C, et al. Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions. BMC Bioinformatics. 2022. [https://doi.org/10.1186/s12859-022-04910-9](https://doi.org/10.1186/s12859-022-04910-9)
17. Silva DA, et al. An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties. Phys Chem Chem Phys. 2023. [https://doi.org/10.1039/D2CP05644E](https://doi.org/10.1039/D2CP05644E)
18. Ozturk H, et al. DeepDTA: deep drug-target binding affinity prediction. Bioinformatics. 2018. [https://doi.org/10.1093/bioinformatics/bty593](https://doi.org/10.1093/bioinformatics/bty593)
19. Nguyen T, et al. GraphDTA: predicting drug-target binding affinity with graph neural networks. Bioinformatics. 2021. [https://doi.org/10.1093/bioinformatics/btaa921](https://doi.org/10.1093/bioinformatics/btaa921)
20. Zhao Q, et al. AttentionDTA: drug-target binding affinity prediction by sequence-based deep learning with attention mechanism. IEEE/ACM Trans Comput Biol Bioinform. 2023. [https://doi.org/10.1109/TCBB.2022.3170365](https://doi.org/10.1109/TCBB.2022.3170365)
