# Provenance, Lineage, and Reproducibility

## Every object must carry
- source identifier(s)
- acquisition timestamp
- parser version
- transformation chain
- confidence score or confidence class if available
- content hash
- parent object IDs if derived

## Reproducibility metadata
Every run must store:
- project config snapshot
- code commit hash or source bundle hash
- environment summary
- library versions
- hardware summary
- RNG seed(s)
- dataset version IDs
- split artifact ID
- feature schema version
- model schema version

## Lineage graph
Must support answering:
- which raw files produced this dataset row?
- which canonical objects fed this model?
- which feature calculators produced this tensor?
- which config produced this checkpoint?
- which source version changed after this run?

## No silent mutation rule
Once an artifact is versioned, mutation must create a new version, not overwrite.
