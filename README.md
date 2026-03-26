# FIA Docs Scraper

Downloads all PDF documents from the FIA Formula One World Championship season page, including documents from collapsed event sections.

## What it does

- Navigates the FIA season documents page using a headless Chrome browser
- Discovers all Grand Prix events listed on the page (including collapsed ones)
- Always checks the latest event for new documents; skips events already present locally
- Downloads missing PDFs organised into per-event folders
- Skips files that have already been downloaded
- Validates downloaded PDFs and re-downloads any that are corrupt

## Requirements

```
pip install selenium requests webdriver-manager pypdf pdfplumber
```

Chrome must be installed. `webdriver-manager` will handle ChromeDriver automatically.

Optionally install `PyPDF2` for PDF integrity validation:

```
pip install PyPDF2
```

## Scripts

### 1. Scrape documents — `scraper.py`

Downloads PDFs from the FIA website into `fia_documents/`.

```
python scraper.py
```

To limit the number of events processed (useful for testing):

```
python scraper.py --limit 3
```

### 2. Merge event documents — `merge_event_pdfs.py`

Merges each event's individual PDFs into a single file, ordered by publication time (newest-first). Output goes to `fia_documents_merged/`.

```
python merge_event_pdfs.py
```

To write merged PDFs to a custom directory:

```
python merge_event_pdfs.py --output my_folder/
```

Already-merged files are skipped on subsequent runs.

### 3. Convert to Markdown — `pdf_to_markdown.py`

Converts the merged PDFs to Markdown for LLM ingestion. Tables are rendered as Markdown table syntax. Output goes to `fia_docs_merged_md/`.

```
python pdf_to_markdown.py
```

Already-converted files are skipped on subsequent runs.

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
```
