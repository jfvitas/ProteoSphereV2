# Broad Mirror Launcher Contract

- Generated at: `2026-03-31T19:53:08.980714+00:00`
- Basis: `artifacts/status/broad_mirror_lane_plan.json`
- Transfer status: `artifacts/status/broad_mirror_remaining_transfer_status.json`
- Selected batch: `uniprot-core-backbone`
- Files: `3`
- Active overlap: `0`

## Launch Command

```powershell
python protein_data_scope/download_all_sources.py --dest "D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed" --tiers direct --sources uniprot --files uniprot_sprot_varsplic.fasta.gz uniref100.fasta.gz uniref90.fasta.gz
```

## Expected Outputs

- `data/raw/protein_data_scope_seed/uniprot/uniprot_sprot_varsplic.fasta.gz` (downloaded_file)
- `data/raw/protein_data_scope_seed/uniprot/uniref100.fasta.gz` (downloaded_file)
- `data/raw/protein_data_scope_seed/uniprot/uniref90.fasta.gz` (downloaded_file)
- `data/raw/protein_data_scope_seed/uniprot/_source_metadata.json` (source_metadata)
- `data/raw/protein_data_scope_seed/download_run_<UTC timestamp>.log` (run_log)
- `data/raw/protein_data_scope_seed/download_run_<UTC timestamp>.json` (run_manifest)

## Duplicate-Process Avoidance

- This batch is limited to the current lane plan's direct-value UniProt backbone files.
- It does not request any file currently observed as active in the transfer-status artifact.
- It does not include the already-active UniProt bulk files or any STRING filenames.
- Overlap detected: none

## Why This Batch

- Source: `uniprot` (direct)
- Value class: `direct-value`
- Rationale: Highest immediate library value: the isoform-aware Swiss-Prot file and representative UniRef FASTA lanes are the smallest, most direct backbone.
- Expected impact: Restores the core sequence reference layer first, with the best direct-value payoff for library consumers.
