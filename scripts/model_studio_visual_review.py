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

SECTION_IDS = (
    "workspace-project-home",
    "workspace-data-strategy",
    "workspace-representation",
    "workspace-pipeline-composer",
    "workspace-execution-console",
    "workspace-analysis-review",
)


def _capture_mode(
    base_url: str,
    output_dir: Path,
    width: int,
    height: int,
    prefix: str,
    browser: str,
) -> dict[str, str]:
    driver = build_browser_driver(browser=browser, width=width, height=height)
    try:
        driver.get(base_url)
        wait_for_workspace(driver)
        screenshots: dict[str, str] = {}
        full_path = output_dir / f"{prefix}_full.png"
        driver.save_screenshot(str(full_path))
        screenshots["full"] = str(full_path)
        for section_id in SECTION_IDS:
            element = driver.find_element(By.ID, section_id)
            section_path = output_dir / f"{prefix}_{section_id}.png"
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});",
                element,
            )
            driver.save_screenshot(str(section_path))
            screenshots[section_id] = str(section_path)
        return screenshots
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Model Studio visual review screenshots.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8770")
    parser.add_argument("--browser", default="edge")
    parser.add_argument(
        "--output-dir",
        default=str(
            Path("artifacts")
            / "reviews"
            / "model_studio_internal_alpha"
            / "visual_round_1"
        ),
    )
    args = parser.parse_args()

    output_dir = ensure_directory(Path(args.output_dir))
    desktop = _capture_mode(
        args.base_url,
        output_dir,
        width=1440,
        height=1800,
        prefix="desktop",
        browser=args.browser,
    )
    mobile = _capture_mode(
        args.base_url,
        output_dir,
        width=430,
        height=1600,
        prefix="mobile",
        browser=args.browser,
    )

    manifest = {
        "base_url": args.base_url,
        "browser": args.browser,
        "output_dir": str(output_dir.resolve()),
        "desktop": desktop,
        "mobile": mobile,
        "sections": list(SECTION_IDS),
    }
    manifest_path = output_dir / "visual_review_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
