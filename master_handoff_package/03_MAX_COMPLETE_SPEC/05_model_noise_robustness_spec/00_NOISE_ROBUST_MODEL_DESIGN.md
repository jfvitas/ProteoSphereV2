# Noise-Robust Model Design Spec

## Goal
Design models capable of “hunting through the noise” in heterogeneous biological data.
The problem is inherently higher-dimensional than any single source captures, so models must:
- integrate multiple modalities
- estimate uncertainty
- learn which modality to trust
- remain robust to missingness and source conflicts

## 1. Multi-view architecture requirement
Do not concatenate all raw features into one monolithic vector by default.
Instead build separate encoders:
- Structure encoder
- Sequence/evolution encoder
- Ligand encoder
- Biology/pathway/evidence encoder
- Optional assay metadata encoder

Each produces an embedding plus optional confidence summary.

## 2. Fusion requirements
Support:
- simple concatenation baseline
- gated fusion
- cross-modal attention fusion
- mixture-of-experts fusion
- residual late fusion
Fusion module must be able to down-weight missing or low-confidence modalities.

## 3. Attention requirements
Within-modality attention:
- residue attention
- atom/edge attention
- pocket attention
Across-modality attention:
- attend over modality embeddings conditioned on task
Need explicit masks and confidence-aware weighting.

## 4. Uncertainty requirements
Required support:
- predictive variance head
- deep ensemble wrapper
- MC dropout option
- calibration evaluation
- confidence-aware loss weighting
- source-quality feature injection

For regression, preferred heteroscedastic loss option:
- predict mean and variance
- penalize both error and variance misuse

## 5. Data-centric noise control
Before model sees data, platform must support:
- structure quality filters
- assay quality filters
- sequence redundancy filters
- family-aware balancing
- outlier review flags
- source conflict burden scoring

## 6. Curriculum learning
Support staged training:
Phase 1:
- highest-quality structures and labels
Phase 2:
- moderately noisy expanded dataset
Phase 3:
- broader weakly labeled or lower-confidence data if task supports it

## 7. Multi-task learning
Required support for shared trunk + multiple heads:
- affinity
- interaction yes/no
- interface hotspot or contact prediction(optional)
- uncertainty
- auxiliary biological plausibility head(optional)

## 8. Learned edge importance
Graph models must support attention/weighting over edges.
Do not assume all spatial neighbors are equally informative.

## 9. Missing-dimension mitigation
When problem complexity exceeds observed features:
- leverage pretrained embeddings
- use evolutionary information
- use pathway context
- use multitask auxiliary supervision
- estimate uncertainty instead of overconfident extrapolation
