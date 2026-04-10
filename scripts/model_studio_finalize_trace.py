from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen

from selenium.webdriver.common.by import By

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_studio_browser_helpers import (
    build_browser_driver,
    ensure_directory,
    wait_for_workspace,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(url: str) -> dict:
    with urlopen(url, timeout=15) as response:  # nosec - local beta server only
        return json.loads(response.read().decode("utf-8"))


def _list_runs(base_url: str) -> list[dict]:
    payload = _load_json(f"{base_url}/api/model-studio/runs")
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def _latest_completed_run(base_url: str, *, study_title: str) -> dict:
    for item in _list_runs(base_url):
        if item.get("study_title") == study_title and item.get("status") == "completed":
            return item
    raise RuntimeError(f"No completed run found for study title: {study_title}")


def _load_local_json(path_str: str) -> dict:
    path = REPO_ROOT / path_str
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_execution_console_screenshot(base_url: str, *, browser: str, output_path: Path) -> None:
    driver = build_browser_driver(browser=browser, width=1440, height=1800)
    try:
        driver.get(base_url)
        wait_for_workspace(driver)
        element = driver.find_element(By.ID, "workspace-execution-console")
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});",
            element,
        )
        element.screenshot(str(output_path))
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a stable Model Studio trace artifact from a completed run.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8782")
    parser.add_argument("--browser", default="edge")
    parser.add_argument("--mode", choices=("ppi", "ligand"), required=True)
    parser.add_argument("--study-title", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = ensure_directory(Path(args.output_dir))
    run = _latest_completed_run(args.base_url, study_title=args.study_title)
    run_id = str(run["run_id"])
    run_payload = _load_json(f"{args.base_url}/api/model-studio/runs/{run_id}")

    artifacts = run_payload.get("artifact_refs") or run.get("artifact_refs") or []
    metrics_path = next((item for item in artifacts if item.endswith("/metrics.json")), "")
    outliers_path = next((item for item in artifacts if item.endswith("/outliers.json")), "")
    analysis_path = next((item for item in artifacts if item.endswith("/analysis.json")), "")
    report_path = next((item for item in artifacts if item.endswith("/report.md")), "")

    metrics = _load_local_json(metrics_path) if metrics_path else {}
    outliers = _load_local_json(outliers_path) if outliers_path else {}
    analysis = _load_local_json(analysis_path) if analysis_path else {}

    final_screenshot = output_dir / f"{args.mode}_after_launch.png"
    _save_execution_console_screenshot(
        args.base_url,
        browser=args.browser,
        output_path=final_screenshot,
    )

    trace = {
        "base_url": args.base_url,
        "browser": args.browser,
        "mode": args.mode,
        "study_title": args.study_title,
        "run_id": run_id,
        "run_status": run_payload.get("status", run.get("status")),
        "dataset_ref": run_payload.get("dataset_ref", run.get("dataset_ref")),
        "model_family": run_payload.get("model_family", run.get("model_family")),
        "resolved_training_backend": run_payload.get(
            "resolved_training_backend",
            run.get("resolved_training_backend"),
        ),
        "metrics": json.dumps(metrics, indent=2) if metrics else "",
        "outliers": json.dumps(outliers, indent=2) if outliers else "",
        "comparison": json.dumps(analysis, indent=2) if analysis else report_path,
        "screenshot": str(final_screenshot.resolve()),
        "artifact_refs": artifacts,
    }
    trace_path = output_dir / "user_sim_trace.json"
    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(trace_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
