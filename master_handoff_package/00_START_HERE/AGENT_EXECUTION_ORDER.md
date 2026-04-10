# AGENT EXECUTION ORDER

## Step 1 — Lockdown build
Unzip and read: `01_LOCKDOWN_SPEC/`
Build the reference pipeline exactly as specified.

Required outcome:
- ingest RCSB + UniProt + BindingDB
- canonicalize chains to proteins
- compute the required first-pass features
- train the locked reference model
- evaluate on the locked split strategy
- run tests

Do not proceed until this works end-to-end.

## Step 2 — Execution + canonical data integration
Read: `02_EXECUTION_AND_CANONICAL_SPEC/`
Refactor / extend the working pipeline so that:
- all objects use canonical records
- all artifacts carry provenance
- DAG execution, checkpointing, retries, and recovery are active
- schema/version invalidation works

## Step 3 — Full expansion
Read: `03_MAX_COMPLETE_SPEC/`
Expand only after Steps 1 and 2 are complete and stable.

Expansion includes:
- broader model families
- richer feature ontology
- motif, disorder, pathway, and evolutionary layers
- noise-robust multimodal architecture
- hybrid/ensemble systems
- advanced GUI controls and registries

## Conflict resolution
If two docs conflict:
1. Lockdown spec wins for first build
2. Execution/canonical spec wins for data/runtime correctness
3. Max complete spec expands but does not override earlier locked decisions unless explicitly promoted in a future milestone
