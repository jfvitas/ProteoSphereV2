# P32 Local Copy Priority

This plan compares the live `bio-agent-lab` trees in `C:\Users\jfvit\Documents\bio-agent-lab\data` and `C:\Users\jfvit\Documents\bio-agent-lab\data_sources` against the repo-local mirror in `D:\documents\ProteoSphereV2\data\raw\local_copies`. The current local copy set already covers a lot of the core build spine, including `alphafold_db`, `alphafold_db_v2`, `bindingdb`, `biolip`, `cath`, `chembl`, `interpro`, `pfam`, `reactome`, `scope`, `uniprot`, `raw_rcsb`, `structures_rcsb`, `extracted_assays`, `extracted_bound_objects`, `extracted_interfaces`, and `pdbbind_pp`.

The uncopied pieces that matter most are the ones that either anchor reproducibility or unlock cheap joinable projections. That pushes small release/provenance slices ahead of the largest archives, even when the archives are valuable.

## Highest-Value Uncopied Slices

1. `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1`
   - `17` files, about `2.3 MB`
   - Why it matters: this is the frozen release/cohort artifact set. It anchors `custom_training_set`, `master_pdb_repository`, and the associated release manifests, so mirroring it de-risks reproducibility before we expand more data-heavy lanes.

2. `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\provenance`
   - `19,416` files, about `20.9 MB`
   - Why it matters: this is the cheapest way to keep source lineage attached to the extracted structure lane. It gives per-entry provenance JSON for the same ids already used in the extracted structure copies.

3. `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\chains`
   - `19,416` files, about `107.3 MB`
   - Why it matters: chain-level structure projections are a high-leverage join surface for summary records, structure cards, and residue-span lookups.

4. `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry`
   - `19,416` files, about `97.0 MB`
   - Why it matters: entry-level projections are the compact structure summaries we can reuse directly without reopening the raw RCSB payloads.

5. `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\skempi\skempi_v2.csv`
   - `1` file, about `1.6 MB`
   - Why it matters: this is a unique protein-protein mutation/affinity benchmark slice that is not already mirrored or registered locally. It adds a signal lane that complements the PDBbind and interaction-network work.

6. `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-L.tar.gz`
   - `3.34 GB`
   - Why it matters: this is the biggest missing PDBbind slice and the most valuable raw archive still absent from `local_copies`. It would expand the ligand/complex lane materially.

7. `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-NA.tar.gz`
   - `154 MB`
   - Why it matters: this adds the protein/nucleic-acid bridge slice, which is useful for edge-case complex modeling and broader binding coverage.

8. `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\NA-L.tar.gz`
   - `9.4 MB`
   - Why it matters: small, but it closes out the nucleic-acid/ligand edge cases and is cheap to mirror.

9. `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\index`
   - `4` index files plus README, about `0.5 MB` for the archive wrapper
   - Why it matters: tiny metadata, but it makes the PDBbind slices easier to join and interpret cleanly.

## What Is Already Covered

- `alphafold` is already mirrored under `alphafold_db` and `alphafold_db_v2`, so it is not a current copy gap.
- `bindingdb`, `biolip`, `chembl`, `cath`, `interpro`, `pfam`, `reactome`, `scope`, and `uniprot` are already represented in `local_copies`.
- `raw_rcsb`, `structures_rcsb`, `extracted_assays`, `extracted_bound_objects`, and `extracted_interfaces` are already mirrored, so the main structure and assay joins are not blocked by missing local copies.
- `pdbbind_pp` is already mirrored, so the missing PDBbind work is focused on the ligand and nucleic-acid slices rather than the protein-protein archive.

## Why This Order

- Start with `releases/test_v1` and `extracted/provenance` because they are small, cheap, and improve reproducibility immediately.
- Mirror `extracted/chains` and `extracted/entry` next because they unlock summary-library joins without forcing heavy source re-reads.
- Pull in `skempi` before the large PDBbind archives because it adds a distinct benchmark signal and is nearly free to copy.
- Mirror `P-L.tar.gz`, `P-NA.tar.gz`, `NA-L.tar.gz`, and the `index` bundle after that because they are the remaining high-value PDBbind slices not already covered by `pdbbind_pp`.

## Build Impact

- These copies reduce the need to reopen raw structure payloads during summary generation.
- They preserve provenance at the same time as the extracted structure rows, which makes the library easier to audit.
- They add a small but important benchmark slice (`skempi`) that broadens mutation and affinity coverage.
- They keep the mirror honest by prioritizing reproducibility artifacts before larger bulk archives.

