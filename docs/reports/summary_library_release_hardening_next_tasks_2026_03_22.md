# Summary Library Release Hardening Next Tasks

The current summary-library stack is structurally good enough to support the next release-hardening wave: the schema already carries protein, pair, and ligand records with provenance/context defaults ([core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py#L384)), and the builder already materializes pair cross-reference records without hiding unresolved gaps ([execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py#L89)). The remaining work is mainly about making the downstream materialization, indexing, and training-package path equally truthful and release-reportable.

## Next Tasks

1. Thread summary-library provenance into package manifests end to end.
   - Preserve summary record ids, planning refs, and source-manifest lineage in the package manifest layer so selected training packets can still be traced back to their summary-library inputs.
   - The manifest model already carries selected examples, raw manifests, and planning refs ([core/storage/package_manifest.py](/D:/documents/ProteoSphereV2/core/storage/package_manifest.py#L493)); the next step is to make sure summary-library origin data survives that hop without being collapsed into generic notes.

2. Make selective materialization explicit about heavy, exact-payload selection.
   - The current materializer already keeps missing artifact payloads and missing canonical records visible ([execution/materialization/selective_materializer.py](/D:/documents/ProteoSphereV2/execution/materialization/selective_materializer.py#L558)), but the release path still needs a stricter contract for exact structural assets such as PDB/mmCIF and other deferred payloads.
   - Add coverage for “selected pointer exists, exact heavy payload is deferred” versus “pointer is missing” so the path stays conservative.

3. Carry release blockers through package build instead of flattening them away.
   - `build_training_package()` already maps selective-materialization issues into package-build issues and rejects published incomplete packages ([execution/materialization/package_builder.py](/D:/documents/ProteoSphereV2/execution/materialization/package_builder.py#L203)), but the release note should preserve the blocker shape more explicitly in the final package metadata.
   - Keep the published/frozen gate truthful: a package can be frozen with partial selection, but it should not read as release-ready until the downstream blockers are clear.

4. Surface runtime-level release gating from cache and planning-index misses.
   - `integrate_storage_runtime()` already detects missing planning-index rows and cache-backed artifact gaps ([execution/storage_runtime.py](/D:/documents/ProteoSphereV2/execution/storage_runtime.py#L222)), but the release view should roll those into a single blocker summary that matches what operators and benchmark reporting need.
   - This is the seam that should reconcile storage-runtime truth with the release-grade benchmark gap analysis ([docs/reports/release_grade_gap_analysis.md](/D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis.md#L13)).

5. Add a full rebuild regression that crosses summary library, manifest, materializer, and package builder.
   - Current tests cover the pieces separately: manifest normalization ([tests/unit/core/test_package_manifest.py](/D:/documents/ProteoSphereV2/tests/unit/core/test_package_manifest.py#L17)), selective materialization behavior ([tests/unit/execution/test_selective_materializer.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_selective_materializer.py#L80)), package build behavior ([tests/unit/execution/test_package_builder.py](/D:/documents/ProteoSphereV2/tests/unit/execution/test_package_builder.py#L72)), and runtime integration ([tests/integration/test_storage_runtime.py](/D:/documents/ProteoSphereV2/tests/integration/test_storage_runtime.py)).
   - What is still missing is one deterministic end-to-end chain that proves join state, provenance, and missing-input behavior all survive the handoff from summary records into a training package.

6. Add a release bundle generator for the benchmark artifacts.
   - The benchmark gap analysis is still explicit that runtime maturity, source coverage depth, and provenance/lineage reporting are the real blockers ([docs/reports/release_grade_gap_analysis.md](/D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis.md#L38)).
   - Once the runtime and packaging path are hardened, generate one release-facing bundle from the current `full_results` artifacts so the final report can cite concrete manifests, checkpoints, blocker counts, and provenance tables instead of a stitched narrative.

7. Add a summary-library round-trip check for mixed record kinds and context defaults.
   - The schema already supports protein, protein-pair, and protein-ligand records with guidance defaults ([core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py#L575), [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py#L688), [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py#L811)), but the release-hardening path should keep a regression locked for mixed-library serialization and deduplication.
   - This is a small guardrail, but it helps ensure the downstream packaging work never reintroduces silent record collapse.
