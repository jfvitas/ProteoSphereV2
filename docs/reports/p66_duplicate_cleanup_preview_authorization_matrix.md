# P66 Duplicate Cleanup Preview Authorization Matrix

This report-only note defines the preview authorization buckets for duplicate cleanup using the current executor status, the P65 operator handoff, the P64 post-mutation verification contract, and the live duplicate status surface.

## Current Boundary

The live cleanup executor remains report-only and delete-disabled:

- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/p65_duplicate_cleanup_operator_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/p65_duplicate_cleanup_operator_handoff.json)
- [artifacts/status/p64_duplicate_cleanup_post_mutation_verification_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_duplicate_cleanup_post_mutation_verification_contract.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)

The safe-first boundary still means:

- exact SHA-256 matching
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites
- allowed cohorts only

## Approval Buckets

### Bucket 1: Report-Only Preview

This is the only live bucket today.

Allowed:

- read inventory, status, and dry-run plan artifacts
- generate preview and report outputs
- no filesystem mutation

Required evidence:

- current executor status
- current dry-run plan
- current cleanup status

Protected-surface rule:

- protected paths stay immutable
- partial paths stay excluded
- latest surfaces stay untouched

Rollback evidence:

- none needed because no mutation is allowed
- any warning is handled by regenerating the report surface, not by cleanup

### Bucket 2: Preview Generated, Unverified

This is a preview-only staging bucket, not a mutation bucket.

Allowed:

- produce a preview artifact
- compare it against the approved plan
- inspect for drift

Required evidence:

- frozen plan identity
- current inventory snapshot
- current status snapshot

Protected-surface rule:

- same as Bucket 1
- any touch of protected or latest surfaces aborts preview acceptance

Rollback evidence:

- preview diffs
- plan-vs-inventory mismatch report
- no destructive rollback required

### Bucket 3: Preview Generated, Verified Assets

This is the strongest preview bucket, but it still does not authorize deletion.

Allowed:

- publish a verified preview manifest
- attach checksum and inventory evidence
- prepare for a future mutation approval

Required evidence:

- frozen plan identity
- refreshed inventory parity
- verified preview asset set
- post-mutation verification contract reference

Protected-surface rule:

- protected, partial, and latest surfaces remain immutable
- any preview result that suggests touching those surfaces fails closed

Rollback evidence:

- verified preview checksum
- before/after path set for the preview run
- operator-visible failure note if the preview cannot be verified

### Bucket 4: Mutation Authorized, Destructive Hold

This bucket is hypothetical and still blocked today.

Allowed:

- only after separate destructive authorization
- only with snapshot parity
- only with the P63 and P64 gates satisfied

Required evidence:

- explicit mutation approval
- frozen plan identity
- current inventory parity
- current status parity
- current approved cohort allowlist

Protected-surface rule:

- protected, partial, and latest surfaces must remain immutable
- any touch aborts the run immediately

Rollback evidence:

- approved recovery target
- applied change log
- rollback or abort note for partial mutation
- refreshed post-mutation inventory
- audit trail with approval id, executor id, and source hashes

## What Still Blocks Destructive Cleanup

Destructive cleanup is still blocked because:

- no mutation-authorizing executor path exists yet
- the current executor remains report-only and delete-disabled
- the approval boundary for destructive cleanup is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation

## Bottom Line

Only the report-only preview bucket is live today. The stronger preview buckets help operators inspect and verify the plan, but none of them authorize deletion or movement of raw storage. Protected surfaces stay immutable in every bucket, and rollback evidence only becomes mandatory once a destructive bucket is ever approved.
