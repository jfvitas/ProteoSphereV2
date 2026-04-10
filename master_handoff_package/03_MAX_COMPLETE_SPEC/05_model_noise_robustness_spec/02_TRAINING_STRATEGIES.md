# Training Strategies for Noisy Multimodal Biology

## Required strategies to support
- clean-to-noisy curriculum
- quality-weighted sampling
- class/target balancing where appropriate
- uncertainty-aware losses
- multitask shared trunk
- ensembling
- ablation tracking by modality
- missing-modality training augmentation(optional advanced)
- confidence calibration post-hoc or integrated

## Ablation requirements
Every flagship model experiment should be runnable with:
- structure only
- sequence only
- biology only
- structure + sequence
- structure + sequence + biology
- full model with uncertainty
This is required to understand which modalities truly help.

## Reporting requirements
- primary task metrics
- calibration metrics where uncertainty enabled
- performance by source-quality tier
- performance by family/group split
- missingness sensitivity analyses
