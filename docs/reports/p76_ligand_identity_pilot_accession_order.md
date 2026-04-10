# p76 Ligand Identity Pilot Accession Order

This note orders the ligand identity pilot accessions using the current support-ready surface, the packet deficit dashboard, and the local ligand gap probe.

## Order

1. `P00387`
2. `Q9NZD4`
3. `P09105`
4. `Q2TAC2`
5. `Q9UCM0` deferred

## Why This Order

`P00387` is first because it is the lead anchor in the support-ready preview and the packet dashboard names it as the top single-modality ligand fix candidate. The next truthful stage for it is local bulk assay ingestion.

`Q9NZD4` is second because it is the only accession in the current support set marked `rescuable_now`, and the local gap probe gives a concrete structure bridge at `1Y01`.

`P09105` and `Q2TAC2` come after that because they remain structure-companion-only lanes with no truthful local ligand rescue candidate yet. They are valid pilot accessions, but they should stay in hold-for-acquisition status for now.

`Q9UCM0` stays deferred because the support slice explicitly excludes it and the packet dashboard still shows unresolved structure, ligand, and ppi deficits.

## Truth Boundary

- report-only
- no ligand row materialization
- no bundle mutation
- no latest-promotion changes
- `Q9UCM0` deferred

## Bottom Line

The compact pilot ordering is `P00387` first, `Q9NZD4` second, then `P09105` and `Q2TAC2` as hold-for-acquisition lanes, with `Q9UCM0` deferred.
