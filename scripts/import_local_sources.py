from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_source_mirror import DEFAULT_RAW_ROOT, mirror_local_sources
from execution.acquire.local_source_registry import DEFAULT_LOCAL_SOURCE_ROOT


def _split_csv(values: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in values.split(",") if item.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Register local bio-agent-lab corpora, including present data/ context folders, "
            "into data/raw manifests. "
            "Scoped imports write timestamped summaries but do not advance repo-wide "
            "local_registry_runs/LATEST.json."
        )
    )
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=DEFAULT_LOCAL_SOURCE_ROOT,
        help="Root path for the local bio-agent-lab workspace.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="Target data/raw root for local registry manifests and inventories.",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="",
        help=(
            "Optional comma-separated subset of source names from the local source registry. "
            "Subset imports are treated as scoped runs and do not overwrite canonical latest."
        ),
    )
    parser.add_argument(
        "--include-missing",
        action="store_true",
        help="Also emit inventories for missing sources so the gaps stay visible in data/raw.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=8,
        help="How many sample file paths to retain per present root summary.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned local import summary without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = mirror_local_sources(
        storage_root=args.storage_root,
        raw_root=args.raw_root,
        source_names=_split_csv(args.sources) or None,
        include_missing=args.include_missing,
        dry_run=args.dry_run,
        sample_limit=max(1, args.sample_limit),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
