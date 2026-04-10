# Release Program Master Plan

Date: 2026-03-22
Scope: full review and expansion of the ProteoSphereV2 program through QA, user-simulation validation, production release, and post-release operations

## North Star

ProteoSphereV2 must become a trustworthy open-source biomolecular intelligence platform that can:

- procure and pin real protein, protein-protein, protein-ligand, structural, pathway, motif, disorder, and evolutionary evidence
- reconcile those sources conservatively into a canonical library with explicit provenance and failure accounting
- design training sets and materialize robust training packets from selected examples only
- train and evaluate versatile multimodal models on real data with stable, reproducible execution
- expose the system through an operator surface that scientists can understand, audit, and use safely
- survive weeklong unattended execution without ambiguous health signals
- reach a release state that is reproducible, documented, regression-tested, and supportable

## Release Definition

The product is only release-ready when all of the following are true:

1. Data completeness is evidence-backed.
   Every supported accession, pair, ligand, and packet lane has a machine-readable provenance and failure state.

2. Canonical integrity is fail-closed.
   No ambiguity is silently flattened into a canonical claim.

3. Training packet materialization is deterministic.
   A selected example can be rehydrated from pinned manifests and checksums on demand.

4. Modeling claims are benchmarked on real data.
   Reported metrics, ablations, and utility judgments are backed by reproducible artifacts, not simulated placeholders.

5. Operator workflows are usable and auditable.
   A scientist can inspect lineage, understand gaps, and run supported workflows without hidden state.

6. QA is multilayered.
   Unit, integration, benchmark, soak, failure-injection, and user-simulation validation all pass the release bar.

7. Release engineering is reproducible.
   A clean-machine install, upgrade, rollback, and cold-start run all succeed from tagged artifacts.

8. Post-release operation is supportable.
   The team can detect drift, recover state, and maintain trust after launch.

## Program Design Principles

- Truth before throughput: no optimistic inference across missing biological evidence.
- Local-first provenance: remote sources are mirrored or pinned before they drive canonical or training state.
- Selective expansion: heavy assets are materialized only when examples are selected or validated.
- Scientific explainability: operator surfaces must show why a record exists, not just that it exists.
- Benchmark honesty: partial data and thin-lane evidence must remain explicit all the way through release.
- Multi-agent discipline: tasks stay small, ownership stays disjoint, and branch isolation remains enforceable.
- Reproducibility by construction: manifests, checksums, release IDs, and runtime identity are first-class.

## Cross-Cutting Workstreams

### Data and Knowledge

- source procurement, mirroring, and retention
- canonical identity and conflict handling
- summary-library enrichment for proteins, pairs, ligands, motifs, pathways, origin, and disorder
- corpus completeness, coverage depth, and failure accounting

### Training and Modeling

- packet materialization, asset normalization, and rebuild determinism
- multimodal model portfolio, ablations, and calibration
- training stability, resume identity, and experiment governance

### Product and Operator

- PowerShell operator robustness
- WinUI handoff and production GUI scope
- workflow recipes, evidence drilldown, dataset design, and user-facing diagnostics

### QA and Release

- regression suites, soak testing, and failure injection
- user-simulation validation and research-scenario playback
- release packaging, installation, upgrade, rollback, and support readiness

## Phase Map

| Phase | Theme | Primary outcome | Required proof |
| --- | --- | --- | --- |
| 1 | Locked baseline | exact reference pipeline and lockdown contract | hardened locked stack integration |
| 2 | Canonical execution | canonical data and provenance graph | canonical pipeline, checkpoint, provenance validation |
| 3 | Source analysis and acquisition | release-stamped source procurement | source matrix, live smokes, raw mirrors |
| 4 | Storage and packet materialization | indexed storage and selective packet build | packet materialization and index rebuild validation |
| 5 | Multimodal modeling | executable flagship runtime | real runtime path, metrics, packaging validation |
| 6 | Benchmark truth surface | honest release bundle and benchmark artifacts | benchmark release validation, operator visibility |
| 7 | Stabilization | procurement and semantics hardening | stabilization regression and lint cleanup |
| 8 | Repo hygiene | repo-wide verification quality | final ruff and test verification |
| 9 | Operator contract | stable machine-readable operator state | parity validator and schema contract |
| 10 | Runtime and coverage hardening | stronger runtime and source depth | executable runtime, hardened source coverage |
| 11 | Materialized library visibility | real library artifact in operator flow | operator/library parity regression |
| 12 | Local corpus reuse | online plus bio-agent-lab integration | local import validation and usefulness review |
| 13 | Corpus gap analysis | ranked missing-source and packet gaps | fingerprint validation and training-packet audit |
| 14 | Cohort uplift discovery | real candidate ranking from source depth | curated PPI slice and protein-depth slice |
| 15 | Cohort enrichment | upgraded benchmark cohort from real evidence | upgraded cohort slice and reranked benchmark |
| 16 | Corpus completion | release-corpus evidence ledger and completeness gate | accession-level completeness report and failure ledger |
| 17 | Scientific library enrichment | decision-grade knowledge cards and recipe design | library coverage validation and recipe reproducibility |
| 18 | Packet industrialization | deterministic heavy-asset packet rebuilds | packet soak, rebuild determinism, rehydration validation |
| 19 | Model portfolio science | competitive multimodal baselines and stable training envelopes | ablation wave, calibration, and stability report |
| 20 | Evaluation and user simulation | scripted scientist workflows with evidence-based utility judgments | user-sim regression matrix and acceptance matrix |
| 21 | Operator workflow productization | robust scientist-facing workflow surface | usability regression, operator parity, workflow docs |
| 22 | Reliability, security, compliance | weeklong soak, failure injection, and risk controls | soak report, security posture, DR/restore validation |
| 23 | Release engineering | reproducible install, upgrade, rollback, and packaging | RC bundle validation and cold-start install proof |
| 24 | Release candidate hardening | dogfood, bug bash, sign-off, and documentation freeze | RC regression matrix and GA sign-off checklist |
| 25 | General availability and post-release ops | tagged release, reproducibility proof, and maintenance runway | GA readiness report and clean-machine reproduction |

## Expanded Phases

### Phase 16: Corpus Completion and Evidence Ledger

Goals:

- convert the current truthful but thin corpus into a release-candidate evidence ledger
- finish high-value missing acquisition lanes for proteins, pairs, ligands, and annotations
- make unresolved evidence machine-auditable at accession, pair, packet, and cohort levels

Exit criteria:

- a release cohort registry exists with explicit inclusion and exclusion reasons
- each candidate accession has a completeness score and a failure-accounting trail
- corpus blockers are surfaced by evidence lane, not buried in narrative reports

### Phase 17: Scientific Library Enrichment and Recipe Design

Goals:

- turn the summary library into a scientific planning surface, not just a joined record set
- add knowledge-card style summaries for motifs, pathways, origins, disorder, families, and relationship traces
- support training-recipe design with constraint-aware split simulation and cohort composition logic

Exit criteria:

- recipe definitions are schema-backed and reproducible
- pair and ligand summaries can be traced back to single-entity evidence and coverage depth
- training-design outputs remain leakage-aware and auditable

### Phase 18: Packet Industrialization and Heavy Asset Management

Goals:

- harden PDB, mmCIF, AlphaFold, ligand, conformer, and evolutionary asset lanes
- enforce checksum-backed packet manifests and deterministic rebuilds
- support packet rehydration on a clean machine without hidden developer state

Exit criteria:

- packet rebuilds are deterministic from pinned manifests
- heavy asset caching obeys explicit retention policy
- partial packets are distinguished cleanly from packet-complete examples

### Phase 19: Model Portfolio and Training Science

Goals:

- move beyond a single flagship runtime into a benchmarked model portfolio
- compare complementary sequence, structure, pair, ligand, and multimodal baselines
- quantify calibration, uncertainty, ablations, failure modes, and training stability

Exit criteria:

- portfolio experiments are registered and reproducible
- calibration and uncertainty are measured, not inferred
- training envelopes are documented with stable ranges and failure conditions

### Phase 20: Evaluation Science and User Simulation

Goals:

- test the product the way a scientist would actually use it
- simulate research workflows such as candidate selection, packet build, benchmark interpretation, and evidence drilldown
- judge output usefulness, trustworthiness, and scientific plausibility on concrete scenarios

Exit criteria:

- user-sim personas and workflow scenarios are explicit and replayable
- utility and plausibility judgments are tied to evidence and artifacts
- the acceptance matrix names pass, weak, and blocked scenarios with reasons

### Phase 21: Operator Workflow Productization

Goals:

- turn the operator surface into a release-worthy workflow product
- support recipe execution, batch review, provenance drilldown, and dataset design
- preserve PowerShell parity while preparing the WinUI path for production

Exit criteria:

- workflow operations have stable operator affordances and docs
- evidence drilldown is available without opening raw JSON by hand
- usability regressions are tested against user-sim scenarios

### Phase 22: Reliability, Security, and Compliance

Goals:

- harden the unattended loop, failure handling, recovery, and operational truth signals
- validate secrets handling, license posture, data retention rules, and disaster recovery
- ensure the system fails closed under corrupted state, bad manifests, and repeated failures

Exit criteria:

- weeklong soak passes with honest alerting
- repeated failures produce visible stop conditions instead of silent looping
- restore and rollback procedures are tested end to end

### Phase 23: Release Engineering and Deployment

Goals:

- make installation, upgrade, rollback, and schema migration reproducible
- produce versioned release artifacts with manifests, checksums, notes, and tutorials
- support local-first distribution for open-source users

Exit criteria:

- clean-machine install passes
- upgrade and rollback succeed without orphaning manifests or canonical state
- release bundles are self-describing and supportable

### Phase 24: Release Candidate Hardening

Goals:

- run the project like a release candidate, not a dev repo
- execute dogfood scenarios, bug-bash workflows, and sign-off ceremonies
- freeze docs, runbooks, support guidance, and governance surfaces

Exit criteria:

- RC regression matrix passes
- release blockers are formally triaged and closed or explicitly deferred
- GA sign-off checklist is complete

### Phase 25: General Availability and Post-Release Operations

Goals:

- tag, publish, and reproduce the GA release
- publish benchmark and model cards with honest boundaries
- establish maintenance, drift detection, and next-wave roadmap review

Exit criteria:

- GA can be reproduced from a clean machine from tagged artifacts alone
- public release documentation matches the shipped behavior
- maintenance and incident-response ownership are explicit

## Global Validation Gates

### Gate A: Research and Source Truth

- every source lane has a schema, coverage, reliability, join, and storage decision
- online and local mirrors are reconciled explicitly

### Gate B: Canonical and Provenance Truth

- proteins, ligands, assays, structures, and pairs preserve ambiguity honestly
- provenance pointers and failure reasons survive materialization

### Gate C: Packet Rebuild Truth

- every selected example can be rebuilt from pinned artifacts
- checksum drift and missing heavy assets fail visibly

### Gate D: Model and Benchmark Truth

- metrics come from reproducible artifacts
- runtime identity, checkpoints, and experiment registry stay aligned

### Gate E: User Workflow Truth

- user-sim scenarios succeed on supported workflows
- weak and blocked scenarios are reported with evidence-backed reasons

### Gate F: Operational Truth

- heartbeat, failures, queue health, and restart cause are visible
- weeklong unattended runs do not masquerade as healthy when stalled

### Gate G: Release Truth

- install, upgrade, rollback, bundle validation, docs, and support surfaces are all verified from release artifacts

## Innovation Targets

- decision-grade biological knowledge cards for proteins, pairs, and ligands
- recipe-driven training-set design instead of ad hoc benchmark selection
- provenance-first evidence drilldown in the operator surface
- scenario-based user simulation for scientific workflows, not just UI clicks
- a model portfolio that treats uncertainty, calibration, and modality gaps as first-class
- deterministic heavy-asset packet rebuilds for reproducible multimodal science

## Immediate Execution Policy

1. Finish the active Phase 15 cohort-enrichment work already in flight.
2. Open Phase 16 immediately behind it so corpus completeness becomes the next hard gate.
3. Start planning artifacts and non-overlapping implementation slices for Phases 17 through 20 in parallel.
4. Keep Phases 21 through 25 in the executable queue now, even if they do not dispatch until upstream gates clear.
5. Preserve the current truth boundary: no release-grade claim until Gates A through G are satisfied.

## Success Condition

The program is complete only when the platform can be installed, mirrored, indexed, packetized, trained, benchmarked, inspected, validated by simulated users, soaked unattended, and released from tagged artifacts with conservative scientific truth preserved at every step.
