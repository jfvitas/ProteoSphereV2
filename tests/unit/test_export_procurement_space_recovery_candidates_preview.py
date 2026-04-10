from __future__ import annotations

from pathlib import Path

from scripts.export_procurement_space_recovery_candidates_preview import (
    build_procurement_space_recovery_candidates_preview,
)


def test_space_recovery_candidates_preview_detects_duplicate_lane(
    monkeypatch, tmp_path: Path
) -> None:
    repo_root = tmp_path
    local = repo_root / "data" / "raw" / "local_copies" / "chembl"
    seed = repo_root / "data" / "raw" / "protein_data_scope_seed" / "chembl"
    local.mkdir(parents=True, exist_ok=True)
    seed.mkdir(parents=True, exist_ok=True)
    (local / "chembl_36_sqlite.tar.gz").write_bytes(b"x" * 100)
    (seed / "chembl_36_sqlite.tar.gz").write_bytes(b"x" * 100)

    import scripts.export_procurement_space_recovery_candidates_preview as module

    monkeypatch.setattr(module, "REPO_ROOT", repo_root)
    payload = build_procurement_space_recovery_candidates_preview()

    assert payload["summary"]["recovery_state"] == "duplicate_first_recovery_lane_available"
    assert payload["rows"][0]["reason"] == "duplicate_name_and_size_detected"


def test_space_recovery_candidates_preview_handles_empty_tree(monkeypatch, tmp_path: Path) -> None:
    import scripts.export_procurement_space_recovery_candidates_preview as module

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    payload = build_procurement_space_recovery_candidates_preview()

    assert payload["summary"]["recovery_state"] == "no_candidates_detected"
