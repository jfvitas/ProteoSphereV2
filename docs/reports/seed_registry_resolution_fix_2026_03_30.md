# Seed Registry Resolution Fix

Date: 2026-03-30

## What This Run Confirmed

- The authoritative local registry refresh at `data/raw/local_registry_runs/LATEST.json` still marks `biogrid`, `intact`, and `prosite` as missing.
- The ProteoSphere seed mirror already contains those payloads under `data/raw/protein_data_scope_seed/`.
- The mismatch was caused by path resolution, not by missing files.

## Root Cause

- `execution/acquire/local_source_registry.py` resolves all relative `candidate_roots` against `DEFAULT_LOCAL_SOURCE_ROOT`, which is the external bio-agent-lab workspace.
- Some newer source definitions intentionally point at repo-local seed mirrors:
  - `data/raw/protein_data_scope_seed/biogrid/...`
  - `data/raw/protein_data_scope_seed/intact/...`
  - `data/raw/protein_data_scope_seed/prosite/...`
- Those repo-local paths were therefore being rewritten under `C:\Users\jfvit\Documents\bio-agent-lab\...` and incorrectly reported as missing.

## Fix Applied

- Added repo-aware resolution for `data/raw/protein_data_scope_seed/` candidates in [`execution/acquire/local_source_registry.py`](D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py).
- External bio-agent-lab paths still resolve against `C:\Users\jfvit\Documents\bio-agent-lab`.
- Repo-local seed mirrors now resolve against the ProteoSphere workspace root.

## Evidence

- [`data/raw/protein_data_scope_seed/biogrid`](D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/biogrid) contains large BioGRID archives.
- [`data/raw/protein_data_scope_seed/intact`](D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/intact) contains `intact.zip` and `mutation.tsv`.
- [`data/raw/protein_data_scope_seed/prosite`](D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/prosite) contains `prosite.dat`, `prosite.doc`, and `prosite.aux`.

## Remaining Constraint

- This shell still cannot execute the Python import pipeline, so the registry refresh was not rerun here.
- The next executable run should rerun the local source mirror/import flow and verify that `biogrid`, `intact`, and `prosite` advance from `missing` to `present`.

## Next Run

1. Rerun the local registry mirror/import pipeline.
2. Confirm `biogrid`, `intact`, and `prosite` resolve as present in `data/raw/local_registry_runs/LATEST.json`.
3. Recompute source coverage and update the blend/merge promotion order using the corrected registry state.
