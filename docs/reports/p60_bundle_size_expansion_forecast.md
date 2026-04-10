# P60 Bundle Size Expansion Forecast

This report-only forecast estimates how the lightweight bundle is likely to grow when the next families are added: `ligands`, `interactions`, `similarity signatures`, and `leakage groups`.

## Baseline

There is still no built preview bundle asset on disk. This forecast is therefore grounded in the current report-only preview contracts and the live source coverage truth, not in a measured bundle size.

Grounding:

- [artifacts/status/p57_bundle_preview_gate.json](/D:/documents/ProteoSphereV2/artifacts/status/p57_bundle_preview_gate.json)
- [artifacts/status/p58_preview_verified_gate.json](/D:/documents/ProteoSphereV2/artifacts/status/p58_preview_verified_gate.json)
- [artifacts/status/p55_bundle_field_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p55_bundle_field_mapping.json)
- [artifacts/status/p56_bundle_contents_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p56_bundle_contents_contract.json)
- [artifacts/status/p51_bundle_manifest_budget_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p51_bundle_manifest_budget_contract.json)
- [artifacts/status/source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
- [artifacts/status/broad_mirror_progress.json](/D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_progress.json)

## Forecast Summary

The next family additions are likely to expand the bundle in this order:

1. `ligands`
1. `interactions`
1. `similarity signatures`
1. `leakage groups`

The first two are the main size drivers. The last two are governance-heavy but comparatively compact.

## Likely Expansion Pressure

### `ligands`

Expected impact: **high**

Why it grows first:

- the repo already has substantial ligand-source coverage in the registry
- the current canonical slice already carries many ligand records, so a lightweight ligand family is a natural next materialization
- ligand summary rows tend to multiply quickly even when raw assay text stays deferred

Likely source drivers:

- BindingDB
- ChEMBL
- wwPDB Chemical Component Dictionary
- BioLiP
- Complex Portal
- curated local bridge payloads where already present

Budget effect:

- likely to push the bundle out of the smallest target band once materialized
- likely to consume one of the main family guardrails in `p51`

### `interactions`

Expected impact: **high**

Why it grows second:

- the current registry already marks the interaction-network lanes as present or partially present for several major sources
- interaction summaries require provenance and evidence lineage even when the raw MITAB or PSI-MI payloads stay excluded
- interaction fan-out can grow faster than ligand summaries once multiple source families are joined

Likely source drivers:

- IntAct
- BioGRID
- Complex Portal
- BindingDB
- Reactome participation and role context
- STRING later, if the missing lane is procured

Budget effect:

- likely to keep the bundle in the acceptable band at first
- could push toward warning if interaction evidence is over-materialized instead of summarized

### `similarity signatures`

Expected impact: **medium**

Why it comes after the primary content families:

- similarity signatures are derived summaries, not primary source payloads
- they are useful for split governance, selection, and dedupe, but they are not as large as source-backed ligands or interactions
- the bundle budget contract explicitly treats similarity and leakage together as a guardrail family

Likely source drivers:

- proteins
- structures
- ligands
- interactions

Budget effect:

- usually modest on its own
- becomes meaningful only when the four core families are all present

### `leakage groups`

Expected impact: **low**

Why it is last:

- leakage groups are governance metadata
- they are essential for safe bundle growth, but they are compact compared with the family summaries they describe
- they are best added once the primary families are in place so they can validate the bundle split policy

Likely source drivers:

- similarity signatures
- current split policy
- current record-family relationships

Budget effect:

- small direct size impact
- high indirect value because it helps keep the bundle from drifting into raw-mirror territory

## Forecast By Budget Class

- Current preview-design state: likely still in the target class because the new families are not yet materialized.
- After ligands: likely moves into the acceptable band.
- After ligands plus interactions: likely stays acceptable, but with a real warning risk if the summaries are too dense.
- After similarity signatures plus leakage groups: likely still acceptable if the family summaries stay compact.

This is a qualitative forecast, not a measured byte estimate.

## Scrape And Procurement Notes

- Do not scrape InterPro, PROSITE, Reactome, CATH, or SCOP for this bundle expansion.
- Do not scrape ELM first; keep it pinned-export first if it is included.
- Do not use scraping to fill `ligands` or `interactions` if a pinned export or local registry lane already exists.
- `STRING` remains a true procurement gap, but the first interaction-family expansion does not need it to begin.

## Bottom Line

The lightweight bundle is most likely to grow first through ligands and interactions, with similarity signatures and leakage groups following as compact governance layers. The bundle should still stay release-friendly if those latter two families are kept small and derived, but the first two families are where the size budget will feel real pressure.
