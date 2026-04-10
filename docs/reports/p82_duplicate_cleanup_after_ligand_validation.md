# P82 Duplicate Cleanup After Ligand Validation

## Conclusion

No direct interaction exists.

Adding `Q9NZD4` bridge validation does **not** change duplicate cleanup prerequisites.

## Why

- [p81_q9nzd4_bridge_evidence_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/p81_q9nzd4_bridge_evidence_handoff.json) keeps `Q9NZD4` candidate-only and non-materialized.
- [local_bridge_ligand_payloads.real.json](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json) is a bridge-evidence surface, not a duplicate-cleanup authorization surface.
- [duplicate_cleanup_first_execution_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_first_execution_preview.json) is still scoped to exact duplicate cleanup in `data/raw/local_copies`.
- [p36_storage_dedupe_safety_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p36_storage_dedupe_safety_contract.json) still ties cleanup to:
  - byte identity
  - provenance lineage
  - role equivalence
  - allowlisted cleanup scope

## Explicit Boundary

Even if `Q9NZD4` bridge validation is added, it:

- does not authorize deletion
- does not alter cleanup ordering
- does not change duplicate eligibility
- does not move bridge-validation artifacts into cleanup candidate classes
