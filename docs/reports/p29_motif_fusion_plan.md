# P29 Motif Fusion Plan

As of `2026-03-30`, the refreshed local registry still marks the motif lane as incomplete, but the summary-library contract already has the right shape to fuse motif evidence without overstating weak lanes. The right pattern is to keep the six motif sources as distinct evidence systems, not as one flattened "motif" bucket: `InterPro`, `Pfam`, `PROSITE`, `ELM`, `Mega Motif Base`, and `Motivated Proteins`.

## Fusion Stack

| Source | Join keys | Confidence tier | Library role |
| --- | --- | --- | --- |
| `InterPro` | `IPRxxxxx`, member-signature accession, UniProt accession, `span_start`, `span_end`, taxon | High | Canonical domain/family/site spine; primary domain reference when the span is covered by InterPro |
| `Pfam` | `PFxxxxx`, `CLxxxxx`, UniProt accession, `span_start`, `span_end` | High | InterPro member-database view; supporting domain reference unless direct Pfam granularity is needed |
| `PROSITE` | `PDOCxxxxx`, `PSxxxxx`, `PRUxxxxx`, UniProt accession, `span_start`, `span_end` | High | Canonical curated sequence-motif lane; strongest source for local functional-site labels |
| `ELM` | `ELME#####`, instance accession or row id, UniProt accession, `span_start`, `span_end`, organism | Medium | Short-linear-motif lane with partner-context and taxon sensitivity |
| `Mega Motif Base` | family / superfamily id, motif or page id, structure id, UniProt accession when available, `span_start`, `span_end` | Low | Structural-motif support lane; page-driven unless a stable export is pinned |
| `Motivated Proteins` | page id or query fingerprint, motif id when available, structure id, UniProt accession when available, `span_start`, `span_end` | Low | Query/capture-only support lane until a repeatable export surface is confirmed |

## Join Rules

- Use UniProt accession as the protein spine for every motif-bearing record.
- Use `span_start` and `span_end` as mandatory disambiguators for all motif and site claims.
- Keep `source_name` and `source_record_id` distinct from the biological label so the record can be rebuilt later.
- Use `domain_references` for InterPro and Pfam when the claim is family/domain-level, and `motif_references` for PROSITE, ELM, Mega Motif Base, and Motivated Proteins.
- Do not merge all sources into one namespace; keep `interpro`, `pfam`, `prosite`, `elm`, `mega_motif_base`, and `motivated_proteins` as separate evidence families.

## Consensus Strategy

- InterPro is the canonical domain/family backbone. When Pfam and InterPro agree on the same span, surface one consensus family/domain line and keep Pfam as supporting provenance rather than a competing primary claim.
- PROSITE is the canonical local site-motif lane. When ELM overlaps the same span, keep both references, but use PROSITE for sequence-local function and ELM for context-rich short-linear-motif evidence.
- Mega Motif Base and Motivated Proteins are supporting structural-motif lanes. They can strengthen a motif call, but they should not be allowed to overrule a high-confidence accessioned source.
- Consensus should be per span, not per protein. If two sources annotate different regions on the same protein, keep both.
- Feed span-stable records into `build_family_motif_consensus` so the library can roll up motif and domain support without losing source identity.

## Confidence Tiers

- `high`: InterPro, Pfam, PROSITE. These are accessioned and span-stable enough to become joined motif references when the source release is pinned.
- `medium`: ELM. Use this tier when the class/instance export is pinned and the instance coordinates are reproducible, but partner context still matters.
- `low`: Mega Motif Base and Motivated Proteins. Use this tier for page-captured or query-only results that are not yet backed by a stable export.
- Weak tiers should never override a stronger tier. If only low-tier evidence exists, the record stays `candidate` or `deferred`, not canonical.

## How Evidence Should Surface

- Attach motif and domain evidence to `SummaryRecordContext.motif_references` and `SummaryRecordContext.domain_references` using `SummaryReference` rows.
- Populate `join_status="joined"` only for span-stable, accession-pinned evidence. Use `candidate` when the source is real but context-sensitive, and `deferred` when the surface is query-only or page-only.
- Keep `evidence_refs` and `notes` on every reference so the operator can see why a call is strong, weak, or unresolved.
- Use `storage_tier="feature_cache"` for PROSITE, ELM, InterPro, and Pfam projections. Use `storage_tier="scrape_only"` or `deferred_fetch` for Mega Motif Base and Motivated Proteins until a repeatable export is pinned.
- Show a tier badge in the summary library rather than a single flat confidence value. A low-tier page capture should read as secondary support, not as a canonical label.

## Practical Ordering

1. InterPro first for domain/family/site normalization.
2. Pfam second as the member-database projection inside InterPro.
3. PROSITE third for curated sequence motifs and ProRules.
4. ELM fourth for partner-context short linear motifs.
5. Mega Motif Base fifth as structural-motif support.
6. Motivated Proteins sixth as query/capture-only support until its export shape is pinned.

## Risks And Stop Conditions

- Do not flatten weak structural pages into high-confidence canonical motif labels.
- Do not collapse Pfam into a second standalone domain lane when the InterPro view already covers the same span.
- Do not downgrade a high-confidence accessioned source because a lower-confidence page capture happens to agree.
- Do not invent release pins for page-only sources; page captures stay explicit about what they are.

## Sources Used

- [Source Motif Systems](./source_motif_systems.md)
- [Source Join Strategies](./source_join_strategies.md)
- [Summary Library Plan](./p29_summary_library_plan.md)
- [Motif Lane Plan](./p29_motif_lane_plan.md)
