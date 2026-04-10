# Packet Operator Blocker Surface

- Generated at: `2026-03-31T20:07:38.190842+00:00`
- Comparison boundary: preserved packet baseline (`D:\documents\ProteoSphereV2\data\packages\LATEST.json`) vs freshest run-scoped packet state (`D:\documents\ProteoSphereV2\data\packages\training-packets-20260331T193611Z`)
- Preserved latest blockers: `5`
- Fresh-run regressions not promotable: `7`
- Next-best actionable rescues: `7`

This surface is operator-facing only. It summarizes the current protected packet deficit dashboard, the packet delta summary, and the delta report without changing promotion rules.

## Preserved Latest Blockers

| Accession | Latest missing | Freshest missing | Next rescue | Next action |
| --- | --- | --- | --- | --- |
| `Q9UCM0` | `structure, ligand, ppi` | `ligand, ppi, structure` | `ligand:Q9UCM0` | Apply ligand:Q9UCM0 to clear Q9UCM0. |
| `P00387` | `ligand` | `ligand, ppi, structure` | `ligand:P00387` | Apply ligand:P00387 to clear P00387. |
| `P09105` | `ligand` | `ligand, ppi` | `ligand:P09105` | Apply ligand:P09105 to clear P09105. |
| `Q2TAC2` | `ligand` | `ligand, ppi` | `ligand:Q2TAC2` | Apply ligand:Q2TAC2 to clear Q2TAC2. |
| `Q9NZD4` | `ligand` | `ppi, structure` | `ligand:Q9NZD4` | Apply ligand:Q9NZD4 to clear Q9NZD4. |

## Fresh-Run Regressions Not Promotable

| Accession | Freshest missing | Truth | Next action |
| --- | --- | --- | --- |
| `P02042` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P02100` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P04637` | `ligand, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ligand, structure before any promotion attempt. |
| `P31749` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P68871` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P69892` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |
| `P69905` | `ppi, structure` | `fresh-run-regressed` | Repair the fresh-run regression in ppi, structure before any promotion attempt. |

## Next-Best Actionable Rescues

| Source ref | Packet accessions | Leverage | Blockers cleared | Next action |
| --- | --- | --- | --- | --- |
| `ligand:P00387` | `P00387` | `5` | `P00387` | Apply ligand:P00387 to clear P00387. |
| `ligand:P09105` | `P09105` | `5` | `P09105` | Apply ligand:P09105 to clear P09105. |
| `ligand:Q2TAC2` | `Q2TAC2` | `5` | `Q2TAC2` | Apply ligand:Q2TAC2 to clear Q2TAC2. |
| `ligand:Q9NZD4` | `Q9NZD4` | `5` | `Q9NZD4` | Apply ligand:Q9NZD4 to clear Q9NZD4. |
| `ligand:Q9UCM0` | `Q9UCM0` | `5` | `Q9UCM0` | Apply ligand:Q9UCM0 to clear Q9UCM0. |
| `structure:Q9UCM0` | `Q9UCM0` | `1` | `Q9UCM0` | Apply structure:Q9UCM0 to clear Q9UCM0. |
| `ppi:Q9UCM0` | `Q9UCM0` | `1` | `Q9UCM0` | Apply ppi:Q9UCM0 to clear Q9UCM0. |

## Truth Boundary

- Preserved latest blockers are still blockers in the protected baseline.
- Fresh-run regressions are not promotable and remain separate from the preserved baseline blockers.
- Rescues are source-level fixes only and do not imply promotion.
