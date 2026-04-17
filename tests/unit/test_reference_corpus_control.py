from __future__ import annotations

import pytest

from core.storage.reference_corpus_control import (
    CorpusProgramState,
    LaneClaim,
    UnifiedSourceRecord,
    WorkUnit,
    WorkerHeartbeat,
    claim_work_units,
    compute_completion_ledger,
    recover_active_claims,
)


def test_unified_source_record_round_trips_and_normalizes_lane() -> None:
    record = UnifiedSourceRecord(
        source_id="string:20260411T000000Z",
        source_family="string",
        snapshot_id="20260411T000000Z",
        volume="D:",
        root_paths=("D:/raw/string/20260411T000000Z",),
        kind="raw-authoritative",
        bytes=120,
        fingerprint="abc123",
        integration_status="planned",
        validation_status="unknown",
        file_count=3,
        lane="interaction-network",
    )

    restored = UnifiedSourceRecord.from_dict(record.to_dict())

    assert restored.kind == "raw_authoritative"
    assert restored.lane == "interaction_network"
    assert restored.bytes == 120


def test_claim_work_units_respects_existing_overlap_and_expires_old_claims() -> None:
    units = (
        WorkUnit(
            work_unit_id="string:current:threshold_999-part-00",
            lane="interaction_network",
            source_family="string",
            snapshot_id="current",
            shard_key="threshold_999-part-00",
            inputs=("D:/raw/string/current",),
            expected_outputs=("E:/staging/string/00",),
        ),
        WorkUnit(
            work_unit_id="string:current:threshold_999-part-01",
            lane="interaction_network",
            source_family="string",
            snapshot_id="current",
            shard_key="threshold_999-part-01",
            inputs=("D:/raw/string/current",),
            expected_outputs=("E:/staging/string/01",),
        ),
    )
    stale_claim = LaneClaim(
        claim_id="claim:old",
        work_unit_id="string:current:threshold_999-part-00",
        lane="interaction_network",
        source_family="string",
        snapshot_id="current",
        shard_key="threshold_999-part-00",
        lease_owner="worker-a",
        lease_expires_at="2026-04-10T00:00:00+00:00",
    )

    recovered = recover_active_claims((stale_claim,), now="2026-04-11T00:00:00+00:00")
    claimed_units, claims = claim_work_units(
        units,
        recovered,
        worker_id="worker-b",
        lane="interaction_network",
        limit=1,
        ttl_seconds=600,
        now="2026-04-11T00:00:00+00:00",
    )

    assert not recovered
    assert claimed_units[0].lease_owner == "worker-b"
    assert claims[0].shard_key == "threshold_999-part-00"


def test_lane_claim_requires_iso_timestamp() -> None:
    with pytest.raises(ValueError):
        LaneClaim(
            claim_id="claim:bad",
            work_unit_id="work:bad",
            lane="interaction_network",
            source_family="string",
            snapshot_id="current",
            shard_key="all",
            lease_owner="worker-a",
            lease_expires_at="not-a-timestamp",
        )


def test_completion_ledger_separates_strict_partial_duplicate_and_blocked_bytes() -> None:
    records = (
        UnifiedSourceRecord(
            source_id="uniprot:current",
            source_family="uniprot",
            snapshot_id="current",
            volume="D:",
            root_paths=("D:/raw/uniprot",),
            kind="raw_authoritative",
            bytes=100,
            fingerprint="fp1",
            integration_status="promoted",
            validation_status="passed",
        ),
        UnifiedSourceRecord(
            source_id="string:current",
            source_family="string",
            snapshot_id="current",
            volume="D:",
            root_paths=("D:/raw/string",),
            kind="raw_authoritative",
            bytes=40,
            fingerprint="fp2",
            integration_status="partial",
            validation_status="warning",
            duplicate_bytes=10,
        ),
        UnifiedSourceRecord(
            source_id="sabio_rk:current",
            source_family="sabio_rk",
            snapshot_id="current",
            volume="D:",
            root_paths=("D:/raw/sabio_rk",),
            kind="raw_authoritative",
            bytes=20,
            fingerprint="fp3",
            integration_status="blocked",
            validation_status="failed",
        ),
    )

    ledger = compute_completion_ledger(records)

    assert ledger.strict_validated_bytes == 100
    assert ledger.partial_bytes == 40
    assert ledger.duplicate_bytes == 10
    assert ledger.blocked_bytes == 20
    assert ledger.untouched_bytes == 0


def test_completion_ledger_uses_work_unit_progress_to_weight_strict_bytes() -> None:
    records = (
        UnifiedSourceRecord(
            source_id="alphafold:current",
            source_family="alphafold",
            snapshot_id="current",
            volume="D:",
            root_paths=("D:/raw/alphafold/current",),
            kind="raw_authoritative",
            bytes=160,
            fingerprint="fp-a",
            integration_status="discovered",
            validation_status="unknown",
        ),
    )
    work_units = (
        WorkUnit(
            work_unit_id="alphafold:current:prefix-00",
            lane="structure",
            source_family="alphafold",
            snapshot_id="current",
            shard_key="prefix-00",
            inputs=("D:/raw/alphafold/current",),
            expected_outputs=("E:/normalized/alphafold/prefix-00",),
            status="promoted",
        ),
        WorkUnit(
            work_unit_id="alphafold:current:prefix-01",
            lane="structure",
            source_family="alphafold",
            snapshot_id="current",
            shard_key="prefix-01",
            inputs=("D:/raw/alphafold/current",),
            expected_outputs=("E:/normalized/alphafold/prefix-01",),
            status="planned",
        ),
    )

    ledger = compute_completion_ledger(records, work_units=work_units)

    assert ledger.strict_validated_bytes == 80
    assert ledger.partial_bytes == 80
    assert ledger.blocked_bytes == 0
    assert ledger.untouched_bytes == 0
    assert ledger.source_counts_by_state["partial"] == 1


def test_program_state_round_trips_active_workers() -> None:
    state = CorpusProgramState(
        operating_mode="Hybrid First",
        milestone="Disk Corpus First",
        control_model="Central Orchestrator",
        cycle_index=3,
        active_workers=(
            WorkerHeartbeat(
                worker_id="registrar-1",
                lane="identity_sequence",
                lease_ids=("claim:a",),
                status="active",
            ),
        ),
        active_claim_count=1,
        resource_tokens={"duckdb/promoter": 1},
        last_cycle_summary={"source_record_count": 12},
    )

    restored = CorpusProgramState.from_dict(state.to_dict())

    assert restored.cycle_index == 3
    assert restored.active_workers[0].worker_id == "registrar-1"
    assert restored.resource_tokens["duckdb/promoter"] == 1
