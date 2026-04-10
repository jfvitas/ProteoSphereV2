# Execution + Canonical Data Spec Overview

This section is the authoritative backbone for data correctness and runtime correctness.

It defines:
- canonical entities
- allowed relationships
- source normalization
- conflict resolution
- lineage
- DAG execution semantics
- task states
- scheduler behavior
- checkpoint/retry/recovery rules
- resource management and caching

No modeling work may bypass this layer.
