# Local / Online Join Expansion

Date: 2026-03-22

This report ranks the highest-value join-expansion opportunities across protein, protein-pair, and ligand lanes using:

- [P13 remaining corpus gaps](D:/documents/ProteoSphereV2/docs/reports/p13_remaining_corpus_gaps.md)
- [Local corpus fingerprint validation](D:/documents/ProteoSphereV2/docs/reports/local_corpus_fingerprint_validation.md)
- [Local source reuse strategy](D:/documents/ProteoSphereV2/docs/reports/local_source_reuse_strategy.md)
- [Training packet audit](D:/documents/ProteoSphereV2/docs/reports/training_packet_audit.md)
- [P13-A006 prep note](D:/documents/ProteoSphereV2/artifacts/reviews/p13_a006_local_online_join_expansion_prep_2026_03_22.md)
- [P13-I005 live probe matrix](D:/documents/ProteoSphereV2/artifacts/status/p13_missing_source_probe_matrix.json)

## Executive Rank

1. Protein lane: accession-first depth expansion
2. Pair lane: curated PPI breadth expansion
3. Ligand lane: local bridge consolidation and selective gap fill

That ordering is the most honest fit for the current evidence surface. Local mirrors already cover much of the protein and ligand spine; the main remaining join value is in PPI breadth and in preserving the exact bridge semantics that keep protein, pair, and ligand rows from collapsing into one another.

## 1) Protein Lane

### Highest-value joins

- `UniProt` remains the canonical identity spine.
- `AlphaFold DB`, `Reactome`, `InterPro`, `Pfam`, and `DisProt` are the best complementary depth lanes.
- `RCSB / PDBe` is the key structural bridge when a protein needs accession-to-structure grounding.

### Why this ranks first

- The local inventory already has strong mirrors for sequence, structure, pathway, and annotation depth.
- The live probe matrix adds useful structure to the depth ranking: `RCSB / PDBe` returned a structured bridge response, while `DisProt` is live but the `P69905` probe came back empty, so that lane should be treated as reachability-confirmed but accession-empty for this exact anchor.
- `DisProt` is still high-value because it adds curated disorder/function depth that the local protein spine otherwise lacks.

### Next actions

- Use accession-first joins for protein expansion and keep all complements attached to the same canonical accession.
- Treat `DisProt` as a real depth lane, but keep empty-target probes explicit instead of inferring absence as negative evidence.
- Preserve `RCSB / PDBe` as the structural bridge for accession-to-chain grounding rather than as a substitute identity source.

### Blockers

- `P13-I005` still has to answer which live sources are join-key rich versus merely reachable.
- A protein row should not be called deep just because a local mirror exists; the row still needs a real complementary lane.

## 2) Pair Lane

### Highest-value joins

- `IntAct` is the strongest curated PPI expansion source.
- `BioGRID` is the next strongest curated PPI breadth source.
- `STRING` is useful, but it is lower-priority context rather than canonical curated PPI evidence.
- Local `PDBbind`, `BioLiP`, and processed RCSB pair surfaces are valuable complements for chain/interface lineage, not substitutes for curated interaction evidence.

### Why this ranks second

- The current local inventory already covers structural and assay complements, but it does not replace curated interaction breadth.
- The live probe matrix gave `IntAct` a structured response and `BioGRID` a reachable download surface. That makes them the highest-value missing pair lanes because they can add direct interaction provenance rather than just neighborhood context.
- `STRING` also returned a structured response, but it is explicitly a breadth/context layer, not the first lane to rank for canonical pair expansion.

### Next actions

- Prioritize `IntAct` and `BioGRID` for pair expansion, and preserve interaction accession / publication provenance / binary-vs-complex lineage.
- Keep `STRING` as a lower-priority expansion candidate until curated PPI sources are pinned.
- When local structural pair corpora are used, keep chain and interface lineage explicit and do not flatten them into generic pair claims.

### Blockers

- `BioGRID` is reachable, but the probe matrix only confirmed the download portal, not a pinned TAB3/MITAB row export.
- Pair rows backed only by probe or summary evidence should stay separated from direct curated PPI rows.

## 3) Ligand Lane

### Highest-value joins

- Local `BindingDB`, `ChEMBL`, `BioLiP`, `PDBbind`, and processed RCSB / PDBe bridge records are already the strongest ligand-side reuse assets.
- Protein-ligand joins should prefer protein accession plus stable ligand identity, using InChIKey first, then stable ligand id, then source-specific ligand id.

### Why this ranks third

- The local tree is already strong on ligand-centric corpora, so the biggest value is in consistent bridge semantics rather than new procurement.
- The live probe matrix did not surface a stronger new ligand source than the local mirrors already provide.
- `SABIO-RK` is reachable but the chosen accession anchor returned no data, which means it is an assay gap-fill lane, not a near-term join-expansion win.

### Next actions

- Keep ligand joins accession-first on the protein side and stable-identity-first on the ligand side.
- Treat SMILES as a fallback matching aid, not as the primary canonical key.
- Preserve mixed-role ligands, peptides, ions, and artifacts as explicit unresolved or separate roles instead of collapsing them into one ligand spine.

### Blockers

- A ligand row should not be upgraded just because a local mirror exists.
- `SABIO-RK` remains a conditional follow-on lane until a better accession anchor or narrower acquisition rule is chosen.

## What `P13-I005` Clarified For A006

The live probe matrix was enough to separate reachable surfaces from true join-value surfaces:

- `IntAct` returned a structured response, so it is a real curated PPI candidate.
- `BioGRID` is reachable on its download portal, but still needs a release-pinned row export.
- `STRING` is reachable and structured, but it should remain breadth/context rather than the first curated PPI lane.
- `RCSB / PDBe` returned a structured bridge response, which is the key structural glue for accession-to-chain joins.
- `DisProt` is live, but the `P69905` accession probe returned no rows, so that exact anchor should stay explicit as empty.
- `EMDB` is structured and useful as structure-depth support, but not as a primary protein source.

That means A006 should rank sources by **join value**, not by reachability alone.

## Recommended Next Steps

1. Pin and ingest curated PPI evidence from `IntAct`.
2. Fetch a release-pinned `BioGRID` interaction archive and ingest TAB3 or MITAB rows.
3. Keep `STRING` as a lower-priority breadth/context layer.
4. Use `RCSB / PDBe` as the structural bridge for accession-to-chain grounding.
5. Expand `DisProt` only on populated accessions, and keep empty-target probes explicit.
6. Keep ligand expansion focused on local reuse and bridge correctness, not new procurement.

## Bottom Line

- Protein expansion should focus on accession-first depth.
- Pair expansion should focus on curated PPI breadth.
- Ligand expansion should focus on stable bridge semantics and local reuse.

The most valuable next work is not to add more lanes indiscriminately. It is to deepen the lanes that already join cleanly and to keep every still-missing or weakly probed source explicit instead of inferred away.
