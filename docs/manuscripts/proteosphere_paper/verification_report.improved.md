# Verification Report: Improved Manuscript Package

## Scope

Every quantitative claim in the improved manuscript draft and supplement was
cross-checked against the local ProteoSphere audit artifacts, the warehouse
manifest, and the runtime-validation snapshot; then each flagship case was
sanity-checked against my own knowledge of the published paper's released
split logic.

## Method

1. **Artifact verification** — for each numeric claim, I loaded the backing
   JSON or Markdown artifact, extracted the relevant counts, and compared
   them to the wording in the improved draft and supplement.
2. **Independent logic check** — for each flagship paper, I reasoned about
   whether the claim is consistent with the paper's published split design
   (release notes, data README, or code pattern), independent of our local
   numbers.
3. **Governance scope check** — I inspected the warehouse manifest's
   `export_policy` block to verify the manuscript's licensing / redistribution
   language against the actual policy.

## Artifact cross-check

| Claim location | Claim | Artifact (path) | Artifact value | Status |
|---|---|---|---|---|
| Abstract + §6.1 | 29 Tier 1 papers, 18 in 2023+ | `literature_hunt_tier1_master_summary.json` → summary | `tier1_total=29`, `recent_2023plus_count=18` | **verified** |
| §6.1 | 14 warm-start / 12 protein-overlapped / 1 direct / 1 invalid-external / 1 random-CV | same | `issue_family_counts = {warm_start_benchmark_family: 14, protein_overlapped_external_family: 12, invalid_external_validation: 1, paper_specific_random_cv_leakage: 1, paper_specific_direct_reuse: 1}` | **verified** |
| §6.1 | 93% protein–ligand / 7% protein–protein | same | `domain_counts = {protein_ligand: 27, protein_protein: 2}` → 93.1% / 6.9% | **verified** |
| §5 | 29 article PDFs and 119 supplemental items locally bundled | `docs/reports/literature_hunt_tier1_source_bundle.md` | `PDFs downloaded: 29` and `Supplemental/evidence files downloaded: 119` | **verified** |
| Table 1, §3.2 | Thirteen warehouse families | `D:/ProteoSphere/reference_library/warehouse_manifest.json` | `family_count=13`; `entity_families` names match paper list 1:1; every family has `default_view="best_evidence"` | **verified** |
| §9 | Runtime validation passes | `D:/ProteoSphere/reference_library/control/runtime_validation.latest.json` | `status: passed` | **verified** |
| §3.4 + S4 | 53 tracked sources; 324.8×10⁹ B of present bytes; warehouse root 74.2 GB; `data/raw` 1.6 TB; incoming mirrors 1.5 TB | `artifacts/status/proteosphere_paper_storage_ledger.json` | `source_count=53`, `present_byte_count=324,755,949,775`, `warehouse_root=79,703,246,157 B (74.2 GB)`, `repo_data_raw=1,755,007,732,004 B (1.6 TB)`, `incoming_mirrors=1,680,590,049,469 B (1.5 TB)` | **verified** (unit convention clarified in patch below) |
| Table 2 / §6.2 | Struct2Graph: 10,004 rows → 8,003 train / 1,000 test; 643 shared PDB IDs; 4EQ6 78× train / 9× test | `docs/reports/struct2graph_reproduced_overlap.md` | Interaction rows 10,004; train 8,003; test 1,000; shared PDB IDs 643; 4EQ6 78/9 | **verified** |
| Table 2 / §6.2 | Silva 2023 PDBbind panel (50): 4 direct / 4 exact-seq / 110 shared-partner | `docs/reports/paper_d2cp05644e_quality_assessment.md` | 50 structures; 4 / 4 / 4 / 110 / verdict `blocked` | **verified** |
| Table 2 / §6.2 | Silva 2023 nanobody panel (47): 1 / 1 / 16 on P00698 | same | 47 structures; 1 / 1 / 1 / 16 / verdict `blocked`; overlap anchored to P00698 | **verified** |
| Table 2 / §6.2 | Silva 2023 metadynamics (19): 26 / 26 / 75 against joint 97-structure audit set | same | 97-structure joint audit set; 26 / 26 / 26 / 75 / verdict `blocked` | **verified** (phrasing fixed — see discrepancies) |
| Table 2 / §6.2 | DeepDTA setting-1 Davis all 68/442 test entities shared; KIBA all 2,027/229 | `literature_hunt_deep_proofs/dta_setting1_family_audit.json` | Davis: test 68/442, shared 68/442, 100% of test entities shared. KIBA: test 2,027/229, shared 2,027/229, 100% of test entities shared (training has 2,111 drugs, 84 extra only in train) | **verified** |
| Table 2 / §6.2 | PDBbind v2016 core: 288/290, 77 shared accessions; v2013: 108/108, 50 shared | `literature_hunt_deep_proofs/pdbbind_core_family_audit.json` | v2016: test 290, overlap 288, shared_accession_count 77. v2013: test 108, overlap 108, shared 50 | **verified** |
| Table 2 / §6.2 | AttentionDTA Davis 68/367; KIBA 2,054/229; Metz 1,206/169 | `literature_hunt_recent_expansion_proofs/attentiondta_random_cv_family_audit.json` | Davis shared 68/68, 367/367. KIBA shared 2,054/2,054, 229/229. Metz shared **1,206 of 1,214 test-unique drugs** and 169/169 targets | **verified** (Metz drug count made precise — see discrepancies) |
| §6.3 | Eleven controls (RAPPPID, GraphPPIS, BatchDTA, HGRL-DTA, NHGNN-DTA, PotentialNet, Deep Fusion Inference, DTA-OM, TEFDTA, DCGAN-DTA, HAC-Net) | carried from `proteosphere_literature_hunt_deep_review` + `proteosphere_literature_hunt_recent_expansion` | 11 items, names match | **verified** |

## Independent logic sanity check

| Case | Published design | Does the ProteoSphere finding follow? |
|---|---|---|
| Struct2Graph (Baranwal *et al.* 2022) | Pair-level train/test split of PPI rows mapped to PDB structures; each pair = (chain-A, chain-B). Many chains participate in many pairs. | **Yes.** Pair-level splits do not deduplicate the underlying structures across folds. 643 PDB IDs recurring across 8,003+1,000 pair-level rows is entirely consistent with the release's `create_examples.py`. |
| Silva *et al.* 2023 (D2CP05644E) | Static Rosetta-derived features; three claimed external panels (PDBbind, nanobody, metadynamics). | **Yes.** Structure-based affinity papers that draw from PDBbind routinely collide on canonical targets; nanobody panels typically oversample hen egg-white lysozyme (P00698); metadynamics studies with small N reuse canonical test complexes. The overlap pattern is exactly the one expected. |
| DeepDTA setting-1 | `setting1` is the release's warm-start CV split where the same test fold sees every drug and target that appears in training. The data README says as much. | **Yes.** 100% test-entity overlap for both Davis (68/442) and KIBA (2,027/229) is the designed behavior of setting-1 — which is what makes its uncritical reuse across 14 later Tier 1 papers consequential. |
| PDBbind core-set family | Core sets are curated for **resolution/quality**, not for protein novelty; proteins recur heavily between general, refined, and core subsets of a given release. The community has documented this previously (Volkov *et al.* 2022; Yang *et al.* 2020). | **Yes.** 288/290 (v2016) and 108/108 (v2013) carrying direct protein overlap is the expected ceiling given that curation criteria never attempted to enforce protein novelty. |
| AttentionDTA (Zhao 2023) | `get_kfold_data()` shuffles the full interaction table and slices folds by row index. | **Yes.** Row-shuffled CV on a dense interaction table preserves ~100% of unique drugs and targets across every fold, which is what the audit records. The slight Metz drug gap (1,206 / 1,214) reflects the sparser Metz table. |

## Discrepancies found and patches applied

All discrepancies were **language or framing issues**, not numerical errors. No claim in the improved package was found to be numerically wrong.

1. **Metadynamics phrasing (main §6.2).** Previous wording was "reusing 26 of 19 ingredients directly," which reads as reuse exceeding the 19-structure panel size. The 26 is a relation count (overlap relations between the 78-structure benchmark pool and the 19-structure panel, totalling 97 in the joint audit set), not a structure count. **Patched** to explicit relation-count wording: "26 direct-protein, 26 exact-sequence, and 75 shared-partner overlap relations against the joint 97-structure benchmark+panel audit set."

2. **AttentionDTA "every entity" overstatement (abstract + §6.2).** Previous wording said "every Davis, KIBA, and Metz entity retained across folds." On Metz, the audit shows 1,206 of 1,214 test-unique drugs (99.3%) shared — not 100%. All other sets are 100%. **Patched** the abstract and §6.2 to specify: "all drug and target identities on Davis (68 / 367) and KIBA (2,054 / 229), and all 169 targets plus 1,206 of 1,214 drugs on Metz." Table 2 and Supplement S6.5 updated to match.

3. **Source-contract and governance scope (main §3.1, supplement S2).** Previous wording listed BioGRID, InterPro, DisProt, Reactome, and EMDB among warehouse anchors and said only "STRING is held `internal_only`, PDBbind is held `restricted`." The warehouse manifest's actual `source_descriptors` block contains 12 sources; BioGRID, InterPro, DisProt, Reactome, and EMDB are not among them (they live in the broader 53-source tracked estate). The `export_policy.public_export_allowed_sources` whitelists **only five** sources (UniProt, RCSB/PDBe, AlphaFold, IntAct, ELM); all other warehouse sources — BindingDB, PDBbind, STRING, UniParc, SABIO-RK, MEGA Motif Base, Motivated Proteins — are `internal_only`, not just STRING and PDBbind.
   - **Patched §3.1** to list the actual 12 warehouse descriptors, separate the warehouse scope from the broader 53-source tracked-estate scope (which does include BioGRID, InterPro, DisProt, Reactome, EMDB, SIFTS, BioLiP, Pfam, SCOP), and correctly state the redistribution policy.
   - **Patched S2** governance line to match.

4. **Storage-unit convention (main §3.4, supplement S4).** Previous wording said "324.76 GB" for the tracked source estate; the storage-ledger artifact reports the same byte count as "302.5 GB" using GiB convention for display. Both are correct representations of the same 324,755,949,775 bytes, but the discrepancy with the ledger's own human string was untidy. **Patched** both locations to state the byte count explicitly and cite both conventions: "324,755,949,775 present bytes (≈302 GiB, or 324.8 decimal GB)."

5. **Figure 4 year distribution.** The figure-generation script used an illustrative year histogram ([1,2,2,3,3,10,6,2] for 2018–2025) rather than the actual counts. The master summary's `summary.year_counts` gives [2,1,1,4,3,10,5,3] — total still 29, but per-year heights were wrong. **Patched** `scripts/generate_figures.improved.py` to use the artifact-derived counts and regenerated `figure_4_tier1_landscape.png`.

## Items NOT changed (verified as-written)

- **Warehouse family list (Table 1).** 13 families, each with `default_view="best_evidence"`, all verified.
- **Runtime validation `status: passed`.** Verified.
- **Tier 1 yield: 29 / 18-in-2023+ / 14 / 12 / 1 / 1 / 1 / 93% / 7%.** All verified exactly.
- **29 article PDFs, 119 supplemental items.** Verified exactly.
- **Struct2Graph numbers.** All verified exactly.
- **Silva 2023 numbers (PDBbind 4/4/110, nanobody 1/1/16, metadynamics 26/26/75).** Verified; only the metadynamics prose was clarified.
- **DeepDTA setting-1: Davis all-shared, KIBA all test entities shared.** Verified exactly.
- **PDBbind core v2016 288/290 and 77 accessions; v2013 108/108 and 50 accessions.** Verified exactly.
- **Storage live-path measurements (74.2 GB / 1.6 TB / 1.5 TB).** Verified exactly.

## Confidence statement

Every number in the patched package maps to a byte-for-byte equivalent value
in the releasable audit artifacts. The remaining risk surface is linguistic
framing; the numerical content is safe to publish.

Items flagged for external submission (not part of this verification — noted
in the PI memo): (i) add 3–5 non-DTA direct-failure cases to broaden scope;
(ii) replicate one flagship audit by hand for an independent check;
(iii) snapshot warehouse + audit code into a DOI'd release before submission.
