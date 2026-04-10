# P54 Variant Evidence Hunt

This report checks whether the repo already holds enough local evidence to support a truthful first `protein_variant` materializer beyond the contract.

## Verdict

Yes, but only narrowly.

The current local evidence can support a first executable mutation-and-isoform slice for `P04637` and `P31749`. It is not yet strong enough for construct-first generalization, and it should not be stretched to broad accession coverage across the full IntAct mutation export.

## What Is Supported

- `P04637` has strong local UniProt variant evidence:
  - `P04637.json` contains 1363 `Natural variant` features.
  - `P04637.txt` includes explicit `VAR_SEQ` entries and variant/isoform narrative.
- `P31749` has local UniProt variant evidence as well:
  - `P31749.json` contains 4 `Natural variant` features.
  - `P31749.txt` includes mutagenesis and isoform references.
- `data/raw/protein_data_scope_seed/intact/mutation.tsv` is present locally and provides explicit mutation rows:
  - 89,940 data rows total.
  - 613 rows matched `P04637`.
  - 532 rows matched `P31749`.
  - Each row carries a short mutation label, span, original/resulting sequence, organism, PubMed ID, and interaction context.
- `aa-variants-v1.cif` is present locally and is useful normalization scaffolding for residue-level changes.

## What This Means For The Materializer

The smallest truthful first implementation can do the following:

- materialize accession-scoped variant rows for `P04637` and `P31749`
- set `protein_ref` and `parent_protein_ref` from the local UniProt spine
- build `variant_signature` from explicit UniProt and IntAct variant labels
- derive `mutation_list` and `sequence_delta_signature` from explicit local evidence
- treat isoform-aware rows as supported when the source already distinguishes them

## What Is Still Deferred

- Construct-first materialization
- Broad generalization to every accession in `mutation.tsv`
- Name-only or alias-only variant inference

I did not find explicit construct labels in the local `P04637` and `P31749` UniProt payloads, so `construct_type` should remain partial or deferred for the first slice.

## Evidence Paths

- [P04637 UniProt JSON](../../data/raw/uniprot/20260323T002625Z/P04637/P04637.json)
- [P04637 UniProt flat file](../../data/raw/uniprot/20260323T002625Z/P04637/P04637.txt)
- [P31749 UniProt JSON](../../data/raw/uniprot/20260323T002625Z/P31749/P31749.json)
- [P31749 UniProt flat file](../../data/raw/uniprot/20260323T002625Z/P31749/P31749.txt)
- [IntAct mutation export](../../data/raw/protein_data_scope_seed/intact/mutation.tsv)
- [aa-variants dictionary extract](../../data/raw/protein_data_scope_seed/pdb_chemical_component_dictionary/aa-variants-v1.cif.gz__extracted/aa-variants-v1.cif)

## Bottom Line

The repo does have enough already-procured evidence to move from contract to a limited first protein-variant implementation. The safe first slice is mutation and isoform evidence for `P04637` and `P31749`, with constructs kept out until a grounded construct lineage appears in the local evidence set.
