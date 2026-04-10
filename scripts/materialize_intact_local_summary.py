from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.library.intact_local_summary import (  # noqa: E402
    DEFAULT_CANONICAL_SUMMARY_PATH,
    DEFAULT_INTACT_RAW_ROOT,
    materialize_intact_local_summary_library,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "status" / "intact_local_summary_library.json"


def _split_csv(values: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in values.split(",") if item.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize an IntAct-enriched local summary library for selected accessions."
    )
    parser.add_argument(
        "--accessions",
        type=str,
        required=True,
        help="Comma-separated accessions to materialize.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_INTACT_RAW_ROOT,
        help="Path to the IntAct raw snapshot root or parent directory.",
    )
    parser.add_argument(
        "--canonical-summary",
        type=Path,
        default=DEFAULT_CANONICAL_SUMMARY_PATH,
        help="Optional canonical summary path for richer base protein records.",
    )
    parser.add_argument(
        "--library-id",
        type=str,
        default="",
        help="Optional explicit library id.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Target JSON artifact path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    library = materialize_intact_local_summary_library(
        accessions=_split_csv(args.accessions),
        raw_root=args.raw_root,
        canonical_summary_path=args.canonical_summary,
        library_id=args.library_id or None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(library.to_dict(), indent=2), encoding="utf-8")
    print(json.dumps(library.to_dict(), indent=2))


if __name__ == "__main__":
    main()
