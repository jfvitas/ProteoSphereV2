# P25 v1.1 Roadmap

## Purpose
This report turns the release learnings into a realistic v1.1 roadmap. It is report-only and fail-closed. It does not claim GA readiness, and it does not change the current `blocked_on_release_grade_bar` posture.

## What We Learned
The recent release work showed a few clear truths:

- A release posture is only useful if the manifests, docs, and dashboard all agree.
- Reproducibility must be explicit, pinned, and rehearsal-friendly before it can be treated as release-grade.
- Public distribution should be staged conservatively, with missing-artifact blockers preserved instead of hidden.
- Maintenance and incident handling need to be documented alongside publication, not after the fact.
- The current benchmark is still bounded by the frozen 12-accession cohort and a local prototype runtime.
- Procurement truth still matters because the STRING and UniRef tail downloads remain partial.

## Current Boundary
The project is still blocked for the same reasons surfaced in the GA readiness report:

- the runtime is still a local prototype
- the benchmark remains cohort-bounded
- the release bundle is staged, not authorized
- the GA path is report-only and fail-closed
- procurement truth still shows two active partial tail downloads

That means v1.1 should be a hardening and capability-release milestone, not a GA claim.

## v1.1 Goal
v1.1 should make the project more usable, more reproducible, and more auditable without widening the truth boundary.

The target is:

- a cleaner release chain
- a more complete operator experience
- stronger training-set and external-dataset tooling
- clearer reproduction and maintenance paths
- fewer hidden assumptions in publication, packaging, and provenance

## Recommended v1.1 Pillars

### 1. Finish the Release Evidence Chain
The first v1.1 pillar should complete the release plumbing that is already partially in place.

Priority work:

- keep `tag_release.py` as the canonical manifest pinning path
- keep `publish_open_source_bundle.py` as the conservative public bundle stager
- keep `publish_release_cards.py` as the evidence-backed card publisher
- keep `p25_clean_machine_plan.md` as the reproduction rehearsal contract
- keep `p25_ga_readiness_report.md` as the top-level report-only readiness summary

Expected outcome:

- a release chain that is explainable end-to-end
- no silent widening of claims
- no mismatch between release docs, support docs, and the dashboard

### 2. Complete the Reproducibility and Recovery Story
v1.1 should make it easier to prove what can be rebuilt and what cannot.

Priority work:

- keep clean-machine reproduction fail-closed on missing or stale artifacts
- keep rollback and docs freshness validators strict
- keep GA signoff and RC regression reports aligned with the dashboard
- make failure cases easier to inspect than success cases

Expected outcome:

- a clear rebuild-and-replay path for tagged artifacts
- explicit boundaries between rehearsal and authorization
- repeatable operator checks that do not depend on tribal knowledge

### 3. Improve the Training-Set and External Dataset Interfaces
This is the most important product-facing theme for v1.1.

Priority work:

- keep `training_set_readiness_preview` as the merged readiness surface
- keep `cohort_compiler_preview` and `package_readiness_preview` as the operator-facing packaging path
- keep `external_dataset_assessment_preview` and the binding/structure/provenance audits as fail-closed checks
- keep `external_dataset_intake_contract_preview` narrow and explicit

Expected outcome:

- a practical interface for building candidate training sets
- a practical interface for assessing external datasets for leakage, provenance, and modality flaws
- a consistent answer to “can we trust this dataset for this purpose?”

### 4. Keep Scraping and Enrichment Structured
v1.1 should continue the structured-source-first approach, but not turn report-only enrichment into release claims.

Priority work:

- continue structured PDB, UniProt, InterPro, BioGRID, IntAct, BindingDB, and M-CSA lanes
- keep STRING and UniRef-derived material non-governing until tail completion and validation
- keep page-level scraping targeted and non-governing by default
- keep provenance-tagged context separate from grounded truth

Expected outcome:

- richer operator context
- cleaner accession and structure summaries
- fewer ambiguous or overextended enrichment claims

### 5. Strengthen Release Operations
v1.1 should make the day-to-day release process easier to operate.

Priority work:

- keep `p24_governance_pack.md` and `post_release_maintenance.md` in sync with actual practice
- keep `release_blocker_tracker.py` and GA readiness reporting honest
- keep the dashboard focused on blockers, packet deficits, and provenance truth
- keep queue and procurement reporting aligned to reality

Expected outcome:

- less manual interpretation
- better incident handling
- clearer maintenance ownership

## Proposed Sequence

### Phase A: Stabilize the Evidence Layer
Finish and harden the current release evidence chain before adding more surface area.

Focus:

- manifest pinning
- public bundle staging
- release card publishing
- GA readiness reporting
- clean-machine reproduction

### Phase B: Expand Training and Dataset Tooling
Use the now-stable release evidence to sharpen the user-facing tooling.

Focus:

- training-set readiness
- cohort compilation
- package readiness
- external dataset assessment
- leakage and provenance audits

### Phase C: Broaden Structured Enrichment
Keep adding structured biological context where it materially improves operator decisions.

Focus:

- PDB and structure metadata
- protein feature and function context
- binding and interaction summaries
- motif and mechanism context

### Phase D: Close Remaining Tail Dependencies
Only after the above is stable should the tail procurement work be treated as a release unlock.

Focus:

- STRING full interaction file completion
- UniRef100 completion
- zero-gap procurement truth
- post-tail validation of any derived interaction or cluster surfaces

## Not In v1.1
These should not be treated as v1.1 goals unless the evidence changes materially:

- GA release authorization
- widening the benchmark cohort just to make release look stronger
- turning report-only enrichment into governing truth
- relaxing fail-closed behavior on missing, stale, or lineage-inconsistent artifacts
- treating partial procurement as complete enough for release claims

## Success Criteria
v1.1 is successful if it gives us:

- a dependable release evidence chain
- a better operator and training-set experience
- a clearer external dataset assessment path
- stronger reproducibility and maintenance stories
- more structured context without overclaiming

It is not successful if it simply increases surface area while leaving the truth boundary unclear.

## Current Recommendation
The right v1.1 plan is to treat release hardening, dataset tooling, and structured enrichment as the three parallel tracks, with procurement completion and GA authorization remaining explicitly blocked until the evidence fully supports them.

## Current Decision
This roadmap is:

- `report-only`
- `fail-closed`
- `blocked_on_release_grade_bar`
