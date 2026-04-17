from __future__ import annotations

import gzip
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from scripts.reference_corpus_orchestrator import (
    _acquire_control_lock,
    _hash_shard_key,
    _merge_work_units,
    build_source_registry,
    claim_for_worker,
    claim_specific_work_unit,
    discover_corpus_objects,
    heartbeat_worker,
    materialize_claimed_work_unit,
    plan_work_units,
    promote_validated_work_units,
    record_validation_receipt,
    run_worker_batch,
    run_worker_once,
    set_loop_control,
    tick_corpus_orchestrator,
)
from core.storage.reference_corpus_control import WorkUnit


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovery_and_registry_prefer_repo_raw_as_canonical_root(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    repo_local_copies = tmp_path / "repo_local_copies"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "string" / "20260411T000000Z" / "a.txt", "authoritative")
    _write_text(repo_local_copies / "string" / "20260411T000000Z" / "b.txt", "dup")
    (warehouse_root / "staging").mkdir(parents=True)

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "repo_local_copies": repo_local_copies,
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        }
    )
    registry = build_source_registry(discovered_objects=discovered, warehouse_manifest_path=None)
    string_record = next(record for record in registry if record.source_family == "string")

    assert string_record.kind == "raw_authoritative"
    assert string_record.authoritative_root.startswith(str(repo_raw))
    assert string_record.duplicate_bytes > 0
    assert len(string_record.root_paths) == 2


def test_tick_writes_control_records_and_claim_updates_lane_claims(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "uniprot" / "20260411T000000Z" / "entry.tsv", "P69905")

    payload = tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )

    assert payload["status"] == "ok"
    assert Path(payload["source_registry_path"]).exists()
    assert Path(payload["work_units_path"]).exists()
    assert Path(payload["completion_ledger_path"]).exists()

    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="extractor-1",
        lane="identity_sequence",
        limit=1,
        ttl_seconds=600,
    )
    claims_path = warehouse_root / "control" / "lane_claims.json"
    claims_payload = json.loads(claims_path.read_text(encoding="utf-8"))

    assert claimed["status"] == "claimed"
    assert claimed["work_units"]
    assert claims_payload[0]["lease_owner"] == "extractor-1"

    heartbeat = heartbeat_worker(
        warehouse_root=warehouse_root,
        worker_id="extractor-1",
        lane="identity_sequence",
        lease_ids=("claim:test",),
        status="active",
    )
    state = json.loads((warehouse_root / "control" / "program_state.json").read_text(encoding="utf-8"))
    stopped = set_loop_control(warehouse_root=warehouse_root, stop_requested=True)

    assert heartbeat["status"] == "heartbeat_recorded"
    assert state["active_workers"][0]["worker_id"] == "extractor-1"
    assert stopped["stop_requested"] is True

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    assert any(unit["lease_owner"] == "extractor-1" for unit in work_units_payload["work_units"])


def test_acquire_control_lock_releases_stale_lock_file(tmp_path: Path) -> None:
    lock_path = tmp_path / "dispatch.lock"
    lock_path.write_text("stale", encoding="utf-8")
    stale_time = lock_path.stat().st_mtime - 3600
    lock_path.touch()
    import os

    os.utime(lock_path, (stale_time, stale_time))

    with _acquire_control_lock(lock_path, timeout_seconds=0.1, stale_after_seconds=1.0, poll_interval=0.01):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_claim_paths_use_dispatch_lock(tmp_path: Path, monkeypatch) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "uniprot" / "20260411T000000Z" / "entry.tsv", "P69905")
    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )

    lock_paths: list[Path] = []

    @contextmanager
    def fake_lock(path: Path, **_: object):
        lock_paths.append(path)
        yield

    monkeypatch.setattr("scripts.reference_corpus_orchestrator._acquire_control_lock", fake_lock)

    claim_result = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="dispatch-worker-1",
        lane="identity_sequence",
        limit=1,
        ttl_seconds=600,
    )
    claim_specific_work_unit(
        warehouse_root=warehouse_root,
        worker_id="dispatch-worker-1",
        work_unit_id=claim_result["work_units"][0]["work_unit_id"],
        ttl_seconds=600,
    )

    expected_lock = warehouse_root / "control" / "dispatch.lock"
    assert lock_paths == [expected_lock, expected_lock]


def test_merge_work_units_reopens_promoted_unit_when_source_bytes_change() -> None:
    planned = (
        WorkUnit(
            work_unit_id="uniparc:20260412T082248Z:all",
            lane="identity_sequence",
            source_family="uniparc",
            snapshot_id="20260412T082248Z",
            shard_key="all",
            inputs=("D:/raw/uniparc/20260412T082248Z",),
            expected_outputs=("E:/warehouse/staging/uniparc", "E:/warehouse/normalized/uniparc"),
            status="planned",
            metadata={"bytes": 400, "file_count": 9, "source_id": "uniparc:20260412T082248Z"},
        ),
    )
    existing = (
        WorkUnit(
            work_unit_id="uniparc:20260412T082248Z:all",
            lane="identity_sequence",
            source_family="uniparc",
            snapshot_id="20260412T082248Z",
            shard_key="all",
            inputs=("D:/raw/uniparc/20260412T082248Z",),
            expected_outputs=("E:/warehouse/staging/uniparc", "E:/warehouse/normalized/uniparc"),
            status="promoted",
            metadata={
                "bytes": 100,
                "file_count": 3,
                "source_id": "uniparc:20260412T082248Z",
                "promotion_id": "promotion:old",
            },
        ),
    )

    merged = _merge_work_units(planned, existing)

    assert merged[0].status == "planned"
    assert merged[0].lease_owner is None
    assert merged[0].metadata["bytes"] == 400
    assert merged[0].metadata["reopened_due_to_source_drift"] is True


def test_merge_work_units_keeps_promoted_unit_when_only_input_path_changes() -> None:
    planned = (
        WorkUnit(
            work_unit_id="uniprot:current:hash-00",
            lane="identity_sequence",
            source_family="uniprot",
            snapshot_id="current",
            shard_key="hash-00",
            inputs=("E:/ProteoSphere/reference_library/incoming_mirrors/uniprot/current/uniprot",),
            expected_outputs=("D:/ProteoSphere/reference_library/staging/uniprot", "D:/ProteoSphere/reference_library/normalized/uniprot"),
            status="validated_unpromoted",
            metadata={
                "bytes": 100,
                "file_count": 3,
                "source_id": "uniprot:current",
                "fingerprint": "same-fingerprint",
            },
        ),
    )
    existing = (
        WorkUnit(
            work_unit_id="uniprot:current:hash-00",
            lane="identity_sequence",
            source_family="uniprot",
            snapshot_id="current",
            shard_key="hash-00",
            inputs=("D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/uniprot",),
            expected_outputs=("E:/ProteoSphere/reference_library/staging/uniprot", "E:/ProteoSphere/reference_library/normalized/uniprot"),
            status="promoted",
            metadata={
                "bytes": 100,
                "file_count": 3,
                "source_id": "uniprot:current",
                "fingerprint": "same-fingerprint",
                "promotion_id": "promotion:old",
            },
        ),
    )

    merged = _merge_work_units(planned, existing)

    assert merged[0].status == "promoted"
    assert merged[0].inputs == planned[0].inputs
    assert merged[0].expected_outputs == planned[0].expected_outputs


def test_discovery_descends_repo_raw_container_roots(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "protein_data_scope_seed" / "string" / "protein.links.txt", "9606.ENSP0001 9606.ENSP0002 999")
    _write_text(repo_raw / "local_registry" / "20260411T000000Z" / "reactome" / "pathways.tsv", "R-HSA-199420")

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        }
    )
    identities = {(item["source_family"], item["snapshot_id"]) for item in discovered}

    assert ("string", "current") in identities
    assert ("reactome", "current") in identities
    assert ("protein_data_scope_seed", "current") not in identities
    assert ("local_registry", "20260411T000000Z") not in identities


def test_discovery_skips_repo_raw_local_copies_shadow_surface(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    repo_local_copies = tmp_path / "repo_local_copies"
    _write_text(repo_raw / "local_copies" / "reactome" / "ReactomePathways.txt", "R-HSA-1\tExample\tHomo sapiens\n")
    _write_text(repo_local_copies / "reactome" / "ReactomePathways.txt", "R-HSA-1\tExample\tHomo sapiens\n")

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "repo_local_copies": repo_local_copies,
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": tmp_path / "warehouse",
        }
    )
    identities = [(item["source_family"], str(item["path"])) for item in discovered]

    assert ("local_copies", str(repo_raw / "local_copies")) not in identities
    assert any(family == "reactome" and path.startswith(str(repo_local_copies)) for family, path in identities)


def test_tick_prunes_stale_active_workers_without_claims(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "uniprot" / "20260411T000000Z" / "entry.tsv", "P69905")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    heartbeat_worker(
        warehouse_root=warehouse_root,
        worker_id="stale-worker-1",
        lane="identity_sequence",
        lease_ids=("claim:nonexistent",),
        status="active",
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    program_state = json.loads((warehouse_root / "control" / "program_state.json").read_text(encoding="utf-8"))

    assert program_state["active_workers"] == []


def test_registry_only_marks_matching_snapshot_as_promoted(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    _write_text(repo_raw / "uniprot" / "20260411T000000Z" / "a.tsv", "P69905")
    _write_text(repo_raw / "uniprot" / "20260412T000000Z" / "b.tsv", "P68871")
    manifest_path = tmp_path / "warehouse_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_id": "warehouse:test",
                "warehouse_root": str(tmp_path / "warehouse"),
                "catalog_path": str(tmp_path / "warehouse" / "catalog.duckdb"),
                "catalog_engine": "duckdb",
                "catalog_status": "ready",
                "source_descriptors": [
                    {
                        "source_key": "uniprot",
                        "source_name": "UniProt",
                        "category": "sequence",
                        "snapshot_id": "20260411T000000Z",
                        "retrieval_mode": "download",
                        "availability_status": "present",
                    }
                ],
                "entity_families": [],
                "validation": {"state": "passed"},
            }
        ),
        encoding="utf-8",
    )

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": tmp_path / "warehouse",
        }
    )
    registry = build_source_registry(discovered_objects=discovered, warehouse_manifest_path=manifest_path)
    statuses = {record.snapshot_id: record.integration_status for record in registry}

    assert statuses["20260411T000000Z"] == "promoted"
    assert statuses["20260412T000000Z"] == "discovered"


def test_registry_falls_back_to_single_descriptor_status_when_snapshot_ids_differ(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    _write_text(repo_raw / "protein_data_scope_seed" / "string" / "protein.links.txt", "9606.ENSP0001 9606.ENSP0002 999")
    manifest_path = tmp_path / "warehouse_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_id": "warehouse:test",
                "warehouse_root": str(tmp_path / "warehouse"),
                "catalog_path": str(tmp_path / "warehouse" / "catalog.duckdb"),
                "catalog_engine": "duckdb",
                "catalog_status": "ready",
                "source_descriptors": [
                    {
                        "source_key": "string",
                        "source_name": "STRING",
                        "category": "interaction_network",
                        "snapshot_id": "string",
                        "retrieval_mode": "download",
                        "availability_status": "partial",
                    }
                ],
                "entity_families": [],
                "validation": {"state": "passed"},
            }
        ),
        encoding="utf-8",
    )

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "warehouse_root": tmp_path / "warehouse",
        }
    )
    registry = build_source_registry(discovered_objects=discovered, warehouse_manifest_path=manifest_path)
    string_record = next(record for record in registry if record.source_family == "string")

    assert string_record.snapshot_id == "current"
    assert string_record.integration_status == "partial"


def test_registry_marks_sources_with_all_promoted_work_units_as_promoted(tmp_path: Path) -> None:
    repo_local_copies = tmp_path / "repo_local_copies"
    incoming_mirrors = tmp_path / "warehouse" / "incoming_mirrors"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_local_copies / "custom_training_sets" / "20260412T000000Z" / "rows.json", "[]")
    _write_text(
        incoming_mirrors / "custom_training_sets" / "20260412T000000Z" / "20260412T000000Z" / "rows.json",
        "[]",
    )

    discovered = discover_corpus_objects(
        {
            "repo_raw": tmp_path / "missing_repo_raw",
            "repo_local_copies": repo_local_copies,
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        }
    )
    registry = build_source_registry(
        discovered_objects=discovered,
        existing_work_units=(
            WorkUnit(
                work_unit_id="custom_training_sets:20260412T000000Z:all",
                lane="warehouse_validation_export",
                source_family="custom_training_sets",
                snapshot_id="20260412T000000Z",
                shard_key="all",
                inputs=(str(incoming_mirrors / "custom_training_sets" / "20260412T000000Z" / "20260412T000000Z"),),
                expected_outputs=("E:/warehouse/staging/custom_training_sets", "E:/warehouse/normalized/custom_training_sets"),
                status="promoted",
                metadata={"validation_decision": "passed"},
            ),
        ),
        warehouse_manifest_path=None,
        warehouse_root=warehouse_root,
    )
    record = next(item for item in registry if item.source_family == "custom_training_sets")

    assert record.integration_status == "promoted"
    assert record.validation_status == "passed"


def test_plan_work_units_excludes_derived_only_sources() -> None:
    records = build_source_registry(
        discovered_objects=(
            {
                "source_family": "graph",
                "snapshot_id": "current",
                "path": Path(__file__),
                "kind": "derived_extract",
                "surface": "bio_agent_root",
            },
        ),
        warehouse_manifest_path=None,
    )

    work_units = plan_work_units(records)

    assert not work_units


def test_discovery_prefers_explicit_bio_agent_data_surfaces_over_project_root_noise(tmp_path: Path) -> None:
    bio_agent_root = tmp_path / "bio-agent-lab"
    warehouse_root = tmp_path / "warehouse"
    _write_text(bio_agent_root / "README.md", "project docs")
    _write_text(bio_agent_root / "apps" / "console" / "index.ts", "export {}")
    _write_text(bio_agent_root / "data" / "raw" / "rcsb" / "entries.json", "[]")
    _write_text(bio_agent_root / "datasets" / "engineered_dataset" / "manifest.json", "{}")

    discovered = discover_corpus_objects(
        {
            "bio_agent_root": bio_agent_root,
            "warehouse_root": warehouse_root,
        }
    )
    identities = {(item["source_family"], item["surface"]) for item in discovered}

    assert ("rcsb_pdbe", "bio_agent_data_raw") in identities
    assert ("engineered_dataset", "bio_agent_datasets") in identities
    assert ("readme.md", "bio_agent_root") not in identities
    assert ("apps", "bio_agent_root") not in identities


def test_discovery_models_bio_agent_data_raw_as_duplicate_raw_surface(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    bio_agent_data_raw = tmp_path / "bio_agent_data_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "rcsb_pdbe" / "20260411T000000Z" / "entry.json", "{}")
    _write_text(bio_agent_data_raw / "rcsb" / "20260411T000000Z" / "entry.json", "{}")

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "bio_agent_data_raw": bio_agent_data_raw,
            "warehouse_root": warehouse_root,
        }
    )
    registry = build_source_registry(discovered_objects=discovered, warehouse_manifest_path=None)
    record = next(item for item in registry if item.source_family == "rcsb_pdbe")

    assert record.kind == "raw_authoritative"
    assert record.authoritative_root.startswith(str(repo_raw))
    assert record.duplicate_bytes > 0


def test_discovery_models_incoming_mirrors_as_duplicate_surface_and_marks_verified(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    incoming_mirrors = warehouse_root / "incoming_mirrors"
    _write_text(repo_raw / "string" / "protein.links.txt", "9606.ENSP0001 9606.ENSP0002 999")
    _write_text(
        incoming_mirrors / "string" / "current" / "string" / "protein.links.txt",
        "9606.ENSP0001 9606.ENSP0002 999",
    )

    discovered = discover_corpus_objects(
        {
            "repo_raw": repo_raw,
            "incoming_mirrors_root": incoming_mirrors,
            "warehouse_root": warehouse_root,
        }
    )
    registry = build_source_registry(
        discovered_objects=discovered,
        warehouse_manifest_path=None,
        warehouse_root=warehouse_root,
    )
    record = next(item for item in registry if item.source_family == "string")

    assert record.kind == "raw_authoritative"
    assert record.duplicate_bytes > 0
    assert str(incoming_mirrors / "string" / "current" / "string") in record.root_paths
    assert record.consolidation_status == "verified"


def test_discovery_descends_c_overflow_container_root_as_duplicate_surface(tmp_path: Path) -> None:
    overflow_root = tmp_path / "c_overflow_root"
    warehouse_root = tmp_path / "warehouse"
    _write_text(
        overflow_root / "protein_data_scope_seed" / "uniprot" / "uniprot_sprot.fasta.gz",
        "payload",
    )

    discovered = discover_corpus_objects(
        {
            "c_overflow_root": overflow_root,
            "warehouse_root": warehouse_root,
        }
    )
    identities = {(item["source_family"], item["snapshot_id"], item["kind"]) for item in discovered}

    assert ("uniprot", "current", "raw_duplicate") in identities
    assert ("protein_data_scope_seed", "current", "raw_duplicate") not in identities


def test_discovery_models_temp_storage_archives_as_duplicate_surface(tmp_path: Path) -> None:
    temp_archives_root = tmp_path / "temp_archives"
    warehouse_root = tmp_path / "warehouse"
    _write_text(temp_archives_root / "alphafold_db" / "UP000005640_9606.tar", "payload")

    discovered = discover_corpus_objects(
        {
            "c_temp_archives_root": temp_archives_root,
            "warehouse_root": warehouse_root,
        }
    )
    identities = {(item["source_family"], item["snapshot_id"], item["kind"]) for item in discovered}

    assert ("alphafold", "current", "raw_duplicate") in identities


def test_validation_and_promotion_receipts_advance_work_unit(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "string" / "20260411T000000Z" / "links.txt", "9606.ENSP0001 9606.ENSP0002 999")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claim = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="validator-1",
        lane="interaction_network",
        limit=1,
        ttl_seconds=600,
    )
    work_unit_id = claim["work_units"][0]["work_unit_id"]

    validation = record_validation_receipt(
        warehouse_root=warehouse_root,
        work_unit_id=work_unit_id,
        decision="passed",
        input_fingerprints={"root": "abc"},
        source_counts={"rows": 10},
        staged_counts={"rows": 10},
        checks={"counts_match": True},
    )
    manifest_path = tmp_path / "warehouse_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_id": "warehouse:test",
                "warehouse_root": str(warehouse_root),
                "catalog_path": str(warehouse_root / "catalog.duckdb"),
                "catalog_engine": "duckdb",
                "catalog_status": "ready",
                "source_descriptors": [],
                "entity_families": [],
                "validation": {"state": "passed"},
            }
        ),
        encoding="utf-8",
    )
    promotion = promote_validated_work_units(
        warehouse_root=warehouse_root,
        warehouse_manifest_path=manifest_path,
        work_unit_ids=(work_unit_id,),
        promotion_id="promotion:test",
    )
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    claims_payload = json.loads((warehouse_root / "control" / "lane_claims.json").read_text(encoding="utf-8"))
    promoted_unit = next(unit for unit in work_units_payload["work_units"] if unit["work_unit_id"] == work_unit_id)

    assert validation["status"] == "validation_recorded"
    assert promotion["status"] == "promoted"
    assert promoted_unit["status"] == "promoted"
    assert not claims_payload


def test_claim_specific_work_unit_targets_requested_shard(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "uniprot" / "20260411T000000Z" / "P04637" / "P04637.json", "{}")
    _write_text(repo_raw / "uniprot" / "20260411T000000Z" / "P31749" / "P31749.json", "{}")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    target_id = next(unit["work_unit_id"] for unit in work_units_payload["work_units"] if unit["shard_key"] == _hash_shard_key("P04637"))

    claimed = claim_specific_work_unit(
        warehouse_root=warehouse_root,
        worker_id="targeted-worker-1",
        work_unit_id=target_id,
        ttl_seconds=600,
    )

    assert claimed["status"] == "claimed"
    assert claimed["work_units"][0]["work_unit_id"] == target_id


def test_run_worker_once_materializes_stage_and_normalized_manifests(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "reactome" / "20260411T000000Z" / "pathways.tsv", "R-HSA-199420")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    processed = run_worker_once(
        warehouse_root=warehouse_root,
        worker_id="pathway-worker-1",
        lane="pathway_reference",
        ttl_seconds=600,
        auto_validate=True,
    )

    stage_manifest = Path(processed["materialized"]["stage_manifest_path"])
    normalized_manifest = Path(processed["materialized"]["normalized_manifest_path"])
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    updated_unit = next(
        unit for unit in work_units_payload["work_units"] if unit["work_unit_id"] == processed["materialized"]["work_unit"]["work_unit_id"]
    )

    assert processed["status"] == "processed"
    assert stage_manifest.exists()
    assert normalized_manifest.exists()
    assert updated_unit["status"] == "validated_unpromoted"


def test_uniprot_materialization_emits_source_aware_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    accession = "P04637"
    snapshot_root = repo_raw / "uniprot" / "20260411T000000Z" / accession
    _write_text(
        snapshot_root / f"{accession}.json",
        json.dumps(
            {
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "primaryAccession": accession,
                "secondaryAccessions": ["Q15086", "Q15087"],
                "organism": {"taxonId": 9606},
                "sequence": {"length": 393},
                "genes": [{"geneName": {"value": "TP53"}}],
                "features": [{"type": "Domain"}, {"type": "Region"}],
                "references": [{"citation": "a"}, {"citation": "b"}],
                "comments": [{"type": "function"}],
            }
        ),
    )
    _write_text(snapshot_root / f"{accession}.fasta", f">{accession}\nMEEPQSDPSV\n")
    _write_text(snapshot_root / f"{accession}.txt", "ID   P04637\n")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="uniprot-worker-1",
        lane="identity_sequence",
        limit=8,
        ttl_seconds=600,
    )
    shard_key = _hash_shard_key(accession)
    work_unit_id = next(unit["work_unit_id"] for unit in claimed["work_units"] if unit["shard_key"] == shard_key)
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=work_unit_id,
        auto_validate=True,
    )

    stage_manifest = json.loads(Path(materialized["stage_manifest_path"]).read_text(encoding="utf-8"))
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert stage_manifest["source_family"] == "uniprot"
    assert stage_manifest["source_extract"]["extract_kind"] == "uniprot_accession_summary"
    assert stage_manifest["source_extract"]["matched_accession_count"] == 1
    assert stage_manifest["source_extract"]["accession_sample"] == [accession]
    assert stage_manifest["source_extract"]["reviewed_entry_count"] == 1
    assert stage_manifest["source_extract"]["total_feature_count"] == 2
    assert stage_manifest["source_extract"]["total_reference_count"] == 2
    assert stage_manifest["source_extract"]["gene_symbol_sample"] == ["TP53"]

    assert normalized_manifest["source_family"] == "uniprot"
    assert normalized_manifest["normalized_summary"]["summary_kind"] == "uniprot_accession_summary"
    assert normalized_manifest["normalized_summary"]["matched_accession_count"] == 1
    assert materialized["validation"]["decision"] == "passed"


def test_bindingdb_materialization_emits_source_aware_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    accession = "P04637"
    snapshot_root = repo_raw / "bindingdb" / "20260411T000000Z" / accession
    _write_text(
        snapshot_root / f"{accession}.bindingdb.json",
        json.dumps(
            {
                "getLindsByUniprotResponse": {
                    "bdb.hit": "2",
                    "bdb.affinities": [
                        {"bdb.monomerid": 123, "bdb.affinity_type": "IC50", "bdb.affinity": "5.0"},
                        {"bdb.monomerid": 456, "bdb.affinity_type": "Ki", "bdb.affinity": "8.0"},
                    ],
                }
            }
        ),
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="bindingdb-worker-1",
        lane="ligand_assay",
        limit=1,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )

    stage_manifest = json.loads(Path(materialized["stage_manifest_path"]).read_text(encoding="utf-8"))
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert stage_manifest["source_family"] == "bindingdb"
    assert stage_manifest["source_extract"]["extract_kind"] == "bindingdb_affinity_summary"
    assert stage_manifest["source_extract"]["affinity_record_count"] == 2
    assert stage_manifest["source_extract"]["unique_ligand_count"] == 2
    assert stage_manifest["source_extract"]["affinity_type_counts"] == {"IC50": 1, "KI": 1}

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "bindingdb_affinity_summary"
    assert normalized_manifest["normalized_summary"]["reported_hit_count"] == 2
    assert materialized["validation"]["decision"] == "passed"


def test_bindingdb_bulk_materialization_emits_release_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "bindingdb"
    _write_text(snapshot_root / "BindingDB_UniProt.txt", "P04637\t123\nP31749\t456\n")
    _write_text(snapshot_root / "BindingDBTargetSequences.fasta", ">P04637\nMEEPQ\n")
    _write_text(snapshot_root / "BindingDB_All_202603_tsv.zip", "zip-bytes")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="bindingdb-bulk-worker-1",
        lane="ligand_assay",
        limit=1,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )

    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "bindingdb_bulk_release_summary"
    assert normalized_manifest["normalized_summary"]["bindingdb_uniprot_mapping_rows"] == 2
    assert normalized_manifest["normalized_summary"]["has_target_sequences_fasta"] is True
    assert normalized_manifest["normalized_summary"]["archive_file_count"] == 2


def test_intact_materialization_emits_source_aware_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    accession = "P04637"
    snapshot_root = repo_raw / "intact" / "20260411T000000Z" / accession
    _write_text(
        snapshot_root / f"{accession}.interactor.json",
        json.dumps(
            {
                "content": [
                    {
                        "interactorPreferredIdentifier": accession,
                        "interactorType": "protein",
                        "interactionCount": 10,
                    },
                    {
                        "interactorPreferredIdentifier": f"{accession}-2",
                        "interactorType": "protein",
                        "interactionCount": 3,
                    },
                ]
            }
        ),
    )
    _write_text(
        snapshot_root / f"{accession}.psicquic.tab25.txt",
        "uniprotkb:P04637\tuniprotkb:P04637\tintact:EBI-1\tintact:EBI-2\n"
        "uniprotkb:P04637\tuniprotkb:P04637\tintact:EBI-3\tintact:EBI-4\n",
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="intact-worker-1",
        lane="interaction_network",
        limit=1,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )

    stage_manifest = json.loads(Path(materialized["stage_manifest_path"]).read_text(encoding="utf-8"))
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert stage_manifest["source_family"] == "intact"
    assert stage_manifest["source_extract"]["extract_kind"] == "intact_interaction_summary"
    assert stage_manifest["source_extract"]["interactor_record_count"] == 2
    assert stage_manifest["source_extract"]["unique_interactor_identifier_count"] == 2
    assert stage_manifest["source_extract"]["psicquic_row_count"] == 2
    assert stage_manifest["source_extract"]["reported_interaction_count"] == 13

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "intact_interaction_summary"
    assert normalized_manifest["normalized_summary"]["interactor_type_counts"] == {"protein": 2}
    assert materialized["validation"]["decision"] == "passed"


def test_rnacentral_bulk_materialization_emits_release_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "rnacentral"
    _write_text(snapshot_root / "rnacentral_active.fasta.gz", "compressed-a")
    _write_text(snapshot_root / "rnacentral_inactive.fasta.gz", "compressed-b")
    _write_text(snapshot_root / "_source_metadata.json", "{}")
    _write_text(snapshot_root / "rnacentral_active.fasta.gz__extracted" / "chunk.txt", "chunk")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="rnacentral-worker-1",
        lane="identity_sequence",
        limit=8,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )

    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["source_family"] == "rnacentral"
    assert normalized_manifest["normalized_summary"]["summary_kind"] == "rnacentral_bulk_release_summary"
    assert normalized_manifest["normalized_summary"]["extracted_directory_count"] == 1
    assert normalized_manifest["normalized_summary"]["archive_file_count"] == 3


def test_uniparc_bulk_materialization_emits_release_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "uniparc" / "20260412T000000Z"
    _write_text(snapshot_root / "README", "UniParc release")
    _write_text(snapshot_root / "download_inventory.json", "{}")
    _write_text(snapshot_root / "fasta" / "active" / "uniparc_active_p1.fasta.gz", ">UPI0001\nMSEQUENCE\n")
    _write_text(snapshot_root / "xml" / "all" / "uniparc_p1.xml.gz", "<uniparc></uniparc>")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="uniparc-worker-1",
        lane="identity_sequence",
        limit=8,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )

    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["source_family"] == "uniparc"
    assert normalized_manifest["normalized_summary"]["summary_kind"] == "uniparc_bulk_release_summary"
    assert normalized_manifest["normalized_summary"]["active_fasta_file_count"] == 1
    assert normalized_manifest["normalized_summary"]["xml_file_count"] == 1
    assert normalized_manifest["normalized_summary"]["has_readme"] is True


def test_rcsb_pdbe_materialization_emits_structure_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    accession = "P04637"
    structure_root = repo_raw / "rcsb_pdbe" / "20260411T000000Z" / accession / "9R2Q"
    _write_text(
        repo_raw / "rcsb_pdbe" / "20260411T000000Z" / accession / f"{accession}.best_structures.json",
        json.dumps(
            [
                {"pdb_id": "9r2q", "experimental_method": "Electron Microscopy"},
                {"pdb_id": "9r2m", "experimental_method": "Electron Microscopy"},
            ]
        ),
    )
    _write_text(structure_root / "9R2Q.cif", "data_9R2Q")
    _write_text(structure_root / "9R2Q.entry.json", json.dumps({"citation": [{"title": "Example"}]}))

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="rcsb-worker-1",
        lane="structure",
        limit=16,
        ttl_seconds=600,
    )
    work_unit_id = next(unit["work_unit_id"] for unit in claimed["work_units"] if unit["source_family"] == "rcsb_pdbe")
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=work_unit_id,
        auto_validate=True,
    )

    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "rcsb_pdbe_structure_summary"
    assert normalized_manifest["normalized_summary"]["matched_accession_count"] == 1
    assert normalized_manifest["normalized_summary"]["best_structure_record_count"] == 2
    assert normalized_manifest["normalized_summary"]["unique_pdb_id_count"] == 2
    assert normalized_manifest["normalized_summary"]["entry_json_count"] == 1


def test_pdbbind_manual_placeholder_materializes_as_single_all_shard(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "pdbbind" / "20260411T000000Z"
    _write_text(
        snapshot_root / "manual_acquisition_required.json",
        json.dumps(
            {
                "status": "manual_acquisition_required",
                "requested_accessions": ["P04637", "P31749"],
                "drop_location": "data\\raw\\pdbbind\\20260411T000000Z\\manual_drop",
            }
        ),
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    pdbbind_units = [unit for unit in work_units_payload["work_units"] if unit["source_family"] == "pdbbind"]
    assert [unit["shard_key"] for unit in pdbbind_units] == ["all"]
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="pdbbind-worker-1",
        lane="ligand_assay",
        limit=1,
        ttl_seconds=600,
    )

    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "pdbbind_manual_placeholder"
    assert normalized_manifest["normalized_summary"]["requested_accession_count"] == 2
    assert normalized_manifest["normalized_summary"]["manual_manifest_present"] is True


def test_pdbbind_inventory_materialization_emits_registry_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "pdbbind_pp"
    _write_text(
        snapshot_root / "inventory.json",
        json.dumps(
            {
                "source_name": "pdbbind_pp",
                "status": "present",
                "join_keys": ["9LWP", "9QTN"],
                "present_root_count": 3,
                "present_file_count": 2800,
                "present_total_bytes": 3163720722,
                "large_payload": True,
            }
        ),
    )
    _write_text(snapshot_root / "manifest.json", "{}")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="pdbbind-registry-worker-1",
        lane="ligand_assay",
        limit=1,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "pdbbind_registry_summary"
    assert normalized_manifest["normalized_summary"]["join_key_count"] == 2
    assert normalized_manifest["normalized_summary"]["present_file_count"] == 2800
    assert normalized_manifest["normalized_summary"]["large_payload"] is True


def test_string_planning_uses_completed_extract_manifest(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "string" / "20260411T000000Z" / "links.txt", "9606.ENSP0001 9606.ENSP0002 999")
    manifest_path = warehouse_root / "staging" / "string_edges_threshold_999" / "manifest.json"
    _write_text(
        manifest_path,
        json.dumps(
            {
                "artifact_id": "string_threshold_edge_extract",
                "status": "completed",
                "completed_at": "2026-04-11T18:27:11.705425+00:00",
                "emitted_rows": 5,
                "rows_per_shard": 250000,
                "shard_count": 2,
                "shard_paths": [
                    str((warehouse_root / "staging" / "string_edges_threshold_999" / "part-0001.csv").as_posix()),
                    str((warehouse_root / "staging" / "string_edges_threshold_999" / "part-0002.csv").as_posix()),
                ],
            }
        ),
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    string_units = [unit for unit in work_units_payload["work_units"] if unit["source_family"] == "string"]

    assert [unit["shard_key"] for unit in string_units] == ["threshold_999-part-0001", "threshold_999-part-0002"]


def test_chembl_materialization_emits_bulk_release_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "chembl"
    _write_text(snapshot_root / "_source_metadata.json", json.dumps({"id": "chembl", "name": "ChEMBL"}))
    _write_text(snapshot_root / "checksums.txt", "abc  chembl_36_sqlite.tar.gz\n")
    _write_text(snapshot_root / "chembl_36_release_notes.txt", "ChEMBL 36 release notes")
    _write_text(snapshot_root / "chembl_36_sqlite.tar.gz", "archive-bytes")
    sqlite_dir = snapshot_root / "chembl_36_sqlite.tar.gz__extracted" / "chembl_36" / "chembl_36_sqlite"
    sqlite_dir.mkdir(parents=True, exist_ok=True)
    sqlite_db = sqlite_dir / "chembl_36.db"
    with sqlite3.connect(str(sqlite_db)) as connection:
        connection.execute("CREATE TABLE assays (assay_id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE molecule_dictionary (molregno INTEGER PRIMARY KEY)")
        connection.commit()

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="chembl-worker-1",
        lane="ligand_assay",
        limit=8,
        ttl_seconds=600,
    )
    work_unit_id = next(unit["work_unit_id"] for unit in claimed["work_units"] if unit["source_family"] == "chembl")
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=work_unit_id,
        auto_validate=True,
    )
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "chembl_bulk_release_summary"
    assert normalized_manifest["normalized_summary"]["chembl_release_id"] == "chembl"
    assert normalized_manifest["normalized_summary"]["checksum_row_count"] == 1
    assert normalized_manifest["normalized_summary"]["sqlite_table_count"] == 2
    assert "assays" in normalized_manifest["normalized_summary"]["sqlite_table_sample"]


def test_chebi_materialization_emits_ontology_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "chebi"
    _write_text(snapshot_root / "_source_metadata.json", json.dumps({"id": "chebi", "name": "ChEBI"}))
    _write_text(snapshot_root / "chebi.json", "{\"chebi\": true}")
    _write_text(snapshot_root / "chebi_core.json", "{\"chebi_core\": true}")
    _write_text(snapshot_root / "chebi_lite.json", "{\"chebi_lite\": true}")
    _write_text(snapshot_root / "chebi.obo", "format-version: 1.2\n[Term]\nid: CHEBI:1\n")
    _write_text(snapshot_root / "chebi.owl", "<owl></owl>")
    _write_text(snapshot_root / "chebi_core.obo__extracted" / "chunk.txt", "chunk")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="chebi-worker-1",
        lane="ligand_assay",
        limit=1,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "chebi_ontology_summary"
    assert normalized_manifest["normalized_summary"]["ontology_file_count"] >= 5
    assert normalized_manifest["normalized_summary"]["has_full_json"] is True
    assert normalized_manifest["normalized_summary"]["has_core_json"] is True
    assert "format-version" in normalized_manifest["normalized_summary"]["obo_head"]


def test_sifts_materialization_emits_mapping_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "sifts"
    for name, content in {
        "pdb_chain_go.csv.gz": "PDB,CHAIN,GO_ID\n1ABC,A,GO:0001\n",
        "pdb_chain_interpro.tsv.gz": "PDB\tCHAIN\tINTERPRO\n1ABC\tA\tIPR0001\n",
        "pdb_chain_pfam.csv.gz": "PDB,CHAIN,PFAM\n1ABC,A,PF0001\n",
    }.items():
        path = snapshot_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write(content)

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="sifts-worker-1",
        lane="structure",
        limit=1,
        ttl_seconds=600,
    )
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=claimed["work_units"][0]["work_unit_id"],
        auto_validate=True,
    )
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "sifts_mapping_summary"
    assert normalized_manifest["normalized_summary"]["mapping_file_count"] == 3
    assert normalized_manifest["normalized_summary"]["mapping_family_count"] == 3
    assert normalized_manifest["normalized_summary"]["has_go_mappings"] is True
    assert normalized_manifest["normalized_summary"]["has_interpro_mappings"] is True
    assert normalized_manifest["normalized_summary"]["has_pfam_mappings"] is True


def test_biolip_inventory_materialization_emits_registry_summary(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    snapshot_root = repo_raw / "biolip"
    _write_text(
        snapshot_root / "inventory.json",
        json.dumps(
            {
                "source_name": "biolip",
                "status": "present",
                "join_keys": ["4HHB", "9S6C"],
                "present_roots": [
                    "C:\\Users\\jfvit\\Documents\\bio-agent-lab\\data_sources\\biolip\\BioLiP.txt",
                    "C:\\Users\\jfvit\\Documents\\bio-agent-lab\\data_sources\\biolip\\BioLiP_extracted",
                ],
                "present_root_count": 2,
                "present_file_count": 3,
                "present_total_bytes": 1175616328,
                "large_payload": False,
            }
        ),
    )
    _write_text(snapshot_root / "manifest.json", "{}")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_for_worker(
        warehouse_root=warehouse_root,
        worker_id="biolip-worker-1",
        lane="ligand_assay",
        limit=16,
        ttl_seconds=600,
    )
    work_unit_id = next(unit["work_unit_id"] for unit in claimed["work_units"] if unit["source_family"] == "biolip")
    materialized = materialize_claimed_work_unit(
        warehouse_root=warehouse_root,
        work_unit_id=work_unit_id,
        auto_validate=True,
    )
    normalized_manifest = json.loads(Path(materialized["normalized_manifest_path"]).read_text(encoding="utf-8"))

    assert normalized_manifest["normalized_summary"]["summary_kind"] == "biolip_registry_summary"
    assert normalized_manifest["normalized_summary"]["join_key_count"] == 2
    assert normalized_manifest["normalized_summary"]["present_root_count"] == 2
    assert normalized_manifest["normalized_summary"]["inventory_manifest_present"] is True


def test_claim_specific_work_unit_claims_requested_unit_within_busy_lane(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "chembl" / "chembl_36_sqlite.tar.gz", "archive")
    _write_text(repo_raw / "chebi" / "chebi.json", "{}")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    claimed = claim_specific_work_unit(
        warehouse_root=warehouse_root,
        worker_id="specific-worker-1",
        work_unit_id="chebi:current:all",
        ttl_seconds=600,
    )

    assert claimed["status"] == "claimed"
    assert claimed["work_units"][0]["work_unit_id"] == "chebi:current:all"

    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    chebi_unit = next(unit for unit in work_units_payload["work_units"] if unit["work_unit_id"] == "chebi:current:all")
    chembl_unit = next(unit for unit in work_units_payload["work_units"] if unit["work_unit_id"] == "chembl:current:hash-00")

    assert chebi_unit["status"] == "claimed"
    assert chebi_unit["lease_owner"] == "specific-worker-1"
    assert chembl_unit["status"] == "planned"


def test_claim_specific_work_unit_can_force_reprocess_promoted_unit(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "uniparc" / "20260412T082248Z" / "manifest.json", "{}")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )

    work_units_path = warehouse_root / "control" / "work_units.json"
    payload = json.loads(work_units_path.read_text(encoding="utf-8"))
    target = payload["work_units"][0]
    target["status"] = "promoted"
    target["metadata"].update(
        {
            "promotion_id": "promotion:old",
            "validation_decision": "passed",
            "stage_manifest_path": "E:/staging/old.json",
            "normalized_manifest_path": "E:/normalized/old.json",
        }
    )
    work_units_path.write_text(json.dumps(payload), encoding="utf-8")

    claimed = claim_specific_work_unit(
        warehouse_root=warehouse_root,
        worker_id="reprocess-worker-1",
        work_unit_id=target["work_unit_id"],
        ttl_seconds=600,
        force_reprocess=True,
    )

    refreshed_payload = json.loads(work_units_path.read_text(encoding="utf-8"))
    refreshed = refreshed_payload["work_units"][0]

    assert claimed["status"] == "claimed"
    assert refreshed["status"] == "claimed"
    assert refreshed["lease_owner"] == "reprocess-worker-1"
    assert refreshed["metadata"]["forced_reprocess"] is True
    assert "promotion_id" not in refreshed["metadata"]
    assert "validation_decision" not in refreshed["metadata"]
    assert "stage_manifest_path" not in refreshed["metadata"]
    assert "normalized_manifest_path" not in refreshed["metadata"]


def test_tick_downgrades_validated_units_without_receipts(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "reactome" / "20260411T000000Z" / "pathways.tsv", "R-HSA-199420")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )

    work_units_path = warehouse_root / "control" / "work_units.json"
    payload = json.loads(work_units_path.read_text(encoding="utf-8"))
    payload["work_units"][0]["status"] = "validated_unpromoted"
    payload["work_units"][0]["metadata"]["validation_decision"] = "passed"
    work_units_path.write_text(json.dumps(payload), encoding="utf-8")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )

    refreshed = json.loads(work_units_path.read_text(encoding="utf-8"))
    unit = refreshed["work_units"][0]
    assert unit["status"] == "planned"
    assert "validation_decision" not in unit["metadata"]


def test_run_worker_batch_processes_and_promotes_across_lanes(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "reactome" / "20260411T000000Z" / "pathways.tsv", "R-HSA-199420")
    _write_text(repo_raw / "sabio_rk" / "20260411T000000Z" / "enzymes.txt", "P69905")
    manifest_path = tmp_path / "warehouse_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_id": "warehouse:test",
                "warehouse_root": str(warehouse_root),
                "catalog_path": str(warehouse_root / "catalog.duckdb"),
                "catalog_engine": "duckdb",
                "catalog_status": "ready",
                "source_descriptors": [],
                "entity_families": [],
                "validation": {"state": "passed"},
            }
        ),
        encoding="utf-8",
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=manifest_path,
    )
    batch = run_worker_batch(
        warehouse_root=warehouse_root,
        warehouse_manifest_path=manifest_path,
        lanes=("pathway_reference", "motif_annotation"),
        worker_prefix="batch-worker",
        ttl_seconds=600,
        auto_validate=True,
        auto_promote=True,
    )
    work_units_payload = json.loads((warehouse_root / "control" / "work_units.json").read_text(encoding="utf-8"))
    promoted_units = [unit for unit in work_units_payload["work_units"] if unit["status"] == "promoted"]

    assert batch["status"] == "completed"
    assert batch["processed_count"] == 2
    assert batch["promotion"]["status"] == "promoted"
    assert len(promoted_units) == 2


def test_run_worker_batch_skips_promotion_when_manifest_missing(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "reactome" / "20260411T000000Z" / "pathways.tsv", "R-HSA-199420")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    batch = run_worker_batch(
        warehouse_root=warehouse_root,
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
        lanes=("pathway_reference",),
        worker_prefix="recovery-worker",
        ttl_seconds=600,
        auto_validate=True,
        auto_promote=True,
    )

    assert batch["status"] == "completed"
    assert batch["processed_count"] == 1
    assert batch["promotion"]["status"] == "blocked_missing_manifest"
    lane_claims = json.loads((warehouse_root / "control" / "lane_claims.json").read_text(encoding="utf-8"))
    assert lane_claims == []


def test_tick_prunes_claims_for_units_no_longer_claimed(tmp_path: Path) -> None:
    repo_raw = tmp_path / "repo_raw"
    warehouse_root = tmp_path / "warehouse"
    _write_text(repo_raw / "reactome" / "20260411T000000Z" / "pathways.tsv", "R-HSA-199420")

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    work_units_path = warehouse_root / "control" / "work_units.json"
    lane_claims_path = warehouse_root / "control" / "lane_claims.json"
    work_units_payload = json.loads(work_units_path.read_text(encoding="utf-8"))
    target = work_units_payload["work_units"][0]
    target["status"] = "validated_unpromoted"
    target["lease_owner"] = "worker-1"
    target["lease_expires_at"] = "2026-04-11T22:00:00+00:00"
    work_units_path.write_text(json.dumps(work_units_payload), encoding="utf-8")
    lane_claims_path.write_text(
        json.dumps(
            [
                {
                    "claim_id": "claim:test",
                    "work_unit_id": target["work_unit_id"],
                    "lane": target["lane"],
                    "source_family": target["source_family"],
                    "snapshot_id": target["snapshot_id"],
                    "shard_key": target["shard_key"],
                    "lease_owner": "worker-1",
                    "lease_expires_at": "2026-04-11T22:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    tick_corpus_orchestrator(
        warehouse_root=warehouse_root,
        discovery_roots={
            "repo_raw": repo_raw,
            "repo_local_copies": tmp_path / "missing_local_copies",
            "bio_agent_root": tmp_path / "missing_bio_root",
            "bio_agent_data_sources": tmp_path / "missing_data_sources",
            "warehouse_root": warehouse_root,
        },
        warehouse_manifest_path=tmp_path / "missing_manifest.json",
    )
    lane_claims = json.loads(lane_claims_path.read_text(encoding="utf-8"))

    assert lane_claims == []
