# Model Studio Reviewer Signoff Matrix

## Required Reviewers

| Reviewer | Ownership | Required For |
| --- | --- | --- |
| Kepler | Architecture, runtime, contracts | Canonical promotion engine, runtime truth, launchability authority |
| Euler | QA, regression, execution matrix | Automated tests, blocker behavior, rehearsal evidence |
| Ampere | UX/UI, user-audit | Guided flow, state wording, diagnostics clarity |
| Mill | Scientific semantics | Structural-biology truth, blocked-lane wording, state pairing claims |
| Bacon | ML systems and provenance | Runtime provenance, adapter truth, compare/export disclosure |
| McClintock | Candidate database and governance | Provenance completeness, admissibility, subset promotion rubric |

## Wave Checklist

Every major wave must record:

- reviewer name
- date
- surface reviewed
- verdict: `approved`, `approved_with_followups`, or `blocked`
- any P1/P2 findings
- evidence artifact paths

## Freeze-Gate Requirement

The controlled external beta cannot ship unless every required reviewer has:

- reviewed the final user-facing lane
- recorded no open P1 findings
- agreed with the current limitation and deferral ledgers

## Current Wave Final Approvals

| Reviewer | Date | Surface Reviewed | Verdict | Open P1 | Notes | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Kepler | 2026-04-10 | canonical authority, runtime truth, readiness control plane | approved_with_followups | no | No open P1/P2 findings. Follow-up: keep compatibility mirror surfaces explicitly compatibility-only until consumers migrate to canonical aliases. | `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10` |
| Euler | 2026-04-10 | regression coverage, execution matrix, launch-path truth | approved_with_followups | no | No open P1/P2 findings. Follow-up: reviewer signoff ledger completion remains a governance follow-up, not a QA/runtime blocker. | `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10` |
| Ampere | 2026-04-10 | user-facing wording, diagnostics clarity, guided flow | approved | no | No open P1/P2 findings. Procurement hotspot is now tracked under `parallel_risks` instead of ship-blocking readiness blockers. | `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10` |
| Mill | 2026-04-10 | scientific wording, blocked-lane truth, state claims | approved_with_followups | no | No open P1/P2 findings. Follow-up: keep the readiness surface synchronized with the refreshed evidence pack as the beta program operates. | `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10/blocked/blocked_feature_trace.json` |
| Bacon | 2026-04-10 | provenance, compare/export disclosure, Stage 2 truth | approved | no | No open P1/P2 findings. Fresh rehearsal evidence and resolved backend/device disclosure are aligned with the live product truth. | `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10` |
| McClintock | 2026-04-10 | candidate-database governance, admissibility, subset promotion | approved | no | No open P1/P2 findings. Canonical row authority now aligns with whole-complex launchability for the promoted external-beta subset, and pool/report wording is fully launchable-now. | `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10` |
