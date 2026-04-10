from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from external_dataset_assessment_support import (  # noqa: E402
    build_external_dataset_intake_contract_preview,
    render_markdown,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_intake_contract_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "external_dataset_intake_contract_preview.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export external dataset intake contract preview.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_external_dataset_intake_contract_preview()
    write_json(args.output_json, payload)
    write_text(
        args.output_md,
        render_markdown("External Dataset Intake Contract Preview", payload),
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
