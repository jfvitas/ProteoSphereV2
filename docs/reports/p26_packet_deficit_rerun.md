# P26 Packet Deficit Rerun

- Generated at: `2026-03-23T15:53:09.923959+00:00`
- Latest-only view: `True`
- Packet count: `12`
- Packet status counts: `{'complete': 4, 'partial': 8}`
- Packet deficit count: `8`
- Modality deficit counts: `{'ligand': 7, 'ppi': 1, 'sequence': 0, 'structure': 1}`

## Key Result

The current selected cohort is materially stronger than before:
- complete packets moved to `4`
- partial packets moved to `8`
- structure deficit dropped to `1`
- ligand deficit dropped to `7`
- PPI deficit remains `1`

## Highest-Leverage Remaining Fixes

- The dominant remaining bottleneck is ligand coverage for `P00387`, `P09105`, `P69892`, `P69905`, `Q2TAC2`, `Q9NZD4`, and `Q9UCM0`.
- The only remaining structure gap is `Q9UCM0`.
- The only remaining PPI gap is `P04637` under the current non-self IntAct rule.

## Artifact Paths

- Deficit dashboard JSON: `artifacts/status/packet_deficit_dashboard.json`
- Deficit dashboard markdown: `docs/reports/packet_deficit_dashboard.md`
