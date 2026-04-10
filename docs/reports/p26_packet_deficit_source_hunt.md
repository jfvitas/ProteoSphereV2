# P26 Packet Deficit Source Hunt

Date: 2026-03-23  
Scope: map the current `10` live source-fix refs in [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) to likely recovery lanes in `C:\Users\jfvit\Documents\bio-agent-lab\data` and `C:\Users\jfvit\Documents\bio-agent-lab\data_sources`.

## Current Truth Surface

The live packet state in [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) is:

- `12` packets total
- `4` complete
- `8` partial
- `10` total missing modality instances
- `10` source-fix refs:
  - `ligand:P00387`
  - `ligand:P09105`
  - `ligand:P69892`
  - `ligand:P69905`
  - `ligand:Q2TAC2`
  - `ligand:Q9NZD4`
  - `ligand:Q9UCM0`
  - `ppi:P04637`
  - `ppi:Q9UCM0`
  - `structure:Q9UCM0`

This report uses that live state, not the older weaker packet audits.

## Highest-Yield Recovery Order

1. Bridge-backed local structure/extracted lanes already on disk
2. Local bulk ligand/assay datasets already on disk
3. Local pair/interface datasets already on disk
4. Local large fallback datasets needing indexing or extraction
5. Fresh online acquisition for the rows that still have no truthful local fallback

## Source-Fix Map

| Source-fix ref | Best current local recovery lanes | Concrete candidate datasets and paths | Honest read | Recommended order |
| --- | --- | --- | --- | --- |
| `ligand:P00387` | BioLiP-guided structure ligand recovery | BioLiP hint rows in `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt` for `1UMK`; bulk assay fallback in `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip` and `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db` | Bridge target `1UMK` is known from the current cohort slice, but the local `1UMK` structure/extracted files are not present. | 1. Reacquire or backfill `1UMK` into `data/raw/rcsb`, `data/structures/rcsb`, and `data/extracted/*`. 2. If that fails, query BindingDB/ChEMBL by accession. |
| `ligand:P09105` | Bulk assay sources only | `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`, `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db` | No local bridge target was reported in the live cohort slice, and no direct BioLiP hit was found in the local BioLiP snapshot. | 1. Targeted accession extraction from BindingDB and ChEMBL. 2. Only then try fresh structure bridge acquisition. |
| `ligand:P69892` | Local structure-derived ligand rescue | Local RCSB/extracted files exist for `1FDH` and `4MQJ`: [1FDH CIF](/C:/Users/jfvit/Documents/bio-agent-lab/data/structures/rcsb/1FDH.cif), [1FDH bound objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1FDH.json), [4MQJ CIF](/C:/Users/jfvit/Documents/bio-agent-lab/data/structures/rcsb/4MQJ.cif), [4MQJ bound objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/4MQJ.json); BioLiP hits for the same accession in `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt` | This is a strong local rescue candidate because ligand-bearing structure files are already present. The current live bridge target `7QU4` is absent locally, but older heme-bearing structures are present. | 1. Mine `bound_objects` for accession-clean small-molecule rows from `1FDH` and `4MQJ`. 2. Use BioLiP as supporting provenance only. 3. Fall back to BindingDB/ChEMBL if bound-object extraction is ambiguous. |
| `ligand:P69905` | Local structure-derived ligand rescue | Local RCSB/extracted files exist for `1A00`, `1A01`, and `1A0U`: [1A00 bound objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1A00.json), [1A01 bound objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1A01.json), [1A0U bound objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1A0U.json); BioLiP hits for the same accession in `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt` | Strong local rescue candidate. The current live structure bridge already points to `1BAB`, and the local tree contains multiple hemoglobin ligand-bearing extracted rows. | 1. Mine local `bound_objects` first. 2. Use local `entry` and `structures/rcsb` for validation. 3. Use BioLiP only as cross-check metadata. |
| `ligand:Q2TAC2` | Bulk assay sources only | `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`, `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db` | No local bridge target was reported, and no direct BioLiP hit was found. | 1. Targeted BindingDB/ChEMBL extraction by accession. 2. If still empty, run fresh bridge search before claiming no ligand lane. |
| `ligand:Q9NZD4` | Local structure-derived ligand rescue | Local bridge-backed files exist for `1Z8U`: [1Z8U CIF](/C:/Users/jfvit/Documents/bio-agent-lab/data/structures/rcsb/1Z8U.cif), [1Z8U bound objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1Z8U.json), [1Z8U entry](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/entry/1Z8U.json) | Strong local rescue candidate even though a direct BioLiP accession hit was not found in the sampled lines. The local bridge-backed extracted lane is already present. | 1. Mine `1Z8U` bound objects directly. 2. Validate accession/chain lineage with `entry` and `raw/rcsb`. 3. Fall back to ChEMBL/BindingDB only if no small-molecule row survives filtering. |
| `ligand:Q9UCM0` | No truthful local ligand fallback found | Bulk assay fallbacks only: `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`, `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db` | This is the weakest row in the current deficit set. There is no local bridge target, no local AlphaFold model, no sampled BioLiP hit, and no local structure fallback already identified. | 1. Fresh online structure bridge and ligand acquisition first. 2. Then targeted BindingDB/ChEMBL extraction. 3. Keep fail-closed if both stay empty. |
| `ppi:P04637` | Local structure-interface rescue, then new curated PPI import | Local structure/extracted files exist for p53-bearing entries such as [1GZH interfaces](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/interfaces/1GZH.json), [1KZY interfaces](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/interfaces/1KZY.json), plus [1GZH entry](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/entry/1GZH.json); current IntAct local summary is still `reachable_empty` in [intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json) | The current IntAct rule leaves this row empty, but local structural interfaces may still support a truthful pair lane if non-self partner identity can be recovered cleanly. | 1. Mine local `interfaces` for accession-clean non-self partners. 2. If lineage is still ambiguous, import BioGRID next. 3. Keep IntAct self-only rows as non-recovery evidence. |
| `ppi:Q9UCM0` | No truthful local PPI fallback found | No bridge target in the live cohort slice; local fallback candidates would have to come from future curated PPI imports such as BioGRID or fresh IntAct/STRING acquisition | This row is empty on both the current IntAct live probe and the local structure bridge. | 1. Fresh curated PPI acquisition first. 2. Only then test any network-style widening. 3. Keep explicit stop conditions if still empty. |
| `structure:Q9UCM0` | No truthful local structure fallback found | Local AlphaFold archive `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar` has no `Q9UCM0` member; no local RCSB or extracted fallback has been identified | This remains a true acquisition gap. | 1. Fresh online AlphaFold DB fetch. 2. Fresh RCSB/PDBe bridge scan. 3. Only then materialize local mirror backfill if a real target is found. |

## Useful Path Patterns By Recovery Mode

### Local structure-plus-extracted rescue

Use these path patterns when a bridge PDB or ligand-bearing structure already exists:

- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\<pdb>.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb\<pdb>.cif`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry\<pdb>.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects\<pdb>.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\interfaces\<pdb>.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\assays\<pdb>.json`

Best current concrete examples:

- `P69905`: `1A00`, `1A01`, `1A0U`
- `P69892`: `1FDH`, `4MQJ`
- `Q9NZD4`: `1Z8U`
- `P04637`: `1GZH`, `1KZY`

### Local bulk assay rescue

Use these when no clean structure bridge exists:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`

These are the best near-term rescue lanes for:

- `P09105`
- `Q2TAC2`
- `Q9UCM0`

### Local structure-ligand hint layer

Use this as a discovery and cross-check surface, not the only provenance source:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`

Confirmed useful current hits:

- `P00387` via `1UMK`
- `P69892` via `1FDH` and `4MQJ`
- `P69905` via `1A00`, `1A01`, `1A0U`
- `P04637` via `1GZH`, `1KZY`, `1TSR`

## Recommended Acquisition And Processing Order

1. Recover local bridge-backed ligand rows first.
   This should target `P69905`, `P69892`, and `Q9NZD4` from `bound_objects` plus `entry` and `structures/rcsb`.

2. Recover local structure-interface PPI for `P04637`.
   Mine `interfaces` plus `entry` before importing new pair sources.

3. Run targeted bulk assay extraction for the bridge-negative ligand rows.
   This should target `P09105`, `Q2TAC2`, and `Q9UCM0` from BindingDB and ChEMBL.

4. Re-run fresh acquisition for the true no-local-fallback rows.
   This should target:
   - `structure:Q9UCM0`
   - `ppi:Q9UCM0`
   - likely also `ligand:Q9UCM0`

5. Import curated PPI breadth next if `P04637` or `Q9UCM0` still fail.
   `BioGRID` is the highest-value missing local PPI source for this purpose.

## Bottom Line

The current deficit set is not uniform.

- `P69905`, `P69892`, and `Q9NZD4` look like local-exploitation problems.
- `P04637` looks like a pair-lineage and structural-interface exploitation problem.
- `P09105`, `Q2TAC2`, and especially `Q9UCM0` still need stronger assay or fresh acquisition work.

That means the next coding wave should not treat all `10` refs the same. It should split them into:

- local extracted rescue
- local bulk assay rescue
- true fresh acquisition gaps

That is the fastest truthful route to reducing the current `8` partial packets.
