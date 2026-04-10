# P10-I014 Source Coverage Integration Prep

Date: 2026-03-22

Scope: integrate the lane-hardening wave behind `P10-T013` into the source-coverage emitter and release-facing reporting without inflating evidence depth.

## Integration Checkpoints

1. Re-emit `runs/real_data_benchmark/full_results/source_coverage.json` from the current cohort and run artifacts after the lane hardening lands.
2. Verify that `scripts/emit_source_coverage.py` still classifies evidence conservatively:
   - `direct_live_smoke`
   - `probe_backed`
   - `snapshot_backed`
   - `verified_accession`
3. Confirm that new annotation, pathway, structural, and direct PPI lanes increase `lane_depth` only when the underlying evidence is actually present.
4. Preserve the distinction between lane depth and validation class. A row can be deeper without becoming a stronger evidence class.
5. Keep the dashboard and operator release-status surfaces aligned with the re-emitted coverage semantics.

## Likely Semantic Traps

- Treating a local-artifact fallback as if it were a direct live smoke hit.
- Letting `lane_depth > 1` imply a stronger evidence class automatically.
- Collapsing probe-backed or snapshot-backed rows into direct evidence just because they now have more lanes.
- Forgetting that `source_coverage.json` is an inventory, not a validation report.
- Regenerating the coverage file without updating the release-facing parity / dashboard notes that read it.
- Losing the thin-cohort warning on the verified-accession rows after enrichment.

## Focused Validation Commands

Run these in order after `P10-T013` is ready:

```powershell
python -m pytest tests\unit\execution\test_acquire_intact_snapshot.py tests\unit\execution\test_acquire_biogrid_snapshot.py tests\unit\execution\test_protein_pair_crossref.py tests\unit\execution\test_acquire_rcsb_pdbe_snapshot.py tests\unit\execution\test_acquire_alphafold_snapshot.py tests\unit\execution\test_acquire_uniprot_snapshot.py tests\unit\execution\test_supplemental_scrape_registry.py tests\unit\execution\test_acquire_interpro_motif_snapshot.py tests\unit\execution\test_acquire_reactome_snapshot.py -q
python -m ruff check execution\acquire\intact_snapshot.py execution\acquire\biogrid_snapshot.py execution\indexing\protein_pair_crossref.py execution\acquire\rcsb_pdbe_snapshot.py execution\acquire\alphafold_snapshot.py execution\acquire\uniprot_snapshot.py execution\acquire\supplemental_scrape_registry.py execution\acquire\interpro_motif_snapshot.py execution\acquire\reactome_snapshot.py scripts\emit_source_coverage.py
python scripts\emit_source_coverage.py
python -m pytest tests\integration\test_source_coverage_hardening.py -q
```

If the integration wave also needs the release-facing operator snapshot, follow with:

```powershell
python -m pytest tests\integration\test_operator_visibility.py -q
python -m pytest tests\integration\test_operator_state_contract.py -q
```

## Exit Criteria

The wave is complete only if:

- the re-emitted coverage matrix is still conservative,
- lane counts rise only where the evidence exists,
- the thin rows remain explicitly labeled as thin,
- the mixed-evidence row stays mixed until its probe lane is genuinely upgraded,
- the release-facing parity / dashboard / operator surfaces still agree on the blocked release-grade boundary,
- the focused tests and lint checks pass.

## Do Not

- Do not widen the cohort to make the coverage matrix look richer.
- Do not let new fallback paths masquerade as direct live validation.
- Do not rewrite `source_coverage.json` to hide thinness.
- Do not treat this wave as a release claim. It is an inventory refresh after lane hardening.

## Summary

The safest interpretation of this integration wave is: “more lanes, same honesty.” The emitter should reflect the richer cohort only where real evidence exists, and the release-facing surface should continue to call out the remaining thin and probe-backed rows explicitly.
