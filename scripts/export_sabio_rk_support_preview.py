from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sabio_rk_support_common import (
    DEFAULT_ACCESSION_MATRIX,
    DEFAULT_OPERATOR_DASHBOARD,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_SABIO_ACCESSION_SEED,
    DEFAULT_SABIO_SEARCH_FIELDS,
    _read_json,
    build_sabio_rk_support_preview,
    render_preview_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the SABIO-RK accession-level support preview."
    )
    parser.add_argument("--accession-matrix", type=Path, default=DEFAULT_ACCESSION_MATRIX)
    parser.add_argument(
        "--sabio-accession-seed",
        type=Path,
        default=DEFAULT_SABIO_ACCESSION_SEED,
    )
    parser.add_argument(
        "--sabio-search-fields",
        type=Path,
        default=DEFAULT_SABIO_SEARCH_FIELDS,
    )
    parser.add_argument("--operator-dashboard", type=Path, default=DEFAULT_OPERATOR_DASHBOARD)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_sabio_rk_support_preview(
        _read_json(args.accession_matrix),
        args.sabio_accession_seed.read_text(encoding="utf-8"),
        args.sabio_search_fields.read_text(encoding="utf-8"),
        _read_json(args.operator_dashboard),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_preview_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
