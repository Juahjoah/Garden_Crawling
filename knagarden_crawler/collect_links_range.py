import argparse
import random
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium.webdriver.common.by import By

from knagarden_selenium_crawler import (
    BASE_URL,
    LIST_URL,
    BlockedPageError,
    is_blocked_page,
    make_driver,
    scroll_to_bottom,
    wait_for_page,
)


def page_url(page: int) -> str:
    return LIST_URL if page == 1 else f"{LIST_URL}?page={page}"


def read_existing_links(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def collect_page_links(driver, page: int) -> set[str]:
    url = page_url(page)
    print(f"[list] page {page}: {url}")
    driver.get(url)
    wait_for_page(driver)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    if is_blocked_page(body_text):
        raise BlockedPageError(f"Blocked on list page {page}.")

    scroll_to_bottom(driver)

    links = set()
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href^='/plants/'], a[href*='knagarden.info/plants/']")
    for anchor in anchors:
        href = anchor.get_attribute("href")
        if not href:
            continue
        href = urljoin(BASE_URL, href)
        parsed = urlparse(href)
        path = parsed.path.rstrip("/")
        if path and path != "/plants" and path.startswith("/plants/"):
            links.add(f"{BASE_URL}{path}")

    print(f"[list] page {page}: found {len(links)} links")
    return links


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect knagarden plant links for a page range.")
    parser.add_argument("--output-dir", default="output", help="Directory for plant_links.txt.")
    parser.add_argument("--start-page", type=int, required=True, help="First list page to scan.")
    parser.add_argument("--end-page", type=int, required=True, help="Last list page to scan.")
    parser.add_argument("--delay-min", type=float, default=30.0, help="Minimum delay between list pages, in seconds.")
    parser.add_argument("--delay-max", type=float, default=90.0, help="Maximum delay between list pages, in seconds.")
    parser.add_argument("--blocked-sleep-min", type=float, default=600.0, help="Minimum wait after a 403 page, in seconds.")
    parser.add_argument("--blocked-sleep-max", type=float, default=1800.0, help="Maximum wait after a 403 page, in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count per blocked page.")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible Chrome window.")
    args = parser.parse_args()

    if args.start_page < 1 or args.end_page < args.start_page:
        raise ValueError("--start-page must be >= 1 and --end-page must be >= --start-page")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    links_path = output_dir / "plant_links.txt"
    all_links = read_existing_links(links_path)
    print(f"[resume] loaded {len(all_links)} existing links")

    driver = make_driver(headless=not args.show_browser)
    try:
        for page in range(args.start_page, args.end_page + 1):
            for attempt in range(1, args.retries + 2):
                try:
                    before = len(all_links)
                    all_links.update(collect_page_links(driver, page))
                    links_path.write_text("\n".join(sorted(all_links)), encoding="utf-8")
                    print(f"[save] total {len(all_links)} links (+{len(all_links) - before})")
                    break
                except BlockedPageError as exc:
                    if attempt > args.retries:
                        print(f"[blocked] skip page {page}: {exc}")
                        break
                    sleep_seconds = random.uniform(args.blocked_sleep_min, args.blocked_sleep_max)
                    print(f"[blocked] page {page} - wait {sleep_seconds:.0f}s before retry {attempt}/{args.retries}")
                    time.sleep(sleep_seconds)

            time.sleep(random.uniform(args.delay_min, args.delay_max))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
