# Packet Delta Report

- Generated at: `2026-03-31T19:59:35.588430+00:00`
- Comparison boundary: preserved packet baseline (`D:\documents\ProteoSphereV2\data\packages\LATEST.json`) vs freshest run-scoped packet state (`D:\documents\ProteoSphereV2\data\packages\training-packets-20260331T193611Z`)
- Latest preserved gap packets: `5`
- Freshest run packets with gaps: `12`
- Packet-level improvements: `0`
- Packet-level regressions: `11`
- Packet-level unchanged gaps: `1`
- Lower-layer evidence improvements: `0`
- Lower-layer evidence regressions: `11`
- Lower-layer evidence mixed: `0`
- Lower-layer evidence unchanged: `1`

Packet-level improvements are counted only when the freshest run reduces the
packet-level missing modality count. Lower-layer evidence changes are not
counted as improvements.

## Packet-Level Improvements

- none

## Lower-Layer Evidence Improvements

- none

## Packet-Level Regressions

- `P00387` latest_missing=`ligand` freshest_missing=`ligand,ppi,structure` delta=`2` refs=`ligand:P00387`
- `P02042` latest_missing=`none` freshest_missing=`ppi,structure` delta=`2` refs=`none`
- `P02100` latest_missing=`none` freshest_missing=`ppi,structure` delta=`2` refs=`none`
- `P04637` latest_missing=`none` freshest_missing=`ligand,structure` delta=`2` refs=`none`
- `P31749` latest_missing=`none` freshest_missing=`ppi,structure` delta=`2` refs=`none`
- `P68871` latest_missing=`none` freshest_missing=`ppi,structure` delta=`2` refs=`none`
- `P69892` latest_missing=`none` freshest_missing=`ppi,structure` delta=`2` refs=`none`
- `P69905` latest_missing=`none` freshest_missing=`ppi,structure` delta=`2` refs=`none`
- `P09105` latest_missing=`ligand` freshest_missing=`ligand,ppi` delta=`1` refs=`ligand:P09105`
- `Q2TAC2` latest_missing=`ligand` freshest_missing=`ligand,ppi` delta=`1` refs=`ligand:Q2TAC2`
- `Q9NZD4` latest_missing=`ligand` freshest_missing=`ppi,structure` delta=`1` refs=`ligand:Q9NZD4`

## Lower-Layer Evidence Regressions

- `P00387` latest_artifacts=`3` freshest_artifacts=`1` latest_notes=`4` freshest_notes=`6` truth=`fresh-run-evidence-regressed`
- `P02042` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P02100` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P04637` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P09105` latest_artifacts=`3` freshest_artifacts=`2` latest_notes=`4` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P31749` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P68871` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P69892` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `P69905` latest_artifacts=`4` freshest_artifacts=`2` latest_notes=`3` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `Q2TAC2` latest_artifacts=`3` freshest_artifacts=`2` latest_notes=`4` freshest_notes=`5` truth=`fresh-run-evidence-regressed`
- `Q9NZD4` latest_artifacts=`3` freshest_artifacts=`2` latest_notes=`4` freshest_notes=`5` truth=`fresh-run-evidence-regressed`

## Unchanged Remaining Gaps

- `Q9UCM0` latest_missing=`structure,ligand,ppi` freshest_missing=`ligand,ppi,structure` delta=`0` refs=`structure:Q9UCM0,ligand:Q9UCM0,ppi:Q9UCM0`

## Lower-Layer Evidence Mixed

- none

## Remaining Freshest Gaps

| Accession | Packet delta | Evidence delta | Latest missing | Freshest missing | Latest refs |
| --- | --- | --- | --- | --- | --- |
| `Q9UCM0` | `fresh-run-unchanged` | `fresh-run-evidence-unchanged` | `structure,ligand,ppi` | `ligand,ppi,structure` | `structure:Q9UCM0,ligand:Q9UCM0,ppi:Q9UCM0` |
| `P00387` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `ligand` | `ligand,ppi,structure` | `ligand:P00387` |
| `P09105` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `ligand` | `ligand,ppi` | `ligand:P09105` |
| `Q2TAC2` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `ligand` | `ligand,ppi` | `ligand:Q2TAC2` |
| `Q9NZD4` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `ligand` | `ppi,structure` | `ligand:Q9NZD4` |
| `P02042` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ppi,structure` | `none` |
| `P02100` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ppi,structure` | `none` |
| `P04637` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ligand,structure` | `none` |
| `P31749` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ppi,structure` | `none` |
| `P68871` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ppi,structure` | `none` |
| `P69892` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ppi,structure` | `none` |
| `P69905` | `fresh-run-regressed` | `fresh-run-evidence-regressed` | `none` | `ppi,structure` | `none` |
