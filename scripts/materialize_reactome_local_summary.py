from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.library.reactome_local_summary import (
    DEFAULT_CANONICAL_SUMMARY_PATH,
    DEFAULT_REACTOME_MAPPING_PATH,
    DEFAULT_REACTOME_PATHWAYS_PATH,
    DEFAULT_REACTOME_RELATIONS_PATH,
    materialize_reactome_local_summary_library,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "status" / "reactome_local_summary_library.json"


def _split_csv(values: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in values.split(",") if item.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize a Reactome-enriched local summary library for selected accessions."
    )
    parser.add_argument(
        "--accessions",
        type=str,
        required=True,
        help="Comma-separated accessions to materialize.",
    )
    parser.add_argument(
        "--canonical-summary",
        type=Path,
        default=DEFAULT_CANONICAL_SUMMARY_PATH,
        help="Optional canonical summary path for richer base protein records.",
    )
    parser.add_argument(
        "--mapping-path",
        type=Path,
        default=DEFAULT_REACTOME_MAPPING_PATH,
        help="Path to UniProt2Reactome_All_Levels.txt.",
    )
    parser.add_argument(
        "--pathways-path",
        type=Path,
        default=DEFAULT_REACTOME_PATHWAYS_PATH,
        help="Path to ReactomePathways.txt.",
    )
    parser.add_argument(
        "--relations-path",
        type=Path,
        default=DEFAULT_REACTOME_RELATIONS_PATH,
        help="Path to ReactomePathwaysRelation.txt.",
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
    library = materialize_reactome_local_summary_library(
        accessions=_split_csv(args.accessions),
        canonical_summary_path=args.canonical_summary,
        mapping_path=args.mapping_path,
        pathways_path=args.pathways_path,
        relations_path=args.relations_path,
        library_id=args.library_id or None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(library.to_dict(), indent=2), encoding="utf-8")
    print(json.dumps(library.to_dict(), indent=2))


if __name__ == "__main__":
    main()
