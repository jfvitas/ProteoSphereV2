# P22 Soak Anomaly Digest

This digest summarizes incident patterns in the soak ledger. It does not upgrade the run to a completed weeklong durability claim.

## Window

- Entries: `12916`
- First observed at: `2026-03-23T09:56:20.928664+00:00`
- Last observed at: `2026-04-05T19:56:10.110868+00:00`
- Observed window: `322.0` hours

## Incident Pattern

- Incident count: `4`
- Incident status counts: `{'unavailable': 4}`
- Queue transition count: `103`
- Longest healthy streak: `12912` samples
- Current healthy streak: `12912` samples

## Recent Incidents

- `2026-03-23T09:56:20.928664+00:00` status=`unavailable` age_seconds=`None`
- `2026-03-23T09:56:36.404126+00:00` status=`unavailable` age_seconds=`None`
- `2026-03-23T09:57:11.395452+00:00` status=`unavailable` age_seconds=`None`
- `2026-03-23T09:57:36.666785+00:00` status=`unavailable` age_seconds=`None`

## Truth Boundary

- Weeklong claim allowed: `False`
- Prototype runtime boundary: `True`
