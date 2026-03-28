# FIA Docs Scraper

A toolchain for scraping, merging, and converting FIA Formula One documents to Markdown.

## Scripts

### `scraper.py`
Scrapes PDFs from the FIA website using Selenium (headless Chrome) and downloads them to `fia_documents/<Event Name YYYY>/`.

- Processes the latest event plus any events missing a local folder, oldest-first
- Skips already-downloaded files
- Optionally uses `webdriver-manager` to auto-manage ChromeDriver (falls back to system ChromeDriver)

```bash
python scraper.py              # scrape all missing events
python scraper.py --limit 2    # process only 2 events
```

### `merge_event_pdfs.py`
Merges all PDFs within each event folder into a single PDF, output to `fia_documents_merged/`.

```bash
python merge_event_pdfs.py
python merge_event_pdfs.py --output my_folder/
```

### `pdf_to_markdown.py`
Converts merged PDFs to Markdown (with table support) for LLM ingestion. Reads from `fia_documents_merged/`, writes `.md` files to `fia_docs_merged_md/`. Runs conversions in parallel.

```bash
python pdf_to_markdown.py
python pdf_to_markdown.py --input fia_documents_merged/ --output fia_docs_merged_md/ --workers 4
```

### `discord_bot.py`
Minimal Discord bot skeleton. Requires a `DISCORD_BOT_TOKEN` environment variable.

```bash
DISCORD_BOT_TOKEN=your_token python discord_bot.py
```

## Dependencies

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `selenium` | Browser automation for scraping the FIA site |
| `requests` | HTTP downloads of PDF files |
| `pypdf` | PDF merging |
| `pdfplumber` | PDF text/table extraction for Markdown conversion |
| `discord.py` | Discord bot |

ChromeDriver is also required for `scraper.py`. Install `webdriver-manager` to manage it automatically:

```bash
pip install webdriver-manager
```

## Directory Structure

```
fia_documents/          # raw PDFs, one subfolder per event
fia_documents_merged/   # one merged PDF per event
fia_docs_merged_md/     # Markdown versions of merged PDFs
```
