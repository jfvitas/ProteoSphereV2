# P67 Ligand Signature Emission Prerequisites

## Objective

Define the exact repo conditions that must be satisfied before any non-null `ligand_identity_group` or `binding_context_group` values can be emitted.

Grounding:

- [p66_ligand_signature_stage1_acceptance.json](/D:/documents/ProteoSphereV2/artifacts/status/p66_ligand_signature_stage1_acceptance.json)
- [p64_ligand_placeholder_implementation_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_ligand_placeholder_implementation_order.json)
- [leakage_group_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_group_preview.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)

## Current Repo State

Current state is still strictly pre-ligand-grouping.

The two direct blockers are visible already:

1. [leakage_group_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_group_preview.json) says:
   - `truth_boundary.ligand_overlap_materialized = false`
2. [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) still shows five unresolved ligand refs:
   - `ligand:P00387`
   - `ligand:P09105`
   - `ligand:Q2TAC2`
   - `ligand:Q9NZD4`
   - `ligand:Q9UCM0`

There is an additional row-specific blocker for `Q9UCM0`:

- `structure:Q9UCM0`
- `ppi:Q9UCM0`

So the repo is not yet in a state where non-null ligand grouping is safe.

## Global Prereqs Before Any Non-Null Ligand Grouping

### G1. Stage-1 support-only emission is already stable

`P66` must already be true first.

That means:

- stage-1 fields are additive only
- row counts stay fixed
- all non-ligand grouping stays fixed
- all ligand grouping fields are still null

If the repo has not demonstrated that stable placeholder phase, it is not ready for non-null ligand groups.

### G2. A repo-visible lightweight ligand family exists

`P64` is explicit: non-null ligand grouping stays blocked until lightweight ligand entities exist.

That means the repo needs a visible, materialized ligand family surface, not just:

- packet deficit refs
- support-only placeholder fields
- upstream canonical ligand counts

### G3. Ligand normalization is deterministic

Before `ligand_identity_group` can be non-null, the repo must be able to assign that group deterministically.

Required properties:

- stable ligand identity namespace
- stable source identifier
- stable normalization basis
- reruns produce the same `ligand_identity_group`

Without that, non-null grouping is not defensible.

### G4. Leakage grouping explicitly includes ligand overlap

The current leakage surface is not enough.

Today:

- [leakage_group_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_group_preview.json) says `ligand_overlap_materialized = false`

Before non-null ligand groups are allowed, that surface must move to a state where ligand overlap is materially represented, not just protein-spine grouping.

### G5. Binding context has a defined constructor

`binding_context_group` is stricter than `ligand_identity_group`.

It requires:

- explicit context components
- deterministic key construction
- row-level provenance for the context inputs

No inferred or hand-waved context grouping is acceptable.

### G6. Packet deficits are no longer the primary basis

The current packet deficit refs are valid pressure signals, but they are not a valid basis for non-null grouping.

Non-null ligand groups must not be emitted from:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`
- `ligand:Q9UCM0`

Those are support refs only.

## Row-Level Prereqs For `ligand_identity_group`

For any specific row, non-null `ligand_identity_group` is allowed only when:

1. the row has repo-visible normalized ligand evidence
2. the group value is derived from that normalized ligand family, not from packet refs or accession alone
3. rerunning the same inputs yields the same group value

## Row-Level Prereqs For `binding_context_group`

For any specific row, non-null `binding_context_group` is allowed only when:

1. all ligand-identity row-level prereqs are already satisfied
2. the required protein context is present and deterministic
3. if structure is part of the context, the required structure surface is materialized for that row
4. the context group is derived from explicit context components, not from accession similarity

## Current Accession-Level Blockers

### `P00387`

Still blocked because:

- `ligand:P00387` is unresolved in the packet deficit dashboard
- there is no repo-visible materialized lightweight ligand family cited here
- leakage grouping still says ligand overlap is not materialized

### `P09105`

Still blocked because:

- `ligand:P09105` is unresolved
- there is no repo-visible materialized lightweight ligand family cited here
- leakage grouping still says ligand overlap is not materialized

### `Q2TAC2`

Still blocked because:

- `ligand:Q2TAC2` is unresolved
- there is no repo-visible materialized lightweight ligand family cited here
- leakage grouping still says ligand overlap is not materialized

### `Q9NZD4`

Still blocked because:

- `ligand:Q9NZD4` is unresolved
- there is no repo-visible materialized lightweight ligand family cited here
- leakage grouping still says ligand overlap is not materialized

### `Q9UCM0`

Still blocked because:

- `ligand:Q9UCM0` is unresolved
- `structure:Q9UCM0` is unresolved
- `ppi:Q9UCM0` is unresolved
- there is no repo-visible materialized lightweight ligand family cited here
- leakage grouping still says ligand overlap is not materialized

`Q9UCM0` is therefore blocked for both ligand identity grouping and binding-context grouping.

## Disallowed Shortcuts

These conditions are not sufficient:

- canonical ligands existing upstream
- stage-1 placeholder fields existing
- packet rows being partial rather than empty
- protein-level leakage groups already existing
- support-only packet refs being present

None of those justify non-null ligand grouping.

## Ready-State Definition

`ligand_identity_group` may be non-null only when:

- all global prereqs are satisfied
- row-level normalized ligand evidence exists
- deterministic normalization exists for that row

`binding_context_group` may be non-null only when:

- all global prereqs are satisfied
- the ligand identity prereqs are satisfied
- deterministic context construction exists for that row
- any required structure context is already materialized

## Bottom Line

Non-null ligand grouping is blocked in the current repo state. The next unlock is not “more packet refs.” The unlock is a repo-visible lightweight ligand family plus deterministic normalization and a leakage surface that explicitly acknowledges ligand overlap materialization.
