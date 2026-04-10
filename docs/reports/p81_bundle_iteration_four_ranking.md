# P81 Bundle Iteration Four Ranking

This is a report-only ranking of the next safest bundle families after the currently included `proteosphere-lite` set.

## Current Bundle State

- The current manifest is aligned with live validation.
- The included families already cover the core protein, variant, structure, dictionary, provenance, and helper surfaces.
- The excluded families are `ligands`, `interactions`, `ligand_similarity_signatures`, and `interaction_similarity_signatures`.

## Ranked Next Families

1. `ligands`
   - This is the next safest candidate.
   - The live operator surfaces already point here: `ligand_identity_pilot_preview` names `P00387` as the lead anchor and `Q9NZD4` as a bridge-rescue candidate, and `operator_next_actions_preview` ranks ligand work first.
   - The bundle already includes `ligand_support_readiness`, so this is not a cold start.
   - It is still not included because the manifest says ligands are declared but not yet materialized.

2. `ligand_similarity_signatures`
   - This is a derivative family after ligands.
   - It becomes meaningful only after ligand rows exist.
   - There is no live operator surface saying it is ready today.

3. `interactions`
   - This remains a future expansion candidate.
   - The manifest still shows zero records.
   - The current operator surfaces do not provide a concrete first accession or row-level anchor for it.

4. `interaction_similarity_signatures`
   - This is the most deferred family.
   - It only becomes useful after interactions exist.
   - There is no supporting live preview for it yet.

## Bottom Line

The next safest bundle family is `ligands`. Everything after that is either derivative or still unsupported, so the ranking should stay narrow until ligand materialization becomes real.
