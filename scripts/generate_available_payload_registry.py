from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.materialization.available_payload_registry import (  # noqa: E402
    build_available_payload_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BALANCED_PLAN_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "balanced_dataset_plan.json"
)
DEFAULT_CANONICAL_LATEST_PATH = REPO_ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "available_payloads.generated.json"
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_fingerprint(payload: Any) -> str:
    return _sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def build_registry_report(
    *,
    balanced_plan_path: Path,
    canonical_latest_path: Path,
    raw_root: Path,
) -> dict[str, Any]:
    balanced_plan = _read_json(balanced_plan_path)
    if not isinstance(balanced_plan, dict):
        raise TypeError("balanced plan must be a JSON object")

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest_path,
        raw_root=raw_root,
    )
    payload = registry.to_dict()
    available_payloads = payload.get("available_payloads") or {}
    input_fingerprints = {
        "balanced_plan_sha256": _file_sha256(balanced_plan_path),
        "canonical_latest_sha256": _file_sha256(canonical_latest_path),
    }
    registry_fingerprints = {
        "available_payloads_sha256": _json_fingerprint(available_payloads),
        "build_sha256": _json_fingerprint(
            {
                "balanced_plan_sha256": input_fingerprints["balanced_plan_sha256"],
                "canonical_latest_sha256": input_fingerprints["canonical_latest_sha256"],
                "available_payloads_sha256": _json_fingerprint(available_payloads),
                "available_payload_count": payload.get("available_payload_count"),
                "missing_payload_count": payload.get("missing_payload_count"),
            }
        ),
        "digest_basis": "sorted_json_content",
        "raw_root_basis": "reflected_by_discovered_payload_entries",
    }
    return {
        "schema_id": "proteosphere-available-payload-registry-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "balanced_plan_path": str(balanced_plan_path).replace("\\", "/"),
        "canonical_latest_path": str(canonical_latest_path).replace("\\", "/"),
        "raw_root": str(raw_root).replace("\\", "/"),
        "input_fingerprints": input_fingerprints,
        "registry_fingerprints": registry_fingerprints,
        **payload,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an available-payload registry for selected cohort materialization."
    )
    parser.add_argument("--balanced-plan", type=Path, default=DEFAULT_BALANCED_PLAN_PATH)
    parser.add_argument("--canonical-latest", type=Path, default=DEFAULT_CANONICAL_LATEST_PATH)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_registry_report(
        balanced_plan_path=args.balanced_plan,
        canonical_latest_path=args.canonical_latest,
        raw_root=args.raw_root,
    )
    _write_json(args.output, report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Available payload registry generated: "
            f"available={report['available_payload_count']} "
            f"missing={report['missing_payload_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
