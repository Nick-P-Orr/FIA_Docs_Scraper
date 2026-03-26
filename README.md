# FIA Docs Scraper

Downloads all PDF documents from the FIA Formula One World Championship season page, including documents from collapsed event sections.

## What it does

- Navigates the FIA season documents page using a headless Chrome browser
- Discovers all Grand Prix events listed on the page (including collapsed ones)
- Clicks through each event to reveal its documents
- Downloads every PDF to a local folder organised by event
- Skips files that have already been downloaded
- Validates downloaded PDFs and re-downloads any that are corrupt

## Requirements

```
pip install selenium requests webdriver-manager
```

Chrome must be installed. `webdriver-manager` will handle the ChromeDriver automatically.

Optionally install `PyPDF2` for PDF integrity validation, and `pypdf` for merging:

```
pip install PyPDF2 pypdf
```

## Usage

### Scrape documents

```
python scraper.py
```

To limit the number of events processed (useful for testing):

```
python scraper.py --limit 3
```

### Merge event documents

After scraping, merge each event's PDFs into a single file sorted by newest-first modification time (chronological publication order):

```
python merge_event_pdfs.py
```

To write merged PDFs to a separate directory instead of alongside the event folders:

```
python merge_event_pdfs.py --output merged/
```

Already-merged files are skipped on subsequent runs.

## Output

PDFs are saved to `fia_documents/<Event Name Year>/`, e.g.:

```
fia_documents/
  CHINESE GRAND PRIX 2026/
    Doc 77 - Championship Points Published on 15.03.26 12_05 CET.pdf
    Doc 76 - Final Race Classification Published on 15.03.26 12_00 CET.pdf
    ...
  CHINESE GRAND PRIX 2026.pdf   ← merged file
```
