# P32 Packet Rescue Priority

The current deficit dashboard is small but clear: five packets are partial, with five ligand gaps, one PPI gap, and one structure gap. The fastest rescue is not to keep probing the same low-yield ligand snapshot first. It is to use the current packet structure where it already exists, and only pivot to direct ligand databases when the local evidence is actually promising.

Evidence used:
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [canonical_store.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
- [q9ucm0_acquisition_proof.json](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_proof.json)
- [local_chembl_rescue_brief.json](/D:/documents/ProteoSphereV2/artifacts/status/local_chembl_rescue_brief.json)

## Ranked Rescue

1. `P00387` first, via `ChEMBL`.
   The current rescue brief already says `CHEMBL2146`, 93 activities, 93 assays, and `can_promote=false`. That is the strongest accession-specific ligand signal in the slice, so it should go first.

2. `P09105`, `Q2TAC2`, and `Q9NZD4` next, via structure-linked ligand extraction.
   All three already have sequence, structure, and PPI in the current packet, but the BindingDB accession probes are null. The best next move is to mine the existing structure with `extracted_bound_objects`, then fall back to `BioLiP`, then `PDBBind_PL`.

3. `Q9UCM0` structure first, then PPI, then ligand.
   This is the only true structure deficit in the slice. The acquisition proof says the local registry only has UniProt, BindingDB is empty, IntAct is alias-only, and RCSB/PDBe has no best-structure hit. That makes `AlphaFold DB` and `RCSB/PDBe` the first two rescue routes, with `IntAct` and then `BioGRID`/`STRING` as the PPI wave, followed by ligand recovery once structure exists.

## Why BindingDB Is Not First

The current BindingDB snapshots are not rescue-ready for this slice.

- `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4` all have local BindingDB files, but the accession-level responses are null.
- `Q9UCM0` is even weaker: the current proof records `hit_count = 0`.

That means direct BindingDB probing is a fallback here, not a first choice. The better move is to reuse the structures we already have and extract ligands from those structures first.

## Accessions

### P00387

- Canonical anchor is present in the current canonical store as `NADH-cytochrome b5 reductase 3` with a 301 aa sequence.
- The packet is partial only because `ligand` is missing.
- Best route: `ChEMBL` rescue first, then `extracted_bound_objects`, then `BioLiP`, then `PDBBind_PL`.

### P09105

- Canonical anchor is present as `Hemoglobin subunit theta-1` with a 142 aa sequence.
- The packet is partial only because `ligand` is missing.
- Best route: `extracted_bound_objects`, then `BioLiP`, then `PDBBind_PL`, then direct ligand databases as fallback.

### Q2TAC2

- Canonical anchor is present as `Coiled-coil domain-containing protein 57` with a 915 aa sequence.
- The packet is partial only because `ligand` is missing.
- Best route: `extracted_bound_objects`, then `BioLiP`, then `PDBBind_PL`, then direct ligand databases as fallback.

### Q9NZD4

- Canonical anchor is present as `Alpha-hemoglobin-stabilizing protein` with a 102 aa sequence.
- The packet is partial only because `ligand` is missing.
- Best route: `extracted_bound_objects`, then `BioLiP`, then `PDBBind_PL`, then direct ligand databases as fallback.

### Q9UCM0

- There is no current canonical protein record for this accession in the canonical store.
- The packet is partial with `structure`, `ligand`, and `ppi` all missing.
- Best route: `AlphaFold DB`, then `RCSB/PDBe`, then structure-linked ligand extraction, then `IntAct`, then `BioGRID` and `STRING` if the alias-only state persists.

## Bottom Line

The rescue order for this slice is:

1. `P00387` ChEMBL rescue.
2. `P09105`, `Q2TAC2`, and `Q9NZD4` structure-linked ligand extraction.
3. `Q9UCM0` structure acquisition, then PPI acquisition, then ligand backfill.

That order clears the most deficits with the highest probability of actually producing a fused winner, while avoiding wasted direct probes against null BindingDB snapshots.

