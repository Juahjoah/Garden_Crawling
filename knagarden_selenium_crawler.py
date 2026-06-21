import argparse
import csv
import json
import random
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = "https://www.knagarden.info"
LIST_URL = f"{BASE_URL}/plants"
SECTION_NAMES = [
    "요약",
    "분포",
    "생육",
    "형태",
    "정원 디자인",
    "정원 관리",
    "연관 정보",
    "출처",
]


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip()


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


def collect_plant_links(driver: webdriver.Chrome, max_pages: int = 1) -> list[str]:
    links = set()

    for page in range(1, max_pages + 1):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        print(f"[list] {url}")
        driver.get(url)
        wait_for_page(driver)
        scroll_to_bottom(driver)

        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href^='/plants/'], a[href*='knagarden.info/plants/']")
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

        print(f"[list] found {len(links) - before} new links, total {len(links)}")

        if page > 1 and len(links) == before:
            break

        time.sleep(random.uniform(1.5, 3.0))

    return sorted(links)


def extract_section_text(full_text: str) -> dict[str, str]:
    sections = {}
    pattern = "|".join(re.escape(name) for name in SECTION_NAMES)
    matches = list(re.finditer(rf"(?:^|\n)({pattern})(?:\n|$)", full_text))

    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)
        text = clean_text(full_text[start:end])
        if text:
            sections[name] = text

    return sections


def extract_plant_detail(driver: webdriver.Chrome, url: str) -> dict:
    print(f"[detail] {url}")
    driver.get(url)
    wait_for_page(driver)
    time.sleep(1.0)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [line.strip() for line in body_text.splitlines() if line.strip()]

    title = ""
    scientific_name = ""
    red_list = ""

    headings = driver.find_elements(By.CSS_SELECTOR, "h1")
    if headings:
        title = clean_text(headings[0].text)

    if title and title in lines:
        title_index = lines.index(title)
        if title_index + 1 < len(lines):
            scientific_name = clean_text(lines[title_index + 1])
        if title_index + 2 < len(lines) and "적색목록" in lines[title_index + 2]:
            red_list = clean_text(lines[title_index + 2])

    family_scientific = ""
    genus_scientific = ""
    family_korean = ""
    genus_korean = ""

    for idx, line in enumerate(lines[:80]):
        if ">" in line and idx + 1 < len(lines):
            if "(" not in line and "(" not in lines[idx + 1]:
                continue
        family_match = re.search(r"^([A-Za-z]+aceae)\s*\(\s*([^)]+)\s*\)\s*>", line)
        genus_match = re.search(r"^([A-Za-z]+)\s*\(\s*([^)]+)\s*\)$", line)
        if family_match:
            family_scientific = family_match.group(1)
            family_korean = family_match.group(2)
        elif family_scientific and genus_match and not genus_scientific:
            genus_scientific = genus_match.group(1)
            genus_korean = genus_match.group(2)

    sections = extract_section_text(body_text)

    return {
        "url": url,
        "slug": urlparse(url).path.rstrip("/").split("/")[-1],
        "name_ko": title,
        "scientific_name": scientific_name,
        "red_list": red_list,
        "family_scientific": family_scientific,
        "family_ko": family_korean,
        "genus_scientific": genus_scientific,
        "genus_ko": genus_korean,
        "sections": sections,
        "raw_text": body_text,
    }


def save_outputs(records: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "knagarden_plants.json"
    csv_path = output_dir / "knagarden_plants.csv"

    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "url",
        "slug",
        "name_ko",
        "scientific_name",
        "red_list",
        "family_scientific",
        "family_ko",
        "genus_scientific",
        "genus_ko",
        *SECTION_NAMES,
    ]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {key: record.get(key, "") for key in fieldnames}
            for section_name in SECTION_NAMES:
                row[section_name] = record.get("sections", {}).get(section_name, "")
            writer.writerow(row)

    print(f"[save] {json_path}")
    print(f"[save] {csv_path}")


def load_existing(output_dir: Path) -> list[dict]:
    json_path = output_dir / "knagarden_plants.json"
    if not json_path.exists():
        return []
    return json.loads(json_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl plant pages from knagarden.info.")
    parser.add_argument("--output-dir", default="output", help="Directory for JSON and CSV outputs.")
    parser.add_argument("--max-list-pages", type=int, default=1, help="How many list pages to scan.")
    parser.add_argument("--limit", type=int, default=0, help="Limit detail pages for testing. 0 means no limit.")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum delay between detail pages.")
    parser.add_argument("--delay-max", type=float, default=5.0, help="Maximum delay between detail pages.")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible Chrome window.")
    parser.add_argument("--links-file", default="", help="Optional text file with one plant URL per line.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    records = load_existing(output_dir)
    done_urls = {record["url"] for record in records if record.get("url")}

    driver = make_driver(headless=not args.show_browser)
    try:
        if args.links_file:
            links = [
                line.strip()
                for line in Path(args.links_file).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            links = collect_plant_links(driver, max_pages=args.max_list_pages)

        if args.limit:
            links = links[: args.limit]

        (output_dir / "plant_links.txt").write_text("\n".join(links), encoding="utf-8")
        print(f"[links] {len(links)} links")

        for url in links:
            if url in done_urls:
                print(f"[skip] {url}")
                continue

            try:
                record = extract_plant_detail(driver, url)
                records.append(record)
                done_urls.add(url)
                save_outputs(records, output_dir)
            except (TimeoutException, WebDriverException) as exc:
                print(f"[error] {url}: {exc}")

            time.sleep(random.uniform(args.delay_min, args.delay_max))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
