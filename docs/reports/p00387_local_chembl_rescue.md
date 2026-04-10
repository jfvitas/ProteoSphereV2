# Local ChEMBL Rescue Brief

- Generated at: `2026-03-23T18:21:41.932421+00:00`
- Accession: `P00387`
- Packet source ref: `ligand:P00387`
- Status: `local_rescue_candidate`
- Wiring: planning-only, not canonical resolution

## Evidence

- Source file: `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`
- Source tables: `['component_sequences', 'target_components', 'target_dictionary', 'assays', 'activities']`
- Source columns: `['component_sequences.accession', 'target_dictionary.chembl_id', 'target_dictionary.pref_name', 'activities.activity_id']`

## Hits

- `P00387` -> `CHEMBL2146` (`NADH-cytochrome b5 reductase`), activities=93

## Recommendation

- Next action: `prioritize ligand procurement/planning around local ChEMBL evidence`
- Expected effect: `can reduce ligand deficit pressure without promoting the packet`

- Planning note: Use this as a ligand-planning signal only; do not treat it as canonical assay resolution or packet completion.