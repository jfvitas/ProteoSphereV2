from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.library.protein_summary_materializer import (  # noqa: E402
    DEFAULT_CANONICAL_LATEST_PATH,
    DEFAULT_INTACT_SUMMARY_PATH,
    DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REACTOME_SUMMARY_PATH,
    materialize_protein_summary_library,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a protein summary library from canonical, Reactome, IntAct, and local "
            "registry-backed motif/classification sources with scalar trust/consensus, "
            "source-rollup annotations, and a compact cross-source connection view."
        )
    )
    parser.add_argument(
        "--canonical-latest",
        type=Path,
        default=DEFAULT_CANONICAL_LATEST_PATH,
        help="Path to data/canonical/LATEST.json.",
    )
    parser.add_argument(
        "--reactome-summary",
        type=Path,
        default=DEFAULT_REACTOME_SUMMARY_PATH,
        help="Path to the current Reactome local summary artifact.",
    )
    parser.add_argument(
        "--intact-summary",
        type=Path,
        default=DEFAULT_INTACT_SUMMARY_PATH,
        help="Path to the current IntAct local summary artifact.",
    )
    parser.add_argument(
        "--library-id",
        type=str,
        default="",
        help="Optional explicit library id.",
    )
    parser.add_argument(
        "--local-registry-summary",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH,
        help="Path to data/raw/local_registry_runs/LATEST.json.",
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
    library = materialize_protein_summary_library(
        canonical_latest_path=args.canonical_latest,
        reactome_summary_path=args.reactome_summary,
        intact_summary_path=args.intact_summary,
        local_registry_summary_path=args.local_registry_summary,
        library_id=args.library_id or "summary-library:protein-materialized:v1",
    )
    payload = library.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
