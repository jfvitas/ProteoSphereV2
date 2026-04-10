# IntAct Local Summary Live Materialization

Date: 2026-03-23

## Command

```powershell
python scripts\materialize_intact_local_summary.py --accessions P04637,P31749
```

## Artifact

- `artifacts/status/intact_local_summary_library.json`

## Result summary

- Library id: `summary-library:intact-local:20260323T013346Z`
- Source manifest id: `IntAct:20260323T002625Z:download:6a49b82dc9ec053d`
- Record count: `4`
- Record types:
  - `protein`: `2`
  - `protein_protein`: `2`

## Accession outcomes

- `P04637`
  - probe state: `reachable_empty`
  - raw rows: `5`
  - self-only rows: `5`
  - binary pair rows: `0`
  - final join reason: `intact_self_only_probe`

- `P31749`
  - probe state: `direct_hit`
  - raw rows: `5`
  - self-only rows: `3`
  - binary pair rows: `2`
  - final pair summaries:
    - `pair:protein_protein:protein:P31749|protein:Q92831`
    - `pair:protein_protein:protein:P31749|protein:Q9Y6K9`

## Interpretation

The local mirrored IntAct slices are not symmetric across accessions. `P04637` currently resolves to self-only curated rows in the stored slice, so it remains useful as a probe-status record but not as pair evidence. `P31749` resolves to two non-self curated binary interactions after correcting the headerless MITAB 2.5 column mapping, so those pair summaries are now available for downstream planning, packaging, and benchmark selection.
