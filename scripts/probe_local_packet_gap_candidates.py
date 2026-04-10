from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_gap_probe import probe_local_gap_candidates  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD_PATH = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_LOCAL_REGISTRY_PATH = REPO_ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "local_packet_gap_candidates.json"
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_local_packet_gap_report(
    *,
    dashboard_path: Path,
    local_registry_path: Path,
    master_pdb_repository_path: Path | None = None,
) -> dict[str, Any]:
    dashboard = _read_json(dashboard_path)
    local_registry = _read_json(local_registry_path)
    if not isinstance(dashboard, dict):
        raise TypeError("packet deficit dashboard must be a JSON object")
    if not isinstance(local_registry, dict):
        raise TypeError("local registry summary must be a JSON object")

    probed = probe_local_gap_candidates(
        packet_deficit_dashboard=dashboard,
        local_registry_summary=local_registry,
        master_pdb_repository_path=master_pdb_repository_path,
    )
    return {
        "schema_id": "proteosphere-local-packet-gap-candidates-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "dashboard_path": str(dashboard_path).replace("\\", "/"),
        "local_registry_path": str(local_registry_path).replace("\\", "/"),
        **probed,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe local bio-agent-lab corpora for packet-deficit recovery candidates."
    )
    parser.add_argument("--dashboard", type=Path, default=DEFAULT_DASHBOARD_PATH)
    parser.add_argument("--local-registry", type=Path, default=DEFAULT_LOCAL_REGISTRY_PATH)
    parser.add_argument("--master-pdb-repository", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_packet_gap_report(
        dashboard_path=args.dashboard,
        local_registry_path=args.local_registry,
        master_pdb_repository_path=args.master_pdb_repository,
    )
    _write_json(args.output, payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local packet gap probe exported: "
            f"candidates={payload['candidate_count']} "
            f"recoverable={payload['recovery_candidate_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
