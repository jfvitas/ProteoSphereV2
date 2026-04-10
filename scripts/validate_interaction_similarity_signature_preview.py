from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from interaction_similarity_signature_common import (  # noqa: E402
    DEFAULT_BUNDLE_MANIFEST,
    DEFAULT_LOCAL_REGISTRY_RUNS_ROOT,
    _read_json,
    build_interaction_similarity_signature_validation,
    render_validation_markdown,
)

DEFAULT_OUTPUT_JSON = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "status"
    / "interaction_similarity_signature_validation.json"
)
DEFAULT_OUTPUT_MD = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reports"
    / "interaction_similarity_signature_validation.md"
)
DEFAULT_PREVIEW_JSON = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "status"
    / "interaction_similarity_signature_preview.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the compact interaction similarity signature preview."
    )
    parser.add_argument("--preview-json", type=Path, default=DEFAULT_PREVIEW_JSON)
    parser.add_argument("--bundle-manifest", type=Path, default=DEFAULT_BUNDLE_MANIFEST)
    parser.add_argument(
        "--local-registry-runs-root",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_RUNS_ROOT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_interaction_similarity_signature_validation(
        _read_json(args.preview_json),
        _read_json(args.bundle_manifest),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_validation_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

