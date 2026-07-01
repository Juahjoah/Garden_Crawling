import argparse
import random
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = "https://www.knagarden.info"
LIST_URL = f"{BASE_URL}/plants"


def make_driver(headless: bool = True, page_load_timeout: int = 45) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1400")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(service=Service(), options=options)
    driver.set_page_load_timeout(page_load_timeout)
    return driver


def wait_for_page(driver: webdriver.Chrome, timeout: int = 20) -> None:
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
    )


def scroll_to_bottom(driver: webdriver.Chrome, max_scrolls: int = 30, pause: float = 0.8) -> None:
    previous_height = 0
    stable_count = 0

    for _ in range(max_scrolls):
        current_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

        if current_height == previous_height:
            stable_count += 1
        else:
            stable_count = 0
        previous_height = current_height

        if stable_count >= 3:
            break


def collect_plant_links(
    driver: webdriver.Chrome,
    start_page: int,
    end_page: int,
    delay_min: float,
    delay_max: float,
    output_path: Path,
    append_existing: bool,
) -> list[str]:
    links = set()
    if append_existing and output_path.exists():
        links.update(
            line.strip()
            for line in output_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        print(f"[resume] loaded {len(links)} existing links")

    for page in range(start_page, end_page + 1):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        print(f"[list] page {page}: {url}")

        driver.get(url)
        wait_for_page(driver)
        scroll_to_bottom(driver)

        anchors = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href^='/plants/'], a[href*='knagarden.info/plants/']",
        )
        before = len(links)
        for anchor in anchors:
            href = anchor.get_attribute("href")
            if not href:
                continue
            href = urljoin(BASE_URL, href)
            parsed = urlparse(href)
            path = parsed.path.rstrip("/")
            if path and path != "/plants" and path.startswith("/plants/"):
                links.add(f"{BASE_URL}{path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(sorted(links)), encoding="utf-8")
        print(f"[save] page {page}: +{len(links) - before}, total {len(links)}")

        time.sleep(random.uniform(delay_min, delay_max))

    return sorted(links)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect only knagarden plant URLs.")
    parser.add_argument("--output", default="output/plant_links.txt", help="Output text file.")
    parser.add_argument("--start-page", type=int, default=1, help="First list page.")
    parser.add_argument("--end-page", type=int, default=52, help="Last list page.")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum delay in seconds.")
    parser.add_argument("--delay-max", type=float, default=5.0, help="Maximum delay in seconds.")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible Chrome window.")
    parser.add_argument("--no-append", action="store_true", help="Do not merge with existing output file.")
    args = parser.parse_args()

    if args.start_page < 1 or args.end_page < args.start_page:
        raise ValueError("--start-page must be >= 1 and --end-page must be >= --start-page")

    driver = make_driver(headless=not args.show_browser)
    try:
        links = collect_plant_links(
            driver=driver,
            start_page=args.start_page,
            end_page=args.end_page,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            output_path=Path(args.output),
            append_existing=not args.no_append,
        )
        print(f"[done] saved {len(links)} links to {args.output}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
