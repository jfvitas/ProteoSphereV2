# Source Coverage Depth Next Tasks

Date: 2026-03-22  
Scope: release-grade source coverage for the frozen 12-accession benchmark cohort  
Primary inputs: [`runs/real_data_benchmark/full_results/source_coverage.json`](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json), [`docs/reports/cohort_lane_coverage_analysis.md`](D:/documents/ProteoSphereV2/docs/reports/cohort_lane_coverage_analysis.md), [`docs/reports/release_grade_gap_analysis.md`](D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis.md), acquisition/reporting modules under [`execution/acquire`](D:/documents/ProteoSphereV2/execution/acquire) and [`scripts`](D:/documents/ProteoSphereV2/scripts)

## Bottom Line

The benchmark remains **not release-grade** on source coverage depth.

The machine-readable coverage matrix is the authority here, and it shows a highly skewed cohort:

- `1` accession with `5` lanes: `P69905`
- `1` accession with `2` lanes: `P68871`
- `10` accessions with `1` lane each

That means the cohort is truthful and leakage-ready, but still too thin to support a release-grade claim of broad multimodal source coverage.

## Thin-Coverage Lanes

The following lanes remain thin in the coverage matrix and are the ones that still block release-grade source claims:

| Accessions | Current lane depth | Current evidence class | Why it is still thin |
| --- | ---: | --- | --- |
| `P04637` | 1 | `direct_live_smoke` | Only IntAct-backed, so it is a single-source PPI anchor rather than broad multimodal coverage. |
| `P31749` | 1 | `direct_live_smoke` | Only BindingDB-backed, so it is a single-source ligand anchor rather than a broad evidence profile. |
| `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892` | 1 each | `snapshot_backed` | These are still only UniProt-backed in the matrix, so they prove identity but not cross-source depth. |
| `P09105`, `Q9UCM0` | 1 each | `verified_accession` | These are accession-verified only, which is the lowest evidence class in the cohort. |
| `P68871` | 2 | `probe_backed` | This is the only mixed-evidence row, and one lane is a summary-library probe rather than a direct live assay. |

## Why These Lanes Still Block Release-Grade Claims

The blocker is not cohort truthfulness. The blocker is that the current matrix still reads like a small set of evidence anchors plus a large set of thin controls:

- the strongest anchor is `P69905` with five lanes,
- `P68871` is multi-lane but still probe-backed on one lane,
- ten of the twelve accessions are single-lane,
- and the single-lane accessions are mostly identity or snapshot level rather than genuinely multi-source.

That is enough for a truthful launch and leakage control, but not enough to claim broad release-grade source coverage across the benchmark.

## Concrete Next Tasks

The next work should deepen lane coverage in the same places where the matrix is thin, without widening the cohort or inflating evidence classes.

| Task | What it should do | Suggested module ownership |
| --- | --- | --- |
| 1. Convert the probe-backed hemoglobin pair into direct PPI evidence | Replace the `P68871` probe lane with direct PPI evidence so the only mixed row becomes a fully direct anchor or is split out honestly. | [`execution/acquire/intact_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/intact_snapshot.py), [`execution/acquire/biogrid_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/biogrid_snapshot.py), [`execution/indexing/protein_pair_crossref.py`](D:/documents/ProteoSphereV2/execution/indexing/protein_pair_crossref.py), [`scripts/emit_source_coverage.py`](D:/documents/ProteoSphereV2/scripts/emit_source_coverage.py) |
| 2. Add structural lanes to the UniProt-only accessions | Give the six snapshot-backed UniProt rows an additional structural source lane where live or pinned data is available. | [`execution/acquire/rcsb_pdbe_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/rcsb_pdbe_snapshot.py), [`execution/acquire/alphafold_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/alphafold_snapshot.py) |
| 3. Add annotation and pathway lanes to the same thin rows | Use motif/domain and pathway acquisitions to turn identity-only rows into truly multimodal rows. | [`execution/acquire/interpro_motif_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/interpro_motif_snapshot.py), [`execution/acquire/reactome_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/reactome_snapshot.py) |
| 4. Expand evolutionary/MSA support beyond the single anchor | Turn the MSA lane from a one-protein anchor into a reusable source lane for more cohort members. | [`execution/acquire/evolutionary_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/evolutionary_snapshot.py), [`scripts/emit_source_coverage.py`](D:/documents/ProteoSphereV2/scripts/emit_source_coverage.py) |
| 5. Upgrade verified-accession rows out of the weakest evidence class | Materialize at least one more source lane for `P09105` and `Q9UCM0` so they are not only accession-verified. | [`execution/acquire/uniprot_snapshot.py`](D:/documents/ProteoSphereV2/execution/acquire/uniprot_snapshot.py), [`execution/acquire/supplemental_scrape_registry.py`](D:/documents/ProteoSphereV2/execution/acquire/supplemental_scrape_registry.py) |
| 6. Keep the coverage inventory conservative and machine-readable | Make sure lane depth, mixed-evidence flags, and thin-coverage labels stay explicit in downstream release notes and dashboards. | [`scripts/emit_source_coverage.py`](D:/documents/ProteoSphereV2/scripts/emit_source_coverage.py), [`scripts/emit_benchmark_provenance.py`](D:/documents/ProteoSphereV2/scripts/emit_benchmark_provenance.py), [`scripts/export_operator_dashboard.py`](D:/documents/ProteoSphereV2/scripts/export_operator_dashboard.py) |

## Recommended Ordering

If the team wants the smallest honest path to a stronger release claim, the right sequence is:

1. remove or upgrade the mixed probe-backed `P68871` lane,
2. add one structural lane to the six snapshot-backed UniProt-only accessions,
3. add one functional/pathway lane to those same accessions,
4. then widen evolutionary support and tighten reporting.

That sequence raises the evidence floor without changing the cohort or pretending that the current one-lane rows are already multimodal.

## Release-Oriented Interpretation

The safe language today is:

- the cohort is pinned and truthful,
- the coverage matrix is conservative and machine-readable,
- one accession has strong multimodal depth,
- one accession is probe-backed and still mixed,
- and ten accessions are still thin enough that they should block release-grade coverage claims.

Until at least some of those thin rows gain additional real lanes, the correct label remains **prototype-ready benchmark with release-safe coverage accounting**, not a release-grade benchmark corpus.
