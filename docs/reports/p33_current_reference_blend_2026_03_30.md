# P33 Current Reference Blend

Generated: 2026-03-30 17:02 -05:00

## What changed

The important state transition during this automation wave is that the authoritative local registry was refreshed at `20260330T215002Z`. That refresh removes the main uncertainty that had dominated the earlier `p30` and `p32` notes:

- `biogrid` is now `present`
- `intact` is now `present`
- `prosite` is now `present`
- `chebi`, `complex_portal`, `rnacentral`, `sifts`, and `pdb_chemical_component_dictionary` are now clearly present in the authoritative snapshot
- `elm` is now `partial`
- `sabio_rk` is now `partial`

This means the old "promote local copies first" queue is no longer the real bottleneck. The current bottleneck is keeping the blend policy and downstream summary artifacts synchronized with the refreshed registry.

## Best current local reference

The strongest current ProteoSphere reference should now be treated as:

- Protein identity and experimental structure:
  - `UniProt` -> canonical protein spine
  - `SIFTS` -> accession-to-structure bridge
  - `RCSB/PDBe` -> experimental structure authority
  - `AlphaFold DB` -> separate predicted companion lane
- Ligand identity and assay context:
  - `wwPDB Chemical Component Dictionary` + `ChEBI` -> chemical identity authority
  - `ChEMBL` + `BindingDB` -> assay-backed ligand evidence
  - `PDBBind` + `BioLiP` -> support context only
- Annotation and pathway context:
  - `Reactome` -> pathway and reaction authority
  - `InterPro` + `Pfam` -> first motif/domain spine
  - `PROSITE` -> now merge-ready motif authority layer
  - `ELM` -> partial motif priors and motif-domain partner context
- Curated interaction context:
  - `IntAct` + `BioGRID` -> canonical curated PPI lanes
  - `Complex Portal` -> curated complex context, not binary PPI truth
- Query-scoped kinetics enrichment:
  - `SABIO-RK` -> partial accession-anchored kinetics context only

## Guardrails that still matter

- `STRING` is still missing in the authoritative registry and must stay out of canonical PPI truth.
- `mega_motif_base` and `motivated_proteins` are still missing and should not be blended.
- The repo-seed `BindingDB` placeholder ZIP stubs are still non-authoritative, but the refreshed registry now also sees a real external BindingDB bulk dump plus per-PDB cache payloads, so the lane itself is no longer blocked.
- The repo-seed AlphaFold partial tar parts are still non-authoritative, but the refreshed registry now sees the external full AlphaFold mirror, so predicted-structure coverage can be treated as present as long as it remains separate from experimental structure truth.

## Practical merge guidance

- Stop describing `BioGRID`, `IntAct`, `PROSITE`, and `ELM` as simply "queued".
- Attach `ELM` only as motif-class and motif-domain interaction context until a fuller mirror exists.
- Attach `SABIO-RK` only as query-scoped kinetics enrichment. Do not pretend it is a bulk kinetics authority.
- Keep the conservative precedence order intact:
  - `UniProt` + `SIFTS` + `RCSB/PDBe`
  - `CCD` + `ChEBI` + `ChEMBL` + `BindingDB`
  - `Reactome` + `InterPro` + `Pfam` + `PROSITE` + partial `ELM`
  - `IntAct` + `BioGRID`

## Best next move

The next useful automation step is not another seed-promotion pass. It is to update the downstream summary-library and source-coverage artifacts so they reflect the refreshed registry state and the new partial-lane semantics for `ELM` and `SABIO-RK`.
