from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_studio_browser_helpers import (
    build_browser_driver,
    ensure_directory,
    wait_for_workspace,
)


def _click(driver, element_id: str) -> None:
    element = driver.find_element(By.ID, element_id)
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
        element,
    )
    driver.execute_script("arguments[0].click();", element)


def _value(driver, element_id: str) -> str:
    return driver.find_element(By.ID, element_id).text.strip()


def _select_value(driver, element_id: str, value: str) -> None:
    Select(driver.find_element(By.ID, element_id)).select_by_value(value)


def _chip(driver, label: str):
    return driver.find_element(
        By.XPATH,
        f"//*[@id='preprocess-modules']//*[@data-chip-label=\"{label}\"]",
    )


def _ensure_chip_selected(driver, label: str) -> None:
    button = _chip(driver, label)
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
        button,
    )
    if button.get_attribute("aria-pressed") == "true":
        return
    driver.execute_script("arguments[0].click();", button)


def _save_element_screenshot(driver, *, element_id: str, output_path: Path) -> None:
    element = driver.find_element(By.ID, element_id)
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});",
        element,
    )
    element.screenshot(str(output_path))


def _parse_run_id(text: str) -> str:
    match = re.search(r"(run-[A-Za-z0-9T:-]+(?:-[A-Za-z0-9]+)?)", text)
    if not match:
        raise ValueError(f"Unable to parse run id from: {text}")
    return match.group(1)


def _load_json(url: str) -> dict:
    with urlopen(url, timeout=15) as response:  # nosec - local beta server only
        return json.loads(response.read().decode("utf-8"))


def _list_runs(base_url: str) -> list[dict]:
    payload = _load_json(f"{base_url}/api/model-studio/runs")
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def _wait_for_run_completion(base_url: str, run_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = _load_json(f"{base_url}/api/model-studio/runs/{run_id}")
        status = str(payload.get("status") or "")
        if status in {"completed", "blocked", "failed", "cancelled"}:
            return payload
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for run completion: {run_id}")


def _wait_for_new_run(
    base_url: str,
    *,
    existing_run_ids: set[str],
    study_title: str,
    timeout: int = 120,
) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for item in _list_runs(base_url):
            run_id = str(item.get("run_id") or "")
            if run_id and run_id not in existing_run_ids and item.get("study_title") == study_title:
                return item
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for launched run for study title: {study_title}")


def _soft_wait_for_ui_run_summary(driver, run_id: str, status: str, timeout: int = 45) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            _click(driver, "refresh-runs-button")
        except Exception:  # pragma: no cover - UI refresh is best-effort only
            pass
        time.sleep(2)
        try:
            run_preview = driver.find_element(By.ID, "run-preview").text
            if run_id in run_preview and status in run_preview:
                return
        except Exception:  # pragma: no cover - UI refresh is best-effort only
            pass
    print(f"UI run summary did not fully settle for {run_id}; continuing with backend-complete evidence.", file=sys.stderr)


def _configure_ppi_flow(driver, *, target_size: int) -> None:
    title = driver.find_element(By.ID, "study-title-input")
    title.clear()
    title.send_keys("Model Studio Final PPI User Sim")
    _select_value(driver, "dataset-primary-select", "release_pp_alpha_benchmark_v1")
    _select_value(driver, "graph-kind-select", "hybrid_graph")
    _select_value(driver, "region-policy-select", "interface_plus_shell")
    _select_value(driver, "model-family-select", "multimodal_fusion")
    size = driver.find_element(By.ID, "target-size-input")
    size.clear()
    size.send_keys(str(target_size))


def _configure_ligand_flow(driver, model_family: str, *, target_size: int) -> None:
    title = driver.find_element(By.ID, "study-title-input")
    title.clear()
    title.send_keys("Model Studio Final Ligand User Sim")
    _select_value(driver, "task-type-select", "protein-ligand")
    _select_value(driver, "label-type-select", "delta_G")
    _select_value(driver, "structure-policy-select", "experimental_only")
    _select_value(driver, "split-strategy-select", "protein_ligand_component_grouped")
    _select_value(driver, "dataset-primary-select", "governed_pl_bridge_pilot_subset_v1")
    _select_value(driver, "graph-kind-select", "whole_complex_graph")
    _select_value(driver, "region-policy-select", "whole_molecule")
    _select_value(driver, "partner-awareness-select", "role_conditioned")
    _ensure_chip_selected(driver, "ligand descriptors")
    size = driver.find_element(By.ID, "target-size-input")
    size.clear()
    size.send_keys(str(target_size))
    if model_family == "graphsage":
        _select_value(driver, "model-family-select", "graphsage")
    else:
        _select_value(driver, "model-family-select", "multimodal_fusion")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Model Studio user-sim review.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8770")
    parser.add_argument("--browser", default="edge")
    parser.add_argument("--mode", choices=("ppi", "ligand"), default="ppi")
    parser.add_argument(
        "--ligand-model-family",
        choices=("graphsage", "multimodal_fusion"),
        default="graphsage",
    )
    parser.add_argument("--target-size", type=int, default=48)
    parser.add_argument(
        "--output-dir",
        default=str(
            Path("artifacts")
            / "reviews"
            / "model_studio_internal_alpha"
            / "user_sim_round_1"
        ),
    )
    args = parser.parse_args()
    output_dir = ensure_directory(Path(args.output_dir))

    driver = build_browser_driver(browser=args.browser, width=1440, height=1800)
    try:
        driver.get(args.base_url)
        wait_for_workspace(driver)

        existing_run_ids = {
            str(item.get("run_id") or "")
            for item in _list_runs(args.base_url)
            if item.get("run_id")
        }
        if args.mode == "ppi":
            _configure_ppi_flow(driver, target_size=args.target_size)
            study_title = "Model Studio Final PPI User Sim"
        else:
            _configure_ligand_flow(driver, args.ligand_model_family, target_size=args.target_size)
            study_title = "Model Studio Final Ligand User Sim"

        _click(driver, "preview-dataset-button")
        WebDriverWait(driver, 60).until(
            lambda drv: "Candidate rows" in drv.find_element(By.ID, "training-set-preview").text
        )
        preview_path = output_dir / f"{args.mode}_after_preview.png"
        _save_element_screenshot(driver, element_id="workspace-data-strategy", output_path=preview_path)

        _click(driver, "build-dataset-button")
        WebDriverWait(driver, 120).until(
            lambda drv: "Dataset ref" in drv.find_element(By.ID, "training-set-build-summary").text
        )
        build_path = output_dir / f"{args.mode}_after_build.png"
        _save_element_screenshot(driver, element_id="workspace-data-strategy", output_path=build_path)

        _click(driver, "validate-draft-button")
        WebDriverWait(driver, 30).until(
            lambda drv: _value(drv, "quality-gate-status") in {"ready", "ready_with_warnings"}
        )
        _click(driver, "compile-draft-button")
        WebDriverWait(driver, 30).until(
            lambda drv: _value(drv, "stage-count").isdigit()
            and int(_value(drv, "stage-count")) >= 10
        )
        _click(driver, "launch-run-button")
        launched_run = _wait_for_new_run(
            args.base_url,
            existing_run_ids=existing_run_ids,
            study_title=study_title,
        )
        run_id = str(launched_run.get("run_id") or "")
        final_run = _wait_for_run_completion(args.base_url, run_id)
        _soft_wait_for_ui_run_summary(driver, run_id, str(final_run.get("status") or ""))
        if final_run.get("status") == "completed":
            try:
                WebDriverWait(driver, 45).until(
                    lambda drv: "Run metrics appear here after evaluation completes."
                    not in drv.find_element(By.ID, "run-metrics").text
                )
            except Exception:  # pragma: no cover - metrics panel lag should not invalidate backend-complete traces
                pass

        final_path = output_dir / f"{args.mode}_after_launch.png"
        _save_element_screenshot(
            driver,
            element_id="workspace-execution-console",
            output_path=final_path,
        )

        trace = {
            "base_url": args.base_url,
            "browser": args.browser,
            "mode": args.mode,
            "ligand_model_family": args.ligand_model_family if args.mode == "ligand" else None,
            "quality_gate_status": _value(driver, "quality-gate-status"),
            "warning_count": _value(driver, "warning-count"),
            "steps": [
                "preview_dataset",
                "build_dataset",
                "validate_draft",
                "compile_draft",
                "launch_run",
                "wait_for_completion",
            ],
            "run_id": run_id,
            "run_status": final_run.get("status"),
            "run_preview": driver.find_element(By.ID, "run-preview").text,
            "metrics": driver.find_element(By.ID, "run-metrics").text,
            "outliers": driver.find_element(By.ID, "run-outliers").text,
            "comparison": driver.find_element(By.ID, "run-comparison").text,
            "preview_screenshot": str(preview_path.resolve()),
            "build_screenshot": str(build_path.resolve()),
            "screenshot": str(final_path.resolve()),
        }
        trace_path = output_dir / "user_sim_trace.json"
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        print(trace_path)
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
