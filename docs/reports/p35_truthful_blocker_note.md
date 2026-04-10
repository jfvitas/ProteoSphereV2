# SABIO-RK and ELM Verification Note

- Generated at: `2026-03-30T22:15:27Z`
- Scope: source verification only
- Manifest touchpoint: [`protein_data_scope/sources_manifest.json`](/D:/documents/ProteoSphereV2/protein_data_scope/sources_manifest.json)

## Verified

- `ELM` interaction-domain export is workable.
- Direct fetch of `http://elm.eu.org/interactions/as_tsv` returned TSV content with a header row and motif-domain records.
- Direct fetch of `http://elm.eu.org/elms/elms_index.tsv` returned the class export with `Content-Disposition: attachment; filename=elm_classes.tsv`.
- I kept the manifest note aligned with that truth: the class export and interaction-domain TSV are both live.

## SABIO-RK Probes Attempted

- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/entryIDs?format=txt&q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/entryIDs?format=txt&q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/sbml?q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/searchKineticLaws/sbml?q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/sabioRestWebServices/count?format=txt&q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/sabioRestWebServices/count?format=txt&q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/newSearch?q=UniProtKB_AC:P31749`
- `https://sabiork.h-its.org/newSearch?q=UniProtKB_AC:%22P31749%22`
- `https://sabiork.h-its.org/newSearch?q=P31749`

## SABIO-RK Outcome

- The REST probes above returned `404`.
- The `newSearch` HTML page returned `200`, but the fetched static page did not expose concrete entry IDs or SBML payloads for `P31749`.
- That leaves the accession-scoped SABIO lane blocked until we get a query form that actually resolves in this environment.

## Next Best Options

- Use browser automation against the SABIO search UI to see which request the page fires for `P31749`, then replay that exact request.
- If the UI reveals a query field/value pair that resolves cleanly, retry the documented `searchKineticLaws/entryIDs` and `searchKineticLaws/sbml` endpoints with that exact query.
- Keep ELM in the truthful queue; it no longer needs blocker status.

## Truth Boundary

No accession-scoped SABIO result was invented. The report records the exact probes that failed and the one ELM path that succeeded.
