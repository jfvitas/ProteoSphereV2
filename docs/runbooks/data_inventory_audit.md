# Data Inventory Audit

Use the inventory audit to answer three questions quickly:

1. Which online raw sources are actually mirrored under `data/raw`?
2. Which large local corpora from `bio-agent-lab` are registered and reusable?
3. How much of that source material has been promoted into `data/canonical`?

Run:

```powershell
python scripts\audit_data_inventory.py
```

Outputs:

- JSON audit: `artifacts/status/data_inventory_audit.json`
- Markdown report: `docs/reports/data_inventory_audit.md`

Recommended workflow:

1. Refresh online snapshots with `python scripts\download_raw_data.py ...`
2. Refresh local registry with `python scripts\import_local_sources.py ...`
3. Refresh canonical outputs with `python scripts\materialize_canonical_store.py ...`
4. Run `python scripts\audit_data_inventory.py`

The audit is meant to be truthful rather than optimistic. If a source is only locally registered, it will appear there and not as an online mirror. If canonical materialization is partial, the top-level report will expose the unresolved counts directly.
