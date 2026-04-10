from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.materialization.packet_gap_execution_plan import (  # noqa: E402
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_EVIDENCE_ARTIFACT_PATHS,
    DEFAULT_LOCAL_LIGAND_SOURCE_MAP_PATH,
    DEFAULT_MARKDOWN_PATH,
    DEFAULT_OUTPUT_PATH,
    build_packet_gap_execution_plan,
    render_markdown,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the packet-gap execution plan from the live deficit dashboard."
    )
    parser.add_argument("--dashboard", type=Path, default=DEFAULT_DASHBOARD_PATH)
    parser.add_argument(
        "--local-ligand-source-map",
        type=Path,
        default=DEFAULT_LOCAL_LIGAND_SOURCE_MAP_PATH,
    )
    parser.add_argument(
        "--evidence-artifact",
        dest="evidence_artifacts",
        action="append",
        type=Path,
        default=None,
        help="Optional rescue/proof artifact to include in the plan. May be repeated.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evidence_artifacts = (
        tuple(args.evidence_artifacts)
        if args.evidence_artifacts is not None
        else DEFAULT_EVIDENCE_ARTIFACT_PATHS
    )
    payload = build_packet_gap_execution_plan(
        dashboard_path=args.dashboard,
        local_ligand_source_map_path=args.local_ligand_source_map,
        evidence_artifact_paths=evidence_artifacts,
    )
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        summary = payload["summary"]
        local_count = (
            summary["quick_local_extraction_count"]
            + summary["local_bulk_assay_extraction_count"]
        )
        print(
            "Packet gap execution plan exported: "
            f"ranked={summary['ranked_source_ref_count']} "
            f"local={local_count} "
            f"fresh={summary['fresh_acquisition_blocker_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
