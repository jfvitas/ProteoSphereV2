from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.pre_tail_readiness_support import (
        materialize_pre_tail_packet_stubs,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pre_tail_readiness_support import (
        materialize_pre_tail_packet_stubs,
        read_json,
        write_json,
        write_text,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_BALANCED_DATASET_PLAN = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "balanced_dataset_plan.json"
)
DEFAULT_PACKET_DEFICIT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_STUB_ROOT = REPO_ROOT / "artifacts" / "pre_tail_packet_stubs"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_materialization_queue_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_packet_materialization_queue_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Training Packet Materialization Queue Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Stub root: `{payload.get('summary', {}).get('stub_root')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / `{row['packet_lane']}` / `{row['materialization_mode']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize pre-tail packet stubs and export the queue preview."
    )
    parser.add_argument("--eligibility-matrix", type=Path, default=DEFAULT_ELIGIBILITY_MATRIX)
    parser.add_argument("--balanced-dataset-plan", type=Path, default=DEFAULT_BALANCED_DATASET_PLAN)
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT)
    parser.add_argument("--stub-root", type=Path, default=DEFAULT_STUB_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = materialize_pre_tail_packet_stubs(
        output_root=args.stub_root,
        eligibility_matrix=read_json(args.eligibility_matrix),
        balanced_dataset_plan=read_json(args.balanced_dataset_plan),
        packet_deficit_dashboard=read_json(args.packet_deficit),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
