# IntAct Local Summary Library

Use the local IntAct mirror to materialize an accession-level and pair-level summary library.

## Purpose

- Preserve accession probe outcomes even when a mirrored IntAct slice contains only self rows.
- Materialize pair summaries only from non-self binary rows with traceable IntAct and IMEx lineage.
- Keep the resulting artifact operator-visible under `artifacts/status/intact_local_summary_library.json`.

## Command

```powershell
python scripts\materialize_intact_local_summary.py --accessions P04637,P31749
```

Optional arguments:

- `--raw-root`: IntAct snapshot root or parent directory. Defaults to `data/raw/intact`.
- `--canonical-summary`: canonical summary JSON used to enrich protein records.
- `--library-id`: explicit library id override.
- `--output`: target artifact path.

## Output

Default artifact:

- `artifacts/status/intact_local_summary_library.json`

The artifact includes:

- accession-level `protein` records that capture probe status, raw row counts, self-only counts, and binary-pair counts
- `protein_protein` records for non-self curated pairs
- IntAct and IMEx cross references on pair records
- release-stamped provenance pointers for both protein and pair summaries

## Truthfulness rules

- Self-only mirrored rows must remain `partial` accession summaries, not promoted to pair evidence.
- Missing local files must remain `intact_unavailable`.
- Pair records may only be created from rows where the two primary accessions differ.
