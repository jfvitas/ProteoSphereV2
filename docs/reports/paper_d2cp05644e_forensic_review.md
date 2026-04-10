# A Forensic Review of the D2CP05644E Dataset Design

## Title

**A forensic audit of the training and evaluation datasets used in "An artificial neural network model to predict structure-based protein-protein free energy of binding from Rosetta-calculated properties" (DOI: 10.1039/D2CP05644E)**

## Executive Summary

We recovered the paper's actual structure sets from the paper supplement, the authors' public repository, and the cited nanobody source dataset. We then evaluated those sets with the local ProteoSphere audit stack, which checks:

- local structure coverage
- protein-level overlap
- exact-sequence reuse
- UniRef-family overlap
- structure-state/context reuse
- fail-closed acceptance status
- remediation options

### Bottom line

The study's evaluation datasets are weaker than they appear.

Our current judgment is:

- the benchmark training pool is partially reconstructable but not fully transparent
- the nominal external **PDBbind** set is **not** a clean independence test
- the **nanobody** validation set is **not** a clean independence test
- the **metadynamics** validation set is **not** an independent test at all

The paper is directionally right that generalization is hard. But our audit suggests the problem is not only feature limitations or distribution shift. The paper's external validation sets also contain enough protein-, sequence-, and structure-context overlap with the benchmark pool to weaken the force of the generalization claims.

## Why this review is checkable

All primary extracted and derived evidence for this review is local:

- detailed local audit artifact:
  - [paper_d2cp05644e_detailed_audit.json](/D:/documents/ProteoSphereV2/artifacts/status/paper_d2cp05644e_detailed_audit.json)
- prior recovery note:
  - [paper_d2cp05644e_quality_assessment.md](/D:/documents/ProteoSphereV2/docs/reports/paper_d2cp05644e_quality_assessment.md)
- authors' public repo snapshot:
  - [PPSUS_repo](/D:/documents/ProteoSphereV2/artifacts/runtime/PPSUS_repo)
- authors' benchmark scorefile:
  - [binding-energy.csv](/D:/documents/ProteoSphereV2/artifacts/runtime/PPSUS_repo/binding_energy_experiments/data/binding-energy.csv)
- authors' PDBbind benchmark file:
  - [prodigy_PDBind.csv](/D:/documents/ProteoSphereV2/artifacts/runtime/PPSUS_repo/binding_energy_experiments/data/benchmark/prodigy_PDBind.csv)
- cited nanobody OA package:
  - [PMC6441729_extracted](/D:/documents/ProteoSphereV2/artifacts/runtime/PMC6441729_extracted)

Primary web sources:

- [Paper landing page](https://pubs.rsc.org/en/content/articlelanding/2023/cp/d2cp05644e/unauth)
- [DOI](https://doi.org/10.1039/D2CP05644E)
- [Supplementary PDF](https://www.rsc.org/suppdata/d2/cp/d2cp05644e/d2cp05644e1.pdf)
- [Authors' public repository](https://github.com/DSIMB/PPSUS)
- [Cited nanobody OA package entry](https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC6441729)

## What the study actually used

### 1. PDBbind test set from Supplementary Table S4

Recovered exact set size: `50`

```text
2WH6 2WP3 3V1C 3VFN 3WQB 4B1Y 4CJ0 4CJ2 4K5A 4KT3
4LZX 4M0W 4NL9 4PJ2 4QLP 4UYP 4WND 4X33 4YL8 4Z99K
5B78 5DC4 5DJT 5E95 5EP6 5H3J 5INB 5MA4 5NT7 5TZP
5V5H 5XCO 5YWR 6B6U 6E3I 6E3J 6HER 6JB2 6FU9 6FUB
6FUD 6J14 5IMK 5IMM 5KXH 5KY4 5KY5 6DDM 6FG8 6NE2
```

### 2. Metadynamics validation set from Supplementary Table S2

Recovered exact set size: `19`

```text
1ACB 1AY7 1BVN 1EMV 1FFW 1KAC 1KTZ 1QA9 1R0R 1US7
2C0L 2OOB 2PTC 2UUY 3A4S 3BZD 3F1P 3LVK 3SGB
```

### 3. Benchmark pool reconstructed from the authors' public repo

The public notebook reads `binding-energy.csv` and then explicitly drops three rows:

- `1GXD`
- `1DE4`
- `1E4K`

That leaves an effective benchmark pool of `78` structures, not a fully paper-disclosed internal split.

Important benchmark-pool detail:

- locally covered benchmark structures: `76`
- locally missing benchmark structures: `2` (`1A2K`, `4CPA`)
- locally typed complex classes among found structures:
  - `75` protein-protein
  - `1` protein-ligand

That means the benchmark pool reconstructed from the public materials is not even perfectly homogeneous as a PPI-only set by our current local typing.

## Method used for local quality assessment

The local audit stack does not just count repeated PDB IDs. It checks at multiple levels:

1. **Structure coverage**
   - Is the structure represented in the local expanded corpus?

2. **Protein overlap**
   - Do train and test reuse the same UniProt accession?

3. **Exact-sequence overlap**
   - Do train and test contain the exact same protein sequence?

4. **Cluster/family overlap**
   - Do train and test share UniRef100, UniRef90, or UniRef50 cohorts?

5. **Structure-state/context reuse**
   - Even if the full complex is not identical, is one side of the complex reused in a nearby context?

6. **Acceptance gate**
   - The split is blocked if the leakage profile is strong enough to invalidate training/test independence.

## Major findings

## Finding 1: the paper/repo benchmark construction is not fully transparent

The public repository lets us reconstruct a `78`-structure benchmark pool, but not the exact paper-internal 70/30 split.

That matters because:

- we can audit the benchmark pool against external evaluations
- but we cannot fully reconstruct the paper's own internal train/test partition from the public materials alone

This is a transparency limitation in the paper/repo package, not just a tooling issue on our side.

## Finding 2: the PDBbind evaluation set is not a clean external benchmark

### Summary

- benchmark pool size: `78`
- PDBbind test size: `50`
- total structures evaluated: `128`
- locally covered: `125`
- direct protein overlaps: `4`
- exact sequence overlaps: `4`
- flagged structure-context overlaps: `16`
- overall decision: `blocked`

### Overlapping proteins that directly link benchmark and PDBbind test

| Shared protein | UniProt | Train structures | Test structures | Why this matters |
|---|---|---|---|---|
| Lysozyme C | `P00698` | `1BVK`, `1DQJ`, `1MLC`, `1P2C`, `1VFB`, `2I25` | `4CJ2`, `6JB2` | repeated target identity across train/test |
| GTPase HRas | `P01112` | `1HE8`, `1LFD` | `5E95` | direct protein reuse |
| Beta-2-microglobulin | `P61769` | `1AKJ` | `3VFN` | direct protein reuse |
| Actin, alpha skeletal muscle | `P68135` | `1ATN` | `4B1Y` | direct protein reuse |

### Most important culprit pair

The single critical PDBbind leak is:

- `1BVK` (train) vs `6JB2` (test)
- shared protein: `P00698` (`Lysozyme C`)
- relation: `exact_protein_set_reuse`

That is stronger than "same family" or "same fold." It is direct reuse of the same protein set across nominal train/test boundaries.

### High-risk context reuse examples

These are not full duplicates, but they are still biologically too close to count as a clean external test:

- `1AKJ` vs `3VFN` on `P61769`
- `1ATN` vs `4B1Y` on `P68135`
- `1BVK` vs `4CJ2` on `P00698`
- `1DQJ` vs `4CJ2` on `P00698`
- `1DQJ` vs `6JB2` on `P00698`
- `1HE8` vs `5E95` on `P01112`
- `1LFD` vs `5E95` on `P01112`

### Interpretation

The PDBbind set is not just "harder than the benchmark." It is also not independent enough to be a clean external generalization test.

## Finding 3: the nanobody validation set also reuses a central antigen target

### Summary

- benchmark pool size: `78`
- nanobody set size: `47`
- total structures evaluated: `125`
- locally covered: `105`
- direct protein overlaps: `1`
- exact sequence overlaps: `1`
- flagged structure-context overlaps: `24`
- overall decision: `blocked`

### The culprit is very specific

All direct overlap runs through one shared protein:

| Shared protein | UniProt | Train structures | Test structures |
|---|---|---|---|
| Lysozyme C | `P00698` | `1BVK`, `1DQJ`, `1MLC`, `1P2C`, `1VFB`, `2I25` | `1RI8`, `1RJC`, `1ZV5`, `1ZVH` |

### Critical exact-protein-set reuses

These four pairs are critical:

- `1BVK` vs `1RI8`
- `1BVK` vs `1RJC`
- `1BVK` vs `1ZV5`
- `1BVK` vs `1ZVH`

All four share the same directly repeated protein:

- `P00698` (`Lysozyme C`)

### Why this matters

This is exactly the kind of target recurrence that can make a "nanobody external validation" look stronger than it really is. Even when the binder differs, the target can still anchor the model in familiar biochemical territory.

### Coverage caution

Our local corpus covers only part of the nanobody set:

- locally missing test structures: `18`

```text
1BZQ 1MVF 1ZVY 2BSE 3G9A 3K1K 3K74 4C57 4C59
4LDE 4LGS 4LHJ 4LHQ 4NBX 4NBZ 4ORZ 4QO1 4S10
```

So this audit is conservative. The real overlap picture could be worse, not better.

## Finding 4: the metadynamics validation set is the most severe problem

### Summary

- benchmark pool size: `78`
- metadynamics set size: `19`
- total structures evaluated: `97`
- locally covered: `94`
- direct protein overlaps: `26`
- exact sequence overlaps: `26`
- flagged structure-context overlaps: `24`
- overall decision: `blocked`

### Why this set fails so badly

The core problem is not only family similarity. Many of the same structures or same protein pairs are effectively reused.

### Exact or near-exact duplicate structure/protein-set reuses

| Train structure | Test structure | Shared proteins | Why it is critical |
|---|---|---|---|
| `1ACB` | `1ACB` | `P00766`, `P01051` | exact structure and exact protein-set reuse |
| `1BVN` | `1BVN` | `P00690`, `P01092` | exact structure and exact protein-set reuse |
| `1EMV` | `1EMV` | `P09883`, `P13479` | exact structure and exact protein-set reuse |
| `1FFW` | `1FFW` | `P07363`, `P0AE67` | exact structure and exact protein-set reuse |
| `1KAC` | `1KAC` | `P36711`, `P78310` | exact structure and exact protein-set reuse |
| `1KTZ` | `1KTZ` | `P10600`, `P37173` | exact structure and exact protein-set reuse |
| `1QA9` | `1QA9` | `P06729`, `P19256` | exact structure and exact protein-set reuse |
| `1R0R` | `1R0R` | `P00780`, `P68390` | exact structure and exact protein-set reuse |
| `1US7` | `1US7` | `P02829`, `Q16543` | exact structure and exact protein-set reuse |
| `2C0L` | `2C0L` | `P22307`, `P50542` | exact structure and exact protein-set reuse |
| `2OOB` | `2OOB` | `P0CH28`, `Q13191` | exact structure and exact protein-set reuse |
| `2TGP` | `2PTC` | `P00760`, `P00974` | different PDB IDs but the same protein pair |
| `3BZD` | `3BZD` | `P0A0L5` | exact structure reuse |
| `3SGB` | `3SGB` | `P00777`, `P68390` | exact structure and exact protein-set reuse |

### Interpretation

This set is not a valid external validation set by current standards. It overlaps too heavily with the benchmark pool to support a strong generalization claim.

## Finding 5: even when exact duplicates are absent, partner/context overlap is very high

This matters because a test set can look distinct at the PDB-ID level while still being too close biologically.

Shared-partner overlap counts:

- benchmark vs PDBbind: `110`
- benchmark vs nanobody: `16`
- benchmark vs metadynamics: `75`

That means the benchmark and evaluation sets often preserve familiar interaction neighborhoods even when they do not reuse the exact same full complex.

## Why the study's generalizability was likely poor

The paper's own framing is not wrong: static Rosetta features are limited, and experimental-label heterogeneity is a real issue.

But our audit suggests a more precise explanation:

1. **The model likely learned useful but narrow structural heuristics.**
   - That matches the paper's basic framing.

2. **The external datasets were not clean enough to measure true independence.**
   - So even modest external performance may still overestimate real out-of-distribution performance.

3. **Repeated targets and repeated protein contexts probably narrowed the effective test difficulty.**
   - Especially `P00698` (`Lysozyme C`) in the nanobody set
   - and the repeated exact structures in the metadynamics set

4. **If generalization remained limited despite this overlap, the true generalization problem is probably even harder than the paper suggests.**

## Comparison to the paper's own claims

## What the paper says that we agree with

From the article landing page abstract:

- the model predicts `ΔG` from Rosetta-derived structural properties
- it reports test RMSE values in the `1.67` to `2.45 kcal mol−1` range
- it presents validation on multiple datasets

That broad framing is fine. We also agree with the likely scientific limitations behind the paper:

- single-structure featurization loses dynamic information
- mixed experimental sources can add label noise
- generalization across protein-protein complexes is genuinely difficult

## Where our audit goes further

The paper's public framing sounds like a story about difficult out-of-distribution prediction.

Our audit adds a sharper conclusion:

- **the external sets are not only hard; they are also overlap-contaminated**
- **the metadynamics set is especially compromised**
- **the nanobody set is likely target-biased through repeated lysozyme usage**
- **the PDBbind set is not independent enough to be treated as a strong external benchmark**

So the issue is not only "the model did not generalize well." The issue is also "the dataset design did not provide a clean enough test of generalization."

## What this reveals about our own audit capabilities

This paper was a good stress test for the local tooling.

### What the tool can now do well

- recover exact evaluation structures from primary and public sources
- link PDB IDs to protein chains and UniProt accessions
- detect direct protein reuse
- detect exact sequence reuse
- detect UniRef cohort overlap
- detect structure-state/context reuse
- produce fail-closed training-readiness verdicts
- propose remediation / holdout plans

### Current limits

1. **We do not yet have a full alignment-heavy homology engine.**
   - We currently rely on exact sequence plus UniRef cohort logic and mutation-like heuristics.

2. **Local structure-file coverage is still incomplete for some secondary validation sets.**
   - Especially the nanobody set.

3. **The paper's own internal train/test split is still not reconstructable from the public record.**
   - We can reconstruct the benchmark pool, but not the exact training partition used for the reported internal split.

Those are real limits, but they do not overturn the main findings above.

## Final judgment

This paper's dataset package is scientifically interesting, but the evaluation design is not strong enough to support a robust claim of clean external generalization.

### Confidence in each evaluation set

| Evaluation set | Our status | Why |
|---|---|---|
| Benchmark pool | `usable but under-documented` | public materials do not fully disclose the internal split |
| PDBbind test set | `blocked as clean external benchmark` | direct protein reuse, exact-sequence reuse, and high-risk context overlap |
| Nanobody set | `blocked as clean external benchmark` | repeated lysozyme target reuse plus context overlap |
| Metadynamics set | `blocked as external benchmark` | direct reuse of the same structures or same protein pairs |

## Appendix A: Practical artifacts to inspect

- detailed machine-readable audit:
  - [paper_d2cp05644e_detailed_audit.json](/D:/documents/ProteoSphereV2/artifacts/status/paper_d2cp05644e_detailed_audit.json)
- previous narrative recovery note:
  - [paper_d2cp05644e_quality_assessment.md](/D:/documents/ProteoSphereV2/docs/reports/paper_d2cp05644e_quality_assessment.md)
- expanded local corpus basis:
  - [pdbbind_expanded_structured_corpus_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/pdbbind_expanded_structured_corpus_preview.json)

## Appendix B: Exact recovered validation-set IDs

### PDBbind 50

```text
2WH6 2WP3 3V1C 3VFN 3WQB 4B1Y 4CJ0 4CJ2 4K5A 4KT3
4LZX 4M0W 4NL9 4PJ2 4QLP 4UYP 4WND 4X33 4YL8 4Z99K
5B78 5DC4 5DJT 5E95 5EP6 5H3J 5INB 5MA4 5NT7 5TZP
5V5H 5XCO 5YWR 6B6U 6E3I 6E3J 6HER 6JB2 6FU9 6FUB
6FUD 6J14 5IMK 5IMM 5KXH 5KY4 5KY5 6DDM 6FG8 6NE2
```

### Metadynamics 19

```text
1ACB 1AY7 1BVN 1EMV 1FFW 1KAC 1KTZ 1QA9 1R0R 1US7
2C0L 2OOB 2PTC 2UUY 3A4S 3BZD 3F1P 3LVK 3SGB
```
