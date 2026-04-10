# Lightweight Reference Library Master Plan

Date: 2026-04-01
Scope: architecture and execution plan for the ProteoSphere lightweight reference library and leakage-safe training-set creator

## Executive Summary

Yes, this makes sense.

The clean way to do this is to separate the system into three layers:

1. `Pinned source mirrors and local mirrors`
   This is the truth-preserving evidence layer. It contains the downloaded online sources, the imported `bio-agent-lab` corpora, and any later supplemental scrape captures.
2. `Lightweight reference library`
   This is the compact, downloadable planning and governance layer. It does not try to hold every raw payload. It holds enough identity, class, lineage, relationship, and provenance information to support balanced cohort design, leakage prevention, gap analysis, and packet planning.
3. `On-demand training-example materialization`
   This is the heavy lane. It uses the lightweight library to decide what to build, then hydrates only the selected examples with coordinates, graphs, residue features, ligand features, PyRosetta-derived outputs, and any other user-selected heavy artifacts.

That gives us the right split:

- the source mirrors stay rich and auditable
- the library stays compact enough to ship with GitHub releases
- the training-set creator can still make strong biological decisions without opening the giant upstream corpora every time

## Current Ground Truth

As of this plan:

- Broad online mirror is still in progress, but the remaining broad gap is now concentrated in `STRING` and `UniProt / UniRef / ID Mapping`.
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json) currently reports `53` tracked sources, with `48 present`, `2 partial`, and `3 missing`.
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) is `ready` with:
  - `11` proteins
  - `4124` ligands
  - `5138` assays
  - `0` unresolved assay cases
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json) is still only a first-slice protein library with `11` records.
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) still shows the protected packet baseline at:
  - `12` packets
  - `7` complete
  - `5` partial
  - remaining gaps:
    - `ligand:P00387`
    - `ligand:P09105`
    - `ligand:Q2TAC2`
    - `ligand:Q9NZD4`
    - `ligand:Q9UCM0`
    - `ppi:Q9UCM0`
    - `structure:Q9UCM0`

That means the current system is already good enough to build the governance layer now. We do not need to wait for every heavy source to finish before defining and implementing the lightweight library architecture.

## Product Goal

The lightweight reference library must answer five questions quickly and truthfully:

1. `What is this biological object?`
   Protein, variant, construct, ligand, pair, structure, pathway context, motif context, taxonomic context, provenance.
2. `What else is biologically close to it?`
   Same protein, same family, same orthogroup, same fold, same ligand class, same binding-site signature, same interaction neighborhood, same pathway role, same mutation neighborhood.
3. `What evidence do we have, and from where?`
   Source-native IDs, release IDs, record IDs, joins, conflicts, and missing lanes.
4. `Can I safely include this in a training set?`
   Coverage status, packet feasibility, leakage-group membership, and balance contributions.
5. `How do I build the full example if I select it?`
   Which raw assets already exist, which heavy assets must be fetched, and which transforms must run.

## Design Principles

- `Protein-first spine`
  Every protein-bearing object normalizes to a UniProt accession spine first.
- `Source-native truth before consensus`
  Consensus is allowed only after normalization and claim-class checks. Real disagreement stays visible.
- `Compact planning, lazy heavy payloads`
  The lightweight library stores routing and governance data, not raw coordinate or full assay dumps.
- `Similarity is multi-axis, not one number`
  Biological closeness must be broken into identity, sequence, fold, binding, motif, pathway, taxon, and provenance axes.
- `Leakage prevention must be first-class`
  The same features used for summarization must also create leakage groups and split guards.
- `Every conclusion must remain reconstructible`
  Every summary value must point back to pinned source evidence.
- `Scraping is supplemental only`
  Structured source exports remain primary. Scraped content fills narrow high-value holes and must stay provenance-tagged.

## What The Library Must Contain

The library should not just be a flat protein table. It needs several compact record families.

### 1. Protein Core

Canonical key:
- `protein:{uniprot_accession}`

Required content:
- accession
- reviewed status
- organism and taxon lineage
- sequence length and sequence version
- sequence checksum
- gene names and aliases
- proteome membership
- orthogroup or cluster identifiers when available
- class assignments:
  - InterPro architecture
  - PROSITE / ELM / motif family presence
  - pathway family membership
  - structural family membership when known

### 2. Protein Variant / Construct Layer

Canonical key:
- `protein_variant:{accession}:{variant_signature}`

Purpose:
- connect wild-type, engineered constructs, isoforms, truncations, and point mutants without collapsing them into one record

Required content:
- parent protein accession
- mutation list
- sequence delta signature
- construct type
- unresolved or partial mapping flag
- relation to active site or interface if known

### 3. Structure Unit Layer

Canonical key:
- `structure_unit:{source}:{structure_id}:{entity_id}:{chain_id}:{assembly_id}`

Purpose:
- distinguish experimental and predicted structures
- preserve chain, assembly, and residue-span specificity
- track multiple PDB IDs involving the same protein or near-variants

Required content:
- protein accession or variant ref
- experimental vs predicted flag
- PDB or model ID
- chain/entity/assembly IDs
- mapped residue span
- quality/confidence summaries
- bound partners and ligands
- structure family or fold class

### 4. Ligand Entity Layer

Canonical key:
- `ligand:{namespace}:{identifier}`

Required content:
- standardized chemical identity
- InChIKey and canonicalized structure strings when available
- ChEBI class lineage
- scaffold or chemotype grouping
- cofactor / drug-like / metabolite / inhibitor / peptide-like class flags
- provenance to BindingDB, ChEMBL, BioLiP, PDBbind, CCD, or local extracts

### 5. Interaction / Pair Layer

Canonical key:
- `pair:{interaction_kind}:{participant_a}|{participant_b}|{context_signature}`

Required content:
- protein refs
- interaction type
- curated vs inferred evidence flags
- native source IDs
- binary vs complex-projection lineage
- interaction confidence bins
- interface-aware flags when structural support exists

### 6. Motif / Domain / Site Layer

Canonical key:
- `annotation:{system}:{protein_or_variant_ref}:{span_signature}`

Required content:
- annotation system
- accession
- stable residue span
- integrated vs supporting status
- active-site / catalytic-site / cofactor-binding-site / interface-site flags where possible

### 7. Pathway / Function Context Layer

Canonical key:
- `pathway_context:{reactome_stable_id}:{species}:{protein_ref}`

Required content:
- pathway and reaction lineage
- pathway ancestry
- catalyst/regulator/participant role
- compartment if available

### 8. Provenance / Snapshot Layer

Canonical key:
- `provenance:{source}:{release_or_snapshot}:{record_id}`

Required content:
- exact source
- release or snapshot ID
- retrieval timestamp
- parser version
- transformation path
- checksum or artifact pointer

## The Key New Idea: Similarity Signatures

To make the training-set creator truly leakage-safe and biologically aware, the library needs more than raw references. It needs precomputed compact similarity signatures.

These should be dense, integer-coded, and queryable.

### Protein Similarity Signature

Fields:
- canonical accession
- variant family ID
- UniRef or sequence-cluster ID
- domain architecture hash
- motif presence bitset
- pathway role signature
- taxon lineage hash

### Structure Similarity Signature

Fields:
- fold/class family ID
- chain-to-accession mapping
- assembly type
- binding-site residue fingerprint
- interface residue fingerprint
- ligand occupancy class
- experimental/predicted flag

### Ligand Similarity Signature

Fields:
- normalized ligand identity
- ChEBI class path
- scaffold hash
- cofactor/drug/metabolite bucket
- physicochemical bins
- binding-context signature

### Interaction Similarity Signature

Fields:
- pair identity
- complex lineage
- partner-class signature
- evidence-class signature
- interface signature if known

### Leakage Group Signature

This is the most important operational output. Each candidate should have multiple leakage groups:

- `exact_entity_group`
  Same accession or exact pair/ligand entity.
- `variant_family_group`
  Wild-type and close mutants / constructs of the same protein.
- `sequence_family_group`
  Same UniRef cluster or near-sequence cluster.
- `structure_family_group`
  Same fold and same mapped site pattern.
- `binding_context_group`
  Same receptor family plus same ligand class plus same binding-site signature.
- `interaction_context_group`
  Same pair family or same complex lineage.
- `pathway_context_group`
  Same pathway role cluster.

Different split modes can then choose which leakage scopes to respect.

## How We Decide Whether Two PDB IDs Are Similar

This is a core requirement, and the library should explicitly support it.

We should compare PDB-like examples on these axes:

1. `Protein identity`
   Same accession, isoform, or close variant?
2. `Sequence family`
   Same cluster, same architecture, same motif set?
3. `Mutation relationship`
   Same parent protein with one or more substitutions, truncations, or engineered changes?
4. `Binding-site similarity`
   Same active-site motif and same residue environment?
5. `Ligand-class similarity`
   Same ChEBI class or scaffold family even if not the same exact ligand?
6. `Structure similarity`
   Same fold/class, same assembly type, same domain arrangement?
7. `Interaction context`
   Same binding partner family or same complex lineage?
8. `Pathway/biological role`
   Same catalytic role, receptor role, or pathway context?
9. `Taxonomic / evolutionary closeness`
   Same species, paralog family, orthogroup, or ancestor branch?

That gives us a principled way to say:

- `same exact training object`
- `dangerously close for splitting`
- `related but acceptable if grouped`
- `sufficiently distinct`

## Concrete Current Examples

### Example A: `P00387`

Already visible in the current library:
- protein summary exists
- PROSITE motif `PS51384` is attached
- multiple InterPro domains are attached
- local ChEMBL rescue work already found real ligand rows

How it should be represented in the future library:
- protein core card
- motif/domain architecture signature
- ligand-context group from local ChEMBL rows
- fold/class assignment when structure support is present
- leakage groups preventing near-identical ligand-context leakage

### Example B: `P04637`

Current system already shows:
- strong protein identity through UniProt
- pathway depth through Reactome
- curated interaction evidence through IntAct-related summaries

How it should be used:
- good example of a protein with rich single-entity, pathway, and curated interaction context
- useful for validating that the library can distinguish direct curated interaction evidence from broader network context

### Example C: `P02042`, `P02100`, `P09105`

These illustrate why exact-accession-only splitting is not enough.

They are biologically close hemoglobin-family proteins:
- closely related sequences
- overlapping fold and oxygen-binding biology
- potentially similar structural and ligand contexts

The library should therefore:
- keep them as distinct proteins
- also place them in shared sequence/family and likely structure-family groups
- optionally block them from being split across train/test when the selected leakage scope is family-level rather than exact-accession-only

### Example D: `Q9NZD4`

The current repo already has a truth-safe fresh-run bridge-ligand improvement for `Q9NZD4`, but it was intentionally not promoted to the protected latest packet baseline.

That is exactly the right pattern for the future library:
- preserve the fresh evidence
- keep the promotion boundary explicit
- let the training-set creator use `current_fresh_evidence`, `protected_latest_evidence`, or `strict_release_evidence` according to user settings

### Example E: `Q9UCM0`

This is the clearest gap exemplar right now:
- missing ligand
- missing PPI
- missing structure

It should remain in the library with explicit missingness rather than being hidden.

That is useful because:
- it exposes where the library is thin
- it reveals bias in any candidate cohort that relies too heavily on complete rows
- it helps the training-set creator quantify whether exclusions are reducing diversity or just improving convenience

## Consensus And Conflict Policy

The library should not flatten source disagreement into a single fake value.

Use the existing trust policy and extend it into the lightweight library with three output shapes:

1. `canonical_consensus`
   Safe to collapse after normalization.
2. `primary_plus_alternates`
   One value wins, but retained alternates still matter.
3. `unresolved_multi_claim`
   Multiple values remain visible because the disagreement is biologically or semantically real.

The source precedence should stay claim-class specific:

- identity: `UniProt`, `ChEBI`, `RCSB/PDBe`, `Reactome`, `InterPro`
- structure: `RCSB/PDBe` over predicted-only sources
- pathway: `Reactome`
- motifs/domains: `InterPro`, `PROSITE`, `ELM`
- curated PPIs: `IntAct`, `BioGRID`
- ligand assay values: `BindingDB`, `ChEMBL`
- context-only layers should never override direct evidence: `STRING`, `AlphaFold DB`, some extracted summaries, future scrape captures

## Lightweight Storage Format

The library should ship as a compact binary bundle, not a giant JSON tree.

Recommended default distribution format:

1. `SQLite` as the primary shipped artifact
   File example:
   - `proteosphere-lite.sqlite.zst`

2. `Zstandard-compressed release bundles`
   Users download a compressed SQLite artifact and the tool unpacks it locally on first use.

3. `Dictionary-coded narrow tables`
   Repeated strings such as source names, ontology accessions, taxa, motif systems, and pathway IDs should be stored through integer dictionaries.

4. `Bitsets / packed arrays for signatures`
   Motif presence, pathway buckets, ligand-class buckets, and leakage scopes should be stored as dense packed vectors or compact blobs.

5. `Optional sidecars only when justified`
   If we later need very large sparse similarity graphs or vector features, keep them as optional sidecars rather than bloating the default downloadable library.

This is preferable to a pure text export because:
- it is smaller
- it is queryable
- it supports indices
- it can be updated by release version
- it can still be exported to JSON/CSV when needed

## Proposed Table Families

### Core tables

- `proteins`
- `protein_variants`
- `structures`
- `structure_sites`
- `ligands`
- `assay_summaries`
- `interaction_summaries`
- `motif_annotations`
- `pathway_annotations`
- `provenance_records`

### Similarity / leakage tables

- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `leakage_groups`
- `candidate_overlap_edges`

### Operational tables

- `coverage_status`
- `packet_feasibility`
- `materialization_routes`
- `source_snapshot_index`
- `scrape_capture_registry`

## What The Training-Set Creator Should Do

The creator should run in six phases.

### Phase 1: Candidate universe definition

Input options:
- accession allowlist
- pair/ligand/structure/PDB allowlist
- taxonomy filters
- modality requirements
- source trust requirements
- evidence-quality requirements
- fresh vs release-grade evidence mode

Output:
- candidate universe with explicit exclusions and reasons

### Phase 2: Balance-aware cohort planning

Use the lightweight library to measure distribution over:
- protein families
- taxa
- pathway groups
- motif groups
- structure families
- ligand classes
- interaction classes
- assay types
- mutation burden
- modality completeness

The planner should identify:
- overrepresented groups
- underrepresented groups
- coverage holes
- groups that must be downsampled or upweighted

### Phase 3: Leakage-safe splitting

The user should choose a leakage policy, for example:
- `exact_entity`
- `variant_family`
- `protein_family`
- `binding_context`
- `interaction_context`
- `structure_family`

Then the split engine should:
- group candidates by the chosen leakage keys
- simulate split difficulty
- produce train/test or train/val/test or CV folds
- emit explicit leakage audit summaries

### Phase 4: Packet blueprint generation

Before downloading anything heavy, the creator should emit a packet blueprint saying:
- what modalities are already satisfied by the lightweight library
- what raw assets already exist locally
- what extra assets must be downloaded
- what transforms must run
- which examples are partial and why

### Phase 5: Heavy asset hydration

Only after the blueprint is accepted should the tool:
- fetch PDB/mmCIF/BCIF or AlphaFold assets
- fetch or unpack selected assay / ligand / interaction raw files
- generate graphs, residue-level features, and ligand features
- optionally run PyRosetta or other heavy processors when enabled

### Phase 6: Final audit

The creator should produce:
- final cohort composition report
- leakage audit
- representation audit
- modality completeness report
- source-provenance manifest
- reproducibility manifest for rebuilding every packet

## Web Scraping Plan

Yes, we should add web scraping eventually, but only as a controlled supplemental layer.

### Scraping should start after these conditions are true

- broad structured-source procurement is stable
- motif and network gaps are better covered
- the lightweight library schema is fixed enough to receive supplemental fields
- provenance and license capture are fully enforced

### Scraping should be used for

- accession-scoped detail pages that expose useful structured facts not present in bulk exports
- motif pages with richer site semantics
- pathway pages with clearer role annotations
- structure pages with curated ligand / active-site notes
- mutation or active-site narrative summaries that can be normalized into controlled fields

### Scraping should not be used for

- primary identity
- replacing bulk structured snapshots
- unlicensed data reuse
- unverifiable narrative facts without provenance

### Scrape output policy

Every scrape capture should store:
- source page URL
- retrieval timestamp
- content hash
- parser version
- extracted normalized fields
- raw capture location
- confidence / trust class

The library should use scrape-derived fields only as:
- supplemental annotations
- confidence hints
- review prompts
- gap-filling side signals

Never as silent canonical overrides.

## How To Condense Without Losing Too Much Content

The right compression strategy is:

1. keep full raw evidence in mirrors
2. normalize only the fields that drive selection, balance, and leakage logic
3. dictionary-code repeated categorical values
4. store arrays and bitsets instead of repeated text lists
5. store provenance pointers, not duplicated payloads
6. store precomputed similarity signatures rather than recomputing from raw corpora every run

That yields a library that is:
- small enough to ship
- rich enough to design good datasets
- honest enough to explain why two examples are considered similar or risky

## Execution Plan

### Stage A: Finish the source spine

Goals:
- finish current broad mirror tail
- finish motif and network gap acquisition program
- reconcile local `bio-agent-lab` corpora with online mirrors under one snapshot model

Deliverables:
- stable source snapshot index
- claim-class trust map
- scrape registry skeleton

### Stage B: Expand the lightweight schema

Goals:
- move from protein-only summaries to full entity graph summaries
- add variants, structures, ligands, interactions, motifs, pathways, and provenance cards

Deliverables:
- schema v2 library tables
- builder/materializer
- compression and release packaging

### Stage C: Add similarity and leakage intelligence

Goals:
- compute protein, structure, ligand, interaction, and pathway similarity signatures
- define leakage groups and overlap edges

Deliverables:
- similarity signature tables
- leakage audit engine
- split-governance rules

### Stage D: Build the cohort planner

Goals:
- expose selection, balancing, and split planning from the lightweight library only

Deliverables:
- candidate-universe builder
- balance diagnostics
- split simulator v2
- dataset recipe compiler

### Stage E: Build the packet blueprint and hydrator

Goals:
- turn selected cohorts into reproducible packet manifests
- hydrate heavy assets only for selected examples

Deliverables:
- packet blueprint generator
- materialization route engine
- heavy hydration executors
- final packet QA reports

### Stage F: Add supplemental web capture

Goals:
- enrich the library in a controlled way where structured sources remain thin

Deliverables:
- scrape registry
- page-specific parsers
- supplemental annotation lanes
- scrape provenance QA

### Stage G: Validate for release use

Goals:
- prove that the library and generator reduce leakage and expose bias rather than hiding it

Deliverables:
- benchmark cohorts with before/after leakage diagnostics
- family-balance and ligand-class-balance tests
- mutation-neighborhood split tests
- user-facing audit workflows for external PDB lists

## Immediate Next Build Slices

The next high-value steps are clear.

1. `Schema v2 design`
   Extend the current summary-record model from `protein / protein_protein / protein_ligand` into the full lightweight library families listed above.
2. `Variant and structure-context layer`
   Add records for constructs, mutations, and multiple-structure context around the same protein.
3. `Similarity-signature materializer`
   Build compact biological similarity and leakage signatures.
4. `Coverage-and-bias analyzer`
   Given a candidate list or external PDB list, report over/under-representation and leakage risk.
5. `Packet blueprint generator`
   Separate planning from heavy materialization cleanly.
6. `Supplemental scrape registry`
   Define where scraping is allowed and what fields it may produce.

## Questions / Assumptions

I do not have any blocking questions at this point.

The main working assumptions I am making are:

- the default distributed artifact should be a compressed SQLite bundle
- structured source exports remain primary and scraping stays supplemental
- the lightweight library must optimize for dataset planning and leakage prevention first, not raw feature storage
- fresh-run evidence and protected release-grade evidence should remain selectable modes rather than being forced into one surface

If those assumptions hold, the plan is clear and executable.

## Bottom Line

We can capture this much information efficiently by making the lightweight library a compact, provenance-rich biological governance layer rather than a miniature copy of the raw corpora.

That means:

- accession-first identity spine
- separate but linked records for structures, variants, ligands, interactions, motifs, pathways, and provenance
- dense similarity and leakage signatures
- explicit balance diagnostics
- packet blueprints before heavy downloads
- optional heavy hydration only after selection
- supplemental web scraping only through a controlled registry

That is the right shape for a GitHub-distributable reference library that can both create strong new training sets and audit old ones for bias and leakage.
