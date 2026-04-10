# P82 Bundle Iteration Following Ligand Validation

This is a report-only ranking of the next safest bundle-facing additions or non-additions after the new `P00387` ligand validation preview.

## Current Bundle State

- The current `proteosphere-lite` manifest is still aligned with live validation.
- `ligand_identity_pilot` is already included.
- `ligands`, `ligand_similarity_signatures`, and `interactions` are still excluded.

## Ranked Follow-Ons

1. `ligands`
   - This is still the next safest bundle-facing addition candidate.
   - `P00387` now has a grounded validation preview and the live operator surface still treats ligand work as the first next action.
   - It is still excluded because the manifest shows zero ligand rows.

2. `Q9NZD4`
   - This should stay operator-only first.
   - The pilot now says it is rescuable now, with a ready local structure bridge at `1Y01`.
   - Its truthful next stage is bridge ingestion, not bundle-family expansion.

3. `ligand_similarity_signatures`
   - This is a derivative non-addition.
   - It only becomes meaningful after ligands exist.
   - There is no live operator surface saying it is ready today.

4. `interactions`
   - This remains a deferred non-addition.
   - The manifest still shows zero records.
   - The current surfaces do not provide a first accession or row-level anchor.

## Decision Boundary

- `Q9NZD4` stays operator-only first.
- Its next truthful stage is to ingest the local structure bridge for `Q9NZD4` using `1Y01`.
- This is not a bundle family addition.

## Bottom Line

Ligands remain the next safest bundle-facing addition, but the `Q9NZD4` bridge-rescue path should stay separate and operator-only.
