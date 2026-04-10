# D2CP05644E Dataset Quality Assessment

## Scope

This report audits the dataset usage described in the paper:

- RSC DOI: https://doi.org/10.1039/D2CP05644E

The goals are:

1. Recover the exact PDB IDs used by the study from primary/public sources.
2. Evaluate dataset quality using local ProteoSphere tooling.
3. Compare those findings to the paper's own limitations discussion.
4. Note any gaps in our current internal audit capability.

## Source Recovery

### PDBbind test set from Supplementary Table S4

Recovered from the supplementary PDF (`d2cp05644e1.pdf`) and text extraction.

Exact PDB IDs:

`2WH6, 2WP3, 3V1C, 3VFN, 3WQB, 4B1Y, 4CJ0, 4CJ2, 4K5A, 4KT3, 4LZX, 4M0W, 4NL9, 4PJ2, 4QLP, 4UYP, 4WND, 4X33, 4YL8, 4Z99K, 5B78, 5DC4, 5DJT, 5E95, 5EP6, 5H3J, 5INB, 5MA4, 5NT7, 5TZP, 5V5H, 5XCO, 5YWR, 6B6U, 6E3I, 6E3J, 6HER, 6JB2, 6FU9, 6FUB, 6FUD, 6J14, 5IMK, 5IMM, 5KXH, 5KY4, 5KY5, 6DDM, 6FG8, 6NE2`

Count: `50`

### Metadynamics validation set from Supplementary Table S2

Exact PDB IDs:

`1ACB, 1AY7, 1BVN, 1EMV, 1FFW, 1KAC, 1KTZ, 1QA9, 1R0R, 1US7, 2C0L, 2OOB, 2PTC, 2UUY, 3A4S, 3BZD, 3F1P, 3LVK, 3SGB`

Count: `19`

### Training benchmark reconstructed from the authors' public repo

Recovered from the public repository notebook logic and CSV files.

Public repo notebook behavior:

- `binding-energy.csv` has `81` rows.
- The notebook explicitly drops row indices `28`, `12`, and `14`.
- Those rows correspond to PDB IDs:
  - `1GXD`
  - `1DE4`
  - `1E4K`

So the effective benchmark dataset used in the notebook is:

- `81` input rows
- `3` dropped rows
- `78` retained rows

Exact retained PDB IDs:

`1A2K, 1ACB, 1AK4, 1AKJ, 1ATN, 1AVZ, 1B6C, 1BJ1, 1BUH, 1BVK, 1BVN, 1CBW, 1DQJ, 1E6E, 1E6J, 1E96, 1EER, 1EFN, 1EMV, 1EWY, 1EZU, 1FC2, 1FFW, 1FSK, 1GCQ, 1GLA, 1HE8, 1I2M, 1I4D, 1J2J, 1JPS, 1JTG, 1JWH, 1K5D, 1KAC, 1KKL, 1KTZ, 1KXQ, 1LFD, 1M10, 1MLC, 1MQ8, 1P2C, 1PPE, 1PVH, 1QA9, 1R0R, 1S1Q, 1US7, 1VFB, 1WEJ, 1XQS, 1XU1, 1Z0K, 1ZHI, 2A9K, 2ABZ, 2AJF, 2AQ3, 2C0L, 2FJU, 2GOX, 2HQS, 2HRK, 2I25, 2MTA, 2NYZ, 2OOB, 2PCB, 2PCC, 2TGP, 2VIR, 2VIS, 2WPT, 3BZD, 3CPH, 3SGB, 4CPA`

Count: `78`

### Nanobody validation set recovered from the cited Data in Brief source

Recovered from the OA package for `PMC6441729`, specifically `mmc2.xlsx`, using rows with a non-empty `ΔGb`.

Exact PDB IDs:

`1BZQ, 1MVF, 1OP9, 1RI8, 1RJC, 1ZV5, 1ZVH, 1ZVY, 2BSE, 3G9A, 3K1K, 3K3Q, 3K74, 3ZKQ, 4C57, 4C59, 4EIG, 4EIZ, 4HEP, 4I0C, 4KRP, 4LDE, 4LGP, 4LGR, 4LGS, 4LHJ, 4LHQ, 4NBX, 4NBZ, 4ORZ, 4P2C, 4QO1, 4S10, 4W6W, 4W6X, 4W6Y, 4WEM, 4WEN, 4WEU, 4X7E, 4X7F, 5E7F, 5HGG, 5HVF, 5IMK, 5J56, 5J57`

Count: `47`

## Local Tool Assessment

Local structured-analysis basis:

- expanded staged corpus rooted in PDBbind-backed structure/protein mappings
- exact-sequence overlap audit
- UniRef cohort overlap audit
- protein overlap audit
- structure-state/context reuse audit
- fail-closed acceptance gate
- remediation planner

### 1. Benchmark training set (78) vs PDBbind test set (50)

Assessment summary:

- total structures evaluated: `128`
- covered locally: `125`
- missing locally: `3`
- direct protein overlap count: `4`
- exact sequence overlap count: `4`
- UniRef100 overlap count: `4`
- shared partner overlap count: `110`
- flagged train/test structure-pair count: `16`
- quality verdict: `blocked`

Blocking reasons:

- `critical_structure_state_reuse`
- `direct_protein_leakage`
- `exact_sequence_reuse`

Important detail:

- the nominal external PDBbind test set is not independent by current standards
- at least one structure-pair relation is `exact_protein_set_reuse`
- the remaining flagged pairs are mostly `shared_protein_different_context`

Known missing structure from this set:

- `4Z99K`

Overlapping accessions:

- `P00698`
- `P01112`
- `P61769`
- `P68135`

Interpretation:

This evaluation set is contaminated by direct protein reuse, exact sequence reuse, and heavy contextual overlap. It is not a clean out-of-distribution generalization benchmark.

### 2. Benchmark training set (78) vs nanobody validation set (47)

Assessment summary:

- total structures evaluated: `125`
- covered locally: `105`
- missing locally: `20`
- direct protein overlap count: `1`
- exact sequence overlap count: `1`
- UniRef100 overlap count: `1`
- shared partner overlap count: `16`
- flagged train/test structure-pair count: `24`
- quality verdict: `blocked`

Blocking reasons:

- `critical_structure_state_reuse`
- `direct_protein_leakage`
- `exact_sequence_reuse`

Interpretation:

This dataset is also not independent. The main recurring overlap appears to center on `P00698`, suggesting target reuse that can make nanobody-set generalization look stronger than it really is.

Coverage limitation:

- local corpus coverage for the nanobody set is only partial
- therefore this audit is conservative; the true overlap picture could be as bad or worse

### 3. Benchmark training set (78) vs metadynamics validation set (19)

Assessment summary:

- total structures evaluated: `97`
- covered locally: `94`
- missing locally: `3`
- direct protein overlap count: `26`
- exact sequence overlap count: `26`
- UniRef100 overlap count: `26`
- shared partner overlap count: `75`
- flagged train/test structure-pair count: `24`
- quality verdict: `blocked`

Blocking reasons:

- `critical_structure_state_reuse`
- `direct_protein_leakage`
- `exact_sequence_reuse`

Interpretation:

This is emphatically not an independent evaluation set. It contains direct structure/protein reuse from the benchmark set itself and should not be treated as a meaningful external validation of generalization.

## Overall Quality Assessment

### Strengths

- The study appears to use real experimental affinity labels and structure-derived Rosetta features.
- The benchmark and validation sets are biologically meaningful protein-protein complexes.
- The paper does evaluate on multiple datasets instead of reporting only one internal split.

### Weaknesses exposed by local audit

1. **Protein-level leakage**
   - Exact protein reuse appears between the benchmark training set and the nominal external evaluations.

2. **Exact-sequence leakage**
   - The current local audit finds exact train/test sequence reuse, which is a stronger warning than mere family similarity.

3. **Structure-state/context reuse**
   - Many train/test relations are not exact duplicate complexes but still reuse one side of the interaction in closely related contexts.
   - This inflates apparent generalization while preserving biological familiarity.

4. **Heavy partner overlap**
   - Shared interaction-partner overlap is extremely high for the PDBbind test set.

5. **Reproducibility mismatch**
   - The paper/supplement/public-repo story is not fully internally consistent.
   - The public notebook produces an effective `78`-structure benchmark set, not an obvious `81`-structure final set.

6. **Partial validation-set transparency**
   - The nanobody files exposed in the public repo appear incomplete relative to the primary-source-derived 47-structure set.

## Why Generalizability Was Likely Poor

The local tool stack suggests that generalizability was poor for at least three interacting reasons:

1. **Static single-structure featurization**
   - Rosetta-derived snapshot features can miss important conformational and environmental effects.

2. **Label heterogeneity**
   - Converting experimental quantities such as `kD` into `ΔG` can add noise and assay inconsistency.

3. **Train/test overlap is not clean enough**
   - Exact protein reuse, exact sequence reuse, and structure-state/context reuse reduce the strength of the external generalization claims.
   - This means the observed performance degradation may still underestimate the true out-of-distribution difficulty.

## Comparison to the Paper's Own Reflections

### Where our audit agrees with the paper

The paper appears to recognize that:

- model performance is weaker when asked to generalize
- static structure-derived features have limits
- experimental source heterogeneity and feature limits matter

These are reasonable and likely true.

### Where our audit goes further

Our local tooling adds stronger claims than the paper appears to make explicitly:

- the nominal external sets are not just distribution-shifted; they are also overlap-contaminated
- the metadynamics set in particular is not independent enough to serve as a clean validation benchmark
- the PDBbind set is also not a clean independence test because of direct protein and exact-sequence reuse
- the nanobody set likely inherits recurring target-family/context reuse

So the paper's “generalization is hard” framing is directionally correct, but our audit suggests the evaluation protocol itself is weaker than ideal and may blur the real size of the generalization gap.

## Limits of Our Current Internal Audit

Our internal tool stack is now strong enough to produce a serious assessment, but a few limitations remain:

1. **Local structure-file incompleteness**
   - The expanded corpus has broad metadata/mapping coverage, but not all structure files are locally materialized.

2. **No full alignment-based homology engine yet**
   - We have exact-sequence and UniRef-backed cohort checks, plus mutation-like heuristics, but not a full substitution/gap-aware all-vs-all alignment audit.

3. **Paper-internal split reconstruction gap**
   - The paper's internal 70/30 train/test split for the benchmark set is not fully reconstructable from the published materials we currently have.

4. **Nanobody-source incompleteness in local mirrored public repo**
   - We had to recover the fuller set from the primary OA package rather than from the authors' repo alone.

## Bottom Line

The local ProteoSphere audit stack is now strong enough to make a substantive judgment on this paper's dataset design.

Current judgment:

- benchmark training corpus: usable but not perfectly transparent
- PDBbind test set: **blocked as a clean external benchmark**
- nanobody test set: **blocked as a clean external benchmark**
- metadynamics set: **blocked as an external benchmark**

The main issue is not only that generalization is hard; it is that the study's evaluation datasets appear to contain enough protein-, sequence-, and structure-context overlap with the training benchmark to weaken the strength of the generalization claims.
