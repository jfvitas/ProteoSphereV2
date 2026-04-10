# Local ChEMBL Rescue Brief

- Generated at: `2026-03-31T19:50:10.470861+00:00`
- Accession: `P09105`
- Packet source ref: `ligand:P09105`
- Status: `no_local_candidate`
- Wiring: planning-only, not canonical resolution

## Evidence

- Source file: `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`
- Source tables: `['component_sequences', 'target_components', 'target_dictionary', 'assays', 'activities']`
- Source columns: `['component_sequences.accession', 'target_dictionary.chembl_id', 'target_dictionary.pref_name', 'activities.activity_id']`

## Hits

- none

## Recommendation

- Next action: `fall through to online procurement`
- Expected effect: `no local ligand rescue available`
- Extraction readiness: `blocked`
- Assay / activity counts: `0` / `0`
- Blockers: `['no_local_chembl_target_hit', 'fall_back_to_online_procurement']`

- Planning note: Use this as a ligand-planning signal only; do not treat it as canonical assay resolution or packet completion.