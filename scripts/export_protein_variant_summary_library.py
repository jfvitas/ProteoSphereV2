from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.library.protein_variant_materializer import (  # noqa: E402
    DEFAULT_INTACT_MUTATION_PATH,
    DEFAULT_LIBRARY_ID,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PROTEIN_SUMMARY_LIBRARY_PATH,
    DEFAULT_UNIPROT_ROOT,
    DEFAULT_VARIANT_EVIDENCE_PATHS,
    build_protein_variant_summary_library_from_paths,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the first executable protein-variant summary library slice from "
            "the materialized protein summary library, local UniProt payloads, and "
            "the local IntAct mutation export."
        )
    )
    parser.add_argument(
        "--protein-summary-library",
        type=Path,
        default=DEFAULT_PROTEIN_SUMMARY_LIBRARY_PATH,
        help="Path to the materialized protein summary library JSON.",
    )
    parser.add_argument(
        "--variant-evidence",
        type=Path,
        action="append",
        default=None,
        help=(
            "Path to a variant evidence-hunt contract JSON that scopes a supported slice. "
            "Repeat to union multiple supported slices."
        ),
    )
    parser.add_argument(
        "--uniprot-root",
        type=Path,
        default=DEFAULT_UNIPROT_ROOT,
        help="Root directory containing accession-scoped local UniProt payloads.",
    )
    parser.add_argument(
        "--intact-mutation-path",
        type=Path,
        default=DEFAULT_INTACT_MUTATION_PATH,
        help="Path to the local IntAct mutation export TSV.",
    )
    parser.add_argument(
        "--library-id",
        type=str,
        default=DEFAULT_LIBRARY_ID,
        help="Optional explicit library id override.",
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
    library = build_protein_variant_summary_library_from_paths(
        protein_summary_library_path=args.protein_summary_library,
        variant_evidence_paths=args.variant_evidence or DEFAULT_VARIANT_EVIDENCE_PATHS,
        uniprot_root=args.uniprot_root,
        intact_mutation_path=args.intact_mutation_path,
        library_id=args.library_id or DEFAULT_LIBRARY_ID,
    )
    payload = library.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
