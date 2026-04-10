from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "tasks" / "task_queue.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "p22_truth_boundary_audit.md"

READINESS_NOTE_PATTERNS = (
    "keep open until",
    "readiness-only",
    "readiness only",
)

READINESS_REPORT_PATTERNS = (
    "readiness assessment",
    "not a claim that",
    "does not yet justify",
    "not yet strong enough to claim",
    "no for any claim that the weeklong soak has already been completed",
)

SOAK_SCOPE_PATTERNS = (
    "weeklong",
    "soak",
    "durability",
)

COMPLETION_CLAIM_TITLE_PATTERNS = (
    "validate",
    "run ",
    "signoff",
    "release",
    "ga ",
    "weeklong",
)


def load_queue(path: Path = QUEUE_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _text_contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in patterns)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _title_can_overclaim(title: str) -> bool:
    return _text_contains_any(title, COMPLETION_CLAIM_TITLE_PATTERNS)


def audit_truth_boundaries(
    queue: list[dict[str, Any]],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    for task in queue:
        task_id = task["id"]
        status = task.get("status")
        notes = str(task.get("notes") or "")
        files = [repo_root / path for path in task.get("files", []) if str(path).endswith(".md")]

        readiness_note = _text_contains_any(notes, READINESS_NOTE_PATTERNS)
        readiness_report_paths = []
        for path in files:
            text = _read_text(path)
            if (
                text
                and _text_contains_any(text, READINESS_REPORT_PATTERNS)
                and _text_contains_any(text, SOAK_SCOPE_PATTERNS)
            ):
                readiness_report_paths.append(str(path))

        report_open_claim = (
            bool(readiness_report_paths)
            and _title_can_overclaim(task["title"])
            and _text_contains_any(task["title"], SOAK_SCOPE_PATTERNS)
        )

        if status == "done" and (readiness_note or report_open_claim):
            findings.append(
                {
                    "task_id": task_id,
                    "title": task["title"],
                    "status": status,
                    "notes_flagged": readiness_note,
                    "notes": notes,
                    "readiness_report_paths": readiness_report_paths,
                    "problem": (
                        "task is marked done even though notes/report text keep the claim open"
                    ),
                }
            )

    return {
        "status": "ok" if not findings else "mismatch",
        "finding_count": len(findings),
        "findings": findings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P22 Truth-Boundary Audit",
        "",
        (
            "This report audits queue status against explicit readiness-only wording "
            "in task notes and reports."
        ),
        "",
        f"- Status: `{report['status']}`",
        f"- Finding count: `{report['finding_count']}`",
        "",
    ]

    if not report["findings"]:
        lines.append("No truth-boundary mismatches were found in the audited queue slice.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Findings")
    lines.append("")
    for finding in report["findings"]:
        lines.append(f"- `{finding['task_id']}` `{finding['title']}`")
        lines.append(f"  Status: `{finding['status']}`")
        lines.append(f"  Problem: {finding['problem']}")
        if finding["notes_flagged"]:
            lines.append(f"  Notes: `{finding['notes']}`")
        if finding["readiness_report_paths"]:
            lines.append(
                "  Readiness-only reports: "
                + ", ".join(f"`{path}`" for path in finding["readiness_report_paths"])
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit queue truth boundaries against readiness-only task notes and reports."
    )
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the audit payload as JSON.")
    args = parser.parse_args(argv)

    queue = load_queue(args.queue)
    report = audit_truth_boundaries(queue, repo_root=REPO_ROOT)

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Truth-boundary audit: "
            f"status={report['status']} findings={report['finding_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
