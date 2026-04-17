# Supplementary Appendix

Companion to *ProteoSphere: A Compact Evidence Warehouse and Dataset Reviewer for Biomolecular Interaction Machine Learning*.

## S1. Scope and claim boundaries

ProteoSphere is operationally effective for warehouse-first review of biomolecular interaction ML benchmarks. It is not yet a full evidence-equivalent replacement for every raw source surface, and this manuscript reports a proof-backed sample of recurring failure modes rather than a field-wide prevalence estimate. The Tier 1 proof set is concentrated in protein–ligand / DTA and PDBbind-style benchmark families, with a smaller protein–protein subset. Flagship cases are reported in four distinct categories — paper-specific split bugs, inherited benchmark-family failures, invalid external validation, and paper-specific protocol failures (random-CV leakage) — and should not be flattened into a single "leakage" claim.

## S2. Warehouse release and validation

- **Snapshot.** `full-local-backbone-2026-04-10`.
- **Root (current build).** `D:\ProteoSphere\reference_library` (environment-specific; release packaging is path-independent).
- **Default view.** `best_evidence`.
- **Runtime validation.** `status: passed` across all thirteen record families in the current build; `claim_surface_materialized: false` for all thirteen, which is the expected state for the summary-contract projection and is consistent with the manuscript's explicit limitation that deeper roster reconstruction sometimes requires the raw estate.
- **Governed sources.** The warehouse manifest's public-export policy names five publicly redistributable sources — UniProt, RCSB/PDBe, AlphaFold, IntAct, ELM. All other warehouse sources (BindingDB, PDBbind, STRING, UniParc, SABIO-RK, MEGA Motif Base, Motivated Proteins) are held `internal_only` and excluded from public bundles.

## S3. Audit contracts

**Canonical split policies.** `paper_faithful_external`, `accession_grouped`, `uniref_grouped`, `protein_ligand_component_grouped`, `unresolved_policy`, plus paper-specific variants flagged explicitly.

**Reason-code catalog.** DIRECT_OVERLAP, ACCESSION_ROOT_OVERLAP, UNIREF_CLUSTER_OVERLAP, SHARED_PARTNER_LEAKAGE, INSUFFICIENT_PROVENANCE, INCOMPLETE_MODALITY_COVERAGE, CANDIDATE_ONLY_NON_GOVERNING, AUDIT_ONLY_EVIDENCE, UNRESOLVED_ENTITY_MAPPING, UNRESOLVED_SPLIT_MEMBERSHIP, POLICY_MISMATCH, WAREHOUSE_COVERAGE_GAP.

**Verdict classes.** `usable`, `usable_with_caveats`, `audit_only`, `blocked_pending_mapping`, `blocked_pending_cleanup`, `unsafe_for_training`.

**Human-review gate.** Escalation is triggered only by genuine ambiguity — conflicting `best_evidence` claims, missing split-generating code, unverifiable external-panel assertions. Deterministic failures resolve to their verdict without escalation.

## S4. Storage framing

The tracked source estate in the current build records 53 sources with 324,755,949,775 present bytes (≈302 GiB, or 324.8 decimal GB). The manuscript build's live storage ledger measures the active warehouse root at 74.2 GB, `data/raw` at 1.6 TB, and the incoming-mirror path at 1.5 TB. These are environment measurements, not release-bound package sizes. The draft does not claim a specific condensation ratio (the "≈2 TB → ≈25 GB" phrase is explicitly avoided) because no dedicated release-bound proof artifact yet certifies that exact number.

## S5. Tier 1 proof set

{{TIER1_TABLE}}

*(Auto-populated at manuscript build from `literature_hunt_tier1_master_summary.json`. Columns: paper, year, domain, issue family, verdict, proof artifact.)*

## S6. Flagship case numerics

Reproduced verbatim from the underlying audit artifacts.

### S6.1 Struct2Graph (Baranwal *et al.*, 2022)
- Reproduced interaction rows: 10,004 (8,003 train / 1,000 test, released `create_examples.py`, seed 1337).
- Shared PDB IDs across partition: 643.
- Highlight structure 4EQ6: 78 train occurrences, 9 test occurrences.
- Proof: `struct2graph_reproduced_overlap.md`, `4EQ6_train_test_overlay.png`.

### S6.2 Silva *et al.* 2023 (RSC D2CP05644E)
- Benchmark pool: 78 retained structures (81 rows; notebook drops indices 12, 14, 28 corresponding to PDB IDs 1DE4, 1E4K, 1GXD).
- PDBbind panel (50): 4 direct-protein / 4 exact-sequence / 4 UniRef100 / 110 shared-partner; overlapping accessions P00698, P01112, P61769, P68135; verdict `blocked_pending_cleanup`.
- Nanobody panel (47): 1 / 1 / 1 / 16 on lysozyme C (P00698); verdict `blocked_pending_cleanup`.
- Metadynamics panel (19): 26 direct-protein / 26 exact-sequence / 26 UniRef100 / 75 shared-partner overlap relations against the joint 97-structure benchmark+panel audit set; verdict `blocked_pending_cleanup`.
- Proof: `paper_d2cp05644e_quality_assessment.md`.

### S6.3 DeepDTA setting-1 family
- Davis: 68 test drugs, 442 test targets — all shared with training.
- KIBA: 2,027 test drugs, 229 test targets — all shared with training.
- Downstream inheritors in Tier 1: 14 papers.
- Proof: `dta_setting1_family_audit.json`.

### S6.4 PDBbind core-set family
- v2016 core: 288 of 290 test complexes carry direct protein overlap with the remaining pool; 77 shared accessions.
- v2013 core: 108 of 108 test complexes carry direct protein overlap; 50 shared accessions.
- Downstream inheritors in Tier 1: 12 papers.
- Proof: `pdbbind_core_family_audit.json`.

### S6.5 AttentionDTA (Zhao *et al.*, 2023)
- Davis: 68 shared drugs, 367 shared targets across random-CV folds.
- KIBA: 2,054 shared drugs, 229 shared targets.
- Metz: 1,206 of 1,214 test-unique drugs shared (99.3%), and all 169 test-unique targets shared.
- Proof: `attentiondta_random_cv_family_audit.json`.

## S7. Controls passing or downgrading cleanly

RAPPPID, GraphPPIS, BatchDTA, HGRL-DTA, NHGNN-DTA, PotentialNet, Deep Fusion Inference, DTA-OM, TEFDTA, DCGAN-DTA, HAC-Net. Each presents a mitigation-aware split (UniRef-grouped, cold-target, or time-split) or restricts its claim scope to what its evaluation supports.

## S8. Figure provenance

All figures in the main manuscript are generated locally from machine-readable artifacts at manuscript-build time. No copyrighted publisher figures are reproduced. The only direct structural rendering used in the flagship panel is the ProteoSphere-generated Struct2Graph train/test overlay, drawn from `struct2graph_overlap/4EQ6_train_test_overlay.png`; the version embedded in the flagship panel is regenerated without the rendering-tool watermark that appeared in the prior asset.

## S9. Reproducibility checklist

- Warehouse manifest and runtime-validation snapshot: released.
- Source registry (release stamps): released.
- Tier 1 proof bundle (29 PDFs + 119 supplemental items): released.
- Flagship proof artifacts (five audits, JSON + Markdown): released.
- Claim ledger: released.
- Figure manifest and figure-generation script: released.
- Governed exclusions: STRING (`internal_only`), PDBbind payloads (`restricted`).
