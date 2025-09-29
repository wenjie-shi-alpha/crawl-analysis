"""Automate thewindpower.net lookups to fetch province information for wind farms."""

from __future__ import annotations

import argparse
import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.thewindpower.net/search_windfarms_en.php"


@dataclass(slots=True)
class BrowserConfig:
    """Runtime configuration for the browser automation."""

    input_path: Path
    output_path: Path
    name_column: str = "name"
    headless: bool = True
    wait_seconds: float = 15.0
    delay_between_queries: float = 1.5
    driver_path: Optional[Path] = None
    remote_url: Optional[str] = None


class TheWindPowerBrowser:
    """Automates user interactions with thewindpower.net search interface."""

    _SEARCH_INPUT_LOCATORS: Sequence[tuple[str, str]] = (
        (By.CSS_SELECTOR, "input#gsc-i-id1"),
        (By.CSS_SELECTOR, "form.gsc-search-box input.gsc-input"),
        (By.CSS_SELECTOR, "input[name='search']"),
        (By.CSS_SELECTOR, "input[type='text']"),
    )
    _SEARCH_RESULT_CONTAINER_LOCATORS: Sequence[tuple[str, str]] = (
        (By.CSS_SELECTOR, "div.gsc-results"),
        (By.CSS_SELECTOR, "div.gsib_a"),
        (By.CSS_SELECTOR, "table"),
    )
    _RESULT_LINK_LOCATORS: Sequence[tuple[str, str]] = (
        (By.CSS_SELECTOR, "a.gs-title"),
        (By.CSS_SELECTOR, "div.gsc-webResult a"),
        (By.CSS_SELECTOR, "table tr td a"),
    )

    _DETAIL_PROVINCE_LOCATORS: Sequence[tuple[str, str]] = (
        (By.XPATH, "//td[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'province')]/following-sibling::td"),
        (By.XPATH, "//td[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'state')]/following-sibling::td"),
        (By.XPATH, "//td[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'region')]/following-sibling::td"),
        (By.XPATH, "//b[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'province')]/parent::td/following-sibling::td"),
    )

    def __init__(self, config: BrowserConfig) -> None:
        self.config = config
        self.driver: Optional[WebDriver] = None
        self._wait: Optional[WebDriverWait] = None

    def __enter__(self) -> "TheWindPowerBrowser":
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _init_driver(self) -> None:
        logging.getLogger("selenium").setLevel(logging.WARNING)
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,1024")
        if self.config.headless:
            options.add_argument("--headless=new")
        if self.config.remote_url:
            self.driver = webdriver.Remote(
                command_executor=self.config.remote_url,
                options=options,
            )
        else:
            service = (
                Service(executable_path=str(self.config.driver_path))
                if self.config.driver_path
                else Service()
            )
            self.driver = webdriver.Chrome(service=service, options=options)
        self._wait = WebDriverWait(self.driver, self.config.wait_seconds)

    def close(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None
            self._wait = None

    def process(
        self,
        names: Iterable[str],
        on_result: Optional[Callable[[dict], None]] = None,
    ) -> List[dict]:
        results: List[dict] = []
        for name in names:
            clean_name = name.strip()
            if not clean_name:
                continue
            logger.info("Searching province for %s", clean_name)
            try:
                data = self.lookup_province(clean_name)
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.exception("Failed to fetch data for %s", clean_name)
                data = {
                    "name": clean_name,
                    "province": "",
                    "detail_url": "",
                    "status": "error",
                    "message": str(exc),
                }
            results.append(data)
            logger.info("Result for %s: %s", clean_name, data)
            if on_result:
                on_result(data)
            time.sleep(self.config.delay_between_queries)
        return results

    def lookup_province(self, name: str) -> dict:
        if not self.driver or not self._wait:
            raise RuntimeError("Browser driver is not initialised. Use as a context manager.")
        driver = self.driver
        wait = self._wait
        driver.get(SEARCH_URL)
        input_box = self._wait_for_any(wait, self._SEARCH_INPUT_LOCATORS)
        input_box.clear()
        input_box.send_keys(name)
        input_box.send_keys(Keys.ENTER)

        self._wait_for_any(wait, self._SEARCH_RESULT_CONTAINER_LOCATORS)
        links = self._collect_result_links()
        if not links:
            return {
                "name": name,
                "province": "",
                "detail_url": "",
                "status": "not_found",
                "message": "No result links detected",
            }

        for title, url in links:
            if not url:
                continue
            province = self._open_detail_and_extract(url)
            if province:
                return {
                    "name": name,
                    "province": province,
                    "detail_url": url,
                    "status": "ok",
                    "message": title,
                }
        return {
            "name": name,
            "province": "",
            "detail_url": links[0][1],
            "status": "no_province",
            "message": links[0][0],
        }

    def _collect_result_links(self) -> List[tuple[str, Optional[str]]]:
        if not self.driver:
            return []
        links: List[tuple[str, Optional[str]]] = []
        seen: set[str] = set()
        for by, selector in self._RESULT_LINK_LOCATORS:
            for element in self.driver.find_elements(by, selector):
                title = element.text.strip()
                href = element.get_attribute("data-ctorig") or element.get_attribute("href")
                key = f"{title}|{href}"
                if not href or key in seen:
                    continue
                seen.add(key)
                links.append((title, href))
            if links:
                break
        return links

    def _open_detail_and_extract(self, url: str) -> Optional[str]:
        if not self.driver or not self._wait:
            return None
        base_window = self.driver.current_window_handle
        self.driver.switch_to.new_window("tab")
        self.driver.get(url)
        try:
            self._wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            province = self._locate_text(self._DETAIL_PROVINCE_LOCATORS)
        finally:
            self.driver.close()
            self.driver.switch_to.window(base_window)
        return province

    def _locate_text(self, locators: Sequence[tuple[str, str]]) -> Optional[str]:
        if not self.driver:
            return None
        for by, selector in locators:
            for element in self.driver.find_elements(by, selector):
                text = element.text.strip()
                if text:
                    return text
        return None

    @staticmethod
    def _wait_for_any(wait: WebDriverWait, locators: Sequence[tuple[str, str]]):
        def _probe(driver: WebDriver):
            for by, selector in locators:
                elements = driver.find_elements(by, selector)
                if elements:
                    return elements[0]
            return False

        try:
            return wait.until(_probe)
        except TimeoutException as exc:
            message = ", ".join(f"{by}={selector}" for by, selector in locators)
            raise TimeoutException(f"Timed out waiting for any of: {message}") from exc


def read_names(path: Path, column: str) -> List[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if column not in reader.fieldnames:
            raise ValueError(f"Column '{column}' not found in CSV header: {reader.fieldnames}")
        return [row[column] for row in reader if row.get(column)]


def write_output(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automate thewindpower.net searches to fetch province information for a list of wind farms.",
    )
    parser.add_argument("input", type=Path, help="CSV file containing wind farm names.")
    parser.add_argument("output", type=Path, help="Destination CSV for results.")
    parser.add_argument(
        "--name-column",
        default="name",
        help="Column name in the input CSV that contains the wind farm names (default: name).",
    )
    parser.add_argument(
        "--driver-path",
        type=Path,
        default=None,
        help="Path to chromedriver executable if it is not on PATH.",
    )
    parser.add_argument(
        "--remote-url",
        default=None,
        help="Connect to a remote chromedriver/WebDriver server (e.g. http://host:port).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Chrome in headed mode (default is headless).",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=15.0,
        help="Maximum seconds to wait for page elements (default: 15).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to sleep between queries to reduce server load (default: 1.5).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> BrowserConfig:
    return BrowserConfig(
        input_path=args.input,
        output_path=args.output,
        name_column=args.name_column,
        headless=not args.headed,
        wait_seconds=args.wait,
        delay_between_queries=args.delay,
        driver_path=args.driver_path,
        remote_url=args.remote_url,
    )


def run(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config = build_config(args)
    names = read_names(config.input_path, config.name_column)
    if not names:
        logger.warning("No names found in %s", config.input_path)
        return
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    with config.output_path.open("w", encoding="utf-8", newline="") as handle:
        writer: Optional[csv.DictWriter] = None
        fieldnames: Optional[List[str]] = None

        def emit(row: dict) -> None:
            nonlocal writer, fieldnames
            if writer is None:
                fieldnames = list(row.keys())
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
            writer.writerow(row)
            handle.flush()

        with TheWindPowerBrowser(config) as browser:
            rows = browser.process(names, on_result=emit)
    logger.info("Saved %d rows to %s", len(rows), config.output_path)


if __name__ == "__main__":
    run()
