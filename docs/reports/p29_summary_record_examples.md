# P29 Summary Record Examples

This artifact shows the operator-facing shape we want for an integrated summary-library card: one protein-centered record with explicit structure, ligand, pathway, interaction, motif, and provenance sections, plus a second record that stays honestly partial when the local registry cannot support more.

The examples are grounded in the current repo artifacts and the refreshed local registry:

- [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py)
- [artifacts/status/selected_cohort_materialization.current.json](/D:/documents/ProteoSphereV2/artifacts/status/selected_cohort_materialization.current.json)
- [artifacts/status/local_bridge_ligand_payloads.real.json](/D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json)
- [artifacts/status/reactome_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/reactome_local_summary_library.json)
- [artifacts/status/intact_local_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/intact_local_summary_library.json)
- [data/raw/local_registry/20260330T054522Z/import_manifest.json](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260330T054522Z/import_manifest.json)
- [docs/reports/q9ucm0_structure_gap_local_investigation_2026_03_23.md](/D:/documents/ProteoSphereV2/docs/reports/q9ucm0_structure_gap_local_investigation_2026_03_23.md)

## Strong Case: `protein:P69905`

`P69905` is the best strong example because the local packet already has sequence, structure, ligand, and PPI payloads, and the registry join index also points at Reactome plus multiple motif lanes. The record should still be honest about what is materialized now versus what remains index-only.

What should be materialized:

- Protein spine: accession, organism, aliases, and compact sequence metadata.
- Structure: the packet-level structure artifact is present and should be exposed as a compact structure section.
- Ligand: the real bridge payload resolves `P69905 -> 1A9W -> CMO`.
- Pathway: Reactome pathway references are already available in the local summary library.
- Interaction: the packet-level `ppi` artifact exists, so the card can surface an interaction lane even if a native pair record is not expanded here.
- Provenance: every section should point back to the packet, the local registry, and the source summaries that created the join.

What should stay indexed or lazy:

- Motif: the join index points at motif-capable sources for `P69905`, but the refreshed local registry still marks the motif lane family as missing, so motif rows should remain index-only or deferred.
- Heavy payloads: mmCIF, full assay tables, full MITAB, and full motif tables should stay lazy.

Recommended shape:

```json
{
  "record_type": "protein",
  "summary_id": "protein:P69905",
  "join_status": "partial",
  "protein": {
    "accession": "P69905",
    "protein_name": "Hemoglobin subunit alpha",
    "organism_name": "Homo sapiens",
    "aliases": ["P69905", "HBA_HUMAN"],
    "sequence_length": 142
  },
  "structure": {
    "join_status": "joined",
    "source_ref": "structure:P69905",
    "materialization_state": "materialized",
    "notes": ["packet artifact present", "structure payload should stay compact"]
  },
  "ligand": {
    "join_status": "joined",
    "source_ref": "ligand:P69905",
    "bridge": "1A9W:CMO",
    "materialization_state": "materialized"
  },
  "pathway": {
    "join_status": "joined",
    "source_name": "Reactome",
    "materialization_state": "materialized"
  },
  "interaction": {
    "join_status": "joined",
    "source_ref": "ppi:P69905",
    "materialization_state": "materialized",
    "notes": ["packet-level PPI summary is present"]
  },
  "motif": {
    "join_status": "deferred",
    "materialization_state": "indexed_only",
    "blocked_by": ["motif source roots are still missing in the refreshed local registry"]
  },
  "provenance": {
    "source_manifest_id": "bio-agent-lab-import-manifest:v1",
    "packet_manifest": "packet-P69905",
    "materialization_state": "materialized"
  }
}
```

## Weak / Partial Case: `protein:Q9UCM0`

`Q9UCM0` is the right weak example because the selected packet only has sequence, the local structure-gap investigation already proved there is no trustworthy local recovery path, and the refreshed import manifest only binds it to UniProt.

What should be materialized:

- Protein spine: accession and sequence-only identity.
- Provenance: the UniProt boundary and the packet boundary should both be visible.

What should stay blocked:

- Structure: no local AlphaFold or RCSB recovery path.
- Ligand: no local ligand lane.
- Interaction: no local PPI lane.
- Motif: no local motif lane.
- Pathway: no local pathway lane.

Recommended shape:

```json
{
  "record_type": "protein",
  "summary_id": "protein:Q9UCM0",
  "join_status": "partial",
  "protein": {
    "accession": "Q9UCM0",
    "organism_name": "Homo sapiens",
    "sequence_length": 77,
    "materialization_state": "materialized"
  },
  "structure": {
    "join_status": "blocked",
    "materialization_state": "lazy",
    "blocked_by": ["no accession-specific local structure payload"]
  },
  "ligand": {
    "join_status": "blocked",
    "materialization_state": "lazy",
    "blocked_by": ["no accession-specific local ligand payload"]
  },
  "pathway": {
    "join_status": "blocked",
    "materialization_state": "lazy",
    "blocked_by": ["no local pathway join"]
  },
  "interaction": {
    "join_status": "blocked",
    "materialization_state": "lazy",
    "blocked_by": ["no local interaction join"]
  },
  "motif": {
    "join_status": "blocked",
    "materialization_state": "indexed_only",
    "blocked_by": ["motif lane is missing in the refreshed local registry"]
  },
  "provenance": {
    "source_manifest_id": "bio-agent-lab-import-manifest:v1",
    "packet_manifest": "packet-Q9UCM0",
    "materialization_state": "materialized"
  }
}
```

## Reading The Example Set

The integrated card is easiest to reason about if the protein spine stays materialized, the present source lanes stay explicit, and every absent lane is labeled as blocked or deferred rather than quietly omitted.

- Materialize the protein spine and provenance pointers.
- Materialize structure, ligand, pathway, and interaction lanes only when the local registry already has a truthful payload.
- Keep motif lanes index-only until the motif sources are actually present locally.
- Keep heavy raw payloads lazy even when the compact summary is materialized.

## Next Command

If we want to sanity-check the artifact shape after any follow-up edits, the next automatable command is:

```powershell
python -c "import json; json.load(open(r'artifacts/status/p29_summary_record_examples.json', encoding='utf-8')); print('ok')"
```
