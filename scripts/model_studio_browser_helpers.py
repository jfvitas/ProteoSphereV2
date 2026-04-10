from __future__ import annotations

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_edge_driver(width: int = 1440, height: int = 1400) -> webdriver.Edge:
    options = EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--force-device-scale-factor=1")
    driver = webdriver.Edge(options=options)
    driver.set_window_size(width, height)
    return driver


def build_browser_driver(
    *,
    browser: str = "edge",
    width: int = 1440,
    height: int = 1400,
) -> webdriver.Edge:
    normalized = browser.strip().lower()
    if normalized != "edge":
        raise ValueError(f"Unsupported browser for this environment: {browser}")
    return build_edge_driver(width=width, height=height)


def wait_for_workspace(driver: webdriver.Edge, timeout: int = 60) -> None:
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.presence_of_element_located((By.ID, "study-title")))
    wait.until(lambda drv: drv.find_element(By.ID, "study-title").text.strip() != "Loading...")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
