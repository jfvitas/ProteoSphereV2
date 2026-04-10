# P32 Upstream Release Watch

Date: 2026-03-30  
Artifact: `p32_upstream_release_watch`

This run did not execute new downloads. Shell-side `python`, `py`, `uv`, and remote fetches are still unavailable here, so the useful work was to reconcile the current official source signals against what is already mirrored under `data/raw/protein_data_scope_seed/`.

## What Changed In This Run

- I treated [p31_online_source_facts.json](/D:/documents/ProteoSphereV2/artifacts/status/p31_online_source_facts.json) as a stale imported snapshot because it still points at `C:\Users\jfvit\Documents\bio-agent-lab` roots instead of the current ProteoSphere workspace.
- I measured the repo-seed mirrors again and used those counts as the real local baseline for this run.
- I reconciled those local mirrors with current official source signals so the next download/import wave can prioritize the highest-yield work.

## Local Mirrors Worth Promoting

- `BioGRID` is already materially present in the repo seed: `5` files and `631,746,404` bytes under [data/raw/protein_data_scope_seed/biogrid](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/biogrid).
- `IntAct` is already materially present: `3` files and `1,384,405,401` bytes under [data/raw/protein_data_scope_seed/intact](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/intact).
- `PROSITE` is already materially present: `4` files and `51,459,499` bytes under [data/raw/protein_data_scope_seed/prosite](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/prosite).
- `ChEBI`, `SIFTS`, and the PDB Chemical Component Dictionary are also present locally and should surface once the registry import is refreshed.

## Lanes That Still Stay Gated

- `bindingdb` remains quarantined because the repo-seed files are still placeholder-scale stubs; the quarantine evidence remains in [p30_seed_placeholder_quarantine.json](/D:/documents/ProteoSphereV2/artifacts/status/p30_seed_placeholder_quarantine.json).
- `string` stays gated because the repo seed still contains metadata only.
- repo-seed `alphafold_db` stays gated because it is still only a partial archive.

## Current Official Signals

- `ChEMBL`: EMBL-EBI's 2025 news index says `ChEMBL 36 is live` on 2025-10-15. That matches the local `chembl_36` mirror, so this lane is current enough to keep active.
- `InterPro`: EMBL-EBI's protein news tag shows `InterPro 105.0: AI for protein classification` on 2025-04-28. InterPro remains a stable active annotation lane.
- `ChEBI`: EMBL-EBI's 2025 news index shows `ChEBI 2.0 launches` on 2025-10-20. Separately, the legacy ChEBI Entity of the Month page shows release number `244` as the latest indexed release number I found. Operationally, this means ChEBI remains authoritative, but downloader assumptions may need adjustment around the 2.0 transition.
- `Reactome`: the download page states that Zenodo download directories are created for every release `quarterly`, and the Reactome release tag page currently references `Version 95`. That makes Reactome refresh useful but not urgent compared with fixing the stale registry import.
- `AlphaFold DB`: EMBL-EBI's AI news tag shows an AlphaFold Database update on 2026-02-17, and the AlphaFold download page still exposes Swiss-Prot and selected proteome bulk downloads. Upstream is alive; the local repo-seed copy is the problem.
- `STRING`: STRING's API help still documents a `current version` endpoint and examples pinned to `version-12-0.string-db.org`. Upstream remains active, but the local seed still lacks a real graph payload.
- `BioGRID`: the BioGRID archive page still tells users to prefer the `CURRENT RELEASE` directory for the most up-to-date dataset. Since the repo seed already contains real BioGRID archives, import/reconciliation is higher value than another speculative re-download.
- `IntAct`: the latest indexed EMBL-EBI release notice I found is `Latest release of IntAct and Complex Portal` from 2023-07-13. That is enough to justify treating the local IntAct seed as import-ready now, while deferring a newer remote probe until execution returns.
- `PROSITE`: current PROSITE entry pages are computed against `UniProtKB/Swiss-Prot release 2026_01`. That keeps PROSITE aligned with the reviewed-sequence spine.

## Best Next Move

1. Regenerate [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json) from the current workspace.
1. Let that refresh flip `biogrid`, `intact`, and `prosite` from stale missing to present, and surface `chebi`, `sifts`, and `pdb_chemical_component_dictionary` in the imported registry snapshot.
1. Keep the canonical blend conservative:
   `UniProt + SIFTS + RCSB` for identity and structure, `CCD + ChEBI + ChEMBL` for ligand authority, `Reactome + InterPro + PROSITE` for annotation, and `IntAct + BioGRID + Complex Portal` for curated interaction once the registry is refreshed.
1. Continue excluding repo-seed `bindingdb`, `string`, and `alphafold_db` from authoritative promotion until real payloads replace the current placeholders.

## Sources

- [EMBL-EBI 2025 news index](https://www.ebi.ac.uk/about/news/2025)
- [AlphaFold DB download page](https://alphafold.ebi.ac.uk/download)
- [EMBL-EBI AI news tag](https://www.ebi.ac.uk/about/news/tag/ai)
- [STRING API help](https://string-db.org/help/api/)
- [BioGRID archive page](https://downloads.thebiogrid.org/BioGRID/Release-Archive/BIOGRID-3.5.177/)
- [Reactome download page](https://reactome.org/download-data)
- [Reactome release tag](https://reactome.org/tag/release)
- [PDBe SIFTS API page](https://www.ebi.ac.uk/pdbe/api/sifts.html)
- [PROSITE entry example with current Swiss-Prot release context](https://prosite.expasy.org/PS01289)
- [ChEBI Entity of the Month page](https://www.ebi.ac.uk/chebi/entityMonthForward.do)
