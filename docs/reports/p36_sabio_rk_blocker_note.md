# SABIO-RK Accession-Scoped Verification Note

- Generated at: `2026-03-30T22:40:00-05:00`
- Scope: SABIO-RK verification only
- Manifest touchpoint: broad procurement now keeps only `sabio_search_fields.xml` and `sabio_uniprotkb_acs.txt`; accession-scoped probes remain blocked here.

## What I Verified

- The live SABIO search UI exposes `UniProtKB_AC` as a real search term in `https://sabiork.h-its.org/newSearch/index?q=P31749`.
- The UI search endpoint is `POST /newSearch/search`.
- I tested the accession-scoped UI request shapes against `P31749`:
  - `q=P31749&searchterms=UniProtKB_AC&view=entry`
  - `q=UniProtKB_AC:P31749&searchterms=UniProtKB_AC&view=entry`
  - `q=P31749&searchterms=UniProtKB_AC&view=reaction`
  - `q=UniProtKB_AC:P31749&searchterms=UniProtKB_AC&view=reaction`
- Each of those UI searches returned the no-results response with the curation-request link, not entry IDs or SBML.

## Exact Probes Attempted

### REST-style probes

- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/entryIDs?format=txt&q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/entryIDs?format=txt&q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/sbml?q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/sbml?q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/count?format=txt&q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/count?format=txt&q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/kinlaws?q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/kinlaws?q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/kineticlawsExportTsv`

### UI-backed probes

- `POST https://sabiork.h-its.org/newSearch/search` with `q=P31749&searchterms=UniProtKB_AC&view=entry`
- `POST https://sabiork.h-its.org/newSearch/search` with `q=UniProtKB_AC:P31749&searchterms=UniProtKB_AC&view=entry`
- `POST https://sabiork.h-its.org/newSearch/search` with `q=P31749&searchterms=UniProtKB_AC&view=reaction`
- `POST https://sabiork.h-its.org/newSearch/search` with `q=UniProtKB_AC:P31749&searchterms=UniProtKB_AC&view=reaction`

## Outcome

- The REST endpoints above returned `404` in this environment.
- The UI-backed searches returned the no-results response, not entry IDs or SBML.
- That means I do not have a runtime-confirmed accession-scoped SABIO request for `P31749` that yields concrete kinetic-law IDs or SBML.

## Best Next Step

- Use browser automation on the SABIO search UI to inspect the live network request that the page emits when a valid accession search succeeds.
- If the UI can be driven to a positive hit for `P31749`, replay that exact request shape before promoting any manifest note.
- If the accession remains empty, keep SABIO-RK in the truthful blocker queue and do not weaken the manifest.

## Truth Boundary

No accession-scoped SABIO result was invented. The report records the exact probes that failed and the one verified UI request shape that still returned no results.
