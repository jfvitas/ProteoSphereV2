# P34 P00387 Fresh-Run Ligand Blocker

- Generated at: `2026-03-31T14:41:05.9810046-05:00`
- Selected gap: `ligand:P00387`
- Fresh-run scope: evidence only

## Commands Run

1. `python scripts/probe_local_ligand_source_map.py --accessions P00387 --output artifacts/status/p34_p00387_local_ligand_source_map.json`
2. `python scripts/export_local_chembl_rescue_brief.py --accession P00387 --output artifacts/status/p34_p00387_local_chembl_rescue_brief.json --markdown docs/reports/p34_p00387_local_chembl_rescue_brief.md`
3. `python scripts/export_p00387_ligand_extraction_contract.py --accession P00387 --output artifacts/status/p34_p00387_ligand_extraction_contract.json --markdown docs/reports/p34_p00387_ligand_extraction_contract.md`

## What The Fresh Run Proved

- The P00387 local ligand source map exported a single accession entry.
- That entry is `bulk_assay_actionable`.
- The ChEMBL hit is `CHEMBL2146` with `93` activities.
- The rescue brief stayed planning-only and did not claim packet promotion.
- The extraction contract stayed at `ready_for_next_step`.

## Why This Is Still A Blocker

The repo can prove the evidence, but it still does not expose a narrow helper that turns those evidence artifacts into a fresh-run ligand packet payload for P00387. That means this slice can refresh evidence and reporting, but it cannot truthfully claim a run-scoped packet payload without adding new execution logic.

## Outcome

- Fresh-run evidence improved.
- Protected latest did not change.
- Packet deficit counts did not change.
- No run-scoped ligand packet payload was materialized.

## Boundary

This slice stays out of the latest-promotion path. Any future promotion would still need a downstream packet payload and the normal guard to pass.
