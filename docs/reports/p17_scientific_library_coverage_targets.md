# P17 Scientific Library Coverage Targets

Date: 2026-03-22
Task: `P17-A001`
Status: `completed`

## Purpose

Define the minimum evidence and packaging targets for a scientific summary library that is useful for release engineering, user-facing search, and robust training-set construction.

The targets below are intentionally split by release posture so we do not confuse a benchmark-capable library with an RC-capable or GA-capable product library.

## Current Baseline

- The frozen benchmark cohort contains `12` included accessions and `0` release-ready rows.
- The strongest current protein row is `protein:P69905`, but it is still blocked by packet incompleteness.
- The release PPI wave currently reaches `11` direct-covered accessions and leaves `1` unresolved accession.
- The release ligand wave currently reaches `1` assay-linked accession, `2` structure-linked accessions, and leaves `9` accessions in held sparse-gap status.
- The canonical store is already useful for proteins, ligands, assays, and structures, but the summary library is not yet deep enough to support release-grade recipe design by itself.

## Coverage Targets

| Entity class | Benchmark target | RC target | GA target |
| --- | --- | --- | --- |
| Protein card | sequence plus 1 pinned evidence lane | sequence plus structure or pathway plus explicit provenance | sequence plus structure plus pathway or motif plus provenance and blockers |
| Protein-protein card | one traceable pair record or explicit empty state | one curated direct pair lane plus source trace | curated direct lane plus partner trace plus split-safe lineage |
| Protein-ligand card | one assay-linked or structure-linked hint | one assay-linked ligand record with source trace | assay-linked ligand support plus bridgeable structure context and package eligibility |
| Motif/family card | accession-level motif availability note | pinned family or motif consensus with evidence notes | reusable consensus summary with conflicts and empty states preserved |
| Pathway card | pathway presence note | traceable pathway membership and source provenance | pathway summary with upstream/downstream evidence notes and release pinning |
| Training packet | partial packet accepted for prototype benchmark | packet must be materially complete for requested modalities | packet complete, pinned, reproducible, and split-policy compliant |

## Quantitative Exit Rules

### Benchmark-capable library

- at least `80%` of selected benchmark proteins must have a protein card with sequence plus one additional lane
- at least `50%` of selected benchmark proteins must have either curated PPI support or an explicit reachable-empty PPI state
- at least `25%` of selected benchmark proteins must have assay-linked or structure-linked ligand evidence
- every selected benchmark row must expose a leakage key, provenance pointers, and blocker notes

### RC-capable library

- at least `90%` of frozen RC proteins must have sequence plus structure plus one of pathway, motif, or curated interaction depth
- at least `75%` of frozen RC proteins must have curated direct PPI coverage or an explicit documented exclusion reason
- at least `60%` of frozen RC proteins must have assay-linked ligand coverage
- `100%` of frozen RC packets must be materially complete for the recipe-requested modalities
- `0` silent unresolved rows are allowed; every weak row must be blocked or excluded explicitly

### GA-capable library

- at least `95%` of GA proteins must meet the RC protein-card bar
- at least `85%` of GA proteins must have curated direct PPI coverage or documented not-applicable semantics
- at least `75%` of GA proteins must have assay-linked ligand coverage, with bridge-only evidence kept separate
- motif/family and pathway summaries must be available for at least `80%` of GA proteins where source data exists
- `100%` of GA packets must be reproducible from pinned raw and canonical manifests

## Innovation Targets

- Keep pair, ligand, motif, pathway, and structure traces as first-class sibling views of a protein, not side comments on a protein row.
- Treat reachable-empty and bridge-only states as useful scientific outputs rather than failed fetches.
- Separate direct biological evidence from bridge glue, probe-backed support, and inferred convenience joins.
- Make recipe design evidence-aware: users should be able to ask for “multilane proteins with assay-linked ligands but no mixed evidence” and get a truthful candidate pool.
- Preserve thin-coverage controls as explicit controls rather than letting them silently disappear during library enrichment.

## Immediate Build Priorities

- upgrade protein cards first, because they anchor every later pair, ligand, motif, pathway, and packet view
- land pair and ligand trace explainers so every summary record can be walked back to raw evidence
- raise ligand depth aggressively, because ligand scarcity is the largest current blocker between the benchmark cohort and an RC-capable library
- convert packet completeness from a runtime note into a hard release gate with pinned modality manifests

## Phase 17 Guidance

- `P17-T002` should encode evidence depth, blockers, and traceability directly in the entity-card schema
- `P17-T003` should treat motif consensus as optional but explicit, never silently absent
- `P17-T004` should keep pair and ligand trace explanations lossless
- `P17-T005` and `P17-T006` should use these targets as recipe and split-simulation constraints rather than post-hoc reporting
