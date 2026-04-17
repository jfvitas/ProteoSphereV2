# ProteoSphere Paper Dataset Evaluator — LLM-Only Assessment

**Artifact ID:** `paper_dataset_evaluator_claude`  
**Evaluated:** 2026-04-13  
**Corpus:** `real_paper_corpus.json` (20 papers across calibration, validation, challenge cohorts)  
**Evidence base:** `best_evidence` view — warehouse-first, no raw/archive fallback  
**Warehouse snapshot:** `full-local-backbone-2026-04-10` (validation status: `passed`)

---

## Summary Table

| paper_id | cohort | verdict | reason_codes | needs_human_review |
|---|---|---|---|---|
| zhang2012preppi | calibration | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | **true** |
| sun2017sequence | calibration | `unsafe_for_training` | POLICY_MISMATCH, INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| sledzieski2021dscript | calibration | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |
| szymborski2022rapppid | calibration | `audit_only` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| yugandhar2014affinity | calibration | `unsafe_for_training` | POLICY_MISMATCH, INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| rodrigues2019mcsm_ppi2 | calibration | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |
| du2017deepppi | validation | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| hashemifar2018dppi | validation | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| chen2019siamese_rcnn | validation | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| baranwal2022struct2graph | validation | `unsafe_for_training` | POLICY_MISMATCH, INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP, WAREHOUSE_COVERAGE_GAP | false |
| gainza2020masif | validation | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP | false |
| dai2021geometric_interface | validation | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP | **true** |
| xie2022interprotein_contacts | validation | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |
| tubiana2022scannet | validation | `audit_only` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP | false |
| wang2020nettree | validation | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |
| zhou2024ddmut_ppi | validation | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |
| krapp2023pesto | challenge | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP | false |
| zhang2020mutabind2 | challenge | `blocked_pending_mapping` | INSUFFICIENT_PROVENANCE, UNRESOLVED_SPLIT_MEMBERSHIP | false |
| bryant2022af2_ppi | challenge | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |
| gao2022af2complex | challenge | `usable_with_caveats` | UNRESOLVED_SPLIT_MEMBERSHIP, INSUFFICIENT_PROVENANCE | false |

---

## Verdict Distribution

| verdict | count | papers |
|---|---|---|
| `usable_with_caveats` | 8 | sledzieski2021dscript, rodrigues2019mcsm_ppi2, xie2022interprotein_contacts, wang2020nettree, zhou2024ddmut_ppi, bryant2022af2_ppi, gao2022af2complex + 1 |
| `blocked_pending_mapping` | 7 | zhang2012preppi, du2017deepppi, hashemifar2018dppi, chen2019siamese_rcnn, gainza2020masif, dai2021geometric_interface, krapp2023pesto, zhang2020mutabind2 |
| `unsafe_for_training` | 3 | sun2017sequence, baranwal2022struct2graph, yugandhar2014affinity |
| `audit_only` | 2 | szymborski2022rapppid, tubiana2022scannet |
| `usable` | 0 | — |
| `blocked_pending_cleanup` | 0 | — |

> Corrected count: `usable_with_caveats` = 8 (sledzieski2021dscript, rodrigues2019mcsm_ppi2, xie2022interprotein_contacts, wang2020nettree, zhou2024ddmut_ppi, bryant2022af2_ppi, gao2022af2complex); `blocked_pending_mapping` = 8 (zhang2012preppi, du2017deepppi, hashemifar2018dppi, chen2019siamese_rcnn, gainza2020masif, dai2021geometric_interface, krapp2023pesto, zhang2020mutabind2); `unsafe_for_training` = 3; `audit_only` = 2. Total: 21 — CORRECTED: 20 papers total.

---

## Verdict Distribution (corrected)

| verdict | count |
|---|---|
| `usable_with_caveats` | 7 |
| `blocked_pending_mapping` | 8 |
| `unsafe_for_training` | 3 |
| `audit_only` | 2 |
| `usable` | 0 |

---

## Cross-Cutting Findings

### 1. Claim surfaces not materialized — universal constraint
All 13 entity families in the warehouse have `claim_surface_materialized: false`. This means no paper can achieve accession-level roster verification from the `best_evidence` logical view. Every assessment carries `UNRESOLVED_SPLIT_MEMBERSHIP` as a structural limitation.

### 2. STRING source — internal-only coverage gap
STRING (`license_scope: internal_only`, `redistributable: false`) is a source family for six papers in the corpus (zhang2012preppi, sun2017sequence, du2017deepppi, hashemifar2018dppi, chen2019siamese_rcnn, szymborski2022rapppid). These papers all receive `WAREHOUSE_COVERAGE_GAP` because public-facing warehouse materialization cannot include STRING-sourced protein-protein interaction edges as governing evidence.

### 3. PDBBind — restricted source coverage gap
PDBBind (`license_scope: restricted`, `redistributable: false`, `retrieval_mode: manual`) contributes to baranwal2022struct2graph and yugandhar2014affinity. Both receive `WAREHOUSE_COVERAGE_GAP`. This, combined with cross-validation policy, drives both to `unsafe_for_training`.

### 4. Cross-validation → POLICY_MISMATCH
Papers with `split_style: cross_validation` (sun2017sequence, baranwal2022struct2graph, yugandhar2014affinity) all fail the ProteoSphere stable holdout policy. Cross-validation and jackknife evaluation do not maintain a deterministic, reusable held-out split. These are `unsafe_for_training`.

### 5. Unseen-protein / homology-guard claims without rosters → audit_only
Papers claiming strict unseen-protein or fold-based separation (szymborski2022rapppid, tubiana2022scannet) map to `uniref_grouped` canonical policy but cannot be verified without explicit accession rosters. These are `audit_only` — useful for comparison but not governing.

### 6. External holdout papers → usable_with_caveats
Papers using recognized external holdout regimes (CAPRI blind tests, CASP-CAPRI, cross-species transfer, SM1124, AB-Bind, E. coli proteome, heterodimer sets) using only public/redistributable sources (RCSB/PDBe, UniProt, AlphaFold) receive `usable_with_caveats`. The split logic is interpretable but exact membership cannot be validated against the warehouse.

### 7. Human review gates triggered
- **zhang2012preppi**: Genome-scale discovery workflow with no recoverable split structure; multiple canonical policies plausible.
- **dai2021geometric_interface**: Multiple benchmarks referenced with no grouping rule; policy mapping is genuinely ambiguous.

---

## Warehouse State Reference

| source | status | redistributable | affects papers |
|---|---|---|---|
| rcsb_pdbe | present | yes | gainza, dai, xie, tubiana, krapp, rodrigues, wang, zhang2020, zhou, bryant, gao, baranwal |
| uniprot | present | yes | zhang2012, sledzieski, szymborski, yugandhar, rodrigues, xie, zhang2020, zhou |
| intact | present | yes | zhang2012, sun, du, hashemifar, chen, sledzieski, szymborski |
| alphafold | present | yes | bryant2022, gao2022 |
| string | present | **no (internal_only)** | zhang2012, sun, du, hashemifar, chen, szymborski |
| pdbbind | present | **no (restricted)** | baranwal, yugandhar |

Warehouse validation state: `passed` (validated 2026-04-11, snapshot `full-local-backbone-2026-04-10`).

---

*Assessment path: LLM-only evaluator. Evidence basis: `best_evidence` logical view. No raw/archive fallback used. Claim surfaces not materialized; member-level verification not performed.*
