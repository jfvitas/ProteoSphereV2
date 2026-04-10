from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from selenium.webdriver.common.by import By

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_studio_browser_helpers import (
    build_browser_driver,
    ensure_directory,
    wait_for_workspace,
)


def _capture_blocked_feature(driver, *, label: str, output_path: Path) -> dict[str, str]:
    button = driver.find_element(
        By.XPATH,
        f"//*[@id='preprocess-modules']//*[@data-chip-label=\"{label}\"]",
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
        button,
    )
    driver.execute_script("arguments[0].click();", button)
    explanation = driver.find_element(By.ID, "inactive-explanation").text.strip()
    driver.save_screenshot(str(output_path))
    return {
        "label": label,
        "status": button.get_attribute("data-chip-status") or "unknown",
        "reason": button.get_attribute("data-chip-reason") or "",
        "inactive_explanation": explanation,
        "screenshot": str(output_path.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture blocked/failure-state review artifacts.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8770")
    parser.add_argument("--browser", default="edge")
    parser.add_argument(
        "--output-dir",
        default=str(
            Path("artifacts")
            / "reviews"
            / "model_studio_internal_alpha"
            / "final_blocked_round"
        ),
    )
    args = parser.parse_args()
    output_dir = ensure_directory(Path(args.output_dir))

    driver = build_browser_driver(browser=args.browser, width=1440, height=1800)
    try:
        driver.get(args.base_url)
        wait_for_workspace(driver)

        pyrosetta = _capture_blocked_feature(
            driver,
            label="PyRosetta",
            output_path=output_dir / "blocked_pyrosetta_explanation.png",
        )
        free_state = _capture_blocked_feature(
            driver,
            label="Free-state comparison",
            output_path=output_dir / "blocked_free_state_explanation.png",
        )

        help_button = driver.find_element(By.ID, "need-help-button")
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
            help_button,
        )
        driver.execute_script("arguments[0].click();", help_button)
        feedback_path = output_dir / "failure_help_report_issue.png"
        driver.save_screenshot(str(feedback_path))

        payload = {
            "base_url": args.base_url,
            "browser": args.browser,
            "blocked_features": [pyrosetta, free_state],
            "feedback_panel_screenshot": str(feedback_path.resolve()),
        }
        trace_path = output_dir / "blocked_feature_trace.json"
        trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(trace_path)
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
