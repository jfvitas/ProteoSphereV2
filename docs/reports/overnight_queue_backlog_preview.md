# Overnight Queue Backlog Preview

- Status: `report_only`
- Job count: `22`
- Active jobs: `0`
- Supervisor pending jobs: `0`
- Catalog jobs: `22`

## Jobs

- `1` `overnight_catalog` `P2-I016` / `Validate provenance integrity`
  detail: priority=high, phase=2
- `2` `overnight_catalog` `P3-I014` / `Build downloaded source release matrix`
  detail: priority=high, phase=3
- `3` `overnight_catalog` `P3-I018` / `Revalidate procurement integrity after hardening`
  detail: priority=high, phase=3
- `4` `overnight_catalog` `P3-T017` / `Implement RCSB and PDBe acquisition pipeline`
  detail: priority=high, phase=3
- `5` `overnight_catalog` `P3-T018` / `Implement UniProt acquisition pipeline`
  detail: priority=high, phase=3
- `6` `overnight_catalog` `P3-T019` / `Implement BindingDB acquisition pipeline`
  detail: priority=high, phase=3
- `7` `overnight_catalog` `P3-T020` / `Implement BioGRID acquisition pipeline`
  detail: priority=high, phase=3
- `8` `overnight_catalog` `P3-T021` / `Implement IntAct acquisition pipeline`
  detail: priority=high, phase=3
- `9` `overnight_catalog` `P3-T023` / `Implement InterPro and motif acquisition pipeline`
  detail: priority=high, phase=3
- `10` `overnight_catalog` `P3-T029` / `Repair evolutionary corpus acquisition pipeline`
  detail: priority=high, phase=3
- `11` `overnight_catalog` `P4-I012` / `Validate training package materialization`
  detail: priority=high, phase=4
- `12` `overnight_catalog` `P4-T009` / `Implement selective materializer`
  detail: priority=high, phase=4
- `13` `overnight_catalog` `P6-I004` / `Validate summary library on real source corpus`
  detail: priority=high, phase=6
- `14` `overnight_catalog` `P6-I023` / `Validate benchmark release artifact integrity`
  detail: priority=high, phase=6
- `15` `overnight_catalog` `P6-I030` / `Revalidate release artifacts after audit hardening`
  detail: priority=high, phase=6
- `16` `overnight_catalog` `P6-T003` / `Implement summary library builder`
  detail: priority=high, phase=6
- `17` `overnight_catalog` `P6-T008` / `Materialize benchmark corpus bundle`
  detail: priority=high, phase=6
- `18` `overnight_catalog` `P6-T010` / `Materialize frozen 12-accession benchmark cohort`
  detail: priority=high, phase=6
- `19` `overnight_catalog` `P7-T001` / `Stabilize hardened manifest identity assertions`
  detail: priority=high, phase=7
- `20` `overnight_catalog` `P7-T002` / `Resolve AlphaFold invalid-manifest expectation drift`
  detail: priority=high, phase=7
- `21` `overnight_catalog` `P8-T001` / `Lint-harden package and storage slice`
  detail: priority=high, phase=8
- `22` `overnight_catalog` `P8-T006` / `Lint-harden remaining execution test debt`
  detail: priority=high, phase=8

## Truth Boundary

- This backlog is report-only. It ranks the next 12-hour window from the observed supervisor state and the task catalog, but it does not launch or duplicate any job.
