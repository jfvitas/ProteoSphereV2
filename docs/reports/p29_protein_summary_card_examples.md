# P29 Protein Summary Card Examples

This is the first concrete operator-facing protein card example set for the summary-library rollout. It is grounded in the existing record examples and the first-slice plan:

- [docs/reports/p29_summary_record_examples.md](/D:/documents/ProteoSphereV2/docs/reports/p29_summary_record_examples.md)
- [docs/reports/p29_summary_library_first_slice.md](/D:/documents/ProteoSphereV2/docs/reports/p29_summary_library_first_slice.md)
- [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py)
- [artifacts/status/selected_cohort_materialization.current.json](/D:/documents/ProteoSphereV2/artifacts/status/selected_cohort_materialization.current.json)
- [artifacts/status/local_bridge_ligand_payloads.real.json](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json)
- [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json)
- [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json)
- [data/raw/local_registry/20260330T054522Z/import_manifest.json](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260330T054522Z/import_manifest.json)
- [docs/reports/q9ucm0_structure_gap_local_investigation_2026_03_23.md](/D:/documents/ProteoSphereV2/docs/reports/q9ucm0_structure_gap_local_investigation_2026_03_23.md)

The goal is simple: show the first protein card that an operator could trust as a fused summary, and show a second card that stays blocked instead of pretending coverage exists.

## Card Shape

Each protein summary card should keep a small fused spine and then attach modality sections:

- `protein` fused fields: accession, protein reference, protein name, organism, sequence length, aliases, and join status.
- `structure`, `ligand`, `pathway`, `interaction`, and `motif` sections: each section must say whether it is materialized, indexed-only, or lazy.
- `provenance` section: compact snippets from the exact source boundaries that produced the card.
- `dissent` section: explicit handling for mismatches, missing modalities, or claims that must not be promoted.

The first-slice plan still applies:

- Materialize the protein spine and provenance first.
- Materialize structure, ligand, pathway, and interaction only when the local registry already has a truthful payload.
- Keep motif index-only until the motif sources are actually present locally.
- Keep heavy raw payloads lazy even when the compact card is materialized.

## Strong Card: `protein:P69905`

`P69905` is the strong example because the local packet has sequence, structure, ligand, and PPI payloads, and the registry join index also points at Reactome plus motif-capable source families. The card is still honest about the motif lane being blocked.

Fused fields should look like this:

- accession: `P69905`
- protein ref: `protein:P69905`
- protein name: `Hemoglobin subunit alpha`
- organism: `Homo sapiens`
- sequence length: `142`
- aliases: `P69905`, `HBA_HUMAN`

Provenance payload snippets should be compact and source-specific:

- import manifest snippet: `P69905 -> uniprot, alphafold_db, reactome, interpro, pfam, string, biogrid, intact, prosite, elm, mega_motif_base, motivated_proteins`
- packet snippet: `sequence`, `structure`, `ligand`, `ppi` all present on `packet-P69905`
- Reactome snippet: `reactome-local:P69905` with `pathway_count:18`
- bridge snippet: `P69905:1A9W:CMO` from `extracted_bound_objects`

Dissent handling should be explicit:

- Do not promote the packet-level PPI artifact into a native pair record unless the pair summary itself is present.
- Treat motif as indexed-only because the local registry still marks the motif family missing.
- If a later source disagrees on protein naming, keep the protein spine accession-first and record the source conflict rather than rewriting the card.

Materialization boundaries for the strong card:

- Materialized: protein spine, structure, ligand, pathway, interaction, provenance pointers.
- Indexed-only: motif section, motif-system hints, source-name hints.
- Lazy: full mmCIF, full MITAB, full assay rows, full motif tables, raw packet blobs.

## Weak / Blocked Card: `protein:Q9UCM0`

`Q9UCM0` is the weak example because the selected packet is sequence-only, the local structure-gap investigation already proved there is no truthful local recovery path, and the refreshed import manifest only binds it to UniProt.

Fused fields should stay minimal:

- accession: `Q9UCM0`
- protein ref: `protein:Q9UCM0`
- organism: `Homo sapiens`
- sequence length: `77`
- aliases: `Q9UCM0`

Provenance payload snippets should make the block visible:

- import manifest snippet: `Q9UCM0 -> uniprot only`
- packet snippet: `packet-Q9UCM0` contains `sequence` only
- structure-gap snippet: no local AlphaFold, no local RCSB, no truthful recovery path

Dissent handling should be strict:

- Do not backfill structure, ligand, pathway, or interaction from generic mirrors.
- Do not turn a missing modality placeholder into a positive join.
- If a downstream resolver later suggests a candidate, route that to acquisition planning instead of updating the card in place.

Materialization boundaries for the blocked card:

- Materialized: protein spine, provenance pointers.
- Indexed-only: motif placeholder, because the motif family is still absent from the refreshed local registry.
- Lazy: structure, ligand, pathway, interaction, raw packet payloads, full source rows.

## Operator Rule Of Thumb

The operator-facing card should read like a trustworthy summary, not a completeness claim. If the registry can prove a modality, materialize it. If the registry only hints at a modality, index it. If the registry cannot support the claim, leave it lazy and say why.

