# p82 Ligand Lane Balance Note

This note is report-only and truth-boundaried. It compares the two grounded ligand pilot lanes, `P00387` and `Q9NZD4`, and recommends the next safe move after both lanes have validation previews.

## Lane Comparison

### P00387

- Status: `bulk_assay_actionable`
- Operator queue label: `lead_anchor`
- Validation preview: `aligned`
- Grounded evidence: local ChEMBL evidence with `93` activities, `25` emitted rows, and `23` distinct ligands
- Target: `CHEMBL2146` / `NADH-cytochrome b5 reductase`
- Safest next executable step: keep the bounded extraction validation / local bulk-assay ingest path, without claiming canonical ligand materialization

### Q9NZD4

- Status: `rescuable_now`
- Operator queue label: `bridge_rescue_candidate`
- Current evidence: local structure bridge is ready now
- Best next source: `1Y01`
- Truth boundary: candidate-only, no ligand rows materialized
- Safest next executable step: ingest the local structure bridge first, then produce a validation preview for that bridge path

## Balance Recommendation

P00387 should stay first because it already has aligned validation and deeper ligand evidence. Q9NZD4 should follow as the bridge-rescue lane because it is concrete locally but still needs bridge ingestion before it can be treated like a ligand-ready candidate.

After both lanes have validation previews, the next safe combined step is a refreshed operator/support preview that keeps both lanes separate and still does not include ligand rows in the bundle.

## Blocked Boundaries

- `bundle_ligands_included` remains `false`.
- No full ligand row materialization is claimed.
- Q9UCM0 remains deferred.
- The queue refresh is advisory only and does not authorize split or bundle mutation.

## Truth Boundary

This note does not promote either lane. It only balances the two grounded pilot lanes and records the next safe progression once both validation previews exist.
