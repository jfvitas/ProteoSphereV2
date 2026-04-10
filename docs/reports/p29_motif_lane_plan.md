# P29 Motif Lane Plan

As of `2026-03-30`, the refreshed local registry still marks all four motif sources as missing: `PROSITE`, `ELM`, `Mega Motif Base`, and `Motivated Proteins`. The refreshed bio-agent-lab manifests at `data/raw/local_registry/20260330T054522Z/` confirm that none of those four have present roots in the local inventory. The only immediately reusable bytes in this workspace are the repo-local PROSITE seed/trial files already on disk.

## What Can Be Copied Now

- `PROSITE` is already present locally at `data/raw/protein_data_scope_seed/prosite/` and `protein_data_scope/trial_downloads/prosite/`.
- Copy / promote these existing files immediately: `prosite.dat`, `prosite.doc`, and `prosite.aux`.
- The refreshed bio-agent-lab registry does not expose any present root for `ELM`, `Mega Motif Base`, or `Motivated Proteins`, so there is nothing new to copy from bio-agent-lab for those lanes right now.

## What Must Be Downloaded Or Captured

- `PROSITE` refresh path: `https://ftp.expasy.org/databases/prosite/` plus the accession pages `https://prosite.expasy.org/PDOC00001` and `https://prosite.expasy.org/PS00001` for release-pinned motif provenance.
- `ELM` public entry points: `http://elm.eu.org/downloads.html`, `http://elm.eu.org/elms/elms_index.tsv`, `http://elm.eu.org/instances/`, and `http://elm.eu.org/instances/candidates`.
- `Mega Motif Base` public entry points: `https://caps.ncbs.res.in/MegaMotifbase/`, `http://caps.ncbs.res.in/MegaMotifbase/download.html`, `http://caps.ncbs.res.in/MegaMotifbase/search.html`, `http://caps.ncbs.res.in/MegaMotifbase/famlist.html`, and `http://caps.ncbs.res.in/MegaMotifbase/sflist.html`.
- `Motivated Proteins` public entry points: `https://motif.gla.ac.uk/`, `https://motif.mvls.gla.ac.uk/motif/index.html`, `https://motif.mvls.gla.ac.uk/ProtMotif21/index.html`, and `https://motif.mvls.gla.ac.uk/motivator.html`.

## Source-by-Source Plan

- `PROSITE`: treat as the high-confidence motif lane. Promote the existing local seed now, then refresh from the FTP mirror only if we need a newer release boundary.
- `ELM`: download the class index TSV and selected instance exports. Keep class accession, instance coordinates, organism, evidence count, and partner-context hints.
- `Mega Motif Base`: capture or download the family/superfamily and search outputs, but keep it as a structural-motif lane with conservative confidence until a reproducible export shape is pinned.
- `Motivated Proteins`: treat as query/capture-only for now. The public site is reachable, but no stable accession-scoped export is confirmed in the refreshed probe matrix, so keep it deferred until we can pin a repeatable payload.

## Summary Library Integration

- Map all motif hits into `SummaryRecordContext.motif_references` as `SummaryReference(reference_kind="motif", ...)` rows.
- Use source-native identifiers first: `PDOCxxxxx`, `PSxxxxx`, `PRUxxxxx` for PROSITE; `ELME#####` for ELM; and source/page identifiers for Mega Motif Base and Motivated Proteins until better export IDs are pinned.
- Keep motif spans explicit with `span_start` and `span_end`; do not collapse site positions into free text.
- Use `join_status="joined"` only for span-stable, accession-pinned rows. Leave page-only or query-only rows as `candidate` or `deferred`.
- Store PROSITE and ELM in the feature-cache tier; keep Mega Motif Base and Motivated Proteins in `scrape_only` or `deferred_fetch` until their exports are repeatable.
- Feed family-level rollups through `build_family_motif_consensus` so motif and domain support can be aggregated without losing source identity.

## Risks And Stop Conditions

- Do not invent a release pin for `ELM`, `Mega Motif Base`, or `Motivated Proteins` if the public surface only gives HTML navigation.
- Do not merge all motif systems into one namespace. The summary library should preserve source identity and evidence lineage.
- Do not treat the absence of a local root as a negative biological result. It only means the lane still needs procurement.

## Next Commands

- `python scripts/import_local_sources.py --sources prosite,elm,mega_motif_base,motivated_proteins --include-missing`
- `python protein_data_scope/download_all_sources.py --sources prosite --extract`

## Sources Used

- `https://prosite.expasy.org/`
- `https://ftp.expasy.org/databases/prosite/`
- `http://elm.eu.org/downloads.html`
- `http://elm.eu.org/elms/elms_index.tsv`
- `https://caps.ncbs.res.in/MegaMotifbase/`
- `https://motif.gla.ac.uk/`
- `https://motif.mvls.gla.ac.uk/motif/index.html`
