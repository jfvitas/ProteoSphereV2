# P29 Motif Execution Slice

This slice turns the motif fusion plan into an execution-ready acquisition and join step for the sources that matter next: `PROSITE`, `InterPro`, `Pfam`, and future `ELM` intake. The key distinction is that `InterPro` and `Pfam` are already present in the refreshed local registry, while the motif lane is still structurally incomplete because `PROSITE` and `ELM` remain missing there. That means we can join the present domain evidence now, but we still need an import/promote step before `PROSITE` becomes a first-class registry-backed motif source.

## Current Source State

| Source | Registry state | Join keys | Storage mode | Confidence | Next step | Blocked today |
| --- | --- | --- | --- | --- | --- | --- |
| `InterPro` | Present | `IPRxxxxx`, member-signature accession, UniProt accession, `span_start`, `span_end`, taxon | `feature_cache` | High | Materialize span-stable domain rows directly into `SummaryRecordContext.domain_references` and keep integrated vs unintegrated provenance separate. | None for the join path. |
| `Pfam` | Present | `PFxxxxx`, `CLxxxxx`, UniProt accession, `span_start`, `span_end` | `feature_cache` | High | Join as the supporting domain view under the InterPro backbone; only split it out when direct Pfam granularity is needed. | None for the join path. |
| `PROSITE` | Missing in the local registry, but repo-local seed/trial bytes exist | `PDOCxxxxx`, `PSxxxxx`, `PRUxxxxx`, UniProt accession, `span_start`, `span_end` | `feature_cache` after import; `deferred_fetch` until then | High | Copy/promotion into the procurement package first, then register and join as the canonical local sequence-motif lane. | Blocked until the seed/trial bytes are promoted into the registry-backed source. |
| `ELM` | Missing in the local registry | `ELME#####`, instance accession or row id, UniProt accession, `span_start`, `span_end`, organism | `scrape_only` or `deferred_fetch` until a stable export is pinned | Medium | Hold as future intake only; capture the class/instance export when it becomes reproducible, then join as candidate evidence. | Blocked because the current surface is still page/download driven and not yet pinned to a stable export. |

## Execution Order

1. Join `InterPro` first so the summary library has the canonical domain/family spine.
2. Join `Pfam` second as a supporting view inside the InterPro backbone, not as a competing primary claim.
3. Promote and import `PROSITE` next, then join span-stable motif references once the registry-backed copy exists.
4. Leave `ELM` as future intake until the class/instance export is pinned and reproducible.

## Join Contract

- Use `UniProt accession` as the protein spine for every motif-bearing record.
- Treat `span_start` and `span_end` as mandatory disambiguators.
- Keep `source_name` and `source_record_id` on every reference so the record can be rebuilt later.
- Route `InterPro` and `Pfam` into `SummaryRecordContext.domain_references`.
- Route `PROSITE` and future `ELM` into `SummaryRecordContext.motif_references`.
- Set `join_status="joined"` only when the span is stable and the source is pinned.
- Set `join_status="candidate"` for future `ELM` intake once coordinates are reproducible but context still matters.
- Set `join_status="deferred"` whenever the source surface is still blocked or capture-only.

## What Is Blocked Today

- `PROSITE` is not yet registry-present, so the first action is promotion/import rather than summary-library join.
- `ELM` has no pinned export yet, so it must remain candidate-only until the intake surface stabilizes.
- No code path should collapse weak motif evidence into the canonical domain spine.
- No code path should mark low-confidence evidence as joined unless the span is reproducible and source identity is preserved.

## Next Commands

```powershell
python scripts/import_local_sources.py --sources interpro,pfam,prosite,elm --include-missing
```

