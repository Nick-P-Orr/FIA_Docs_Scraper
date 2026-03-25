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
import argparse
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
    """Return list of {title, url, data_id} for each event on the season page."""
    driver.get(START_URL)
    wait_for_page(driver)

    events = []
    seen_ids = set()

    # Event titles in this layout are rendered as <a class="event-title" ...> or <div class="event-title active">.
    item_selectors = ["a.event-title", "div.event-title"]
    for selector in item_selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, selector):
            title = el.text.strip()
            if not title:
                continue

            href = el.get_attribute("href") or ""
            data_id = el.get_attribute("data-id") or ""

            # Some `div.event-title` (active event) does not have a data-id, but its sibling wrapper does.
            if not data_id:
                try:
                    wrapper = el.find_element(By.XPATH, "following-sibling::ul[contains(@class, 'document-type-wrapper')]")
                    m = re.search(r"data-id-(\d+)", wrapper.get_attribute("class") or "")
                    if m:
                        data_id = m.group(1)
                except Exception:
                    data_id = ""

            # Fallback to href-based data-id
            if not data_id and href:
                m = re.search(r"/decision-document-list/nojs/(\d+)", href)
                if m:
                    data_id = m.group(1)

            if not data_id:
                # in case we cannot find an id, skip now to avoid duplicates and empties.
                continue

            if data_id in seen_ids:
                continue

            seen_ids.add(data_id)
            events.append({
                "title": title,
                "url": urljoin(BASE_URL, href) if href else "",
                "data_id": data_id,
            })

    # Fallback: collect any internal decision-document-list/nojs links if nothing found.
    if not events:
        for el in driver.find_elements(By.TAG_NAME, "a"):
            href = el.get_attribute("href") or ""
            title = el.text.strip() or href
            m = re.search(r"/decision-document-list/nojs/(\d+)", href)
            if m:
                data_id = m.group(1)
                if data_id in seen_ids:
                    continue
                seen_ids.add(data_id)
                events.append({"title": title, "url": urljoin(BASE_URL, href), "data_id": data_id})

    print(f"Found {len(events)} event link(s).")
    return events


def get_document_links(driver: webdriver.Chrome, event: dict) -> list[dict]:
    """Return list of {title, url} for each PDF in an event block."""
    docs = []
    seen = set()

    def parse_pdf_links_from_element(el):
        found = []
        # Anchor selectors may be flaky in older WebDriver CSS implementations, so use all links and filter by extension.
        for a in el.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if not href or not href.lower().endswith(".pdf"):
                continue
            href = urljoin(BASE_URL, href)
            if href in seen:
                continue
            seen.add(href)
            title = a.text.strip() or a.get_attribute("title") or Path(urlparse(href).path).stem
            found.append({"title": title, "url": href})
        return found

    # First, try to scrape from the season page block for the event
    if event.get("data_id"):
        if driver.current_url != START_URL:
            driver.get(START_URL)
            wait_for_page(driver)
            time.sleep(1)

        data_id = event["data_id"]
        wrapper_selector = f"ul.document-type-wrapper.data-id-{data_id}"

        try:
            wrapper = driver.find_element(By.CSS_SELECTOR, wrapper_selector)

            # If wrapper is not currently visible (collapsed), click the associated event title.
            if wrapper.value_of_css_property("display") == "none":
                try:
                    event_el = wrapper.find_element(
                        By.XPATH,
                        "preceding-sibling::*[contains(concat(' ', normalize-space(@class), ' '), ' event-title ')][1]",
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", event_el)
                except Exception:
                    # fallback search by exact title text
                    if event.get("title"):
                        try:
                            title_xpath = f"//a[contains(@class,'event-title') and normalize-space(.)='{event['title']}'] | //div[contains(@class,'event-title') and normalize-space(.)='{event['title']}']"
                            event_el = driver.find_element(By.XPATH, title_xpath)
                            driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", event_el)
                        except Exception:
                            pass

            # Wait for wrapper visibility and PDF count to stabilize.
            try:
                wrapper = WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, wrapper_selector))
                )
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, f"{wrapper_selector} a")) > 0
                )
                wrapper = driver.find_element(By.CSS_SELECTOR, wrapper_selector)
            except Exception:
                pass

            docs.extend(parse_pdf_links_from_element(wrapper))
        except Exception:
            pass


    # If no PDFs found in season page DOM, fallback to direct event URL page parsing
    if not docs and event.get("url"):
        try:
            driver.get(event["url"])
            wait_for_page(driver)
            time.sleep(1)
            docs.extend(parse_pdf_links_from_element(driver))
        except Exception:
            pass

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
    parser = argparse.ArgumentParser(description="Scrape FIA Formula One documents.")
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of events to process (default: process all)')
    args = parser.parse_args()

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

        # Limit the number of events if specified
        events_to_process = events[:args.limit] if args.limit else events

        downloaded = 0
        for event in events_to_process:
            print(f"\nEvent: {event['title']} (id={event.get('data_id')})")
            docs = get_document_links(driver, event)
            print(f"  Found {len(docs)} document(s).")
            if docs:
                # Extract year from the first document's title
                match = re.search(r"Published on \d{2}\.\d{2}\.(\d{2})", docs[0]["title"])
                year = "20" + match.group(1) if match else "2026"  # fallback to current year
                event_title_with_year = f"{event['title']} {year}"
            else:
                event_title_with_year = event["title"]
            
            # Check how many documents already exist locally
            existing_count = 0
            docs_to_download = []
            for doc in docs:
                doc["event"] = event_title_with_year
                event_dir = DOWNLOAD_DIR / sanitise_filename(doc["event"])
                filename = sanitise_filename(doc["title"])
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                dest = event_dir / filename
                if dest.exists():
                    existing_count += 1
                else:
                    docs_to_download.append((doc, dest))
            
            to_download = len(docs) - existing_count
            print(f"  {existing_count} already exist locally, {to_download} to download.")
            
            # Download the documents for this event
            for doc, dest in docs_to_download:
                print(f"  Downloading: {doc['url']}")
                if download_pdf(doc["url"], dest, session):
                    downloaded += 1
                    print(f"    Saved: {dest}")
                else:
                    print(f"    Failed: {doc['url']}")

        print(f"\nDone. Downloaded {downloaded} new file(s) to '{DOWNLOAD_DIR}/'.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
