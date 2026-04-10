# P18 Packet Rebuild Determinism

Date: 2026-03-22  
Task: `P18-I007`

## Verdict

The packet rebuild path is **deterministic for the same pinned inputs**, and explicit drift detection works when the rebuilt packet changes.

Using the new rehydration CLI, rerunning the same manifest with the same pinned artifact mapping yields the same packet identity checksum even when run metadata changes. When a pinned artifact is missing and the remaining artifact checksum changes, the rebuild is kept explicitly `partial` and the checksum audit marks the packet as `drifted`.

## What Was Proven

- The rehydration CLI can replay the same pinned packet twice and preserve the same `asset_identity_checksum`.
- Run metadata changes such as `materialization_run_id` and `materialized_at` do not change packet identity.
- A reference checksum audit can distinguish a stable rerun (`drift_state = same`) from a changed rebuild (`drift_state = drifted`).
- Missing pinned artifacts remain explicit through both the materialization result and the checksum audit.

## What Remains Explicit

- This validates deterministic rebuild behavior for the pinned packet replay path, not full corpus equivalence.
- A `partial_rehydration` result is still a degraded rebuild, even when the CLI is allowed to return success.
- The weeklong unattended soak remains a separate open validation lane.

## Evidence Used

- [rehydrate_training_packet.py](D:/documents/ProteoSphereV2/scripts/rehydrate_training_packet.py)
- [test_packet_rebuild_determinism.py](D:/documents/ProteoSphereV2/tests/integration/test_packet_rebuild_determinism.py)
- [test_packet_rehydration.py](D:/documents/ProteoSphereV2/tests/integration/test_packet_rehydration.py)

## Verification

- `python -m pytest tests\\integration\\test_packet_rebuild_determinism.py tests\\integration\\test_packet_rehydration.py -q`
- `python -m ruff check scripts\\rehydrate_training_packet.py tests\\integration\\test_packet_rehydration.py tests\\integration\\test_packet_rebuild_determinism.py`

## Integration Read

This is the right determinism boundary for the current queue: pinned packet rebuilds are reproducible when the selected inputs stay the same, and the system is honest when the rebuilt packet drifts or only partially materializes.
