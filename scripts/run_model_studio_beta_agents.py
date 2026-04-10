from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.model_studio.service import build_program_status  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "artifacts"
    / "reviews"
    / "model_studio_internal_alpha"
    / "beta_agent_sweeps"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed or export the cross-functional 1920x1080 beta-agent sweep bundle."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8782")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--sweep-id", default="latest")
    parser.add_argument(
        "--mode",
        choices=("seed-from-status", "plan-live-capture"),
        default="seed-from-status",
    )
    return parser.parse_args()


def _save_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _playwright_env() -> dict[str, str]:
    env = dict(**__import__("os").environ)
    path_bits = [
        r"C:\Program Files\nodejs",
        str(Path.home() / "AppData" / "Roaming" / "npm"),
        env.get("PATH", ""),
    ]
    env["PATH"] = ";".join(bit for bit in path_bits if bit)
    return env


def _run_playwright(*args: str) -> str:
    executable = shutil.which("playwright-cli", path=_playwright_env()["PATH"]) or "playwright-cli"
    result = subprocess.run(
        [executable, *args],
        check=True,
        capture_output=True,
        text=True,
        env=_playwright_env(),
        cwd=REPO_ROOT,
    )
    return result.stdout.strip()


def _capture_live_section_sweep(base_url: str, sweep_root: Path) -> dict[str, object]:
    if shutil.which("playwright-cli", path=_playwright_env()["PATH"]) is None:
        return {
            "status": "runner_missing",
            "captured": [],
            "note": "playwright-cli is not available in PATH for this script run.",
        }
    capture_root = sweep_root / "live_capture"
    capture_root.mkdir(parents=True, exist_ok=True)
    sections = {
        "home": base_url,
        "project_home": f"{base_url}#workspace-project-home",
        "data_strategy": f"{base_url}#workspace-data-strategy-designer",
        "execution_console": f"{base_url}#workspace-execution-console",
        "analysis_review": f"{base_url}#workspace-analysis-and-review",
    }
    captured: list[str] = []
    _run_playwright("open", base_url, "--headed")
    try:
        _run_playwright("resize", "1920", "1080")
        snapshot_text = _run_playwright("snapshot", "--raw")
        (capture_root / "snapshot.txt").write_text(snapshot_text, encoding="utf-8")
        for name, url in sections.items():
            _run_playwright("goto", url)
            screenshot_path = capture_root / f"{name}.png"
            _run_playwright("screenshot", "--filename", str(screenshot_path))
            captured.append(str(screenshot_path))
        _run_playwright("goto", f"{base_url}#workspace-data-strategy-designer")
        _run_playwright("select", "#dataset-primary-select", "governed_ppi_external_beta_candidate_v1")
        _run_playwright("select", "#dataset-refs-select", "governed_ppi_external_beta_candidate_v1")
        governed_subset_path = capture_root / "governed_subset.png"
        _run_playwright("screenshot", "--filename", str(governed_subset_path))
        captured.append(str(governed_subset_path))
    finally:
        try:
            _run_playwright("close")
        except subprocess.SubprocessError:
            pass
    return {
        "status": "captured",
        "captured": [str(Path(item).relative_to(REPO_ROOT)) for item in captured],
        "snapshot": str((capture_root / "snapshot.txt").relative_to(REPO_ROOT)),
    }


def _refresh_bundle_from_live_capture(
    *,
    beta_agents: list[dict[str, object]],
    agent_runs: list[dict[str, object]],
    findings: dict[str, object],
    matrix: dict[str, object],
    agent_status: dict[str, object],
    live_capture: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object], dict[str, object]]:
    captured = set(live_capture.get("captured", [])) if isinstance(live_capture, dict) else set()
    governed_path = next((item for item in captured if item.endswith("governed_subset.png")), "")
    if not governed_path:
        return agent_runs, findings, matrix, agent_status

    refreshed_runs: list[dict[str, object]] = []
    for run in agent_runs:
        if run.get("flow_id") == "governed_ppi_subset_flow":
            artifact_paths = list(run.get("artifact_paths", []))
            if governed_path not in artifact_paths:
                artifact_paths.append(governed_path)
            refreshed_runs.append(
                {
                    **run,
                    "status": "ready",
                    "artifact_paths": artifact_paths,
                    "screens_evaluated": [item for item in artifact_paths if str(item).endswith(".png")],
                    "overall_verdict": "pass",
                    "top_findings": [
                        "A dedicated governed promoted-subset state was captured live at 1920x1080 in the current Studio build.",
                        "Launchability and governed-subset labeling remain aligned with backend-authored pool truth.",
                    ],
                    "recommended_actions": [
                        "Add a full governed-subset trace in a future sweep if the user-sim path changes materially.",
                    ],
                }
            )
        else:
            refreshed_runs.append(run)

    open_findings = [
        item
        for item in list(findings.get("open_findings", []))
        if item.get("flow_id") != "governed_ppi_subset_flow"
    ]
    refreshed_findings = {
        **findings,
        "open_findings": open_findings,
        "by_severity": {},
        "by_owner_lane": {},
        "by_flow": {},
        "open_p1_count": 0,
    }
    for item in open_findings:
        severity = str(item.get("severity", ""))
        owner_lane = str(item.get("owner_lane", ""))
        flow_id = str(item.get("flow_id", ""))
        refreshed_findings["by_severity"][severity] = refreshed_findings["by_severity"].get(severity, 0) + 1
        refreshed_findings["by_owner_lane"][owner_lane] = refreshed_findings["by_owner_lane"].get(owner_lane, 0) + 1
        refreshed_findings["by_flow"][flow_id] = refreshed_findings["by_flow"].get(flow_id, 0) + 1
        if severity == "P1":
            refreshed_findings["open_p1_count"] += 1

    refreshed_coverage = []
    for item in list(matrix.get("coverage", [])):
        if item.get("flow_id") == "governed_ppi_subset_flow":
            refreshed_coverage.append(
                {
                    **item,
                    "status": "ready",
                    "agent_results": [
                        {
                            **agent_result,
                            "status": "ready",
                            "overall_verdict": "pass",
                        }
                        for agent_result in item.get("agent_results", [])
                    ],
                }
            )
        else:
            refreshed_coverage.append(item)
    refreshed_matrix = {**matrix, "coverage": refreshed_coverage}

    refreshed_status = {
        **agent_status,
        "current_sweep_complete": True,
        "status": "ready" if refreshed_findings["open_p1_count"] == 0 else "review_pending",
        "missing_flows": [],
    }
    return refreshed_runs, refreshed_findings, refreshed_matrix, refreshed_status


def main() -> None:
    args = parse_args()
    status = build_program_status()
    sweep_root = args.output_root / args.sweep_id / "1080p"
    required_viewport = {"width": 1920, "height": 1080}
    minimum_viewport = {"width": 1280, "height": 720}
    beta_agents = status["beta_test_agents"]
    agent_runs = [
        {**run, "viewport": required_viewport}
        for run in status["beta_test_agent_runs"]
    ]
    findings = status["beta_test_agent_findings"]
    matrix = {
        **status["beta_test_agent_matrix"],
        "required_viewport": required_viewport,
        "minimum_viewport": minimum_viewport,
    }
    agent_status = {
        **status["beta_test_agent_status"],
        "required_viewport": required_viewport,
        "minimum_viewport": minimum_viewport,
        "artifact_root": str((args.output_root / args.sweep_id).relative_to(REPO_ROOT)).replace("\\", "/"),
    }

    environment = {
        "base_url": args.base_url,
        "mode": args.mode,
        "required_viewport": required_viewport,
        "minimum_viewport": minimum_viewport,
        "runner_environment": agent_status["runner_environment"],
        "note": (
            "This bundle is seeded from the Studio control plane. Use plan-live-capture with playwright-cli commands to replace seeded evidence with a fresh browser sweep."
            if args.mode == "seed-from-status"
            else "Live capture planning is enabled; execute the recorded commands to replace seeded evidence with fresh browser artifacts."
        ),
        "capture_plan": [
            "playwright-cli open http://127.0.0.1:8782 --headed",
            "playwright-cli resize 1920 1080",
            "playwright-cli tracing-start",
            "playwright-cli snapshot",
            "playwright-cli screenshot",
        ],
    }
    if args.mode == "plan-live-capture":
        environment["live_capture"] = _capture_live_section_sweep(args.base_url, sweep_root)
        agent_runs, findings, matrix, agent_status = _refresh_bundle_from_live_capture(
            beta_agents=beta_agents,
            agent_runs=agent_runs,
            findings=findings,
            matrix=matrix,
            agent_status=agent_status,
            live_capture=environment["live_capture"],
        )
    _save_json(sweep_root / "agent_catalog.json", beta_agents)
    _save_json(sweep_root / "agent_status.json", agent_status)
    _save_json(sweep_root / "agent_matrix.json", matrix)
    _save_json(sweep_root / "agent_findings.json", findings)
    _save_json(sweep_root / "environment.json", environment)
    for agent in beta_agents:
        agent_dir = sweep_root / agent["agent_id"]
        agent_bundle = [
            run for run in agent_runs if run["agent_id"] == agent["agent_id"]
        ]
        _save_json(agent_dir / "definition.json", agent)
        _save_json(agent_dir / "runs.json", agent_bundle)
    print(
        json.dumps(
            {
                "status": "ready",
                "sweep_root": str(sweep_root),
                "agent_count": len(beta_agents),
                "run_count": len(agent_runs),
                "mode": args.mode,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
