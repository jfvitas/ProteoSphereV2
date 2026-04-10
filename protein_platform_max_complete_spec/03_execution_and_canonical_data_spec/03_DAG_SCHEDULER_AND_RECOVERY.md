# DAG, Task Lifecycle, Scheduler, and Recovery

## 1. DAG node classes
- source_acquire
- raw_validate
- normalize
- map_ids
- feature_extract
- feature_aggregate
- dataset_build
- split_generate
- model_train
- model_validate
- model_test
- calibrate
- explain
- export
- cleanup/cache maintenance

## 2. Task state machine
- created
- queued
- scheduled
- running
- paused
- checkpointing
- completed
- failed_retryable
- failed_nonretryable
- cancelled
- stale_requires_rebuild

Transitions must be explicit and logged.

## 3. Scheduler requirements
- topological ordering
- dependency-aware priority queue
- configurable parallelism
- resource-aware scheduling
- retry backoff
- checkpoint-aware resume
- stale artifact invalidation by input hash/config hash

## 4. Retry logic
- retry_count configurable per node type
- exponential backoff with jitter
- source_acquire nodes may switch to alternate mirrors or cached raw payloads
- nonretryable failure classes include schema mismatch caused by code bug, not transient I/O

## 5. Checkpoint rules
Must checkpoint:
- after raw source acquisition
- after normalization/mapping
- after feature extraction
- after dataset build
- during long training runs
- before export if export transforms are costly

Checkpoint contents:
- node inputs hash
- node outputs pointer
- config hash
- code version
- RNG state if relevant
- optimizer/scheduler state for training nodes
- lineage pointers

## 6. Recovery rules
- if downstream node fails, upstream valid checkpoints remain reusable
- if schema version changes incompatibly, dependent checkpoints become stale
- if source version changes, affected canonical/feature nodes must be invalidated per lineage graph
- recovery must never silently mix artifacts from incompatible schemas

## 7. Caching
- raw payload cache
- parsed object cache
- feature cache
- embedding cache
- train/val/test split cache
- model checkpoint cache
Each cache must include version and hash metadata.

## 8. Resource manager
Track:
- available CPUs
- available GPUs
- VRAM utilization
- RAM usage
- disk/cache pressure
Policies:
- max concurrent jobs per GPU
- small-job packing rules
- CPU fallback
- OOM-aware resubmission with adjusted batch size(optional)
