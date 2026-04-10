from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.materialization.raw_canonical_materializer import (
    DEFAULT_BINDINGDB_LOCAL_SUMMARY,
    DEFAULT_BOOTSTRAP_SUMMARY,
    DEFAULT_CANONICAL_ROOT,
    DEFAULT_LOCAL_REGISTRY_SUMMARY,
    materialize_raw_bootstrap_to_canonical,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize canonical records from pinned raw bootstrap snapshots."
    )
    parser.add_argument(
        "--bootstrap-summary",
        type=Path,
        default=DEFAULT_BOOTSTRAP_SUMMARY,
        help="Path to the raw bootstrap summary JSON.",
    )
    parser.add_argument(
        "--canonical-root",
        type=Path,
        default=DEFAULT_CANONICAL_ROOT,
        help="Target root for canonical outputs.",
    )
    parser.add_argument(
        "--local-registry-summary",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_SUMMARY,
        help="Optional local registry summary JSON for context reporting.",
    )
    parser.add_argument(
        "--bindingdb-local-summary",
        type=Path,
        default=DEFAULT_BINDINGDB_LOCAL_SUMMARY,
        help="Optional local BindingDB dump summary JSON for richer assay materialization.",
    )
    parser.add_argument(
        "--include-all-alphafold-records",
        action="store_true",
        help=(
            "Ingest every AlphaFold prediction record in each downloaded JSON, "
            "not just the first."
        ),
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="",
        help="Optional explicit run id for the canonical materialization output folder.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = materialize_raw_bootstrap_to_canonical(
        bootstrap_summary_path=args.bootstrap_summary,
        canonical_root=args.canonical_root,
        local_registry_summary_path=args.local_registry_summary,
        bindingdb_local_summary_path=args.bindingdb_local_summary,
        first_alphafold_record_only=not args.include_all_alphafold_records,
        run_id=args.run_id or None,
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
