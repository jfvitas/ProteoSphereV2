# Model Studio Controlled External Beta Charter

## Scope

This beta is a controlled, invited, user-facing beta for Model Studio. The shipped lane is PPI-first and only admits post-PPI broadening after the PPI freeze gate is cleared.

Safe launchable lanes at charter time:

- `release_pp_alpha_benchmark_v1`
- `robust_pp_benchmark_v1`
- `expanded_pp_benchmark_v1`
- `governed_ppi_blended_subset_v2`

Visible but not launchable at charter time:

- review-pending governed subset candidates
- PyRosetta and free-state prototype lanes

Active beta lanes that are still not part of the stable launchable pool list:

- atom-native beta, when the selected controls remain launchable and the current beta limits are acceptable for the study
- the Studio-local deterministic sequence-embedding beta lane, when the selected controls remain launchable and the current leakage/provenance caveats remain acceptable for the study

Out of scope for ship:

- broad non-PPI expansion
- public GA claims
- AlphaFold-derived support
- unreviewed or non-native scientific materialization lanes

## Beta Bar

The beta is ready only when all of the following are true:

- launchability and governance derive from one canonical row-to-subset-to-pool authority, with any legacy summary surfaces treated as compatibility mirrors rather than independent decision paths
- the guided flow is usable by an invited first-time user without shell help
- blocked lanes explain what is missing and do not feel broken
- reviewer signoff is complete with no open P1 findings
- participant docs, support, triage, reporting, and rollback procedures are in place

## State Vocabulary

The user-facing state model is locked to:

- `Launchable now`
- `Review pending`
- `Inactive`

Internal workflow states may be richer, but they must map cleanly to the user-facing vocabulary.

## Severity Model

- `P1`: blocks beta ship
- `P2`: may ship only with explicit deferral and non-user-breaking scope
- `P3`: backlog item with no immediate beta block
- `P4`: polish or future enhancement

## Reviewer Ownership

- `Kepler`: architecture, runtime, contracts, promotion engine
- `Euler`: QA, regression, matrix, blocker behavior
- `Ampere`: UX/UI, user-audit, state language
- `Mill`: scientific and structural-biology semantics
- `Bacon`: ML systems, runtime provenance, compare/export truth
- `McClintock`: candidate database, provenance, governance, admissibility

## Ship Rule

No major wave advances with an open P1 from a required reviewer.
