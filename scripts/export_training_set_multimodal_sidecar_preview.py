from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.final_structured_dataset_support import (
        resolve_canonical_store_path,
        resolve_materialization_summary_path,
    )
    from scripts.pre_tail_dataset_support import (
        build_training_set_multimodal_sidecar_preview,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from final_structured_dataset_support import (  # type: ignore[no-redef]
        resolve_canonical_store_path,
        resolve_materialization_summary_path,
    )
    from pre_tail_dataset_support import (
        build_training_set_multimodal_sidecar_preview,
        read_json,
        write_json,
        write_text,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "seed_plus_neighbors_structured_corpus_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_multimodal_sidecar_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_multimodal_sidecar_preview.md"
)


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Training Set Multimodal Sidecar Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Examples: `{summary.get('example_count')}`",
        f"- Issues: `{summary.get('issue_count')}`",
        f"- Canonical records: `{summary.get('canonical_record_count')}`",
        "",
    ]
    for row in (payload.get("strict_governing_training_view") or []):
        lines.append(f"- `governing`: `{row.get('example_id')}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the training-set multimodal sidecar preview."
    )
    parser.add_argument("--corpus-preview", type=Path, default=DEFAULT_CORPUS_PREVIEW)
    parser.add_argument("--materialization-summary", type=Path, default=None)
    parser.add_argument("--canonical-store", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    materialization_summary = args.materialization_summary or resolve_materialization_summary_path()
    canonical_store = args.canonical_store or resolve_canonical_store_path()
    payload = build_training_set_multimodal_sidecar_preview(
        read_json(args.corpus_preview),
        read_json(materialization_summary),
        read_json(canonical_store),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
