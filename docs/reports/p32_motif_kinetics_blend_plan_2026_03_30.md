# P32 Motif And Kinetics Blend Plan

Date: `2026-03-30`

This run still could not execute live downloads from the shell, but it closed an important truth gap in the acquisition plan: `elm` and `sabio_rk` are real missing families in the local-reference story, and the repo now has concrete seed definitions for both.

## What Changed

- Added `ELM` to the protein-data-scope downloader manifest with stable TSV exports for motif-class regex definitions and motif-domain interaction tables.
- Added `SABIO-RK` to the downloader manifest as a query-scoped kinetics lane built around official REST surfaces plus a concrete `P31749` probe.
- Extended the local source registry so repo-seed files under `data/raw/protein_data_scope_seed/elm` and `data/raw/protein_data_scope_seed/sabio_rk` can count as truthful local presence after the next import refresh.

## Blend Policy

### ELM

- Treat `elm_classes.tsv` as a motif-prior layer.
- Use it to complement `PROSITE` and `InterPro`, not to replace them.
- Blend order:
  1. `PROSITE` for curated pattern/profile authority.
  1. `ELM` for short linear motif priors and motif-partner context.
  1. `InterPro` for broader domain/family coverage and cross-database normalization.
- Do not promote raw ELM regex hits to equal status with curated experimental motif evidence.

### SABIO-RK

- Treat `SABIO-RK` as a query-scoped kinetics evidence lane, not a broad bulk mirror.
- Start with accession-anchored exports such as `P31749` so provenance stays explicit.
- Keep `SABIO-RK` separate from `BindingDB` and `ChEMBL` assay truth:
  - `ChEMBL` remains the broad chemistry and assay authority.
  - `BindingDB` remains a secondary ligand-association lane once placeholder payloads are replaced.
  - `SABIO-RK` should enrich mechanistic kinetics and reaction context only where an accession-scoped query is actually materialized.

## Why This Matters

- Motif breadth was still structurally thin even after `PROSITE` landed, because the local-reference plan still lacked an `ELM` path.
- Enzymology and kinetic context were still represented as a missing family with no downloader contract at all.
- After the next live seed run and local-registry refresh, both families can appear in the authoritative local reference without inventing synthetic coverage.

## Next Execution Step

When networked execution is available again, the next truthful seed commands are:

```powershell
cd protein_data_scope
python download_all_sources.py --sources elm sabio_rk --allow-manual
python ..\scripts\import_local_sources.py --include-missing
```

Then confirm that:

- `elm` flips from `missing` to `present` or `partial` using repo-seed TSV evidence.
- `sabio_rk` flips from `missing` to at least a truthful query-scoped `present` or `partial` state.
- downstream reports describe `ELM` as motif priors and `SABIO-RK` as kinetics enrichment, not broad bulk authorities.

## Source Evidence

- ELM resource update paper: `https://academic.oup.com/nar/article/52/D1/D442/7420098`
- ELM class TSV export path used in published workflows: `http://elm.eu.org/elms/elms_index.tsv`
- ELM interaction TSV export path used in published workflows: `http://elm.eu.org/interactions/as_tsv`
- SABIO-RK web services overview: `https://sabio.h-its.org/layouts/content/webservices.gsp`
- SABIO-RK Python client examples: `https://www.sabio.h-its.org/layouts/content/docuRESTfulWeb/searchPython.gsp`
