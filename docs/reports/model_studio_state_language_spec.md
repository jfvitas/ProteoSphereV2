# Model Studio State Language Spec

## User-Facing States

Decision points shown to invited users must use only:

- `Launchable now`
- `Review pending`
- `Inactive`

## Definitions

### Launchable now

Use when the backend authoritatively allows the lane, dataset, or feature in the current beta surface.

### Review pending

Use when the surface is visible, technically real enough to inspect or review, but not safe for routine study launches.

### Inactive

Use when the surface is out of the current beta lane or still lacks the implementation or evidence needed for meaningful review.

## Do Not Use As Primary User Language

- `beta_soon`
- `planned_inactive`
- `hold`
- `promotion candidate`
- `governed bridge readiness`

These may appear in advanced or internal views, but they must not replace the primary user-facing state language.

## Guidance

- Keep blocked explanation local to the selected control or drawer.
- Prefer short, concrete reasons over catalog jargon.
- If a surface is review-pending, say what evidence would unblock it.
