# Missing PPI / Data Procurement Next Wave

Date: 2026-03-23

The inventory audit shows the local/canonical side is now in good shape, so the next missing work is focused external procurement and registry alignment. The safest order is:

1. `IntAct` registry alignment and canonical export hardening
2. `BioGRID` release archive pinning and row ingest
3. `EMDB` bridge pinning for structure-depth support
4. `DisProt` accession-scoped follow-up on populated accessions
5. `STRING` breadth-only context, only after curated PPI sources are pinned

## 1) IntAct Registry Alignment

**Why first**

- It is the highest-value curated PPI source in the live probe matrix.
- It already has structured responses, so it can upgrade the frozen cohort without guesswork.

**Do next**

- Pin the IntAct export form that carries stable interaction lineage.
- Preserve interaction AC / IMEx lineage, participant accessions, and binary-vs-complex context.
- Keep the two IntAct empty accession cases explicit:
  - `P04637`
  - `Q9UCM0`

**Do not overclaim**

- Do not treat reachability as a finished row export.
- Do not collapse empty accession probes into positive PPI evidence.

## 2) BioGRID Release Pinning

**Why second**

- It is the next curated PPI breadth source after IntAct.
- The live probe matrix shows the portal is reachable, but the release archive still needs to be pinned as a row-level source.

**Do next**

- Pin a BioGRID TAB3 or MITAB release archive.
- Ingest interaction ID, UniProt or Entrez cross-refs, experiment type, taxon, and publication provenance.
- Use it as curated breadth, not as a substitute for IntAct canonical lineage.

**Do not overclaim**

- Do not call the source row-ready until a release archive is pinned.
- Do not rank STRING ahead of BioGRID for curated PPI truth.

## 3) EMDB Bridge Pinning

**Why third**

- EMDB is structured and useful as bridge-only structure glue.
- It strengthens the protein-depth side without pretending to be a primary protein source.

**Do next**

- Pin release-stamped EMDB records and keep the accession-to-PDB / accession-to-bridge mapping explicit.
- Use EMDB as structure-depth support for the bridge-positive set, not as a canonical protein source.

**Do not overclaim**

- Do not merge EMDB bridge glue with direct curated PPI evidence.
- Do not use EMDB as a stand-in for curated interaction provenance.

## 4) DisProt Accessions

**Why fourth**

- DisProt is live and useful, but the real P14 outputs show it is mixed: a few positive hits and many empty hits.
- It is depth, not canonical PPI, so it should follow curated PPI alignment.

**Do next**

- Focus on the accession-scoped positives:
  - `P04637`
  - `P31749`
  - `Q9NZD4`
- Keep empty hits explicit for:
  - `P69905`
  - `P68871`
  - `Q2TAC2`
  - `P00387`
  - `P02042`
  - `P02100`
  - `P69892`
  - `P09105`
  - `Q9UCM0`

**Do not overclaim**

- Do not retry the same empty DisProt accessions as if they were likely to become positive.
- Do not promote a DisProt empty into a negative biological statement.

## 5) STRING Breadth Only

**Why last**

- STRING is structured and useful, but it is breadth-only context in this cohort.
- It should not outrank curated PPI sources for canonical pair truth.

**Do next**

- Use STRING neighborhood or edge-context queries only after IntAct and BioGRID are pinned.
- Treat STRING as discovery / breadth support, not as canonical curated interaction evidence.

**Do not overclaim**

- Do not present STRING as a curated PPI replacement.
- Do not let breadth-only context overwrite direct curated evidence.

## Source-By-Source Summary

- `IntAct`: highest priority for canonical PPI alignment.
- `BioGRID`: next highest PPI breadth source, but only after a pinned release archive exists.
- `EMDB`: structure bridge glue and depth support.
- `DisProt`: useful protein-depth follow-up on populated accessions, with empties kept explicit.
- `STRING`: last, and breadth-only.

## Concrete Next-Step Signals

- Prioritize accessions with direct curated PPI yield already visible in the P14 slices.
- Keep `P04637` and `Q9UCM0` explicit as IntAct empties.
- Keep `P31749` explicit as a SABIO-RK empty, but do not use that as a reason to widen the assay lane prematurely.
- Do not widen the cohort before these source-specific gaps are handled truthfully.
