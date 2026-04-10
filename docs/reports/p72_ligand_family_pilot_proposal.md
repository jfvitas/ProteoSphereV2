# P72 Ligand Family Pilot Proposal

This is a report-only proposal for the first safe ligand pilot, grounded in the current live bundle manifest, ligand gap probes, source maps, and the existing ligand stage contracts.

## What The Pilot Is

The pilot is still support-only. The current bundle still says `ligands.included = false` and `ligands.record_count = 0`, so this proposal does not pretend a real ligand family already exists.

What it does do is define the safest first ligand pilot shape:

- keep the pilot limited to four accessions
- keep `Q9UCM0` deferred
- keep ligand grouping fields null for now
- keep split behavior and leakage keys unchanged

## Safe Row Shape

The live placeholder contracts already show the safe boundary clearly. The pilot row shape should stay on the support side of that boundary:

- `ligand_placeholder_status`
- `ligand_support_refs`
- `ligand_truth_note`

The future identity-core ligand family can later use:

- `ligand_row_id`
- `ligand_identity_namespace`
- `ligand_identity_source_id`
- `ligand_normalization_basis`
- `source_provenance_refs`
- `linked_protein_refs`

The current report does not authorize any non-null ligand grouping fields.

## Safe Scope

The first pilot wave should be limited to:

- `P00387`
- `P09105`
- `Q2TAC2`
- `Q9NZD4`

`Q9UCM0` stays out of the first wave because it still has unresolved structure and PPI blockers.

That keeps the pilot aligned with the current gap surface and avoids opening a broader ligand family before the repo can support it truthfully.

## Blockers

The main blockers are straightforward:

- the bundle still excludes ligands
- the live leakage preview still says ligand overlap is not materialized
- the operator dashboard is still `no-go`
- the release grade bar is still blocked
- the repo does not yet have a real lightweight ligand family to normalize against

In other words, this is still a support-only pilot proposal, not a claim that the family already exists.

## Expected First Accessions

The safest first accessions, in order, are:

1. `P00387`
1. `P09105`
1. `Q2TAC2`
1. `Q9NZD4`

`P00387` is the strongest anchor because it already has local ChEMBL and BioLiP support in the current source map. The other three stay in the pilot because they are current ligand-gap accessions, but they should remain support-only until the repo has a real ligand family to materialize.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim a materialized ligand family, ligand-aware split behavior, or release readiness that the current bundle and dashboard do not support.
