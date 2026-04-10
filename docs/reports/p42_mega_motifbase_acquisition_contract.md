# MegaMotifBase Acquisition Contract

This is the next external motif lane to pursue after the current breadth map. The contract is intentionally strict: it names the real public surface, the pinning rules, and the normalization contract, but it does not pretend we already have a downloadable payload.

## Why This Lane Next

- Current library use is already solid on `InterPro`, `PROSITE`, and `Pfam`.
- `ELM` is useful but still partial.
- `mega_motif_base` is the first remaining true external motif lane that still blocks breadth once the imported backbone is counted honestly.

## Exact Source Surface

Use the public MegaMotifBase surfaces already named in the lane plan:

- `https://caps.ncbs.res.in/MegaMotifbase/`
- `http://caps.ncbs.res.in/MegaMotifbase/download.html`
- `http://caps.ncbs.res.in/MegaMotifbase/search.html`
- `http://caps.ncbs.res.in/MegaMotifbase/famlist.html`
- `http://caps.ncbs.res.in/MegaMotifbase/sflist.html`

Current local evidence still says the lane is missing and points at the bio-agent-lab locator:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\mega_motif_base\mega_motif_base_latest.json_latest`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\mega_motif_base\mega_motif_base_latest.tsv_latest`

## Release And Pinning Expectations

- Treat this lane as `scrape_only` until a stable export or query snapshot is proven.
- Do not claim a payload download until one is actually captured.
- If a stable export appears, pin the release version, retrieval timestamp, checksums, and source-native ids.
- If only HTML/query pages are available, pin the exact URL, query parameters, retrieval timestamp, and page fingerprint.
- Keep raw snapshots separate from normalized rows.

## Normalization Rules

- Require `uniprot_accession` for any merged row.
- Preserve `residue_span` when the source gives residue coordinates.
- Preserve the exact source-native identifier or page identifier in `source_native_id`.
- Preserve `organism`, `source_record_id`, `source_page_url`, and provenance fields.
- Do not coerce MegaMotifBase identifiers into InterPro, PROSITE, Pfam, or ELM namespaces.
- Do not synthesize spans, accessions, or release ids when the source does not provide them.

## How It Merges In The Library

- `InterPro` stays the canonical domain/family/site spine.
- `PROSITE` stays the canonical curated motif/profile layer.
- `Pfam` stays a supporting family view under `InterPro`.
- `ELM` stays the short-linear-motif and partner-context source.
- `MegaMotifBase` should land as supplemental motif-family context, not as a replacement for canonical sources.
- If a MegaMotifBase row matches an existing protein and span, attach it as an additional `motif_references` entry with its own provenance.
- If a row only resolves to a family or superfamily label, keep it as family context rather than a site-level claim.

## Evidence Paths

- `artifacts/status/p41_motif_breadth_action_map.json`
- `artifacts/status/p40_motif_scope_completeness_view.json`
- `artifacts/status/p39_motif_gap_next_step_contract.json`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`
- `artifacts/status/p31_online_source_facts.json`
- `artifacts/status/p29_motif_lane_plan.json`
- `data/raw/local_registry/20260323T003221Z/mega_motif_base/manifest.json`
- `data/raw/local_registry/20260323T003221Z/mega_motif_base/inventory.json`

## Bottom Line

No payload is claimed here. The next step is not a fake download. The next step is to capture the real MegaMotifBase surface, pin it, and normalize it into the same accession/span/provenance shape used by the rest of the motif library.
