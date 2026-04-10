# Protein Data Scope Downloader Package

This package contains:

- `sources_manifest.json` - curated manifest of major protein, interaction, pathway, motif, nucleic-acid, and chemistry databases for broad-scope ingest.
- `source_policy.json` - procurement tier policy for direct, guarded, and resolver-first sources.
- `download_all_sources.py` - downloads explicit top-level files into the repository raw seed area by default.
- `catalog_summary.md` - human-readable summary of sources and file coverage.
- `run_download.bat` - Windows batch wrapper.

## What this package does

It is designed for a broad-scope protein data platform covering:

- protein structures
- protein-protein interactions
- protein-ligand data
- protein-nucleic-acid resources
- pathway, reaction, and complex resources
- domain, motif, and family annotation
- sequence and identifier mapping backbones

## Important caveats

1. Some resources expose archive directories with thousands to millions of files. For those sources, this package focuses on top-level bulk files and the most important bulk entry points.
2. A few resources use dynamic download pages, unstable release numbers, or license and authentication gates. Those are marked in the manifest with `manual_review_required: true`.
3. The downloader skips manual-review sources and HTML landing-page placeholders by default unless they are explicitly enabled.
4. The script does not extract every archive automatically by default because some archives are very large. It can optionally unpack `.zip`, `.tar`, `.tar.gz`, and `.gz` archives.
5. Archive extraction is path-sanitized to avoid writing outside the destination tree.
6. Every run emits both a text log and a JSON manifest with per-file checksum and size metadata.
7. The downloader skips files that already exist unless `--overwrite` is used.

## Quick start

### Option A: safe trial seed

```powershell
python download_all_sources.py --sources prosite pdb_chemical_component_dictionary
```

### Option B: direct-tier seed

```powershell
python download_all_sources.py --tiers direct
```

## Useful flags

```powershell
python download_all_sources.py --help
```

Key options:

- `--dest D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed`
- `--sources reactome sifts uniprot`
- `--tiers direct guarded resolver`
- `--extract`
- `--overwrite`
- `--timeout 1800`
- `--retries 4`
- `--allow-manual`
- `--allow-html-placeholders`

## Output layout

```text
D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/
  reactome/
  string/
  sifts/
  uniprot/
  alphafold_db/
  biogrid/
  intact/
  complex_portal/
  bindingdb/
  chembl/
  chebi/
  rnacentral/
  interpro/
  prosite/
  pdb_chemical_component_dictionary/
  download_run_YYYYMMDD_HHMMSS.log
  download_run_YYYYMMDD_HHMMSS.json
```

## Recommended workflow

1. Run the Tier 1 direct sources first:
   - `reactome`
   - `sifts`
   - `uniprot`
   - `chebi`
   - `prosite`
   - `pdb_chemical_component_dictionary`
2. Run the Tier 2 guarded sources only after snapshot pinning is in place:
   - `string`
   - `biogrid`
3. Keep Tier 3 resolver and manual-first sources blocked until they have concrete pinned URLs:
   - `alphafold_db`
   - `intact`
   - `bindingdb`
   - `chembl`
   - `complex_portal`
   - `rnacentral`
   - `interpro`

## Notes on very large sources

- AlphaFold DB: the full global set is enormous. This package includes representative bulk entry points rather than every proteome tarball.
- wwPDB archive: the experimental structure archive is better handled through a dedicated mirror strategy instead of a one-shot downloader.
- BioGRID, IntAct, and Complex Portal: release identifiers can change. Guarded or resolver policy still applies before production procurement.
