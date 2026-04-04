# FIA Docs Scraper

A toolchain for scraping, merging, and converting FIA Formula One documents to Markdown for LLM ingestion.

## What it does

- Navigates the FIA season documents page using a headless Chrome browser
- Discovers all Grand Prix events listed on the page (including collapsed ones)
- Always checks the latest event for new documents; skips events already present locally
- Downloads missing PDFs organised into per-event folders
- Skips files that have already been downloaded
- Validates downloaded PDFs and re-downloads any that are corrupt
- Merges per-event PDFs into single files
- Converts merged PDFs to Markdown with table support

## Requirements

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `selenium` | Browser automation for scraping the FIA site |
| `requests` | HTTP downloads of PDF files |
| `pypdf` | PDF merging |
| `pdfplumber` | PDF text/table extraction for Markdown conversion |
| `beautifulsoup4` | HTML parsing for Wikipedia calendar scraping |
| `discord.py` | Discord bot |

Chrome must be installed. Optionally install `webdriver-manager` to manage ChromeDriver automatically:

```bash
pip install webdriver-manager
```

> **Raspberry Pi note:** `webdriver-manager` may download an x86 binary incompatible with ARM. Use the system ChromeDriver instead:
> ```bash
> sudo apt install chromium-browser chromium-chromedriver
> ```

## Scripts

### 1. Scrape documents — `scraper.py`

Downloads PDFs from the FIA website into `fia_documents/`. Processes the latest event plus any events missing a local folder, oldest-first.

```bash
python scraper.py              # scrape all missing events
python scraper.py --limit 3    # process only 3 events (useful for testing)
```

### 2. Merge event documents — `merge_event_pdfs.py`

Merges each event's individual PDFs into a single file, ordered by publication time (newest-first). Output goes to `fia_documents_merged/`. Already-merged files are skipped on subsequent runs.

```bash
python merge_event_pdfs.py
python merge_event_pdfs.py --output my_folder/
```

### 3. Convert to Markdown — `pdf_to_markdown.py`

Converts the merged PDFs to Markdown for LLM ingestion. Tables are rendered as Markdown table syntax. Runs in parallel using 25% of available CPU cores by default. Output goes to `fia_docs_merged_md/`. Already-converted files are skipped on subsequent runs.

```bash
python pdf_to_markdown.py
python pdf_to_markdown.py --input fia_documents_merged/ --output fia_docs_merged_md/ --workers 4
```

### 4. F1 calendar — `f1_calendar.py` / `f1_calendar_v2.py`

Gates the FIA docs scraper so it only runs after a new race weekend has occurred. Two versions are available with identical interfaces but different data sources:

| Script | Source |
|---|---|
| `f1_calendar.py` | [Ergast community API](https://api.jolpi.ca/ergast/f1) |
| `f1_calendar_v2.py` | [Wikipedia season article](https://en.wikipedia.org/wiki/2026_Formula_One_World_Championship) (scraped with BeautifulSoup) |

```bash
python f1_calendar_v2.py                   # show completed races this year
python f1_calendar_v2.py --update          # refresh calendar from Wikipedia
python f1_calendar_v2.py --year 2025       # show a specific year
python f1_calendar_v2.py --check           # exit 0 if scraper should run, 1 if not
python f1_calendar_v2.py --mark-scraped    # record that scraper ran today
```

The `--check` flag compares the most recently completed race date against the last-scraped date — exits 0 if a new race has occurred since the last scrape, 1 otherwise.

Each version maintains its own cache and state files (`f1_calendar.json` / `f1_state.json` for v1, `f1_calendar_v2.json` / `f1_state_v2.json` for v2).

### 5. Discord bot — `discord_bot.py`

Minimal Discord bot skeleton. Requires a `DISCORD_BOT_TOKEN` environment variable.

```bash
DISCORD_BOT_TOKEN=your_token python discord_bot.py
```

## Scheduling on a Raspberry Pi

Use **cron** to run the scraper automatically. Open the crontab editor:

```bash
crontab -e
```

### Calendar-aware scheduling (recommended)

Use `f1_calendar_v2.py --check` to gate the scraper so it only runs when a new race weekend has occurred. First, keep the calendar up to date with a weekly refresh:

```
0 0 * * 1 cd /home/pi/FIA_Docs_Scraper && venv/bin/python f1_calendar_v2.py --update >> scraper.log 2>&1
```

Then run the scraper periodically; it will skip runs when no new race has happened:

```
0 */6 * * * cd /home/pi/FIA_Docs_Scraper && venv/bin/python f1_calendar_v2.py --check && venv/bin/python scraper.py && venv/bin/python f1_calendar_v2.py --mark-scraped >> scraper.log 2>&1
```

### Simple scheduling (no calendar gate)

Example — run every 6 hours on race weekends (Fri, Sat, Sun):

```
0 */6 * * 5,6,0 cd /home/pi/FIA_Docs_Scraper && venv/bin/python scraper.py >> scraper.log 2>&1
```

Example — run every 30 minutes during the F1 season (March–November):

```
*/30 * * 3-11 * cd /home/pi/FIA_Docs_Scraper && venv/bin/python scraper.py >> scraper.log 2>&1
```

Use [crontab.guru](https://crontab.guru) to verify your schedule expressions.

**Tips:**
- Always use absolute paths or `cd` into the project directory first so relative paths (e.g. `fia_documents/`) resolve correctly
- Redirect output to a log file (`>> scraper.log 2>&1`) to capture errors
- Use a virtual environment (`venv/bin/python`) to avoid system Python conflicts

## Output structure

```
fia_documents/                  ← individual PDFs per event
  JAPANESE GRAND PRIX 2026/
    Doc 1 - ...pdf
    Doc 2 - ...pdf
    ...
  CHINESE GRAND PRIX 2026/
    ...

fia_documents_merged/           ← one merged PDF per event
  JAPANESE GRAND PRIX 2026.pdf
  CHINESE GRAND PRIX 2026.pdf
  ...

fia_docs_merged_md/             ← Markdown versions for LLM ingestion
  JAPANESE GRAND PRIX 2026.md
  CHINESE GRAND PRIX 2026.md
  ...

f1_calendar.json                ← cached race schedules — Ergast API (v1)
f1_state.json                   ← scraper state for v1 (last run date)
f1_calendar_v2.json             ← cached race schedules — Wikipedia (v2)
f1_state_v2.json                ← scraper state for v2 (last run date)
```
