import argparse
from pathlib import Path

from knagarden_selenium_crawler import (
    BlockedPageError,
    collect_plant_links_with_retries,
    make_driver,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect knagarden plant detail URLs only.")
    parser.add_argument("--output-dir", default="output", help="Directory for plant_links.txt.")
    parser.add_argument("--max-list-pages", type=int, default=52, help="How many list pages to scan.")
    parser.add_argument("--delay-min", type=float, default=20.0, help="Minimum delay between list pages.")
    parser.add_argument("--delay-max", type=float, default=45.0, help="Maximum delay between list pages.")
    parser.add_argument("--retries", type=int, default=3, help="Retry count when a 403/blocked page appears.")
    parser.add_argument("--blocked-sleep-min", type=float, default=300.0, help="Minimum wait after a 403 page.")
    parser.add_argument("--blocked-sleep-max", type=float, default=900.0, help="Maximum wait after a 403 page.")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible Chrome window.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    driver = make_driver(headless=not args.show_browser)
    try:
        links = collect_plant_links_with_retries(
            driver=driver,
            max_pages=args.max_list_pages,
            page_delay_min=args.delay_min,
            page_delay_max=args.delay_max,
            retries=args.retries,
            blocked_sleep_min=args.blocked_sleep_min,
            blocked_sleep_max=args.blocked_sleep_max,
        )
        links_path = output_dir / "plant_links.txt"
        links_path.write_text("\n".join(links), encoding="utf-8")
        print(f"[done] saved {len(links)} links to {links_path}")
    except BlockedPageError as exc:
        print(f"[blocked] stopped while collecting links: {exc}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
