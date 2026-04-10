# P13 Remaining Corpus Gaps

Date: 2026-03-22

This audit separates what the local bio-agent-lab mirrors already cover from the online corpora that still need to stay procurement targets for protein, protein-protein, and protein-ligand coverage.

## Local Mirrors Already In Place

The local tree is strong on reusable mirrors and derivatives:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources` contains local corpora for `uniprot`, `alphafold`, `reactome`, `bindingdb`, `interpro`, `pfam`, `cath`, `scope`, `biolip`, `pdbbind`, and `chembl`.
- `C:\Users\jfvit\Documents\bio-agent-lab\data` adds large derivative/local mirror surfaces, especially `raw` (~46k files), `processed` (~39k), `structures` (~19k), `extracted` (~116k), and `custom_training_sets` (7 snapshot folders).
- The assay mirror under `data/extracted/assays` and the training-set exports under `data/custom_training_sets` are useful local reuse assets, but they are not new procurement targets.

## What The Local Inventory Still Does Not Replace

The local mirrors do **not** fully replace the missing online evidence layers for interaction breadth, curated interaction depth, disorder/function coverage, and experimental bridge context.

## Online Procurement Targets, Ranked

1. `IntAct`
   - Highest priority.
   - Best missing curated protein-protein evidence layer.
   - Needed because the local mirrors do not provide a live or local substitute for curated interaction provenance.

2. `BioGRID`
   - Highest priority.
   - Broadest missing protein-protein interaction breadth.
   - Needed to widen the PPI network surface beyond the curated pair lanes already represented locally.

3. `RCSB/PDBe structure bridge`
   - High priority.
   - Not a local corpus replacement; it is the missing live bridge for accession-to-chain and complex provenance.
   - Needed to keep protein-ligand and protein-protein joins honest when local corpora like `BioLiP` and `PDBbind` need structural grounding.

4. `STRING`
   - Medium-high priority.
   - Interaction-context enrichment rather than curated evidence.
   - Useful after IntAct/BioGRID, but less precise and more graph-like than the curated PPI sources.

5. `Evolutionary / MSA`
   - Medium priority.
   - Protein coverage depth gap rather than interaction gap.
   - Still important for sequence-family context because the local mirrors do not provide an equivalent online-sourced evolutionary lane.

6. `DisProt`
   - Medium priority.
   - Motif-adjacent / disorder-function evidence gap.
   - Worth keeping online because InterPro and Pfam are already local, but they do not substitute for disorder-specific evidence.

7. `EMDB`
   - Medium priority.
   - Experimental structure-depth gap.
   - Useful for low-resolution or cryo-EM-heavy protein contexts when the local structure mirrors are not enough.

## Protein-Ligand Reality Check

Protein-ligand coverage is **better locally than online-gap-heavy**:

- Local mirrors already cover `BindingDB`, `ChEMBL`, `BioLiP`, and `PDBbind`.
- The remaining online need is mostly the RCSB/PDBe bridge that keeps chain-level provenance and mixed-role complexes honest.
- There is no strong case for treating protein-ligand as the main procurement gap right now unless a new compound-target source is explicitly added.

## Bottom Line

The next online procurement wave should stay focused on missing interaction and evidence-depth sources, not on duplicating the local mirrors.

Recommended order:

`IntAct` -> `BioGRID` -> `RCSB/PDBe bridge` -> `STRING` -> `Evolutionary / MSA` -> `DisProt` -> `EMDB`

That ordering is the most honest fit for the current local inventory and the remaining protein, PPI, and protein-ligand gaps.
