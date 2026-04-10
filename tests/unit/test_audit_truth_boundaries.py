from __future__ import annotations

from pathlib import Path

from scripts.audit_truth_boundaries import audit_truth_boundaries, render_markdown


def test_audit_truth_boundaries_flags_done_task_with_readiness_note(tmp_path: Path) -> None:
    queue = [
        {
            "id": "P22-I007",
            "title": "Run weeklong unattended soak validation",
            "status": "done",
            "notes": "Keep open until the ledger covers a real weeklong unattended window.",
            "files": ["docs/reports/p22_weeklong_soak.md"],
        }
    ]
    report_path = tmp_path / "docs" / "reports" / "p22_weeklong_soak.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        (
            "This note is a readiness assessment, not a claim that a weeklong "
            "run has already completed."
        ),
        encoding="utf-8",
    )

    report = audit_truth_boundaries(queue, repo_root=tmp_path)

    assert report["status"] == "mismatch"
    assert report["finding_count"] == 1
    assert report["findings"][0]["task_id"] == "P22-I007"


def test_audit_truth_boundaries_ignores_non_done_task(tmp_path: Path) -> None:
    queue = [
        {
            "id": "P22-I007",
            "title": "Run weeklong unattended soak validation",
            "status": "dispatched",
            "notes": "Keep open until the ledger covers a real weeklong unattended window.",
            "files": ["docs/reports/p22_weeklong_soak.md"],
        }
    ]
    report_path = tmp_path / "docs" / "reports" / "p22_weeklong_soak.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        (
            "This note is a readiness assessment, not a claim that a weeklong "
            "run has already completed."
        ),
        encoding="utf-8",
    )

    report = audit_truth_boundaries(queue, repo_root=tmp_path)

    assert report["status"] == "ok"
    assert report["finding_count"] == 0


def test_render_markdown_lists_findings() -> None:
    markdown = render_markdown(
        {
            "status": "mismatch",
            "finding_count": 1,
            "findings": [
                {
                    "task_id": "P22-I007",
                    "title": "Run weeklong unattended soak validation",
                    "status": "done",
                    "notes_flagged": True,
                    "notes": "Keep open until the ledger covers a real weeklong unattended window.",
                    "readiness_report_paths": [
                        "D:/documents/ProteoSphereV2/docs/reports/p22_weeklong_soak.md"
                    ],
                    "problem": (
                        "task is marked done even though notes/report text keep "
                        "the claim open"
                    ),
                }
            ],
        }
    )

    assert "# P22 Truth-Boundary Audit" in markdown
    assert "`P22-I007`" in markdown
    assert "readiness-only reports" in markdown.lower()
