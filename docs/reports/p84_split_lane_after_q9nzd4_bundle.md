# p84 Split Lane After Q9NZD4 Bundle

This note is report-only. Including `q9nzd4_bridge_validation_preview` in the preview bundle does not change split or leakage claims.

## Current Reading

- The Q9NZD4 bridge preview is `aligned` and candidate-only.
- The split lane is still `blocked_report_emitted`.
- The leakage surfaces are still driven by the protein-spine previews.
- The bundle preview gate is still report-only and does not include ligand row materialization.

## Why Nothing Changes

Q9NZD4 is now a stronger bridge-rescue candidate, but it is still not a full ligand row and it does not rewrite the split assignment or leakage-group surfaces. The current split and leakage claims remain tied to the protein spine, variant, and structure previews already in the repo.

## What Should Stay True

- Split claims stay unchanged.
- Leakage claims stay unchanged.
- `bundle_ligands_included` remains `false`.
- The Q9NZD4 bridge stays candidate-only.

## Truth Boundary

This note does not authorize split progression or leakage recalculation. It only records that bundling the Q9NZD4 bridge preview does not by itself alter the current split or leakage truth.
