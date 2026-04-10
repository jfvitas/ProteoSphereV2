from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_source_mirror import build_bio_agent_lab_context_registry
from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_ROOT,
    build_default_local_source_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "p35_local_registry_expansion.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "p35_local_registry_expansion.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_local_registry_expansion_report(
    storage_root: str | Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> dict[str, Any]:
    root = Path(storage_root)
    baseline_registry = build_default_local_source_registry(root)
    expanded_registry = build_bio_agent_lab_context_registry(root)
    baseline_names = {entry.source_name for entry in baseline_registry.entries}
    new_entries = sorted(
        (entry for entry in expanded_registry.entries if entry.source_name not in baseline_names),
        key=lambda entry: entry.source_name.casefold(),
    )
    return {
        "schema_id": "proteosphere-p35-local-registry-expansion-2026-03-30",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "storage_root": str(root),
        "baseline_registry_id": baseline_registry.registry_id,
        "expanded_registry_id": expanded_registry.registry_id,
        "baseline_source_count": baseline_registry.entry_count,
        "expanded_source_count": expanded_registry.entry_count,
        "source_count_delta": expanded_registry.entry_count - baseline_registry.entry_count,
        "new_source_count": len(new_entries),
        "new_source_groups": [
            {
                "source_name": entry.source_name,
                "category": entry.category,
                "load_hints": list(entry.load_hints),
                "status": entry.status,
                "present_root_count": len(entry.present_roots),
                "present_roots": list(entry.present_roots),
            }
            for entry in new_entries
        ],
        "notes": [
            "Registry counts are source-group counts, not file counts.",
            "Only present bio-agent-lab/data context folders are promoted into "
            "the expansion delta.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Registry Expansion",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Storage root: `{payload.get('storage_root')}`",
        f"- Baseline source groups: `{payload.get('baseline_source_count')}`",
        f"- Expanded source groups: `{payload.get('expanded_source_count')}`",
        f"- Delta: `{payload.get('source_count_delta')}`",
        "",
        "## Newly Registered Context Folders",
        "",
        "| Source | Category | Load hints | Present roots |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload.get("new_source_groups") or []:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{item.get('source_name')} | "
            f"{item.get('category')} | "
            f"{', '.join(item.get('load_hints') or []) or '-'} | "
            f"{item.get('present_root_count')} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            *(f"- {note}" for note in payload.get("notes") or []),
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the latest local-registry expansion into a compact report."
    )
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_LOCAL_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_registry_expansion_report(args.storage_root)
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload) + "\n")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local registry expansion exported: "
            f"baseline={payload['baseline_source_count']} "
            f"expanded={payload['expanded_source_count']} "
            f"new={payload['new_source_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
