import argparse
import random
import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from knagarden_selenium_crawler import (
    BlockedPageError,
    append_failed_url,
    crawl_detail_with_retries,
    load_existing,
    make_driver,
    save_outputs,
)


def load_links(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl knagarden plant details from a URL list.")
    parser.add_argument("--output-dir", default="output", help="Directory for JSON and CSV outputs.")
    parser.add_argument("--links-file", default="output/plant_links.txt", help="Text file with one plant URL per line.")
    parser.add_argument("--limit", type=int, default=0, help="Limit detail pages for testing. 0 means no limit.")
    parser.add_argument("--delay-min", type=float, default=45.0, help="Minimum delay between detail pages.")
    parser.add_argument("--delay-max", type=float, default=90.0, help="Maximum delay between detail pages.")
    parser.add_argument("--retries", type=int, default=3, help="Retry count when a 403/blocked page appears.")
    parser.add_argument("--blocked-sleep-min", type=float, default=300.0, help="Minimum wait after a 403 page.")
    parser.add_argument("--blocked-sleep-max", type=float, default=900.0, help="Maximum wait after a 403 page.")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible Chrome window.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    links = load_links(Path(args.links_file))
    if args.limit:
        links = links[: args.limit]

    records = load_existing(output_dir)
    done_urls = {record["url"] for record in records if record.get("url")}
    print(f"[links] {len(links)} links")
    print(f"[resume] {len(done_urls)} already done")

    driver = make_driver(headless=not args.show_browser)
    try:
        for url in links:
            if url in done_urls:
                print(f"[skip] {url}")
                continue

            try:
                record = crawl_detail_with_retries(
                    driver=driver,
                    url=url,
                    retries=args.retries,
                    blocked_sleep_min=args.blocked_sleep_min,
                    blocked_sleep_max=args.blocked_sleep_max,
                )
                if record:
                    records.append(record)
                    done_urls.add(url)
                    save_outputs(records, output_dir)
            except BlockedPageError as exc:
                append_failed_url(output_dir, url, str(exc))
            except (TimeoutException, WebDriverException) as exc:
                print(f"[error] {url}: {exc}")
                append_failed_url(output_dir, url, str(exc))

            time.sleep(random.uniform(args.delay_min, args.delay_max))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
