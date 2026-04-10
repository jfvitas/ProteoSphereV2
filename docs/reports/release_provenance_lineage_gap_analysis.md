# Release Provenance and Lineage Gap Analysis

Date: 2026-03-22

## Bottom Line

The benchmark evidence is honest, but it is **not release-grade for provenance / lineage depth yet**.

The repo already has solid primitive types in `core/provenance/record.py` and `core/provenance/lineage.py`. The blocker is that the benchmark emitter still assembles a flat provenance table from run artifacts instead of emitting a full provenance graph with stable record IDs, parent/child edges, and completeness accounting.

## Exact Gaps Still Blocking Release-Grade Claims

1. **No benchmark lineage graph is emitted.**
   `scripts/emit_benchmark_provenance.py` builds `provenance_table.json` as a row inventory, but it does not materialize `ProvenanceRecord` / `ProvenanceLineage` objects for the benchmark cohort.

2. **Per-row provenance identity is missing.**
   The current rows have accession, evidence mode, and evidence refs, but no stable `provenance_id`, no parent/child chain, and no graph closure that ties source acquisition to the benchmark outputs.

3. **Reproducibility metadata is only partially threaded.**
   `core/provenance.record` supports source bundle hashes, code versions, dataset version IDs, split artifact IDs, and model schema versions, but the benchmark table does not yet surface them as first-class row or run-context fields.

4. **Lineage completeness and conflict accounting are not explicit enough.**
   The current artifacts say the run happened and that resume continuity is identity-safe, but they do not yet expose corpus-scale counts for unresolved provenance, conflicting evidence, or missing lineage links.

5. **The release bundle still treats provenance depth as supporting evidence, not a contract.**
   `release_bundle_manifest.json` carries the blocker categories, but it still lacks a stable provenance-depth contract that would let the bundle stand alone as release-grade lineage evidence.

## Best Next Tasks

1. **Emit a real provenance graph for the benchmark cohort.**
   Own `scripts/emit_benchmark_provenance.py`, `core/provenance/record.py`, `core/provenance/lineage.py`, and `tests/unit/core/test_lineage.py`.
   Deliverable: benchmark provenance emitted as `ProvenanceRecord` / `ProvenanceLineage` data with closed, acyclic links.

2. **Add stable provenance IDs and edge links to each cohort row.**
   Own `scripts/emit_benchmark_provenance.py` and `runs/real_data_benchmark/full_results/provenance_table.json`.
   Deliverable: each row should carry a stable `provenance_id`, `parent_ids`, `child_ids`, and a lineage path back to source evidence.

3. **Thread reproducibility metadata through the benchmark provenance output.**
   Own `scripts/emit_benchmark_provenance.py` and `tests/unit/core/test_provenance_record.py`.
   Deliverable: row/run context should expose `source_bundle_hash`, `code_version`, `dataset_version_ids`, `split_artifact_id`, and `model_schema_version` where available.

4. **Make provenance gaps machine-readable.**
   Own `scripts/emit_benchmark_provenance.py` and `runs/real_data_benchmark/full_results/release_bundle_manifest.json`.
   Deliverable: explicit counters for unresolved records, conflicting evidence, missing lineage links, and evidence-mode coverage.

5. **Add round-trip tests for provenance and lineage serialization.**
   Own `tests/unit/core/test_lineage.py` and `tests/unit/core/test_provenance_record.py`.
   Deliverable: tests that prove the benchmark lineage can serialize, deserialize, and remain closed without silently dropping edges.

6. **Bind the release bundle to the new provenance-depth contract.**
   Own `docs/reports/release_benchmark_bundle.md`, `docs/reports/release_grade_gap_analysis.md`, and `runs/real_data_benchmark/full_results/release_bundle_manifest.json`.
   Deliverable: the bundle should describe provenance depth as a required contract field, not just a blocker note.

## Recommended Ownership Split

| Task | Primary owners |
| --- | --- |
| Provenance graph emission | `scripts/emit_benchmark_provenance.py`, `core/provenance/record.py`, `core/provenance/lineage.py` |
| Row-level provenance IDs | `scripts/emit_benchmark_provenance.py` |
| Reproducibility threading | `scripts/emit_benchmark_provenance.py`, `tests/unit/core/test_provenance_record.py` |
| Gap accounting | `scripts/emit_benchmark_provenance.py`, `runs/real_data_benchmark/full_results/release_bundle_manifest.json` |
| Serialization tests | `tests/unit/core/test_lineage.py`, `tests/unit/core/test_provenance_record.py` |
| Bundle contract wiring | `docs/reports/release_benchmark_bundle.md`, `docs/reports/release_grade_gap_analysis.md` |

## Final Read

The provenance surface is **sound but shallow**. The immediate next step is not to redesign the provenance primitives; it is to wire the benchmark emitter to those primitives and make lineage completeness, reproducibility, and unresolved gaps explicit in the release bundle.
