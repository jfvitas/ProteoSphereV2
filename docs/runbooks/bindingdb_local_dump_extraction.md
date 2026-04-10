# BindingDB Local Dump Extraction

The lightweight BindingDB REST lane is useful for quick ligand discovery, but it does not reliably expose `reactant_set_id`. That makes canonical assay materialization incomplete, because the assay ingest layer requires a stable BindingDB source identifier.

To recover the richer assay shape, use the local full BindingDB SQL dump already present in `bio-agent-lab`:

```powershell
python scripts\extract_bindingdb_local_dump.py --accessions P04637,P31749
```

By default this reads:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`

And writes accession-scoped raw slices under:

- `D:\documents\ProteoSphereV2\data\raw\bindingdb_dump_local`

Each run produces:

- `summary.json`
- `LATEST.json`
- one accession file per selected target, for example `P04637.bindingdb_dump.json`

Current extraction strategy:

- find `polymer` rows whose `unpid1` or `unpid2` matches the requested accession
- attach `poly_name` aliases for the matched polymers
- collect `enzyme_reactant_set` rows whose `enzyme_polymerid` points at those polymers
- collect matching `assay`, `entry`, and inhibitor `monomer` rows

Important limitations:

- the extractor is intentionally accession-scoped and conservative
- it uses line-oriented SQL parsing, so it is best suited for targeted slices instead of full-database conversion
- this is a raw procurement step; canonical assay materialization should still happen downstream from the extracted slice
