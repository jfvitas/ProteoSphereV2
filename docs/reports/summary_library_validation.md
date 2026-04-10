# Summary Library Validation

Date: 2026-03-22

## Scope

Validated the landed summary-library builder against a small live-derived corpus built from real source data.

## Live Corpus

- UniProt live snapshot for `P69905` and `P68871`
- RCSB live snapshot for `4HHB`

The summary library was assembled from those live records, then routed through the protein-pair cross-reference index and the summary-library builder.

## Outcome

- The summary library materialized successfully from real source data.
- Protein records retained live provenance pointers back to UniProt.
- The live RCSB-derived pair record preserved its native interaction identifier in `interaction_refs` even though its provenance pointers were intentionally absent, which exercises the conservative preservation path.
- No ligand summaries were populated in this validation.

## Gaps

- BindingDB acquisition was blocked in this environment.
- The IntAct live acquisition endpoint used for the broader corpus check returned 404 during probing.
- Because of those gaps, this validation stays honest about covering proteins and one protein-protein example only.

## Verification

- Focused integration test: `tests/integration/test_summary_library_real_corpus.py`
- Focused Ruff check: `tests/integration/test_summary_library_real_corpus.py`
