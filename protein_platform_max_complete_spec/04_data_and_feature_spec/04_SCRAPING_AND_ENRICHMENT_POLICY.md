# Scraping and Enrichment Policy

## Prefer structured access over scraping
Order of preference:
1. official bulk downloads
2. official APIs
3. official programmatic search services
4. controlled HTML extraction only when there is no stable structured access

## Enrichment targets
- motifs not already captured in canonical annotations
- disorder/IDR enrichment
- pathway membership/context
- family/domain architecture
- evolutionary alignments and conservation
- site/pocket motif similarity
- interaction evidence context

## Policy rules
- preserve raw source output before transformation
- rate-limit and log acquisition details
- version enrichment snapshots
- tag all weakly extracted text-derived annotations as lower-confidence
- never mingle speculative text extraction with curated truth without provenance distinction
