# Local Source Reuse Strategy

Date: 2026-03-22  
Inputs used: [bio_agent_lab_source_inventory.md](/D:/documents/ProteoSphereV2/docs/reports/bio_agent_lab_source_inventory.md), [source_coverage_depth_next_tasks.md](/D:/documents/ProteoSphereV2/docs/reports/source_coverage_depth_next_tasks.md), [p10_i014_source_coverage_integration_prep.md](/D:/documents/ProteoSphereV2/docs/reports/p10_i014_source_coverage_integration_prep.md), [release_grade_gap_analysis_p10_refresh.md](/D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis_p10_refresh.md)

## Bottom Line

Reuse should be organized around one rule: preload small control artifacts, index reusable corpora, and lazy-import large or accession-specific payloads. The local workspace is already strong enough to support protein, protein-protein, protein-ligand, pathway, annotation, and derived-training reuse, but it is still thin on some interaction and motif sources. The strategy below keeps duplicates deduped, complements explicit, and missing lanes visible.

## What To Preload

Preload only small, high-signal artifacts that drive discovery, validation, or operator/reporting state.

### Local

- Source manifests, source-state JSON, and release summaries.
- Cohort and benchmark control files, including split diagnostics and coverage inventories.
- Operator/library materialization state and checkpoint summaries.
- Thin-lane notes and evidence maps that explain what is missing rather than inflating coverage.

### Online

- Small source metadata endpoints or release manifests only, not bulk payloads.
- Per-source identity and release headers for:
  - UniProt
  - RCSB / PDBe
  - AlphaFold DB
  - IntAct
  - BindingDB
  - Reactome
  - InterPro / Pfam

These are preload-worthy only when they help seed identity, versioning, or source capability checks. Bulk records should still be indexed or lazy-imported.

## What To Index

Index the sources that are reused across many tasks and can safely act as canonical join anchors.

| Source family | Index role | Reuse note |
| --- | --- | --- |
| UniProt | Protein identity anchor | Primary accession namespace for protein joins. |
| RCSB / PDBe | Structure and residue/entity context | Best for protein-structure lanes and cross-reference enrichment. |
| AlphaFold DB | Predicted structure lane | Use as a structural complement, not a substitute for experimental structure. |
| IntAct / BioGRID | Protein-protein interaction index | Canonical pair evidence when direct interaction data exists. |
| BindingDB / ChEMBL | Protein-ligand evidence index | Ligand joins should prefer assay-backed identifiers and target accessions. |
| Reactome | Pathway lane index | Best paired with UniProt accession joins. |
| InterPro / Pfam | Domain / motif lane index | Use to enrich identity-only proteins without widening the claim class. |
| PDBbind / BioLiP | Curated complex and pair corpora | Good complements for structure-aware pair and ligand reuse. |
| Graph / training artifacts | Derived reuse layer | Index once, then load selectively by dataset or run id. |

## What To Lazy-Import

Lazy import anything that is large, per-accession, or easy to overclaim if loaded wholesale.

### Local

- Raw RCSB JSON and mmCIF trees selected by accession.
- Per-accession extracted payloads under `data/extracted/{assays,bound_objects,chains,entry,interfaces,provenance}`.
- Large bulk archives such as AlphaFold, BindingDB, and ChEMBL snapshots.
- Run outputs and custom training artifacts that are only needed for a specific validation or audit.

### Online

- Full source payloads for accessions that are not already pinned locally.
- Direct live-smoke fetches for missing lanes only.
- Missing interaction corpora that are not staged locally, including BioGRID and IntAct when they are used as gap-fillers rather than primary indexed corpora.
- Missing motif / assay corpora when the current question only needs one accession or one pair.

The rule is simple: if a source is big, sparse, or accession-specific, do not preload it. Fetch it on demand and cache the result as a local snapshot.

## Duplicates, Complements, And Missing Lanes

- Deduplicate by canonical accession or source record id, but preserve provenance pointers from every contributing source.
- Treat duplicate evidence as complementary only when it adds a new lane type; do not count the same lane twice just because it came from two sources.
- Use complements to deepen a row:
  - sequence plus structure,
  - interaction plus pathway,
  - ligand plus assay,
  - domain plus functional annotation.
- Leave missing lanes explicit. A row that only has identity evidence should stay thin until a real additional lane exists.

## Join Strategies By Entity Type

### Protein

Join proteins by UniProt accession first. Use RCSB/PDBe, AlphaFold, Reactome, and InterPro/Pfam as complementary lanes keyed back to that accession. If local and online sources disagree, keep the accession stable and record the mismatch in provenance rather than widening the row.

Example: `P69905`

- preload UniProt identity and release metadata,
- index AlphaFold DB, RCSB/PDBe, InterPro, Reactome, and MSA support,
- lazy-import raw structure files only when a structural review needs them.

### Protein-Protein

Join pairs by the sorted accession pair plus a stable source interaction id when available. Prefer direct PPI corpora over summary probes, and keep probe-backed rows explicitly marked as mixed until direct evidence replaces them.

Example: `P68871` with its hemoglobin partner

- index IntAct / BioGRID as the canonical direct pair lane,
- keep the current summary-library probe as a temporary complement, not a release-grade substitute,
- preserve the pair as a mixed row until direct interaction evidence is present.

### Protein-Ligand

Join by protein accession plus ligand identity, preferring InChIKey, then canonical ligand id, then source-specific ligand id. SMILES is useful for matching, but it should remain a fallback when no stronger ligand identifier exists.

Example: `P31749`

- preload BindingDB metadata and target identity,
- index BindingDB and ChEMBL for assay-backed reuse,
- lazy-import PDBbind or BioLiP only when a structure-backed ligand lane is needed.

## Missing-Lane Policy

The current inventory shows the main gaps clearly:

- interaction corpora such as STRING, BioGRID, and staged IntAct are still missing locally,
- motif/assay corpora such as SABIO-RK, PROSITE, ELM, MegaMotifBase, and Motivated Proteins are also missing locally.

Those gaps should stay visible as lazy-import or online-only candidates, not be hidden by fallback joins.

## Release-Oriented Interpretation

This strategy is conservative on purpose:

- preload the small control surface,
- index the reusable corpora,
- lazy-import the large or missing lanes,
- and keep every deduplicated join tied to its real provenance.

That is the safest reuse model for the current benchmark and release work: broad enough to support PPI, protein, and protein-ligand reuse, but strict enough to avoid silently widening claims.
