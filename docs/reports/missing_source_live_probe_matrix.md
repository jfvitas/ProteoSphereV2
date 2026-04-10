# Missing Source Live Probe Matrix

Date: 2026-03-22T18:57:48-05:00
Task: `P13-I005`
Status: `completed`

## Verdict

The missing-source probe matrix now reflects current live checks against the official surfaces listed in the backlog manifest.
It distinguishes sources that returned structured data from sources where only the download or query surface was confirmed, and it keeps empty-target or non-HTTP analysis-job cases explicit.

## Aggregate Findings

- Backlog entries probed: `12`
- Reachable official surfaces: `11`
- Structured responses observed: `4`
- Surface-only successes: `5`
- Reachable but target-empty probes: `2`
- Analysis-job-only entries: `1`
- Failed probes: `0`

## What The Live Checks Show

- `IntAct`, `STRING`, `RCSB/PDBe bridge`, and `EMDB` returned structured current responses from official endpoints, which is enough to plan targeted acquisition with real field shapes rather than guesswork.
- `DisProt` returned a structured API response, but the accession-scoped `P69905` probe came back empty, so the source is live while that exact anchor remains absent in the current dataset.
- `SABIO-RK` is reachable, but the accession-scoped `P31749` kinetic-law probe returned `no data found`, so the assay lane needs either a better anchor or a narrower acquisition rule before bulk work.
- `BioGRID`, `PROSITE`, `ELM`, `MegaMotifBase`, and `Motivated Proteins` are reachable on their official surfaces, but this pass intentionally stops short of pretending a release-pinned row export has already been fetched.
- `Evolutionary / MSA` remains an analysis job rather than a single remote corpus, so the next truthful step is a pinned local family-slice run, not a fake web probe.

## Source Matrix

| Source | State | Reachable | Structured | Observed Fields / Hints | Next Step |
| --- | --- | --- | --- | --- | --- |
| IntAct | `structured_response` | `yes` | `yes` | interactorAc, interactorName, interactorIntactName, interactorPreferredIdentifier, interactorDescription | Use the IntAct WS or release exports to fetch release-stamped interaction evidence for P69905 and preserve interaction AC plus complex-vs-binary lineage. |
| BioGRID | `surface_reachable` | `yes` | `no` | download portal reachable, TAB3/MITAB release files not fetched in this probe | Pin a BioGRID release archive and ingest TAB3 or MITAB rows with interaction ID, UniProt or Entrez cross-refs, experiment type, taxon, and publication provenance. |
| STRING | `structured_response` | `yes` | `yes` | queryIndex, stringId, ncbiTaxonId, taxonName, preferredName | Use targeted STRING neighborhood queries as a breadth layer only after curated PPI sources are pinned. |
| SABIO-RK | `reachable_no_target_data` | `yes` | `no` | entryIDs endpoint reachable, target accession returned no data | Keep SABIO-RK in the assay gap-fill lane, but verify whether P31749 is the right anchor or choose a known populated accession before bulk kinetic procurement. |
| PROSITE | `surface_reachable` | `yes` | `no` | PDOC and PS accessions reachable, release-pinned motif profile or export still needed | Acquire a release-pinned PROSITE documentation or profile export and join motif spans back to UniProt accessions. |
| ELM | `surface_reachable` | `yes` | `no` | download surface reachable, class or instance exports visible from HTML surface | Pin one ELM class plus one instance export and preserve motif coordinates, evidence count, organism, and partner context. |
| MegaMotifBase | `surface_reachable` | `yes` | `no` | legacy HTML surface reachable, record or export shape not yet pinned | Treat MegaMotifBase as a follow-on motif candidate and do not integrate it beyond pilot probing until a stable record or export shape is pinned. |
| Motivated Proteins | `surface_reachable` | `yes` | `no` | site reachable, stable accession-scoped export still unpinned | Keep Motivated Proteins in the follow-on motif lane until an accession-scoped export or reproducible query surface is pinned. |
| RCSB/PDBe bridge | `structured_response` | `yes` | `yes` | audit_author, cell, citation, database2, diffrn | Use the RCSB data API as the bridge glue for structure-to-protein provenance and keep PDB or CIF-level joins explicit. |
| DisProt | `reachable_no_target_data` | `yes` | `yes` | data, size | Use the DisProt API for accession-scoped disorder pulls, but keep absence of hit explicit rather than treating it as a negative label. |
| EMDB | `structured_response` | `yes` | `yes` | _id, admin, crossreferences, emdb_id, interpretation | Use EMDB as a related structure-depth layer, pinned by release and linked back to PDB or accession bridges rather than as a primary protein source. |
| Evolutionary / MSA | `analysis_job_required` | `no` | `no` | analysis job, pinned sequence corpus, family slice, MMseqs2 parameters | Run a pinned local MSA job for one accession family slice and record the exact sequence corpus, aligner version, and parameters; there is no single authoritative hosted corpus to probe here. |

## Notes

- The machine-readable probe matrix is stored in `artifacts/status/p13_missing_source_probe_matrix.json`.
- A reachable site is not being upgraded into a full acquisition claim unless this pass observed a structured row-level or API-level response.
- Empty target probes stay explicit; they are useful blockers, not silent failures.
