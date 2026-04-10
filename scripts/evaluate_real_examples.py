from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_RESULTS_DIR = Path("runs/real_data_benchmark/full_results")


def build_real_example_review(results_dir: str | Path = DEFAULT_RESULTS_DIR) -> dict[str, object]:
    from execution.materialization.training_packet_audit import audit_training_packets

    return audit_training_packets(results_dir).to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit real benchmark training packets.")
    parser.add_argument(
        "--results-dir",
        default=str(DEFAULT_RESULTS_DIR),
        help="Path to the real benchmark full_results directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a compact human-readable summary.",
    )
    args = parser.parse_args(argv)

    review = build_real_example_review(args.results_dir)
    if args.json:
        print(json.dumps(review, indent=2, sort_keys=True))
        return 0

    print("Real example packet audit")
    print(f"  benchmark_task: {review['benchmark_task']}")
    print(f"  packet_count: {review['summary']['packet_count']}")
    print(f"  useful: {review['summary']['judgment_counts']['useful']}")
    print(f"  weak: {review['summary']['judgment_counts']['weak']}")
    print(f"  blocked: {review['summary']['judgment_counts']['blocked']}")
    print(f"  selected_accession_count: {review['selected_accession_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
