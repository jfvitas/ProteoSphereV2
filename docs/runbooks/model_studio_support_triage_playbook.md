# Model Studio Support Triage Playbook

## Intake Categories

- `launchability_confusion`
- `dataset_governance`
- `runtime_failure`
- `scientific_wording`
- `ux_clarity`
- `analysis_compare_export`

## Severity

- `P1`: beta ship blocker, misleading or broken user-facing behavior
- `P2`: high-priority beta issue with workaround or limited scope
- `P3`: normal beta feedback
- `P4`: polish or future enhancement

## Routing

- `launchability_confusion` -> Ampere + Kepler
- `dataset_governance` -> McClintock + Kepler
- `runtime_failure` -> Kepler + Bacon + Euler
- `scientific_wording` -> Mill + Ampere
- `ux_clarity` -> Ampere + Euler
- `analysis_compare_export` -> Bacon + Euler + Mill as needed

## Daily Triage

1. Group new issues by category and severity.
2. Escalate P1 issues immediately.
3. Link each issue to evidence when possible.
4. Record whether the issue changes launchability, blocker language, or deferrals.
5. Close only when the runtime truth, UI wording, and docs all agree.

## Participant Response Expectation

- P1 issues: same-day acknowledgement
- usability and clarity issues: grouped into the next review wave
- documentation gaps: corrected in the current docs pack where possible
