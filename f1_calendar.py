"""
F1 Race Calendar Database
Fetches and caches F1 race schedules from the Ergast community API.
Used to gate the FIA docs scraper — only run it after a new race weekend.

API: https://api.jolpi.ca/ergast/f1/{year}/races.json

Usage:
    python f1_calendar.py                   # show completed races this year
    python f1_calendar.py --update          # refresh calendar from API
    python f1_calendar.py --year 2025       # show a specific year
    python f1_calendar.py --check           # exit 0 if scraper should run, 1 if not
    python f1_calendar.py --mark-scraped    # record that scraper ran today
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import requests

CALENDAR_FILE = Path("f1_calendar.json")
STATE_FILE = Path("f1_state.json")
ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"


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
# Calendar fetching
# ---------------------------------------------------------------------------

def fetch_calendar(year: int) -> list[dict]:
    """Fetch the race calendar for *year* from the Ergast API."""
    url = f"{ERGAST_BASE}/{year}/races.json?limit=100"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    races = resp.json()["MRData"]["RaceTable"]["Races"]
    return [
        {
            "round": int(r["round"]),
            "name": r["raceName"],
            "circuit": r["Circuit"]["circuitName"],
            "location": r["Circuit"]["Location"]["locality"],
            "country": r["Circuit"]["Location"]["country"],
            "date": r["date"],  # ISO 8601, e.g. "2025-03-16"
        }
        for r in races
    ]


def update_calendar(year: int) -> list[dict]:
    """Fetch calendar for *year*, merge into the local cache, and return races."""
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
        # No race has happened yet this year; try last year as a fallback.
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
    parser = argparse.ArgumentParser(description="F1 race calendar database.")
    parser.add_argument("--year", type=int, default=date.today().year,
                        help="Season year (default: current year)")
    parser.add_argument("--update", action="store_true",
                        help="Fetch/refresh the calendar from the API")
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
    print(f"\nF1 {args.year} Calendar ({len(races)} races)\n")
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
