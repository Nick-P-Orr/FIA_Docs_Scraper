"""
Merges all PDFs within each event folder into a single unified PDF.

Usage:
    python merge_event_pdfs.py                        # output to fia_documents_merged/
    python merge_event_pdfs.py --output my_folder/   # output to a custom directory
"""

import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter

DOWNLOAD_DIR = Path("fia_documents")
MERGED_DIR = Path("fia_documents_merged")


def merge_event(event_dir: Path, output_path: Path) -> int:
    """Merge all PDFs in event_dir into output_path. Returns page count."""
    pdfs = sorted(
        [p for p in event_dir.iterdir() if p.suffix.lower() == ".pdf"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not pdfs:
        print(f"  No PDFs found, skipping.")
        return 0

    writer = PdfWriter()
    for pdf_path in pdfs:
        try:
            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            print(f"  WARNING: skipping {pdf_path.name} — {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return len(writer.pages)


def main():
    parser = argparse.ArgumentParser(description="Merge per-event FIA PDFs into unified files.")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=MERGED_DIR,
        help=f"Directory to write merged PDFs (default: {MERGED_DIR}/)",
    )
    args = parser.parse_args()

    event_dirs = sorted(
        [d for d in DOWNLOAD_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )

    if not event_dirs:
        print(f"No event folders found in '{DOWNLOAD_DIR}/'.")
        return

    args.output.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(event_dirs)} event folder(s). Outputting to '{args.output}/'.\n")

    for event_dir in event_dirs:
        output_path = args.output / f"{event_dir.name}.pdf"

        if output_path.exists():
            print(f"[SKIP] {event_dir.name} — merged PDF already exists.")
            continue

        print(f"Merging: {event_dir.name}")
        pages = merge_event(event_dir, output_path)
        if pages:
            print(f"  -> {output_path} ({pages} pages)")

    print("\nDone.")


if __name__ == "__main__":
    main()
