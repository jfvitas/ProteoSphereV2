from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.model_studio.paper_evaluator import (
    DEFAULT_CORPUS_PATH,
    DEFAULT_WAREHOUSE_ROOT,
    evaluate_paper_corpus,
    load_live_warehouse_snapshot,
    load_paper_corpus,
    render_evaluation_markdown,
)

DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_dataset_evaluator.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "paper_dataset_evaluator.md"
DEFAULT_PER_PAPER_DIR = REPO_ROOT / "artifacts" / "status" / "paper_dataset_evaluator"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate paper-described dataset splits against the ProteoSphere warehouse.")
    parser.add_argument("--input-json", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--warehouse-root", type=Path, default=DEFAULT_WAREHOUSE_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--per-paper-dir", type=Path, default=DEFAULT_PER_PAPER_DIR)
    return parser.parse_args()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    corpus = load_paper_corpus(args.input_json)
    snapshot = load_live_warehouse_snapshot(args.warehouse_root)
    report = evaluate_paper_corpus(corpus, snapshot)
    _write_json(args.output_json, report)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_evaluation_markdown(report), encoding="utf-8")
    args.per_paper_dir.mkdir(parents=True, exist_ok=True)
    for row in report["papers"]:
        _write_json(args.per_paper_dir / f"{row['paper_id']}.json", row)
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_md}")
    print(f"Wrote {len(report['papers'])} per-paper artifacts to {args.per_paper_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
