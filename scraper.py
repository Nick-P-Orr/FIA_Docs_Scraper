"""
FIA Document Scraper
URL: https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season

Requires:
    pip install selenium requests
    ChromeDriver matching your Chrome version (or use webdriver-manager):
    pip install webdriver-manager
"""

import os
import re
import time
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

BASE_URL = "https://www.fia.com"
START_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season"
DOWNLOAD_DIR = Path("fia_documents")
PAGE_LOAD_WAIT = 10  # seconds


def make_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    if USE_WDM:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    return webdriver.Chrome(options=options)


def wait_for_page(driver: webdriver.Chrome, timeout: int = PAGE_LOAD_WAIT):
    """Wait until the page body is present."""
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(2)  # allow JS to settle


def get_event_links(driver: webdriver.Chrome) -> list[dict]:
    """Return list of {title, url} for each event on the season page."""
    driver.get(START_URL)
    wait_for_page(driver)

    events = []
    # The FIA site uses different selectors depending on the year; try several.
    selectors = [
        "a.event-title",
        "a.event-card",
        ".event-title a",
        ".season-document-event a",
        "article a",
        ".views-row a",
    ]

    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            for el in elements:
                href = el.get_attribute("href") or ""
                title = el.text.strip() or el.get_attribute("title") or href
                if href and "/documents/" in href:
                    events.append({"title": title, "url": href})
            if events:
                break

    # Fallback: collect all internal links that look like event pages
    if not events:
        for el in driver.find_elements(By.TAG_NAME, "a"):
            href = el.get_attribute("href") or ""
            if (
                href.startswith(BASE_URL)
                and "/documents/" in href
                and href != START_URL
                and href not in {e["url"] for e in events}
            ):
                title = el.text.strip() or href
                events.append({"title": title, "url": href})

    print(f"Found {len(events)} event link(s).")
    return events


def get_document_links(driver: webdriver.Chrome, event_url: str) -> list[dict]:
    """Return list of {title, url} for each PDF on an event page."""
    driver.get(event_url)
    wait_for_page(driver)

    docs = []
    seen = set()

    for el in driver.find_elements(By.TAG_NAME, "a"):
        href = el.get_attribute("href") or ""
        if not href:
            continue
        # Normalise relative URLs
        href = urljoin(BASE_URL, href)
        if href.lower().endswith(".pdf") and href not in seen:
            seen.add(href)
            title = el.text.strip() or el.get_attribute("title") or Path(urlparse(href).path).stem
            docs.append({"title": title, "url": href})

    return docs


def sanitise_filename(name: str) -> str:
    """Replace characters that are illegal in filenames."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:200]  # keep filenames reasonably short


def download_pdf(url: str, dest: Path, session: requests.Session) -> bool:
    """Download a PDF to *dest*. Returns True on success."""
    try:
        resp = session.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as exc:
        print(f"    ERROR downloading {url}: {exc}")
        return False


def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    })

    driver = make_driver()
    try:
        events = get_event_links(driver)

        if not events:
            print("No events found — check selectors or try without headless mode.")
            return

        all_docs: list[dict] = []

        for event in events:
            print(f"\nEvent: {event['title']}")
            docs = get_document_links(driver, event["url"])
            print(f"  Found {len(docs)} document(s).")
            for doc in docs:
                doc["event"] = event["title"]
            all_docs.extend(docs)

        print(f"\nTotal documents found: {len(all_docs)}")

        downloaded = 0
        for doc in all_docs:
            event_dir = DOWNLOAD_DIR / sanitise_filename(doc["event"])
            filename = sanitise_filename(doc["title"])
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            dest = event_dir / filename

            if dest.exists():
                print(f"  SKIP (exists): {dest}")
                continue

            print(f"  Downloading: {doc['url']}")
            if download_pdf(doc["url"], dest, session):
                downloaded += 1
                print(f"    Saved: {dest}")

        print(f"\nDone. Downloaded {downloaded} new file(s) to '{DOWNLOAD_DIR}/'.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
