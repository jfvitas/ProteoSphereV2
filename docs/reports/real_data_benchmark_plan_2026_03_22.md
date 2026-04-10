# Real Data Benchmark Plan

Date: 2026-03-22
Task: `P6-I007`

## Purpose

Prepare the benchmark/evaluation package so execution can start immediately once the flagship pipeline is ready. This plan stays conservative: it assumes the landed canonical pipeline, provenance threading, checkpoint/retry, and ingest slices are the evaluation substrate, and it does not invent new architecture.

## What Is Already Proven Live

The plan is grounded in real smoke evidence already landed in the repo:

- UniProt live anchor retrieval works for `P69905`.
- InterPro live protein annotation retrieval works for `P69905` and returned `6` protein-linked entries, including `IPR000971` `Globin`.
- Reactome live pathway mapping works for `P69905` through the UniProt mapping endpoint and returned `6` pathway rows.
- BindingDB live protein-ligand acquisition works for `P31749` after parser normalization and returns a non-empty live record set.

One useful negative boundary is also known:

- A guessed Reactome direct query path returned `404`.
- The benchmark should use the UniProt mapping endpoint, not assume the query surface.

## What Still Needs First Real-Corpus Validation

These items are not yet proven on a real benchmark corpus:

- Multi-protein cohort packaging at corpus scale.
- Train/val/test split hygiene over accession-level bundles.
- Aggregated benchmark statistics across mixed rich, moderate, and sparse proteins.
- Week-long unattended execution with checkpoint resume across repeated runs.
- Explicit handling of real-corpus gaps where one source is missing while others are present.

## Candidate Corpora

Use one master accession spine and attach source-specific layers around it.

### Core benchmark spine

Human UniProt accessions with stable canonical identifiers.

Preferred seed accessions for the first wave:

- `P69905` for a strongly annotated hemoglobin example.
- `P04637` for a high-visibility cancer/regulatory example.
- `P31749` if the ligand-positive lane is included in the same benchmark package.

### Enrichment layers

- InterPro protein annotation corpus.
- Reactome pathway mapping corpus via UniProt accession.
- Optional BindingDB protein-ligand corpus for the ligand-positive extension lane.

### Control cohort

Add a sparse or negative-control slice of proteins that legitimately have fewer annotations or missing pathway coverage. The goal is not to force every source to resolve, but to verify that missingness remains explicit and does not collapse into silent success.

## Minimum Viable Benchmark Cohort

Start small and make the bundle reproducible.

- `12` total proteins is the minimum sensible cohort for the first real-corpus pass.
- Suggested composition:
  - `4` rich-coverage proteins with InterPro + Reactome coverage.
  - `4` moderate-coverage proteins with at least one missing layer.
  - `4` sparse or negative controls.
- At least one accession in the cohort should be `P69905`.
- If the ligand lane is enabled, include `P31749` so the summary library can exercise a real protein-ligand example without widening the cohort.

## Packaging Approach

Package by protein accession, not by row.

- Keep one immutable manifest per accession bundle.
- Preserve source-native IDs, raw source provenance, and source release pins in the package.
- Keep all records for a single accession together across source layers.
- Assign train/val/test split labels at the accession level only.
- Never split a multi-row source bundle across partitions.
- Preserve explicit unresolved and conflicting cases as first-class records or sidecars.

### Suggested split strategy

- Use an accession-level stratified split.
- Keep proteins grouped by coverage richness so each split contains representative examples.
- A practical first split for the `12`-protein MVP is `8` train / `2` val / `2` test.
- For a later expanded corpus, move toward a `70/15/15` or `80/10/10` accession split while keeping the same no-leakage rule.

## Statistics To Report

Report both coverage and provenance quality.

### Coverage and yield

- Number of planned accessions.
- Number of accessions resolved by UniProt.
- Number of proteins with InterPro annotations.
- Number of proteins with Reactome pathway mappings.
- Number of proteins with BindingDB ligand evidence, if that lane is included.
- Mean, median, and p90 annotation count per protein by source.

### Provenance and lineage

- Fraction of retained records with complete provenance.
- Fraction of records preserving the UniProt accession spine.
- Number of unresolved records surfaced explicitly.
- Number of conflicts surfaced explicitly.
- Number of partially mapped records.

### Split hygiene

- Train/val/test counts by accession.
- Split balance by richness bucket.
- Leakage count across splits.

### Run health

- Checkpoint writes and resumes.
- Retry counts by source.
- Wall-clock runtime.
- Per-source failure counts and error classes.

## Failure Criteria

Treat the run as failed if any of the following happen:

- A resolved record loses provenance or source-native identity.
- An unresolved or conflicting case is silently collapsed into a clean success.
- The same accession appears in more than one split.
- The benchmark bundle drops source bundles without recording why.
- A source endpoint change, schema drift, or retry exhaustion is not surfaced as a blocker.
- The canonical accession spine cannot be preserved across the bundle.

For the first real-corpus pass, treat source-layer missingness as acceptable only when it is explicit and counted. Missingness is not a failure; silent missingness is.

## Week-Long Unattended Run Considerations

The benchmark should be able to run unattended for a week without mutating the cohort.

- Pin the cohort manifest and source release metadata up front.
- Keep retries bounded and recorded.
- Write checkpoints after each accession bundle and after each source layer.
- Preserve raw responses long enough for replay and postmortem.
- Compare daily counts and hashes against the pinned manifest.
- If a source becomes unavailable or changes shape, stop widening the cohort and mark the run blocked.
- Prefer deterministic reruns over adaptive recovery that changes the benchmark population.

## Execution Gate

This benchmark plan is ready to execute as soon as the flagship pipeline is available. The first run should validate:

1. accession-level packaging,
2. provenance preservation,
3. explicit unresolved/conflict surfacing,
4. split hygiene, and
5. unattended checkpointed stability.

If the first corpus run exposes source gaps, keep them visible and treat the result as a benchmark input issue, not as a reason to weaken the contract.
