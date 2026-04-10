# Broad Mirror Progress

- Generated at: `2026-04-06T00:46:45.125861+00:00`
- Manifest: `protein_data_scope/sources_manifest.json`
- Seed root: `data/raw/protein_data_scope_seed`
- Sources tracked: `17`
- File coverage: `162/162`
- Coverage percent: `100.0%`
- Complete sources: `17`
- Incomplete sources: `0`
- Missing files: `0`
- Partial stubs: `0`
- Active `.part` files: `0`
- Active `.part` bytes: `0`

## Priority Overview

### P4 complete

| Source | Status | Value | Coverage | Missing | Partial | Representative missing files |
| --- | --- | --- | --- | --- | --- | --- |
| `alphafold_db` | complete | complete | 100.0% | 0 | 0 | none |
| `bindingdb` | complete | complete | 100.0% | 0 | 0 | none |
| `biogrid` | complete | complete | 100.0% | 0 | 0 | none |
| `chebi` | complete | complete | 100.0% | 0 | 0 | none |
| `chembl` | complete | complete | 100.0% | 0 | 0 | none |
| `complex_portal` | complete | complete | 100.0% | 0 | 0 | none |
| `elm` | complete | complete | 100.0% | 0 | 0 | none |
| `intact` | complete | complete | 100.0% | 0 | 0 | none |
| `interpro` | complete | complete | 100.0% | 0 | 0 | none |
| `pdb_chemical_component_dictionary` | complete | complete | 100.0% | 0 | 0 | none |
| `prosite` | complete | complete | 100.0% | 0 | 0 | none |
| `reactome` | complete | complete | 100.0% | 0 | 0 | none |
| `rnacentral` | complete | complete | 100.0% | 0 | 0 | none |
| `sabio_rk` | complete | complete | 100.0% | 0 | 0 | none |
| `sifts` | complete | complete | 100.0% | 0 | 0 | none |
| `string` | complete | complete | 100.0% | 0 | 0 | none |
| `uniprot` | complete | complete | 100.0% | 0 | 0 | none |

## Source Notes

- `alphafold_db`: `The full site exposes many proteome tarballs. This manifest includes Swiss-Prot bulk files and representative entry points only.`
- `bindingdb`: `BindingDB updates monthly. The broad download page currently wraps many links in an HTML ready page, so the manifest uses direct file paths where verified. Update the YYYYMM stamp if needed.`
- `chembl`: `Pinned to the current ChEMBLdb latest bulk artifacts. Additional release drift should still be reviewed when the release token changes.`
- `complex_portal`: `The verified current-release root exposes a compact truth-first queue: released_complexes.txt plus the human complextab TSVs. Species fan-out and PSI packages remain resolver-gated.`
- `elm`: `ELM exposes stable TSV exports for motif-class regex definitions and motif-domain interaction tables. The class export and interaction-domain TSV are both live; broad instance harvesting and license-sensitive redistribution still need manual review.`
- `intact`: `FTP layout can shift. Common bulk resources include PSI-MI XML 2.5, PSI-MI XML 3.0, MITAB 2.7, and mutation export tables.`
- `interpro`: `InterPro 108.0 now has a verified root-file queue. The large XML and tarball payloads remain deferred by size, but the small truth-bearing release files are pinned.`
- `reactome`: `Reactome's current download index exposes ReactionPMIDS.txt and ComplexParticipantsPubMedIdentifiers_human.txt; the old reactionPMIDS.txt and humanComplexes.txt names were stale. reactome.graphdb.tgz is still live in current_release, but the last seed sync failed before it landed.`
- `rnacentral`: `Pinned to stable current_release bulk files. SQL access now goes through the public Postgres database at https://rnacentral.org/help/public-database. Genome-coordinate BED fan-out and per-database mapping families still require directory enumeration before full manifest coverage.`
- `sabio_rk`: `SABIO-RK is best handled as a query-scoped kinetics lane instead of a fake bulk dump. The broad procurement mirror keeps exactly the stable REST vocabulary and UniProt accession suggestion list; accession-scoped P31749 probe outputs 404 in the current logs and are documented in docs/reports/p36_sabio_rk_blocker_note.md instead of being counted as broad expected files.`
- `uniprot`: `Cross-drive download authority is satisfied through the overflow root.`

