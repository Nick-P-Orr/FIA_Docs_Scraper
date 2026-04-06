"""
Merges all PDFs within each event folder into a single unified PDF.

Usage:
    python merge_event_pdfs.py                        # output to fia_documents_merged/
    python merge_event_pdfs.py --output my_folder/   # output to a custom directory
"""

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
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

    todo = []
    for event_dir in event_dirs:
        output_path = args.output / f"{event_dir.name}.pdf"
        if output_path.exists():
            print(f"[SKIP] {event_dir.name} — merged PDF already exists.")
        else:
            todo.append((event_dir, output_path))

    if not todo:
        print("\nDone.")
        return

    workers = min(len(todo), max(1, os.cpu_count() or 1))
    print(f"\nMerging {len(todo)} event(s) using {workers} worker(s)...")

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(merge_event, event_dir, output_path): (event_dir, output_path)
                   for event_dir, output_path in todo}
        for future in as_completed(futures):
            event_dir, output_path = futures[future]
            try:
                pages = future.result()
                if pages:
                    print(f"  -> {output_path} ({pages} pages)")
            except Exception as e:
                print(f"  ERROR merging {event_dir.name}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
