# Reactome Local Summary

Materialize a Reactome-enriched protein summary library from the local `bio-agent-lab` mapping tables.

Run:

```powershell
python scripts\materialize_reactome_local_summary.py `
  --accessions P04637,P31749,P69905,P09105
```

Default output:

- `artifacts/status/reactome_local_summary_library.json`

Behavior:

1. Uses local Reactome mapping, pathway, and hierarchy tables from `bio-agent-lab`.
2. Reuses canonical protein metadata from `data/canonical/LATEST.json` when available.
3. Emits valid protein summary records with `pathway_references` and Reactome provenance.
4. Keeps empty hits explicit as `partial` protein summaries instead of silently dropping them.
