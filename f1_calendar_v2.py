"""
F1 Race Calendar Database V2
Fetches and caches F1 race schedules by scraping Wikipedia season articles.
Used to gate the FIA docs scraper — only run it after a new race weekend.

Source: https://en.wikipedia.org/wiki/2026_Formula_One_World_Championship
        (pattern: https://en.wikipedia.org/wiki/{year}_Formula_One_World_Championship)

Usage:
    python f1_calendar_v2.py                   # show completed races this year
    python f1_calendar_v2.py --update          # refresh calendar from Wikipedia
    python f1_calendar_v2.py --year 2025       # show a specific year
    python f1_calendar_v2.py --check           # exit 0 if scraper should run, 1 if not
    python f1_calendar_v2.py --mark-scraped    # record that scraper ran today
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

CALENDAR_FILE = Path("f1_calendar_v2.json")
STATE_FILE = Path("f1_state_v2.json")
WIKIPEDIA_BASE = "https://en.wikipedia.org/wiki"

# Month name → zero-padded number
_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Wikipedia scraping
# ---------------------------------------------------------------------------

def _parse_date(raw: str, year: int) -> Optional[str]:
    """
    Convert a Wikipedia date cell to an ISO 8601 string (YYYY-MM-DD).

    Handles formats like:
      "8 March"   "15–17 March"   "March 15"   "15 March 2026"
    Returns None if the date cannot be parsed.
    """
    # Strip footnote markers and excess whitespace
    text = re.sub(r"\[.*?\]", "", raw).strip()

    # Try "DD Month" or "DD–DD Month"
    m = re.search(r"(\d{1,2})(?:–\d{1,2})?\s+([A-Za-z]+)", text)
    if m:
        day = m.group(1).zfill(2)
        month = _MONTHS.get(m.group(2).lower())
        if month:
            return f"{year}-{month}-{day}"

    # Try "Month DD"
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2})", text)
    if m:
        month = _MONTHS.get(m.group(1).lower())
        day = m.group(2).zfill(2)
        if month:
            return f"{year}-{month}-{day}"

    return None


def _wikipedia_url(year: int) -> str:
    return f"{WIKIPEDIA_BASE}/{year}_Formula_One_World_Championship"


def fetch_calendar(year: int) -> list[dict]:
    """Scrape the race calendar for *year* from Wikipedia."""
    url = _wikipedia_url(year)
    resp = requests.get(url, timeout=15, headers={"User-Agent": "FIA-Docs-Scraper/2.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    races = []

    # Wikipedia season articles contain a race calendar table.
    # We look for a wikitable that has a "Round" column header.
    for table in soup.find_all("table", class_="wikitable"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not any("round" in h for h in headers):
            continue

        # Map column index to semantic name
        col_map = {}
        header_row = table.find("tr")
        for i, th in enumerate(header_row.find_all("th")):
            text = th.get_text(strip=True).lower()
            if "round" in text:
                col_map["round"] = i
            elif "grand prix" in text or "race" in text:
                col_map["name"] = i
            elif "circuit" in text:
                col_map["circuit"] = i
            elif "location" in text or "city" in text or "country" in text:
                col_map["location"] = i
            elif "date" in text:
                col_map["date"] = i

        if "round" not in col_map or "date" not in col_map:
            continue

        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            def cell_text(key):
                idx = col_map.get(key)
                if idx is None or idx >= len(cells):
                    return ""
                return cells[idx].get_text(" ", strip=True)

            round_text = cell_text("round")
            # Skip sub-header rows
            if not round_text.isdigit():
                continue

            raw_date = cell_text("date")
            iso_date = _parse_date(raw_date, year)
            if iso_date is None:
                continue

            # Extract location and country from the location cell (often "City, Country")
            loc_raw = cell_text("location")
            parts = [p.strip() for p in loc_raw.split(",")]
            location = parts[0] if parts else loc_raw
            country = parts[-1] if len(parts) > 1 else ""

            races.append({
                "round": int(round_text),
                "name": cell_text("name"),
                "circuit": cell_text("circuit"),
                "location": location,
                "country": country,
                "date": iso_date,
            })

        if races:
            break  # Found and parsed the calendar table

    if not races:
        raise ValueError(
            f"Could not find a parseable race calendar table on {url}. "
            "The Wikipedia page structure may have changed."
        )

    return races


def update_calendar(year: int) -> list[dict]:
    """Fetch calendar for *year* from Wikipedia, merge into local cache, return races."""
    calendar = _load_json(CALENDAR_FILE, {})
    races = fetch_calendar(year)
    calendar[str(year)] = races
    _save_json(CALENDAR_FILE, calendar)
    print(f"Cached {len(races)} races for {year} → {CALENDAR_FILE}")
    return races


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_races(year: int) -> list[dict]:
    """Return all cached races for *year*, or an empty list."""
    calendar = _load_json(CALENDAR_FILE, {})
    return calendar.get(str(year), [])


def get_completed_races(year: int) -> list[dict]:
    """Return races whose date is on or before today."""
    today = date.today().isoformat()
    return [r for r in get_races(year) if r["date"] <= today]


def last_completed_race(year: int) -> Optional[dict]:
    """Return the most recently completed race, or None."""
    completed = get_completed_races(year)
    return completed[-1] if completed else None


# ---------------------------------------------------------------------------
# Scraper gate
# ---------------------------------------------------------------------------

def load_state() -> dict:
    return _load_json(STATE_FILE, {"last_scraped": None})


def save_state(state: dict):
    _save_json(STATE_FILE, state)


def should_scrape() -> tuple[bool, str]:
    """
    Return (True, reason) if the scraper should run, (False, reason) if not.

    Logic:
      - If no state recorded → always scrape.
      - If the last completed race occurred after last_scraped → scrape.
      - Otherwise → skip.
    """
    state = load_state()
    last_scraped = state.get("last_scraped")

    year = date.today().year
    race = last_completed_race(year)

    if race is None:
        race = last_completed_race(year - 1)

    if race is None:
        return False, "No completed races found in local calendar (run --update first)."

    if last_scraped is None:
        return True, f"No scrape recorded yet; last race was {race['name']} on {race['date']}."

    if race["date"] > last_scraped:
        return True, (
            f"New race since last scrape: {race['name']} on {race['date']} "
            f"(last scraped: {last_scraped})."
        )

    return False, (
        f"Last race ({race['name']} on {race['date']}) already scraped "
        f"(last scraped: {last_scraped})."
    )


def mark_scraped(scraped_date: Optional[str] = None):
    """Record that the scraper ran on *scraped_date* (defaults to today)."""
    if scraped_date is None:
        scraped_date = date.today().isoformat()
    state = load_state()
    state["last_scraped"] = scraped_date
    save_state(state)
    print(f"Marked last_scraped = {scraped_date} in {STATE_FILE}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="F1 race calendar database (Wikipedia source).")
    parser.add_argument("--year", type=int, default=date.today().year,
                        help="Season year (default: current year)")
    parser.add_argument("--update", action="store_true",
                        help="Fetch/refresh the calendar from Wikipedia")
    parser.add_argument("--check", action="store_true",
                        help="Exit 0 if the scraper should run, 1 if not")
    parser.add_argument("--mark-scraped", metavar="DATE", nargs="?", const="today",
                        help="Record a successful scrape (DATE defaults to today, ISO format)")
    args = parser.parse_args()

    if args.mark_scraped is not None:
        d = None if args.mark_scraped == "today" else args.mark_scraped
        mark_scraped(d)
        return

    if args.update:
        update_calendar(args.year)

    if args.check:
        run, reason = should_scrape()
        print(reason)
        sys.exit(0 if run else 1)

    # Default: print the calendar for the requested year.
    races = get_races(args.year)
    if not races:
        print(f"No cached calendar for {args.year}. Run with --update to fetch it.")
        return

    today = date.today().isoformat()
    print(f"\nF1 {args.year} Calendar ({len(races)} races)  [source: Wikipedia]\n")
    print(f"{'Rd':>3}  {'Date':<12}  {'Race':<45}  {'Circuit':<35}  Status")
    print("-" * 110)
    for r in races:
        status = "done" if r["date"] <= today else "upcoming"
        print(f"{r['round']:>3}  {r['date']:<12}  {r['name']:<45}  {r['circuit']:<35}  {status}")

    state = load_state()
    print(f"\nLast scraped: {state.get('last_scraped') or 'never'}")
    run, reason = should_scrape()
    print(f"Should scrape: {'yes' if run else 'no'}  ({reason})")


if __name__ == "__main__":
    main()
