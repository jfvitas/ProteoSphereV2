# P29 Summary Library Plan

The current summary-library stack is already pointing in the right direction: [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py) supports protein, pair, and ligand records with provenance/context defaults, [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py) keeps unresolved evidence visible, and the storage/join strategy docs already insist on accession-first joins with lazy heavy payloads. This plan extends that shape into a single operator-facing library that also covers structures, motifs, pathways, and provenance without pretending missing sources are present.

## Ground Truth

- The refreshed local registry at [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json) reports 39 selected/imported sources, with 29 present, 2 partial, and 8 missing.
- The category split is honest: structure, ligand, pathway, and structural-classification sources are present locally; motif and broad interaction-network sources are still missing.
- The source coverage matrix at [docs/reports/source_coverage_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/source_coverage_matrix.md) still flags motifs and interaction networks as priority gaps.
- The existing Reactome and IntAct materializations at [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json) and [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json) show the current conservative pattern: compact summaries, explicit partials, and preserved native ids.
- The frozen benchmark cohort in [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json) is the right operator-facing spine for the first integrated release.

## Proposed Schema

The proposal is a schema v2 operator library with one accession-first spine and seven record families.

| Family | Canonical key | Source fusion | Materialize | Index | Lazy |
| --- | --- | --- | --- | --- | --- |
| Protein | `protein:{UniProt accession}` | UniProt plus cohort and registry state | accession, review status, organism, sequence length/version, aliases, provenance | accession, namespaces, join status, manifest id | long comments, evidence text, rare isoforms, full annotation payload |
| Structure | `structure:{source}:{pdb_or_model_id}:{entity_id}:{chain_id}:{assembly_id}` | RCSB/PDBe, AlphaFold DB, and extracted structure views | structure kind, protein ref, ids, residue span, confidence, provenance | structure ids, spans, manifest id | mmCIF, coordinates, maps, validation bundles |
| Ligand | `ligand:{namespace}:{identifier}` | BindingDB, ChEMBL, BioLiP, and PDBbind | chemical id, assay id, measurements, provenance | InChIKey, SMILES, Reactant_set_id, MonomerID | full assay rows, assay text, publication context |
| Interaction | `pair:{kind}:{participant_a}|{participant_b}` | IntAct, BioGRID, STRING, Complex Portal, and PDBbind projections | participant refs, native ids, evidence count, confidence, provenance | interaction ids, evidence refs, lineage flags | full MITAB, PSI-MI XML, complex payloads |
| Motif | `motif:{system}:{protein_ref}:{span_start}:{span_end}` | InterPro, Pfam, PROSITE, ELM, and motif catalogs | stable span hits, motif system, provenance | motif accession, span, partner hints | full motif tables, logos, long docs |
| Pathway | `pathway:{Reactome stable_id}:{species}` | Reactome and pathway annotation tables | stable id, species, ancestry, provenance | pathway id, hierarchy keys, source record id | diagrams, BioPAX, SBML, broad bundles |
| Provenance | `provenance:{source_name}:{manifest_id}:{source_record_id}` | source release manifests, raw snapshot metadata, and the refreshed local registry | release version/date, checksum, acquisition metadata | manifest id, locator, snapshot fingerprint | raw payloads and portal captures |

## Source Fusion Strategy

1. Keep UniProt accession as the only protein spine. Secondary accessions remain aliases.
2. Keep experimental structures and predicted structures separate. AlphaFold is a companion, not a merge target.
3. Join ligands by stable chemical identity first. Target names alone are not enough.
4. Preserve native interaction ids, association ids, and complex lineage. Binary projections are summaries, not identity.
5. Join motifs by system plus accession plus residue span. If the span is not stable, keep the row index-only.
6. Join pathways by stable Reactome ID and species, then preserve ancestry and evidence code.
7. Emit provenance cards from source release manifests and raw snapshot boundaries so operators can trace every card back to the exact input.

## Materialize, Index, Lazy

| Family | Must materialize | Must index | Must stay lazy |
| --- | --- | --- | --- |
| Protein | accession, organism, sequence length/version, aliases, provenance pointers | accession, namespaces, join status, source manifest id | long comments, evidence text, rare isoforms |
| Structure | structure kind, protein ref, ids, residue span, confidence, provenance pointers | PDB/model ids, chain/assembly ids, spans, manifest id | mmCIF, coordinates, maps, validation reports |
| Ligand | protein ref, ligand ref, chemical id, assay id, measurement summary, provenance pointers | InChIKey, SMILES, Reactant_set_id, MonomerID, manifest id | full assay rows, assay text, publication context |
| Interaction | participant refs, native ids, evidence count, confidence, provenance pointers | interaction ids, evidence refs, lineage flags, manifest id | full MITAB, PSI-MI XML, complex payloads |
| Motif | only span-stable hits with provenance; otherwise explicit deferred placeholders | motif catalog ids, span keys, partner hints, manifest id | full motif tables, logos, long docs |
| Pathway | stable id, species, ancestry, evidence code, provenance pointers | pathway ids, hierarchy keys, source record id | diagrams, BioPAX, SBML |
| Provenance | release version/date, checksum, acquisition metadata | manifest id, locator, snapshot fingerprint, artifact refs | raw payloads and portal captures |

## Materialization Plan

1. Materialize provenance cards and the protein spine first. That gives the operator a compact, auditable boundary before any heavy join work begins.
2. Materialize present local structure, ligand, and Reactome pathway summaries next. Those sources are already present in the refreshed local registry and are the fastest path to useful operator cards.
3. Materialize curated interaction summaries only when the source snapshot is pinned and the evidence is traceable. Weak, partial, and self-only evidence should stay explicit rather than being widened away.
4. Keep motif and broad interaction-network coverage index-first until the local registry actually has those sources. The current registry still marks them missing, so this is an honest gap, not a bug.
5. Wire every heavy payload through lazy pointers. The operator library should stay small and rebuildable, with the raw MITAB, mmCIF, assay, diagram, and motif assets fetched only on demand.

## Why This Shape

- It matches the current repo contract in [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py) and [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py).
- It follows the storage tiers defined in [docs/reports/source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md): canonical store for identity, planning index for routing, feature cache for operator cards, and deferred fetch for heavy payloads.
- It follows the join rules in [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md): accession-first proteins, stable structure keys, native interaction ids, span-aware motifs, and species-aware pathways.
- It stays consistent with the existing conservative materializations in [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json) and [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json).
- It respects the live cohort truth from [artifacts/status/release_cohort_registry.json](/D:/documents/ProteoSphereV2/artifacts/status/release_cohort_registry.json) and the local ligand-gap map in [docs/reports/p27_remaining_ligand_local_source_map.md](/D:/documents/ProteoSphereV2/docs/reports/p27_remaining_ligand_local_source_map.md).

## Residual Risks

- Motif and broad interaction-network sources are still missing in the refreshed local registry, so those rows must remain index-only or deferred until procurement changes.
- Bare protein accessions still need registry-aware resolution in downstream indexes, so accession normalization must stay explicit.
- Some accessions remain true acquisition gaps, so this plan must not imply universal ligand or interaction completeness.
- Heavy payloads are intentionally deferred, so the operator surface needs clear lazy pointers or the library will look incomplete even when the summary is correct.

## Outcome

This plan gives the operator one compact library with a single protein spine, separate structure and ligand cards, honest interaction lineage, pathway context, span-aware motif placeholders, and provenance cards that trace every row back to the exact source boundary. It is concrete enough to materialize now for the present local registry, but still conservative enough to keep the missing motif and network lanes visible instead of hiding them.
