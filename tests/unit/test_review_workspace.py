from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.review_workspace import build_review_workspace

REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_fixture_tree(temp_root: Path) -> Path:
    (temp_root / "scripts").mkdir(parents=True, exist_ok=True)
    (temp_root / "docs" / "reports").mkdir(parents=True, exist_ok=True)
    (temp_root / "runs" / "real_data_benchmark" / "full_results").mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        REPO_ROOT / "scripts" / "review_workspace.py",
        temp_root / "scripts" / "review_workspace.py",
    )
    shutil.copy2(
        REPO_ROOT / "scripts" / "operator_recipes.ps1",
        temp_root / "scripts" / "operator_recipes.ps1",
    )
    shutil.copy2(
        REPO_ROOT / "docs" / "reports" / "p20_acceptance_matrix.md",
        temp_root / "docs" / "reports" / "p20_acceptance_matrix.md",
    )
    shutil.copy2(
        REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "user_sim_regression.json",
        temp_root / "runs" / "real_data_benchmark" / "full_results" / "user_sim_regression.json",
    )
    return temp_root


def _run_cli(repo_root: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "review_workspace.py"),
            "--results-dir",
            str(repo_root / "runs" / "real_data_benchmark" / "full_results"),
            "--reports-dir",
            str(repo_root / "docs" / "reports"),
            "--operator-recipes",
            str(repo_root / "scripts" / "operator_recipes.ps1"),
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def test_review_workspace_promotes_and_blocks_real_user_sim(tmp_path: Path) -> None:
    repo_root = _copy_fixture_tree(tmp_path / "repo")

    workspace = build_review_workspace(
        results_dir=repo_root / "runs" / "real_data_benchmark" / "full_results",
        reports_dir=repo_root / "docs" / "reports",
        operator_recipes_path=repo_root / "scripts" / "operator_recipes.ps1",
    )

    payload = workspace.to_dict()
    promoted = payload["groups"]["promoted"]
    weak = payload["groups"]["weak"]
    blocked = payload["groups"]["blocked"]

    assert payload["scenario_count"] == 6
    assert payload["promoted_count"] == 1
    assert payload["weak_count"] == 4
    assert payload["blocked_count"] == 1
    assert payload["stop_count"] == 1
    assert payload["batch_state"] == "blocked"
    assert payload["batch_action"] == "stop"
    assert payload["operator_recipe_ids"] == [
        "acceptance-review",
        "packet-triage",
        "benchmark-review",
        "soak-readiness",
        "onboarding",
    ]

    assert len(promoted) == 1
    assert promoted[0]["scenario_id"] == "P20-G001-P69905"
    assert promoted[0]["review_state"] == "promoted"
    assert promoted[0]["action"] == "promote"
    assert promoted[0]["stop"] is False
    assert promoted[0]["promotion_target"] == "acceptance-review"
    assert "promoted for acceptance-review" in promoted[0]["summary"]

    assert len(weak) == 4
    assert {item["review_state"] for item in weak} == {"weak"}
    assert any(
        item["scenario_id"] == "P20-G002-P68871"
        and item["recipe_hint"] == "acceptance-review"
        for item in weak
    )
    assert any(
        item["scenario_id"] == "P20-G003-P04637"
        and item["recipe_hint"] == "packet-triage"
        for item in weak
    )
    assert any(
        item["scenario_id"] == "P20-G005-Q9NZD4"
        and item["recipe_hint"] == "benchmark-review"
        for item in weak
    )
    assert any(item["scenario_id"] == "P20-G005-Q9NZD4" for item in weak)

    assert len(blocked) == 1
    assert blocked[0]["scenario_id"] == "P20-G006-BLOCKED-SOAK"
    assert blocked[0]["review_state"] == "blocked"
    assert blocked[0]["action"] == "stop"
    assert blocked[0]["stop"] is True
    assert blocked[0]["recipe_hint"] == "soak-readiness"
    assert "must stop" in blocked[0]["summary"]


def test_review_workspace_cli_emits_json_with_explicit_states(tmp_path: Path) -> None:
    repo_root = _copy_fixture_tree(tmp_path / "repo")

    payload = _run_cli(repo_root)

    assert payload["batch_state"] == "blocked"
    assert payload["batch_action"] == "stop"
    assert payload["promoted_count"] == 1
    assert payload["blocked_count"] == 1
    assert payload["groups"]["promoted"][0]["review_state"] == "promoted"
    assert payload["groups"]["blocked"][0]["review_state"] == "blocked"
    assert payload["groups"]["blocked"][0]["stop"] is True
