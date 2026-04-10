# Packet Delta Operator Summary

- Generated at: `2026-03-31T20:03:23.879791+00:00`
- Comparison boundary: preserved packet baseline (`D:\documents\ProteoSphereV2\data\packages\LATEST.json`) vs freshest run-scoped packet state (`D:\documents\ProteoSphereV2\data\packages\training-packets-20260331T193611Z`)
- Still latest-baseline blockers: `5`
- Fresh-run evidence not promotable: `7`
- Actionable packet count: `12`
- Latest preserved gap packets: `5`
- Freshest remaining gap packets: `12`

This surface only summarizes the current packet delta and deficit artifacts.
It does not change the latest-promotion guard or claim anything promotable on its own.

## Still Latest-Baseline Blockers

| Accession | Latest missing | Freshest missing | Truth | Next action |
| --- | --- | --- | --- | --- |
| `Q9UCM0` | `structure, ligand, ppi` | `ligand, ppi, structure` | `fresh-run-unchanged` | Resolve the preserved-baseline blocker in structure, ligand, ppi; start from source refs structure:Q9UCM0, ligand:Q9UCM0, ppi:Q9UCM0 and rerun the packet path. |
| `P00387` | `ligand` | `ligand, ppi, structure` | `fresh-run-regressed` | Resolve the preserved-baseline blocker in ligand; start from source refs ligand:P00387 and rerun the packet path. |
| `P09105` | `ligand` | `ligand, ppi` | `fresh-run-regressed` | Resolve the preserved-baseline blocker in ligand; start from source refs ligand:P09105 and rerun the packet path. |
| `Q2TAC2` | `ligand` | `ligand, ppi` | `fresh-run-regressed` | Resolve the preserved-baseline blocker in ligand; start from source refs ligand:Q2TAC2 and rerun the packet path. |
| `Q9NZD4` | `ligand` | `ppi, structure` | `fresh-run-regressed` | Resolve the preserved-baseline blocker in ligand; start from source refs ligand:Q9NZD4 and rerun the packet path. |

## Fresh-Run Evidence Not Promotable

| Accession | Latest missing | Freshest missing | Truth | Next action |
| --- | --- | --- | --- | --- |
| `P02042` | `none` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P02100` | `none` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P04637` | `none` | `ligand, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ligand, structure before any promotion attempt. |
| `P31749` | `none` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P68871` | `none` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P69892` | `none` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P69905` | `none` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |

## Truth Boundary

- Preserved-baseline blockers are still blocking the latest baseline and should be fixed first.
- Fresh-run not promotable items are fresh-run regressions only; they should be repaired before any promotion attempt.
