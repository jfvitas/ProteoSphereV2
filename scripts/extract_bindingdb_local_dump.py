from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.bindingdb_dump_extract import (
    extract_bindingdb_dump_records,
    write_bindingdb_dump_extract,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP_PATH = (
    Path("C:/Users/jfvit/Documents/bio-agent-lab/data_sources/bindingdb/BDB-mySQL_All_202603_dmp.zip")
)
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "raw" / "bindingdb_dump_local"


def _split_csv(values: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in values.split(",") if item.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract accession-scoped BindingDB slices from the local full SQL dump."
    )
    parser.add_argument(
        "--accessions",
        required=True,
        help="Comma-separated UniProt accessions to extract from the local BindingDB dump.",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=DEFAULT_ZIP_PATH,
        help="Path to the local BindingDB SQL dump zip.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory where extracted raw BindingDB dump slices should be written.",
    )
    parser.add_argument(
        "--dump-entry-name",
        default=None,
        help="Optional explicit dump entry name inside the zip archive.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional output run id. Defaults to a timestamped value.",
    )
    args = parser.parse_args()

    result = extract_bindingdb_dump_records(
        args.zip_path,
        _split_csv(args.accessions),
        dump_entry_name=args.dump_entry_name,
    )
    paths = write_bindingdb_dump_extract(result, output_root=args.output_root, run_id=args.run_id)
    print(
        json.dumps(
            {
                "status": "ok",
                "accessions": list(result.accessions),
                "slice_count": len(result.slices),
                "paths": paths,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
