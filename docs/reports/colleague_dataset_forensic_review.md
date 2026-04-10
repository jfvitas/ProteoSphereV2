# Forensic Review of the Colleague Training/Test Dataset

## Scope

This review is based only on the two provided files:

- [train_labels_520.csv](/C:/Users/jfvit/Downloads/train_labels_520.csv)
- [test_labels.csv](/C:/Users/jfvit/Downloads/test_labels.csv)

I did **not** assume anything about the paper, model, or intended claims. This is a dataset-first review.

The main goals were:

1. characterize what kind of dataset this is
2. evaluate bias, leakage, and split quality
3. identify likely failure/outlier examples
4. make the reasoning transparent enough that the work can be checked

Machine-readable backing artifacts:

- full audit export:
  - [colleague_dataset_forensic_review.json](/D:/documents/ProteoSphereV2/artifacts/status/colleague_dataset_forensic_review.json)
- culprit/details supplement:
  - [colleague_dataset_forensic_details.json](/D:/documents/ProteoSphereV2/artifacts/status/colleague_dataset_forensic_details.json)

## Executive Summary

This is a **protein-protein binding affinity** dataset with a large, mixed-source training set and a test set that is **not cleanly independent** from the training pool.

### Bottom line

The dataset is scientifically useful, but the current train/test split is **not training-ready as a robust generalization benchmark** by the standards of the local audit stack.

Main reasons:

- `45` directly overlapping proteins across train and test
- `46` exact sequence overlaps across train and test
- `334` flagged train/test structure-context overlap pairs
- `116` of those are **critical exact-protein-set reuses**
- `182` more are **high-risk shared-protein different-context reuses**

The local acceptance gate therefore marks this split:

- `overall_decision = blocked`
- `readiness = not_training_ready`

This does **not** mean the dataset is worthless. It means:

- it may still be useful for model development
- it is weak as evidence for clean external generalization
- it likely overestimates independence between train and test

## What the dataset looks like

## Size and structure

### Train set

- rows: `517`
- unique PDB IDs: `517`
- duplicate PDB IDs: `0`
- label range (`exp_dG`): `-21.4043` to `-2.1843`
- mean `exp_dG`: `-9.9942`
- median `exp_dG`: `-9.9199`
- std dev: `3.0601`

### Test set

- rows: `98`
- unique PDB IDs: `98`
- duplicate PDB IDs: `0`
- label range (`exp_dG`): `-19.09` to `-0.92`
- mean `exp_dG`: `-10.2417`
- median `exp_dG`: `-10.19`
- std dev: `3.2912`

## Source composition in train

The training set is not from one clean upstream source. It is a merged collection:

- `381` from `PDBbind v2020`
- `83` from `SKEMPI v2.0`
- `31` from `SAbDab`
- `22` from `Affinity Benchmark v5.5`

That is not automatically bad, but it does mean the train set is heterogeneous in provenance and probably heterogeneous in assay/reporting conventions too.

## Structural-method composition in train

- `397` X-ray structures
- `119` solution NMR structures
- `1` electron microscopy structure

That is another real source of heterogeneity.

## Local structure typing

Among locally covered structures:

- train: `477` protein-protein, `2` protein-ligand
- test: `89` protein-protein

So this is overwhelmingly a protein-protein affinity dataset, but the train set is not perfectly pure by local structure typing.

## Coverage

Across the full split:

- total structures evaluated locally: `615`
- locally covered: `568`
- locally missing: `47`
- coverage fraction: `0.9236`

Test-side locally missing structures:

```text
1C1Y 1CSE 1M9E 1SIB 3BTH 3BTT 5M2O 5K39 1S0W
```

This means the audit is already strong, but not total. Missing structures make some conclusions conservative.

## The biggest problem: train/test leakage

## High-level leakage profile

The split is blocked because it fails at multiple levels simultaneously:

- `45` direct protein overlaps
- `46` exact sequence overlaps
- `4` mutation-like overlap pairs
- `334` flagged structure-context overlaps

Structure-context breakdown:

- `116` `exact_protein_set_reuse`
- `182` `shared_protein_different_context`
- `20` `close_family_context_overlap`
- `16` `broad_family_context_overlap`

This is not subtle. The test set contains many examples that remain biologically too close to training examples even when the PDB IDs differ.

## What "critical" means here

A **critical** overlap means the test item shares the exact same mapped protein set as some train item. That is much stronger than merely being from the same protein family.

## Exact culprit patterns

## Repeated protein pair family around `P00782` + `Q40059`

This is the strongest recurring cluster in the test outlier list.

The following test structures all map to the same accession pair:

- `1TM1`
- `1TM4`
- `1TM5`
- `1TO1`
- `1Y33`
- `1Y4A`
- `1Y4D`

And they all show critical overlap against the training structure:

- `1Y3C`

Critical relation:

- `train = 1Y3C`
- `test = 1TM1 / 1TM4 / 1TM5 / 1TO1 / 1Y33 / 1Y4A / 1Y4D`
- shared proteins = `P00782`, `Q40059`
- relation = `exact_protein_set_reuse`

This looks like a classic "same system, many nearby variants/conditions" cluster split across train and test.

## Repeated lysozyme-centered leakage around `P00698`

The accession `P00698` is another major source of test contamination.

Training-side hits:

- `1RI8`
- `1RJC`
- `1ZMY`
- `1ZVH`
- `2I25`
- `3M18`
- `4CJ2`
- `4GLV`
- `4GN3`
- `4GN4`
- `4GN5`
- `5J7C`
- `6JB2`
- `6JB8`

Test-side hits:

- `1UUZ`
- `1ZV5`
- `2I26`
- `4GLA`

One especially bad pattern:

- test `1ZV5` is critically reused against multiple train structures:
  - `4GLV`
  - `4GN3`
  - `4GN4`
  - `4GN5`

All of those share:

- `P00698`

So even where the full complexes differ, the test set is still anchored to a recurrent protein identity that the model has already seen.

## Other exact-protein-set reuse examples

These are some additional critical train/test overlaps:

- `1B27` vs `1BRS`
  - shared proteins: `P00648`, `P11540`
- `1F5R` vs `3FP6`
  - shared proteins: `P00763`, `P00974`
- `1KAC` vs `1P6A`
  - shared proteins: `P36711`, `P78310`
- `2FTL` vs `2PTC`
  - shared proteins: `P00760`, `P00974`
- `2LZ6` vs `2MCN`
  - shared proteins: `P0CG48`, `Q9JLQ0`
- `4APX` vs `4XXW`
  - shared proteins: `Q99PF4`, `Q99PJ1`
- `4AQE` vs `4XXW`
  - shared proteins: `Q99PF4`, `Q99PJ1`
- `4LGR` vs `5J56`
  - shared protein: `P02879`
- `4LGR` vs `5J57`
  - shared protein: `P02879`

These are not abstract family-level concerns. They are concrete train/test collisions.

## Biases and design risks

## 1. Source-mix bias

The train set is dominated by PDBbind and then topped up by several curated benchmark sources. That means the model can learn a mixture of:

- PDBbind-style reporting conventions
- SKEMPI-style mutation/interaction biases
- antibody-heavy SAbDab patterns
- older benchmark curation choices

That can be useful for scale, but it makes it harder to reason cleanly about what the test set is actually challenging.

## 2. Structural-method bias

The train set mixes:

- many X-ray structures
- a large NMR minority
- one EM case

If the test set is structurally cleaner or noisier than the train set, performance can drift for reasons unrelated to true biological generalization.

## 3. Hidden subgroup skew

The explicit subgroup field is sparse:

- `482` unspecified
- `31` antibody-antigen
- `4` TCR-pMHC

So there may be meaningful biological subgroup bias that the metadata does not capture well.

## 4. Distributional label risk

The test set includes both:

- very strong binders such as `1BRS` (`-19.09`)
- very weak binders down to `-0.92`

That wide range is good in principle, but examples at the extremes are more likely to behave like outliers if their local neighborhood in train is sparse or structurally inconsistent.

## Predicted outliers

These are **not** observed model residuals. They are **predicted high-risk evaluation examples** based on leakage, exact-sequence overlap, state/context reuse, and label extremity.

## Highest-risk predicted outliers

1. `1TM1`
   - risk score: `59.802`
   - critical overlaps: `8`
   - high-risk overlaps: `3`
   - exact-sequence overlap hits: `2`
   - mapped proteins: `P00782`, `Q40059`

2. `1TM5`
   - risk score: `59.302`
   - same repeated protein pair as above

3. `1TM4`
   - risk score: `58.709`
   - same repeated protein pair as above

4. `1TO1`
   - risk score: `58.346`
   - same repeated protein pair as above

5. `1Y4A`
   - risk score: `58.067`
   - same repeated protein pair as above

6. `1Y4D`
   - risk score: `58.062`
   - same repeated protein pair as above

7. `1Y33`
   - risk score: `57.964`
   - same repeated protein pair as above

8. `1ZV5`
   - risk score: `53.449`
   - critical overlaps: `8`
   - mapped protein: `P00698`

9. `2MCN`
   - risk score: `49.076`
   - critical overlaps: `1`
   - high-risk overlaps: `16`
   - mapped proteins: `P0CG48`, `Q9JLQ0`

10. `1BRS`
   - risk score: `47.459`
   - critical overlaps: `6`
   - exact-sequence overlap hits: `2`
   - very strong binder (`-19.09`)
   - mapped proteins: `P00648`, `P11540`

## Why these are likely outliers

There are two broad outlier modes here:

### Mode A: "too easy / too contaminated"

Examples like `1TM1`, `1TM4`, `1TM5`, `1TO1`, `1Y33`, `1Y4A`, and `1Y4D` are not necessarily hard because they are far from train. They are high-risk because they appear too close to train in exactly the wrong way. If a model performs well on them, that would not be convincing evidence of generalization.

### Mode B: "hard because of both extremity and entanglement"

Examples like `1BRS`, `2PTC`, and `3FP6` are risky because they combine:

- train/test overlap
- strong or unusual binding values
- repeated protein context

These are the kinds of points that can dominate error analysis or make a model look unstable.

## The good

This dataset does have genuine strengths:

- nontrivial size for a protein-protein affinity task
- mixed-source aggregation increases scope
- all PDB IDs are unique within each split
- the test set is not tiny
- the label range is broad enough to stress a regressor
- most locally covered examples are typed as protein-protein complexes

So there is a lot here that can support model-building.

## The bad

The split quality is weak:

- too much direct protein reuse
- too much exact-sequence reuse
- too many critical protein-set collisions
- too many high-risk contextual overlaps
- incomplete local coverage for part of the test set
- train provenance is mixed while test provenance is underspecified

## The ugly

The ugliest issue is not a single duplicate PDB. It is the repeated reuse of the same protein systems across train and test under slightly different structural contexts.

That creates the risk of a misleading result pattern:

- model appears to generalize
- but is actually exploiting repeated biological identity and neighborhood familiarity

The `P00782/Q40059` block and the `P00698`-centered block are the clearest examples of that.

## Practical recommendation

Current recommendation from the local gate:

- **re-split before treating this as a clean training/test benchmark**

At minimum, a stronger split should:

1. separate exact shared proteins across train and test
2. separate exact shared sequences across train and test
3. collapse repeated protein-pair series into one side of the split
4. review repeated target-centric clusters like the `P00698` block
5. re-check performance after those removals

## What to tell the colleague

If they want a candid but constructive summary:

- the dataset is useful and not trivial
- the model may still learn meaningful signals from it
- but the current split is not strong enough to support a high-confidence generalization claim
- if they publish with this split as-is, reviewers could reasonably question leakage and repeated-system bias

The cleanest path forward is not to abandon the dataset, but to:

- keep it as a development resource
- produce a stronger de-leaked evaluation split
- then report both:
  - performance on the current split
  - performance on the stricter split

That would turn a weakness into a credibility upgrade.

## Check-your-work appendix

Main machine-readable outputs:

- [colleague_dataset_forensic_review.json](/D:/documents/ProteoSphereV2/artifacts/status/colleague_dataset_forensic_review.json)
- [colleague_dataset_forensic_details.json](/D:/documents/ProteoSphereV2/artifacts/status/colleague_dataset_forensic_details.json)

Key scalar findings to verify:

- blocked reasons:
  - `critical_structure_state_reuse`
  - `direct_protein_leakage`
  - `exact_sequence_reuse`
- direct protein overlaps: `45`
- exact sequence overlaps: `46`
- mutation-like overlap pairs: `4`
- flagged structure-context pairs: `334`
- critical pairs: `116`
- high-risk pairs: `182`
- missing test structures: `9`

Top repeated test problem cases:

- `1TM1`
- `1TM4`
- `1TM5`
- `1TO1`
- `1Y33`
- `1Y4A`
- `1Y4D`
- `1ZV5`
- `2MCN`
- `1BRS`
