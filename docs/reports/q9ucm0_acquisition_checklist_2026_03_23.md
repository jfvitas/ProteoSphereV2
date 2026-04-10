# Q9UCM0 Acquisition Checklist

Date: 2026-03-23

## Scope

Turn the current `Q9UCM0` evidence pass into a concrete acquisition checklist that can be executed later without re-investigating the gap.

## Current Truth

`Q9UCM0` is still unresolved for:

- `structure`
- `ligand`
- `ppi`

Current live packet state:

- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [packet-q9ucm0/packet_manifest.json](/D:/documents/ProteoSphereV2/data/packages/selected-cohort-strict-20260323T1648Z/packet-q9ucm0/packet_manifest.json)
- [p15_upgraded_cohort_slice.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/p15_upgraded_cohort_slice.json)

The current truthful read is:

- `structure`: missing
- `ligand`: missing
- `ppi`: missing

## Repo And Local Paths Already Checked

### Local registry and imported `bio-agent-lab` inventories

- [local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json)
- [import_manifest.json](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/import_manifest.json)
- [alphafold inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/alphafold_db/inventory.json)
- [structures_rcsb inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/structures_rcsb/inventory.json)
- [raw_rcsb inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/raw_rcsb/inventory.json)
- [uniprot inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/uniprot/inventory.json)

### Current online-mirror artifacts

- [Q9UCM0.best_structures.json](/D:/documents/ProteoSphereV2/data/raw/rcsb_pdbe/20260323T154140Z/Q9UCM0/Q9UCM0.best_structures.json)
- [Q9UCM0.interactor.json](/D:/documents/ProteoSphereV2/data/raw/intact/20260323T154140Z/Q9UCM0/Q9UCM0.interactor.json)
- [Q9UCM0.psicquic.tab25.txt](/D:/documents/ProteoSphereV2/data/raw/intact/20260323T154140Z/Q9UCM0/Q9UCM0.psicquic.tab25.txt)

### Local `bio-agent-lab` roots checked directly

- [master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/master_pdb_repository.csv)
- [test_v1 master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/data/releases/test_v1/master_pdb_repository.csv)
- [swissprot_pdb_v6.tar](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/alphafold/swissprot_pdb_v6.tar)
- [structures/rcsb](/C:/Users/jfvit/Documents/bio-agent-lab/data/structures/rcsb)
- [raw/rcsb](/C:/Users/jfvit/Documents/bio-agent-lab/data/raw/rcsb)
- [extracted/interfaces](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/interfaces)
- [BioLiP.txt](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/biolip/BioLiP.txt)
- `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`
- [chembl_36.db](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db)

## Why `Q9UCM0` Is Still Unresolved

### Structure

- The local registry binds `Q9UCM0` only to UniProt sequence, not to AlphaFold or local RCSB structure lanes.
- The local AlphaFold tar does not contain a `Q9UCM0` member.
- The current mirrored RCSB/PDBe best-structures artifact is empty:
  - [Q9UCM0.best_structures.json](/D:/documents/ProteoSphereV2/data/raw/rcsb_pdbe/20260323T154140Z/Q9UCM0/Q9UCM0.best_structures.json)
- The current cohort slice already records the same truth:
  - `bridge.state = "missing"`
  - `reason = "no bridge target reported in the structure bridge scan"`

### PPI

- Current mirrored IntAct evidence is reachable but not rescuing `Q9UCM0`.
- [Q9UCM0.interactor.json](/D:/documents/ProteoSphereV2/data/raw/intact/20260323T154140Z/Q9UCM0/Q9UCM0.interactor.json) points to `P69905`, not a clean `Q9UCM0` canonical interactor row.
- [Q9UCM0.psicquic.tab25.txt](/D:/documents/ProteoSphereV2/data/raw/intact/20260323T154140Z/Q9UCM0/Q9UCM0.psicquic.tab25.txt) includes `Q9UCM0` only as an alternate identifier on the `P69905` side.
- The current cohort slice truthfully records:
  - `curated_ppi.pair_count = 0`
  - `curated_ppi.empty_state = "reachable_empty"`

### Ligand

- No local bridge-backed structure exists to support a truthful ligand extraction.
- No local BioLiP or master-PDB mapping was found that cleanly binds `Q9UCM0` to a rescuable local structure asset.
- Local bulk assay sources are present, but there is no current verified `Q9UCM0` hit in the indexed local evidence already checked.

## Exact Fresh Probes Required Next

Run these in order.

### 1. AlphaFold DB explicit accession probe

Goal:

- determine whether a real AlphaFold structure payload exists for `Q9UCM0`

Success counts as:

- a real `Q9UCM0` AlphaFold record or structure file is retrieved and mirrored into ProteoSphere raw storage
- the payload is accession-clean and usable as a structure artifact

Failure counts as:

- no `Q9UCM0` AlphaFold record found
- only landing-page or ambiguous results

### 2. RCSB/PDBe fresh best-structures re-probe

Goal:

- determine whether a current RCSB/PDBe bridge target now exists for `Q9UCM0`

Success counts as:

- a non-empty best-structures result for `Q9UCM0`
- or a concrete PDB target that can be mirrored as raw JSON plus `.cif`

Failure counts as:

- best-structures remains empty
- or only ambiguous alias-only records are found

### 3. BioGRID guarded procurement first wave

Goal:

- determine whether curated non-IntAct PPI evidence exists for `Q9UCM0`

Required first-wave files:

- `BIOGRID-ORGANISM-LATEST.mitab.zip`
- `BIOGRID-ALL-LATEST.mitab.zip`

Success counts as:

- at least one parseable, non-self, accession-mappable `Q9UCM0` pair row in the frozen guarded snapshot

Failure counts as:

- no `Q9UCM0` rows
- alias-only noise that still cannot be mapped cleanly to canonical `Q9UCM0`
- parser or guarded validation failure

### 4. STRING guarded procurement first wave

Goal:

- determine whether network-scale curated or high-confidence interaction evidence can rescue the PPI lane for `Q9UCM0`

Required first-wave files:

- `protein.physical.links.detailed.v12.0.txt.gz`
- `protein.links.detailed.v12.0.txt.gz`
- `protein.info.v12.0.txt.gz`
- `protein.aliases.v12.0.txt.gz`
- `species.v12.0.txt`

Success counts as:

- at least one high-confidence `Q9UCM0` interaction row that joins cleanly through STRING IDs, aliases, and species metadata

Failure counts as:

- no cleanly joinable `Q9UCM0` rows
- mixed-version or validator-blocked snapshot
- only weak alias noise with no canonical accession recovery

### 5. Fresh ligand-source accession probe

This should happen only after the structure probes above, unless a bulk assay lane is already being extracted for another reason.

Recommended sources:

- local or refreshed BindingDB accession probe
- local or refreshed ChEMBL accession probe

Success counts as:

- at least one ligand or assay row that can be cleanly tied to `Q9UCM0`
- with enough provenance to materialize a truthful ligand packet lane

Failure counts as:

- no `Q9UCM0` rows
- only ambiguous text matches with no accession-safe mapping

## Modality-Specific Rescue Criteria

### Structure rescue

`Q9UCM0` is rescued for structure only if one of these becomes true:

- a mirrored AlphaFold DB structure exists for `Q9UCM0`
- a mirrored RCSB/PDBe bridge target exists for `Q9UCM0`

### PPI rescue

`Q9UCM0` is rescued for PPI only if one of these becomes true:

- BioGRID yields a canonical, non-self, accession-mappable pair for `Q9UCM0`
- STRING yields a cleanly joined `Q9UCM0` interaction after alias and species reconciliation
- a future stronger IntAct acquisition yields a direct canonical pair instead of alias-only noise

### Ligand rescue

`Q9UCM0` is rescued for ligand only if one of these becomes true:

- a newly acquired structure lane exposes target-clean bound small molecules for `Q9UCM0`
- BindingDB yields accession-clean ligand/assay rows for `Q9UCM0`
- ChEMBL yields accession-clean ligand activity rows for `Q9UCM0`

## Recommended Execution Order

1. AlphaFold DB explicit accession probe
2. RCSB/PDBe fresh best-structures re-probe
3. BioGRID guarded procurement first wave
4. STRING guarded procurement first wave
5. BindingDB / ChEMBL accession probe only if structure rescue still fails or bulk ligand extraction is already underway

## Bottom Line

`Q9UCM0` is not blocked by a missing parser or a hidden local rescue. It is blocked because the currently checked local and mirrored evidence stays empty or alias-only for all three missing modalities.

The next work is acquisition, not reinterpretation:

- fresh structure probe
- fresh curated PPI procurement
- then targeted ligand-source probe if needed
