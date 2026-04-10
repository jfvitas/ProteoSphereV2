# P31 Local Source Facts

This report is grounded only in the refreshed local registry and local copy artifacts under `data/raw/local_registry_runs/LATEST.json` and `data/raw/local_registry/20260330T054522Z/`. The current registry is `29 present / 2 partial / 8 missing`, so the local corpus is already useful for a summary-library build, but it is not yet complete across all modalities.

## What Is Present

- Structure is the largest local lane by footprint: the registry records about `97,506` files across the structure category, with `structures_rcsb` at `19,354` files / `23.7 GB` and `raw_rcsb` at `39,318` files / `0.2 GB`. Concrete structure examples include `10JU`, `4HHB`, and `9LWP`.
- Extracted structure assets are already registered and cheap to join: `extracted_chains` and `extracted_entry` each carry `19,416` files, and `extracted_interfaces` adds another `19,416` files. These projections keep the build from having to reopen every raw coordinate bundle.
- Ligand data is broad and heavy: the registry records about `47,419` files across the protein-ligand lane, with `bindingdb` at `6,972` files / `3.0 GB`, `biolip` at `3` files / `1.2 GB`, `pdbbind_pl` partial at `2` files / `3.3 GB`, `pdbbind_pp` at `2,800` files / `3.2 GB`, `pdbbind_p_na` at `1,034` files / `0.9 GB`, and `pdbbind_na_l` at `574` files / `0.06 GB`.
- Extracted ligand assets are also present: `extracted_assays` and `extracted_bound_objects` each have `19,416` files, which gives the library an already-normalized layer for ligand summaries and bound-object lookups.
- Motif/pathway coverage is the useful local annotation spine: `interpro` is present at `1` file / `40.8 MB`, `pfam` at `2` files / `23.8 GB`, and `reactome` at `3` files / `117.6 MB`. Concrete join examples from the registry include `P69905` for `InterPro` and `Pfam`, and `P69905` plus `P09105` for `Reactome`.

## What Each Source Contributes

- `structures_rcsb`: authoritative experimental structure corpus; de-risks coordinate lookups and gives the library a stable structure identity layer.
- `raw_rcsb`: deposit-level traceability; de-risks reprocessing because the raw source is still available locally.
- `extracted_chains`: chain-level access paths; accelerates span and chain joins without reopening whole PDB/mmCIF payloads.
- `extracted_entry`: entry-level normalization; gives a compact summary layer for structure cards.
- `extracted_interfaces`: interface projections; useful for pair/assembly summaries and for reusing complex evidence in a smaller surface.
- `bindingdb`: assay and affinity evidence; strengthens ligand-target summaries with a broad local benchmark corpus.
- `biolip`: structure-bound ligand examples; useful as a concrete structure-to-ligand bridge.
- `pdbbind_pl`: protein-ligand benchmark set; currently partial, so it helps but should stay labeled as incomplete.
- `pdbbind_pp`: protein-protein benchmark set; useful for complex-adjacent evidence and similarity checks.
- `pdbbind_p_na` and `pdbbind_na_l`: nucleic-acid/ligand bridge cases; they widen ligand context and rescue edge cases.
- `extracted_assays`: assay projections; de-risks direct use of ligand evidence in the summary library.
- `extracted_bound_objects`: bound-object projections; helps attach ligand evidence to concrete structure instances.
- `interpro`: canonical domain/family/site backbone; accelerates accession-first joins and keeps domain labels stable.
- `pfam`: member-database domain view; useful supporting evidence under the InterPro spine.
- `reactome`: pathway context; gives functional routing and helps de-risk overfitting motifs to a single annotation family.

## How The Local Corpus Helps The Library Build

- It gives the summary library a real, accession-first backbone for structures, ligands, and pathway annotations before we finish the missing motif lanes.
- It lets us build with compact extracted assets instead of reopening every heavy raw file on every pass.
- It makes provenance auditable because the registry keeps present roots, missing roots, and manifest paths explicit.
- It reduces overclaiming: `InterPro`, `Pfam`, and `Reactome` can carry useful annotation now, while the missing motif sources remain visibly absent instead of being faked.

## Residual Gaps

- The motif category is still structurally missing in the registry: `PROSITE`, `ELM`, `Mega Motif Base`, and `Motivated Proteins` are registered as missing, so motif breadth is not yet complete.
- `pdbbind_pl` is partial, so the ligand lane still needs rescue work before we can treat it as closed.
- The sequence lane is still partial, so reviewed-only coverage remains narrower than the structure and ligand corpora.

