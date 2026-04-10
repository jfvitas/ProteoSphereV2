# Benchmark Corpus Manifest

Date: 2026-03-22
Task: `P6-I007`

## Bottom Line

This candidate corpus manifest is ready to hand off as soon as `P5-I012` clears. The prep is conservative and stays inside the landed storage/joinability direction: accession-level packaging, pinned source boundaries, explicit lineage, and no new runtime architecture.

The only remaining real-corpus gap is the first pinned multi-accession corpus pull. The source slices below are already proven live in small smoke runs, but the full 12-protein benchmark pack still needs to be assembled and split at the corpus level.

## Candidate Manifest

- `manifest_id`: `benchmark-corpus-manifest-2026-03-22`
- `spine`: human UniProt accession spine
- `packaging_unit`: accession bundle, not row
- `minimum_cohort_size`: `12`
- `split_policy`: accession-level only, suggested `8/2/2` train/val/test
- `required_anchors`: `P69905`, `P04637`
- `ligand_lane_anchor`: `P31749`
- `cohort_shape`: `4` rich coverage, `4` moderate coverage, `4` sparse or negative controls

## Candidate Source Slices

| Slice | Live proof already gathered | Role in the benchmark | First real-corpus pull still needed? |
| --- | --- | --- | --- |
| UniProt identity spine | `P69905` anchor retrieval succeeded | Canonical accession spine for every bundle | Yes, for the frozen 12-accession bundle |
| InterPro enrichment | `P69905` returned `6` protein-linked entries, including `IPR000971` | Domain/family/site enrichment lane | Yes, for the full cohort |
| Reactome pathway mapping | `P69905` returned `6` pathway rows through the UniProt mapping endpoint | Pathway enrichment lane | Yes, for the full cohort |
| BindingDB ligand evidence | `P31749` normalized to a non-empty live record set | Ligand-positive extension lane | Yes, for the full cohort |
| IntAct PPI evidence | `P04637` resolved to UniProt participants in live PSICQUIC smoke | Interaction evidence lane | Yes, for the full cohort |
| Experimental structure | `1CBS` live RCSB/PDBe smoke succeeded after parser hardening | Structure lane for experimental coordinates | Yes, for the full cohort |
| Predicted structure | `P69905` AlphaFold smoke succeeded | Predicted-structure companion lane | Yes, for the full cohort |
| Evolutionary/MSA corpus | `P69905` live-derived MSA smoke succeeded with one record | Family-aware conservation lane | Yes, for a pinned multi-record corpus snapshot |

## Minimum Benchmark Cohort

The first execution-ready cohort should stay small and easy to replay:

1. `4` rich-coverage proteins with InterPro + Reactome coverage.
2. `4` moderate-coverage proteins with at least one missing layer.
3. `4` sparse or negative-control proteins that keep missingness explicit.
4. `P69905` must be included.
5. `P31749` should be included if the ligand lane is enabled.
6. `P04637` should be included to exercise the PPI lane.

This gives us a cohort that can validate accession-level packaging, source-layer missingness, and split hygiene without forcing every lane to resolve.

## Enrichment Fields To Require

### Shared fields for every slice

- `manifest_id`
- `source_name`
- `release_version`
- `release_date`
- `retrieval_mode`
- `source_locator`
- `source_record_id`
- `canonical accession`
- `provenance`
- `quality_flags`
- `raw_payload_sha256` or source checksum
- `lazy_materialization_refs`

### Slice-specific fields

- UniProt: accession, protein name, taxon, sequence length, sequence version, sequence hash.
- InterPro: `IPR` accession, member signature accession, residue span, representative flag.
- Reactome: stable ID, species, pathway ancestry, UniProt participation.
- BindingDB: target accession, `MonomerID` or `Reactant_set_id`, assay ID, ligand identifiers, affinity type/value, `SMILES` / `InChIKey`.
- IntAct: interaction AC, IMEx ID, participant accessions, organism, interaction type, feature spans, native-complex flag.
- RCSB/PDBe: PDB ID, entity ID, chain ID, assembly ID, SIFTS span, validation or quality slice.
- AlphaFold DB: accession, `sequenceChecksum`, `modelEntityId`, version, confidence summary, asset refs.
- Evolutionary/MSA: accession, sequence version/hash, UniRef cluster IDs, orthogroup IDs, alignment depth, quality flags.

## What Is Proven Live Versus What Still Needs First Corpus Pulls

### Proven live

- UniProt anchor retrieval for `P69905`.
- InterPro enrichment for `P69905`.
- Reactome pathway mapping for `P69905`.
- BindingDB ligand acquisition for `P31749`.
- IntAct PPI acquisition for `P04637`.
- RCSB/PDBe experimental structure smoke for `1CBS`.
- AlphaFold DB smoke for `P69905`.
- Evolutionary/MSA smoke seeded from `P69905`.

### Still needing first real-corpus pulls

- The frozen 12-accession cohort bundle.
- The accession-level `8/2/2` split labels.
- The mixed rich / moderate / sparse bucket assembly.
- The cohort-wide enrichment pulls for the non-smoke accessions.
- The checkpointed unattended benchmark run over the assembled bundle.

## Execution Gate

Start the benchmark as soon as `P5-I012` clears. No new architecture is required; this is a packaging and pinning task on top of the landed pipeline and storage strategy.

## Commands Run

- `Get-Content docs/reports/real_data_benchmark_plan_2026_03_22.md`
- `Get-Content docs/reports/live_source_smoke_2026_03_22.md`
- `Get-Content docs/reports/evolutionary_live_smoke_2026_03_22.md`
- `Get-Content docs/reports/annotation_pathway_live_smoke_2026_03_22.md`
- `Get-Content docs/reports/bindingdb_live_smoke_2026_03_22.md`
- `Get-Content docs/reports/ppi_live_smoke_2026_03_22.md`
- `Get-Content docs/reports/source_joinability_analysis.md`
- `Get-Content docs/reports/source_storage_strategy.md`

## Evidence Basis

The manifest follows the live smoke and benchmark-plan evidence already landed in-tree:

- `docs/reports/real_data_benchmark_plan_2026_03_22.md:12-18`
- `docs/reports/annotation_pathway_live_smoke_2026_03_22.md:7-8, 107-120`
- `docs/reports/bindingdb_live_smoke_2026_03_22.md:57-76`
- `docs/reports/ppi_live_smoke_2026_03_22.md:9-12, 74-77`
- `docs/reports/evolutionary_live_smoke_2026_03_22.md:14-20, 63-75`
