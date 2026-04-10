# P17 Scientific Library Validation

Date: 2026-03-22  
Task: `P17-I007`

## Verdict

The scientific library coverage is **valid for benchmark-capable release engineering**, but it is still **not RC/GA-capable**.

The real-corpus artifacts in `runs/real_data_benchmark/full_results/` are internally consistent and keep the gaps explicit:

- the benchmark summary remains blocked on the release-grade bar,
- the source coverage inventory is conservative rather than promotional,
- the evidence ledger keeps packet, ligand, and PPI blockers visible,
- and the bundle manifest preserves the prototype-runtime truth boundary instead of overclaiming release readiness.

## What Is Proven

- `P69905` is the strongest benchmark row, with five lanes and `direct_multilane` coverage.
- `P68871` remains probe-backed and mixed, not silently upgraded to direct assay depth.
- `P04637` is a direct single-lane PPI anchor only.
- `P31749` is ligand-linked only and still missing sequence, structure, and PPI modalities.
- The frozen benchmark cohort remains leakage-ready and split-clean, but the corpus is still partial at release depth.

## Remaining Explicit Gaps

- Most cohort rows are still single-lane or thin.
- `P68871` remains probe-supported rather than fully direct.
- `P04637` and `P31749` remain partial packets with missing modalities.
- The release bundle still carries blocker categories for runtime maturity, source coverage depth, and provenance/reporting depth.
- The corpus is not release-grade yet because provenance depth and coverage breadth are still bounded by prototype evidence.

## Evidence Used

- [summary.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/summary.json)
- [source_coverage.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json)
- [release_corpus_evidence_ledger.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json)
- [training_packet_audit.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/training_packet_audit.json)
- [release_bundle_manifest.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json)

## Verification

- `python -m pytest tests\\integration\\test_summary_library_real_corpus.py -q`
- `python -m ruff check tests\\integration\\test_summary_library_real_corpus.py`

## Integration Read

The correct interpretation is that the scientific library is now good enough for release engineering and candidate ranking, but it still needs deeper packet completeness, broader source coverage, and full provenance/reporting depth before it can be called RC or GA ready.
