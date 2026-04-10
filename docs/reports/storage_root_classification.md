# Storage Root Classification

- Generated at: `2026-04-01T00:00:00-05:00`
- Scope: read-only dedupe planning for the current raw/local mirror setup
- Cleanup rule: protect source-of-record, latest-pointer, and active run-log roots unless a separate retention or promotion decision exists

This index is intentionally conservative. Roots marked `mirror` are the only ones that should be treated as duplicate-byte cleanup candidates, and even then only after checksum and manifest agreement with the source-of-record.

## Source Of Record

| Root | Role | Cleanup safety |
| --- | --- | --- |
| `data/raw/protein_data_scope_seed` | Pinned seed mirror and provenance anchor for the protein data scope. | Protect. Do not dedupe away or move without replacement provenance and a confirmed downstream pointer update. |
| `data/raw/uniprot` | Primary UniProt raw source root used to anchor protein identity and joins. | Protect. Only collapse exact duplicates inside this source family after manifest and checksum agreement. |
| `data/raw/alphafold` | Primary AlphaFold raw source root for predicted-structure payloads. | Protect. Do not merge with local mirror roots unless the payload hash and source manifest agree. |
| `data/raw/bindingdb` | Primary BindingDB raw source root for assay and ligand evidence. | Protect. Exact duplicates may be removed only after source/version checks prove they are redundant. |
| `data/raw/intact` | Primary IntAct raw source root for PPI evidence and interaction lineages. | Protect. Keep direct evidence and provenance records stable across scans. |
| `data/raw/pdbbind` | Primary PDBbind raw source root for structure-backed ligand evidence. | Protect. Only exact redundant copies within the same release boundary are cleanup candidates. |
| `data/raw/rcsb_pdbe` | Primary RCSB/PDBe raw source root for structure and residue-context evidence. | Protect. Treat as authoritative source input, not as a mirror target. |

## Mirror

| Root | Role | Cleanup safety |
| --- | --- | --- |
| `data/raw/alphafold_local` | Local mirror root for AlphaFold payloads and staging copies. | Cleanup candidate only after checksum match to the source-of-record and confirmation that no active transfer is in flight. |
| `data/raw/bindingdb_dump_local` | Local mirror root for BindingDB dump material. | Cleanup candidate only if the authoritative BindingDB payload is already captured elsewhere and no current run is writing here. |
| `data/raw/local_copies` | Local mirror root used by copy-planning and local staging workflows. | Cleanup candidate after file identity is proven against the source-of-record and there is no robocopy or partial-transfer evidence. |

## Run Log

| Root | Role | Cleanup safety |
| --- | --- | --- |
| `data/raw/local_registry` | Timestamped local import run manifests and registry snapshots. | Retain as audit trail. Archive only under an explicit retention policy; do not dedupe into payload roots. |
| `data/raw/local_registry_runs` | Reserved run-log root for local registry execution traces. | Retain if populated. Treat as operational history, not as content storage. |
| `data/raw/bootstrap_runs` | Bootstrap execution outputs and run history under the raw storage tree. | Archive rather than dedupe. Keep long enough to explain how the raw tree was established. |
| `artifacts/runtime` | Runtime process and supervisor traces used by the monitoring surfaces. | Retain until downstream reports are regenerated and the audit window closes. |
| `logs` | Top-level workspace log sink for operator and execution traces. | Retain or archive by log retention policy; do not treat as payload duplication. |
| `runs/bridge_ligand_regen_check` | Execution trace for a ligand regeneration check run. | Retain until the run is superseded and the evidence is captured elsewhere. |
| `runs/bridge_ligand_regen_check_v2` | Second execution trace for the ligand regeneration check lane. | Retain as versioned run history; only archive under an explicit policy. |
| `runs/bridge_ligand_regen_check_v3` | Third execution trace for the ligand regeneration check lane. | Retain as run evidence. Do not dedupe into the copy or source trees. |
| `runs/canonical_selector_fix_check` | Execution trace for the canonical selector fix check. | Retain for auditability; treat as evidence of a check, not as a reusable payload. |
| `runs/tier1_direct_validation` | Validation run history for the tier-1 direct validation path. | Retain until the validation outputs are published and captured in report form. |

## Latest Pointer

| Root | Role | Cleanup safety |
| --- | --- | --- |
| `data/packages/LATEST.json` | Current preserved packet baseline pointer. | Protect. Never dedupe or rename without controlled promotion logic and a replacement pointer update. |
| `data/packages/LATEST.partial.json` | Partial latest pointer used during incomplete or transitional materialization. | Protect. Keep it available until a new latest pointer has been fully promoted or retired. |

## Derived Output

| Root | Role | Cleanup safety |
| --- | --- | --- |
| `data/canonical` | Canonical store for normalized object graphs and durable entity records. | Rebuildable only if the upstream raw inputs and canonicalization logic are still available and the current release does not depend on the snapshot. |
| `data/features` | Rebuildable feature cache and compact derived training surface. | Rebuildable from upstream manifests and canonical data; keep current snapshots if a run or report still cites them. |
| `data/planning_index` | Hot planning index for source routing and candidate generation. | Rebuildable from pinned inputs; remove only when a fresh index is already materialized. |
| `data/reports` | Workspace-generated report outputs stored alongside the data tree. | Safe to refresh from source artifacts, but preserve any report that is still referenced by a downstream review or board. |
| `artifacts/status` | Current machine-readable status and board artifacts. | Rebuildable from the live scripts and source inputs; keep the latest snapshot that operators are reading. |
| `docs/reports` | Human-readable report mirror for the status and planning surfaces. | Rebuildable, but retain any report that is currently cited or under review. |
| `runs/real_data_benchmark` | Benchmark run tree containing manifests, summaries, and final results. | Rebuildable in principle, but keep the current run tree while it is the audit and comparison baseline. |
| `data/packages/selected_cohort_materialization.json` | Materialized selected-cohort payload used by packet and procurement surfaces. | Rebuildable from the materialization pipeline, but keep while it is the current selection input for downstream reports. |

## Cleanup Rules

- Source-of-record roots are not dedupe targets. Use them as checksum baselines.
- Mirror roots are the only roots that should routinely be examined for byte-for-byte redundancy.
- Run-log roots should be retained or archived by policy, not collapsed into payload roots.
- Latest-pointer roots are operational control points and should never be deduped away.
- Derived-output roots are rebuildable, but only when no current report, board, or audit surface still depends on them.

