# P22 Rolling Soak Evidence Summary

This report summarizes the current append-only soak ledger. It is not a claim that the weeklong soak has already completed.

## Current Window

- Ledger entries: `12916`
- First observed at: `2026-03-23T09:56:20.928664+00:00`
- Last observed at: `2026-04-05T19:56:10.110868+00:00`
- Observed window: `322.0` hours
- Progress to weeklong threshold: `1.0`
- Remaining to weeklong threshold: `0.0` hours
- Estimated weeklong threshold at: `2026-03-30T09:56:20.928664+00:00`

## Heartbeat Quality

- Status counts: `{'healthy': 12912, 'unavailable': 4}`
- Non-healthy incidents: `4`
- Healthy sample ratio: `0.9997`
- Max heartbeat age seen: `40` seconds

## Queue Snapshot

- Latest queue counts: `{'blocked': 1, 'done': 483}`
- Queue high-water marks: `{'blocked': 12, 'dispatched': 11, 'done': 483, 'pending': 95, 'ready': 4}`
- Latest benchmark completion status: `blocked_on_release_grade_bar`

## Truth Boundary

- Prototype runtime boundary remains active: `True`
- Weeklong requirement met: `True`
- Weeklong claim allowed: `False`

## Judgment

The rolling ledger is useful for unattended validation, but it does not yet justify a completed weeklong durability claim.
