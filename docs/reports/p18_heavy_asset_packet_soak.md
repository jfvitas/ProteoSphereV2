# P18 Heavy Asset Packet Soak

Date: 2026-03-22  
Task: `P18-I008`

## Verdict

The representative heavy-asset packet soak is **stable on the mirrored raw-asset slice** and keeps cache reuse and failures explicit.

Using real mirrored structure payloads for `P04637` and `P31749`, plus an explicit expected-miss probe for `P69905`, the structure-cache layer produced `5` unique cache entries from `6` heavy-asset selections: `4` reusable hits, `1` miss, and `0` checksum-drift cases.

## What Was Proven

- Re-selecting the same heavy experimental asset (`9R2Q.cif`) collapses onto a single reusable cache key instead of widening the packet silently.
- Real mirrored experimental (`RCSB/PDBe mmCIF`) and predicted (`AlphaFold DB CIF`) assets both normalize into reusable cache entries.
- Failure accounting stays explicit: the expected but absent `P69905` AlphaFold structure remains a cache `miss`, not a silent hit.
- After fixing the duplicate-checksum note bug, repeated checked assets are no longer mislabeled as “missing checksums.”

## Observed Slice

- Representative selections: `6`
- Unique cache entries: `5`
- Reusable hits: `4`
- Explicit misses: `1`
- Checksum drift cases: `0`
- Representative mirrored assets:
  - [9R2Q.cif](/D:/documents/ProteoSphereV2/data/raw/rcsb_pdbe/20260323T002625Z/P04637/9R2Q/9R2Q.cif)
  - [P04637 AlphaFold CIF](/D:/documents/ProteoSphereV2/data/raw/alphafold/20260323T002625Z/P04637/P04637.cif.cif)
  - [7NH5.cif](/D:/documents/ProteoSphereV2/data/raw/rcsb_pdbe/20260323T002625Z/P31749/7NH5/7NH5.cif)
  - [P31749 AlphaFold CIF](/D:/documents/ProteoSphereV2/data/raw/alphafold/20260323T002625Z/P31749/P31749.cif.cif)
- Explicit miss target:
  - [P69905 AlphaFold CIF expected path](/D:/documents/ProteoSphereV2/data/raw/alphafold/20260323T002625Z/P69905/P69905.cif.cif)

## What Remains Explicit

- This is a representative heavy-asset soak on the currently mirrored raw-asset slice, not a full 12-accession published packet soak.
- [data/packages](/D:/documents/ProteoSphereV2/data/packages) is still not the operative source for this lane, so the soak is anchored on the raw mirror rather than a completed package store.
- The unattended weeklong soak remains a separate open validation lane under [p22_weeklong_soak.md](/D:/documents/ProteoSphereV2/docs/reports/p22_weeklong_soak.md).

## Evidence Used

- [training_packet_audit.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/training_packet_audit.json)
- [structure_cache.py](/D:/documents/ProteoSphereV2/execution/assets/structure_cache.py)
- [test_structure_cache.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_structure_cache.py)

## Verification

- `python -m pytest tests\\unit\\execution\\test_structure_cache.py -q`
- `python -m ruff check execution\\assets\\structure_cache.py tests\\unit\\execution\\test_structure_cache.py`

## Integration Read

This is the right honesty boundary for the current queue: mirrored heavy structure assets can be reused deterministically within a representative packet slice, explicit misses remain visible, and the report does not overclaim a full package-store or full-cohort soak that has not yet been materialized.
