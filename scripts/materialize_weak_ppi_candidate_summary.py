from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.library.weak_ppi_candidate_summary import (  # noqa: E402
    DEFAULT_ACCESSIONS,
    DEFAULT_INTACT_RAW_ROOT,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    materialize_weak_ppi_candidate_summary,
    write_weak_ppi_candidate_summary_artifact,
)


def _split_csv(values: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in values.split(",") if item.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize a weak-PPI summary decision artifact for selected accessions."
    )
    parser.add_argument(
        "--accessions",
        type=str,
        default=",".join(DEFAULT_ACCESSIONS),
        help="Comma-separated accessions to analyze.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_INTACT_RAW_ROOT,
        help="Path to the IntAct raw snapshot root or parent directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Target JSON artifact path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Target markdown report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifact = materialize_weak_ppi_candidate_summary(
        accessions=_split_csv(args.accessions),
        raw_root=args.raw_root,
    )
    write_weak_ppi_candidate_summary_artifact(
        artifact,
        output_path=args.output,
        report_path=args.report,
    )
    print(json.dumps(artifact.to_dict(), indent=2))


if __name__ == "__main__":
    main()
