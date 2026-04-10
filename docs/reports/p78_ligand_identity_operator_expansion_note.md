# p78 Ligand Identity Operator Expansion Note

This note identifies the next safe operator-visible ligand step now that the ordered accessions are surfaced.

## Next Safe Step

Publish a compact operator-visible queue card for the stage-1 ligand pilot.

It should show:

1. `P00387` as the first lane.
2. `Q9NZD4` as the second lane.
3. `P09105` as a support follow-up lane.
4. `Q2TAC2` as a support follow-up lane.
5. `Q9UCM0` as deferred.

## Why This Is The Right Next Step

The current ligand preview and support surface already expose the ordered accessions and their next truthful actions. The operator dashboard is still `no-go`, so the smallest safe move is visibility, not materialization.

This means operators can see the stage-1 queue without any claim that ligand rows exist in the bundle.

## What The Step Must Not Claim

- ligand rows are materialized
- `ligand_identity_group` is non-null
- `binding_context_group` is non-null
- the operator dashboard is release-ready

## Truth Boundary

- report-only
- no ligand row materialization
- no bundle mutation
- no latest-promotion changes
- `Q9UCM0` deferred

## Bottom Line

The next safe operator-visible ligand step is a queue-style preview card for the ordered stage-1 accessions, not ligand materialization: `P00387` first, `Q9NZD4` second, `P09105` and `Q2TAC2` as follow-ups, and `Q9UCM0` deferred.
