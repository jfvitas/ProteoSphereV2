# Complex Portal / AlphaFold Gap Review

- Generated at: `2026-03-30T22:55:00-05:00`
- Scope: procurement metadata only
- Manifest action: none

## AlphaFold DB

- The AlphaFold seed mirror is still incomplete.
- In `data/raw/protein_data_scope_seed/alphafold_db`, both tarballs are still `.part` files and both are zero bytes:
  - `swissprot_cif_v6.tar.part`
  - `swissprot_pdb_v6.tar.part`
- That means the lane is still downloading or stalled, not ready for promotion.
- The manifest does not need correction; the upstream AlphaFold URLs are still the right ones.

## Complex Portal

- Complex Portal is different from AlphaFold: the complete truth-bearing files are already present, but the two predicted ZIPs in the seed mirror are only empty ZIP placeholders.
- The files are:
  - `complexesMIF25_predicted.zip`
  - `complexesMIF30_predicted.zip`
- Both are 22 bytes and begin with the empty ZIP end-of-central-directory signature (`PK 05 06`), which means they contain no payload entries.
- That is not a completed download. It should be classified as a placeholder artifact, not promoted mirror content.

## What This Means

- No manifest correction is needed for either source.
- AlphaFold DB should stay in the `still_downloading` bucket until a real tar archive lands.
- Complex Portal predicted ZIPs should stay quarantined as empty placeholders.
- The promoted Complex Portal truth set remains `released_complexes.txt` plus the human `complextab/*.tsv` files.

## Next Best Step

- Resume or rerun the AlphaFold tar acquisition if we want to close the lane.
- Keep the Complex Portal predicted ZIPs out of the usable mirror until a non-empty archive is available.
