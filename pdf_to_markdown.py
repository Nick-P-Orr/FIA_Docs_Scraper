"""
Converts merged event PDFs to Markdown for LLM ingestion.

Reads PDFs from fia_documents_merged/ and writes .md files to fia_docs_merged_md/.
Tables are converted to Markdown table syntax. Already-converted files are skipped.

Usage:
    python pdf_to_markdown.py
    python pdf_to_markdown.py --input fia_documents_merged/ --output fia_docs_merged_md/

Requires:
    pip install pdfplumber
"""

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pdfplumber

INPUT_DIR = Path("fia_documents_merged")
OUTPUT_DIR = Path("fia_docs_merged_md")


def table_to_markdown(table: list[list]) -> str:
    """Convert a pdfplumber table (list of rows) to a Markdown table string."""
    # Clean cell values
    cleaned = [
        [cell.strip().replace("\n", " ") if cell else "" for cell in row]
        for row in table
    ]

    if not cleaned:
        return ""

    # Determine column widths
    col_count = max(len(row) for row in cleaned)
    # Pad rows to equal column count
    cleaned = [row + [""] * (col_count - len(row)) for row in cleaned]

    header = cleaned[0]
    rows = cleaned[1:]

    def fmt_row(cells):
        return "| " + " | ".join(cells) + " |"

    separator = "| " + " | ".join(["---"] * col_count) + " |"

    lines = [fmt_row(header), separator] + [fmt_row(r) for r in rows]
    return "\n".join(lines)


def pdf_to_markdown(pdf_path: Path) -> str:
    """Extract text and tables from a PDF and return as a Markdown string."""
    lines = [f"# {pdf_path.stem}\n"]

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            lines.append(f"\n---\n<!-- Page {page_num} -->\n")

            tables = page.extract_tables()
            if tables:
                # Build a set of bounding boxes for table regions so we can
                # avoid duplicating that text in the plain-text pass.
                table_bboxes = [table_obj.bbox for table_obj in page.find_tables()]

                # Extract text outside table regions
                non_table_page = page
                for bbox in table_bboxes:
                    non_table_page = non_table_page.filter(
                        lambda obj, bb=bbox: not (
                            bb[0] <= obj["x0"] <= bb[2] and bb[1] <= obj["top"] <= bb[3]
                        )
                    )

                text = non_table_page.extract_text() or ""
                if text.strip():
                    lines.append(text.strip())

                for table in tables:
                    md_table = table_to_markdown(table)
                    if md_table:
                        lines.append(f"\n{md_table}\n")
            else:
                text = page.extract_text() or ""
                if text.strip():
                    lines.append(text.strip())

    return "\n".join(lines)


def convert_one(args: tuple[Path, Path]) -> tuple[str, bool, str]:
    """Worker function: convert a single PDF. Returns (filename, success, message)."""
    pdf_path, out_path = args
    try:
        markdown = pdf_to_markdown(pdf_path)
        out_path.write_text(markdown, encoding="utf-8")
        return pdf_path.name, True, str(out_path)
    except Exception as e:
        return pdf_path.name, False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Convert merged FIA PDFs to Markdown.")
    parser.add_argument("--input", "-i", type=Path, default=INPUT_DIR)
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT_DIR)
    default_workers = max(1, int(os.cpu_count() * 0.25))
    parser.add_argument("--workers", "-w", type=int, default=default_workers,
                        help=f"Parallel worker processes (default: {default_workers})")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input directory '{args.input}' not found.")
        return

    pdfs = sorted(args.input.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in '{args.input}'.")
        return

    args.output.mkdir(parents=True, exist_ok=True)

    # Filter out already-converted files before submitting to the pool.
    todo = [(p, args.output / (p.stem + ".md")) for p in pdfs if not (args.output / (p.stem + ".md")).exists()]
    skipped = len(pdfs) - len(todo)

    if skipped:
        print(f"[SKIP] {skipped} already converted.")
    if not todo:
        print("Nothing to do.")
        return

    print(f"Converting {len(todo)} PDF(s) using {args.workers} worker(s)...\n")

    converted = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(convert_one, item): item[0] for item in todo}
        for future in as_completed(futures):
            name, success, message = future.result()
            if success:
                print(f"  OK  {name} -> {message}")
                converted += 1
            else:
                print(f"  ERR {name}: {message}")

    print(f"\nDone. Converted {converted}/{len(todo)} file(s).")


if __name__ == "__main__":
    main()
