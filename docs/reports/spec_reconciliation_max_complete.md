# Spec Reconciliation: Max-Complete Scope

## Scope Signal

The max-complete package is the authoritative full-scope handoff, not a prototype brief. It expands the current inferred plan in five important ways:

1. The platform is expected to be registry-driven and schema-driven across ML, UI, and backend selection.
2. The data layer is expected to cover proteins, protein-ligand systems, protein-protein systems, protein-nucleic-acid systems, and mixed assemblies with explicit cross-references, not just isolated baseline records.
3. The summary library must be rich enough to support robust dataset design, leakage-aware splitting, and later selective packet materialization.
4. The flagship model is explicitly multimodal, uncertainty-aware, and noise-robust.
5. Release readiness requires real end-to-end validation, provenance, leakage checks, diagnostics, and reproducibility, not only passing unit tests.

## Data-Source Coverage Requirements

Backbone sources are explicitly required:

- RCSB/PDBe for structure, assemblies, ligands, and geometry
- UniProt for canonical identity and cross-reference spine
- AlphaFold DB for predicted structure gap fill
- BindingDB for assay/ligand-target measurements
- InterPro for domains/families/motifs
- DisProt for disorder truth
- BioGRID and IntAct for interaction evidence
- EMDB for advanced cryo-EM modality
- motif search systems and local structural motif methods
- Reactome for pathway context
- evolutionary/MSA pipelines for conservation and coupling

The source matrix also makes clear that the platform must support protein-ligand and protein-protein combinations as first-class data products, then cross-reference those back to reusable single-protein identity and annotation records.

## Summary-Library Expectations

The data/feature spec implies a richer summary library than the current queue states explicitly.

Required content classes:

- canonical protein / ligand / pair identity
- structure quality and completeness
- assay layer with confidence and provenance
- motif, domain, disorder, pathway, and evolutionary annotations
- protein-ligand pocket and contact summaries
- protein-protein interface and evidence summaries
- uncertainty / quality / conflict burden fields
- missingness masks and confidence-aware aggregation rules

The summary library is not just a cache. It is a planning and dataset-design surface that must support:

- robust filtering and split governance
- family/motif/pathway/evolution-aware grouping
- retrieval of source ancestry
- later selective packet materialization for chosen examples

## UI Requirements

The spec requires a schema-driven, dependency-aware UI. A flat form or hand-coded per-model control surface is explicitly out of contract.

Minimum UI behavior required by the spec:

- sections for acquisition, canonicalization, features, splits, models, training, evaluation, export, and lineage/logging
- visibility tiers: Basic, Advanced, Expert
- dynamic dependency rules for impossible or incompatible settings
- versioned config saving
- experiment config cloning and diffing

Pragmatic implication:

- a PowerShell or CLI operator surface is acceptable as an interim execution tool
- it does not satisfy the full UI requirement by itself
- the actual GUI must eventually bind to registries and parameter schemas

## ML / Runtime / Noise-Robustness Requirements

The ML spec is broader than the current queue.

Required architectural capabilities:

- baseline models plus honest baseline comparisons
- tree, dense, CNN, sequence, graph, generative, uncertainty, hybrid, and ensemble families
- backend abstraction for PyTorch primary, TensorFlow/sklearn-compatible support, and future JAX extension
- registry-backed parameter schemas instead of scattered literals
- multimodal flagship architecture with separate encoders for structure, sequence/evolution, ligand, and biology/pathway/evidence
- fusion modes including concatenation baseline, gated fusion, cross-modal attention, mixture-of-experts, and residual late fusion
- uncertainty support: variance heads, ensembles, MC dropout, calibration
- noise-robust training: curriculum, quality-weighted sampling, multitask, ablation tracking, missing-modality handling

This package is explicit that the flagship model should be able to down-weight missing or low-confidence modalities rather than assuming all sources are equally reliable.

## Real-Data Validation Expectations

The validation contract is materially stricter than the current bootstrap baseline.

Required validation classes:

- unit tests for connectors, normalization, features, models, training, execution
- integration tests for source -> canonical -> features -> dataset -> split -> train -> eval
- lineage query validation for raw-source ancestry
- system tests for dry runs, failure injection with resume, schema invalidation behavior, and reproducibility
- leakage checks for sequence clusters, ligand/pocket duplicates, and complex/assay duplication across splits
- diagnostics: feature missingness, source coverage, conflict burden, split leakage, calibration

The current max-complete spec expects real pipeline behavior and recovery behavior, not only simulations.

## Release-Readiness Criteria

The implementation contract defines release-level completeness as:

- connectors produce versioned raw artifacts
- canonicalization produces valid typed objects with provenance
- feature extraction emits declared schema plus masks/confidence
- at least one baseline and one flagship multimodal model train end-to-end
- leakage-safe evaluation runs
- DAG execution resumes from checkpoint after simulated failure
- GUI/API load schemas dynamically

The appendices also state that a first release may defer modules, but every deferral must be explicit with reason, dependency, milestone, and impact. Omission without architectural placement is out of spec.

## Contradictions / Gaps Versus Current Queue

The current queue is directionally correct, but it is still below the max-complete scope in several concrete ways.

1. Connector breadth is incomplete.
   The queue currently has stronger emphasis on RCSB, UniProt, BindingDB, and source-analysis reports than on implementing the rest of the required connector/module map:
   AlphaFold, InterPro, DisProt, BioGRID, IntAct, EMDB, motif, Reactome, evolution.

2. The feature ontology is underrepresented.
   Current tasks cover baseline sequence/assay/PPI features and later multimodal tasks, but not the full atom/residue/interface/ligand/biology/quality ontology required by the spec.

3. Registry-driven ML/UI architecture is mostly absent.
   The queue currently does not yet include explicit tasks for model family registry, optimizer/scheduler/loss registries, parameter-schema registry files, or schema-bound dynamic GUI loading.

4. UI scope is too thin.
   The queue includes a PowerShell operator interface and a low-priority WinUI scaffold, but the spec requires a schema-driven GUI with dynamic dependencies and visibility tiers.

5. Validation is still lighter than contract.
   Current work has strong unit scaffolding and some integration planning, but the max-complete contract requires stronger system tests, lineage queries, leakage checks, calibration diagnostics, and reproducibility verification.

6. Release-readiness reporting is not yet aligned to full contract.
   The queue has readiness reporting tasks, but it does not yet explicitly enforce the complete max-complete definition of done or deferral accounting.

7. Implementation order needs tightening.
   The appendix says not to reverse the backbone order by racing ahead to flashy modeling before provenance, canonicalization, mapping, and feature/schema integrity are sound. The current queue is aware of this in spirit, but it should be reprioritized more aggressively around provenance, conflict resolution, complete connector coverage, and feature ontology before deeper model breadth.

## Recommended Queue Adjustments

Immediate additions or reprioritizations:

- raise registry and schema tasks from optional/nice-to-have to core
- add explicit connector implementation tasks for AlphaFold, InterPro, DisProt, BioGRID, IntAct, EMDB, motif, Reactome, and evolution
- add summary-library tasks that include motif/pathway/evolution and pair-to-protein cross-reference guarantees
- add explicit lineage query, leakage diagnostics, calibration, and reproducibility tasks
- add true GUI schema-binding tasks instead of only operator-shell tasks
- keep real-data acquisition and packet-materialization validation as required release work, not stretch goals

Bottom line:

The current queue is a reasonable bootstrap for the backbone, but it does not yet satisfy the max-complete scope. The main missing pieces are full connector breadth, full feature ontology coverage, registry-driven ML/UI architecture, and release-grade real-data/system validation.
