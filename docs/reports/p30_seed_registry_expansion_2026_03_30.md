# P30 Seed Registry Expansion

- Generated at: `2026-03-30T09:00:00-05:00`
- Focus: promote already-downloaded `protein_data_scope_seed` lanes into the authoritative local-source registry so the merge planner can see the full local reference surface.

## What Changed

- Extended [`execution/acquire/local_source_registry.py`](D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py) with five repo-local seed-backed sources that were present on disk but absent from the registry:
  - `chebi`
  - `complex_portal`
  - `rnacentral`
  - `sifts`
  - `pdb_chemical_component_dictionary`
- Kept all of them on repo-local `data/raw/protein_data_scope_seed/...` paths so they resolve through the repo-aware seed prefix logic added earlier on 2026-03-30.

## Why These Sources Matter

- `sifts` is the cleanest accession-to-structure bridge in the project docs and should tighten UniProt to PDB chain/entity joins.
- `pdb_chemical_component_dictionary` and `chebi` strengthen the ligand identity lane by anchoring CCD IDs, HET codes, and ChEBI-linked chemistry to the same local reference.
- `complex_portal` adds curated complex membership context that complements BioGRID and IntAct rather than replacing them.
- `rnacentral` does not become assay truth, but it adds resolver-grade mapping payloads that the docs already call out as a pending tier gap.

## Local Evidence Snapshot

| Source | Local files | Approx bytes | Sample payloads |
| --- | ---: | ---: | --- |
| `chebi` | 10 | 2,880,408,822 | `chebi.obo`, `chebi.owl`, `chebi.json` |
| `complex_portal` | 85 | 104,541,810 | `9606.tsv`, `9606_predicted.tsv`, species zips |
| `rnacentral` | 17 | 106,578,115,797 | `id_mapping.tsv.gz`, `rnacentral.gpi.gz`, `rnacentral_active.fasta.gz` |
| `sifts` | 20 | 276,048,114 | `pdb_chain_uniprot.tsv.gz`, `uniprot_pdb.tsv.gz`, `uniprot_segments_observed.tsv.gz` |
| `pdb_chemical_component_dictionary` | 7 | 713,821,717 | `components.cif.gz`, `chem_comp_model.cif.gz`, `aa-variants-v1.cif.gz` |

## Revised Merge Order

1. Refresh the authoritative local registry so the already-fixed seed-backed sources (`uniprot`, `biogrid`, `intact`, `prosite`) plus the five new definitions become visible in `data/raw/local_registry_runs/LATEST.json`.
2. Promote `sifts` immediately after `uniprot` and before any structure-heavy merge, because it provides the strongest structure-to-accession crosswalk.
3. Blend `pdb_chemical_component_dictionary` with `chebi`, `bindingdb`, `chembl`, `biolip`, and `pdbbind*` as the chemical identity layer.
4. Merge `complex_portal` after `biogrid` and `intact` as complex-context support, keeping native-complex evidence distinct from binary PPI truth.
5. Keep `rnacentral` in resolver/support mode until a concrete downstream consumer needs its mapping families in the canonical store.

## Blocker

- This shell still lacks `python`, `py`, and `uv`, so the registry refresh could not be executed here after the definition expansion.

## Next Run

```powershell
python scripts\import_local_sources.py --include-missing
```

- Then verify that the next `LATEST.json` contains:
  - `biogrid`, `intact`, `prosite` as `present`
  - the newly tracked `chebi`, `complex_portal`, `rnacentral`, `sifts`, and `pdb_chemical_component_dictionary`
- After that refresh, recompute the source-coverage and blend-order reports from the corrected registry state.
