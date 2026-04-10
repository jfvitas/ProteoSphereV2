from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

from scripts.validate_release_docs import (  # noqa: E402
    DEFAULT_REQUIRED_REPORT_DOCS,
    DEFAULT_REQUIRED_RUNBOOK_DOCS,
    build_release_docs_validation,
)


def _write_doc(path: Path, *, text: str, mtime: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    timestamp = mtime.timestamp()
    os.utime(path, (timestamp, timestamp))


def _prepare_docs(
    root: Path,
    stale_path: Path | None = None,
    stale_mtime: datetime | None = None,
) -> None:
    now = datetime(2026, 4, 3, 12, 0, tzinfo=UTC)
    stale_absolute = root / stale_path if stale_path is not None else None
    for rel_path in list(DEFAULT_REQUIRED_REPORT_DOCS) + list(DEFAULT_REQUIRED_RUNBOOK_DOCS):
        path = root / rel_path
        if stale_absolute is not None and path == stale_absolute:
            continue
        if path.suffix == ".json":
            contents = json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "status": "assembled_with_blockers",
                }
            )
        else:
            contents = "# Release doc\n\n- Generated at: `2026-04-03T12:00:00+00:00`\n"
        _write_doc(path, text=contents, mtime=now)
    if stale_absolute is not None and stale_mtime is not None:
        if stale_absolute.suffix == ".json":
            contents = json.dumps({"generated_at": (now - timedelta(hours=1)).isoformat()})
        else:
            contents = "# Release doc\n\n- Generated at: `2026-04-03T11:00:00+00:00`\n"
        _write_doc(stale_absolute, text=contents, mtime=stale_mtime)


def test_validate_release_docs_marks_fresh_required_sets(tmp_path: Path) -> None:
    _prepare_docs(tmp_path)
    as_of = datetime(2026, 4, 3, 12, 0, tzinfo=UTC)

    payload = build_release_docs_validation(
        repo_root=tmp_path,
        required_report_docs=DEFAULT_REQUIRED_REPORT_DOCS,
        required_runbook_docs=DEFAULT_REQUIRED_RUNBOOK_DOCS,
        stale_after_days=21,
        as_of=as_of,
    )

    assert payload["status"] == "ok"
    assert payload["overall_assessment"]["blocked_reasons"] == []
    assert payload["overall_assessment"]["missing_doc_count"] == 0
    assert payload["overall_assessment"]["stale_doc_count"] == 0
    assert payload["report_validation"]["required_count"] == len(DEFAULT_REQUIRED_REPORT_DOCS)
    assert payload["runbook_validation"]["required_count"] == len(DEFAULT_REQUIRED_RUNBOOK_DOCS)
    assert all(item["status"] == "fresh" for item in payload["report_validation"]["checks"])
    assert all(item["status"] == "fresh" for item in payload["runbook_validation"]["checks"])


def test_validate_release_docs_blocks_missing_and_stale_docs(tmp_path: Path) -> None:
    missing_report = DEFAULT_REQUIRED_REPORT_DOCS[1]
    stale_runbook = DEFAULT_REQUIRED_RUNBOOK_DOCS[-1]
    _prepare_docs(
        tmp_path,
        stale_path=stale_runbook,
        stale_mtime=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
    )
    _write_doc(
        tmp_path / stale_runbook,
        text="# Release doc\n",
        mtime=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
    )
    (tmp_path / missing_report).unlink()

    payload = build_release_docs_validation(
        repo_root=tmp_path,
        required_report_docs=DEFAULT_REQUIRED_REPORT_DOCS,
        required_runbook_docs=DEFAULT_REQUIRED_RUNBOOK_DOCS,
        stale_after_days=21,
        as_of=datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
    )

    assert payload["status"] == "blocked"
    assert "missing_release_docs" in payload["overall_assessment"]["blocked_reasons"]
    assert "stale_release_docs" in payload["overall_assessment"]["blocked_reasons"]
    assert str((tmp_path / missing_report).as_posix()) in payload["report_validation"][
        "missing_docs"
    ]
    assert str((tmp_path / stale_runbook).as_posix()) in payload["runbook_validation"][
        "stale_docs"
    ]


def test_validate_release_docs_prefers_generated_at_over_old_mtime(tmp_path: Path) -> None:
    _prepare_docs(
        tmp_path,
        stale_path=DEFAULT_REQUIRED_REPORT_DOCS[0],
        stale_mtime=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
    )

    payload = build_release_docs_validation(
        repo_root=tmp_path,
        required_report_docs=DEFAULT_REQUIRED_REPORT_DOCS,
        required_runbook_docs=DEFAULT_REQUIRED_RUNBOOK_DOCS,
        stale_after_days=21,
        as_of=datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
    )

    first_check = payload["report_validation"]["checks"][0]
    assert first_check["status"] == "fresh"
    assert first_check["timestamp_source"] in {"json-marker", "text-marker"}


def test_validate_release_docs_cli_exits_nonzero_on_stale_doc(tmp_path: Path) -> None:
    _prepare_docs(
        tmp_path,
        stale_path=DEFAULT_REQUIRED_RUNBOOK_DOCS[0],
        stale_mtime=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    _write_doc(
        tmp_path / DEFAULT_REQUIRED_RUNBOOK_DOCS[0],
        text="# Release doc\n",
        mtime=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    output_json = tmp_path / "release_docs_validation.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_release_docs.py"),
            "--repo-root",
            str(tmp_path),
            "--stale-after-days",
            "21",
            "--output-json",
            str(output_json),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked"
