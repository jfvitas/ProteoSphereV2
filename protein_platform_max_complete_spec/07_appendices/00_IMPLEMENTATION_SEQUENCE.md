# Recommended Implementation Sequence

1. Core config and schema engine
2. Provenance system
3. Connectors for backbone sources
4. Canonical entities and mapping logic
5. Conflict-resolution layer
6. Feature calculators for core structural and sequence features
7. Dataset builder and splitters
8. Baseline models
9. Flagship multimodal model
10. Trainer/evaluator
11. DAG scheduler/checkpointing
12. GUI schema binding
13. API layer
14. Advanced motif/pathway/evolution enrichments
15. AutoML/experiment manager
16. Interpretability and diagnostics

Never reverse this by building flashy models before canonicalization and provenance are sound.
