"""
Flask web interface for FIA Docs Scraper.

Routes:
  GET  /                    — list events
  GET  /docs/<event>        — render markdown doc
  GET  /pdf/<event>         — serve merged PDF
  GET  /admin               — admin script runner
  GET  /admin/run/<script>  — SSE stream of script output
"""

import subprocess
import sys
from pathlib import Path

import markdown
from flask import Flask, Response, render_template, send_file, stream_with_context

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "fia_docs_merged_md"
MERGED_PDF_DIR = BASE_DIR / "fia_documents_merged"
RAW_DOCS_DIR = BASE_DIR / "fia_documents"

SCRIPTS = {
    "scraper": {
        "label": "Scrape FIA Website",
        "script": "scraper.py",
        "description": "Downloads new PDFs from the FIA website.",
    },
    "merge": {
        "label": "Merge PDFs",
        "script": "merge_event_pdfs.py",
        "description": "Merges per-event PDFs into single files.",
    },
    "convert": {
        "label": "Convert to Markdown",
        "script": "pdf_to_markdown.py",
        "description": "Converts merged PDFs to Markdown for LLM ingestion.",
    },
}


@app.route("/")
def index():
    events = []
    # Collect all known event names from any of the three directories
    names = set()
    for d in (DOCS_DIR, MERGED_PDF_DIR, RAW_DOCS_DIR):
        if d.exists():
            if d == RAW_DOCS_DIR:
                names.update(p.name for p in d.iterdir() if p.is_dir())
            else:
                names.update(p.stem for p in d.glob("*.pdf" if d == MERGED_PDF_DIR else "*.md"))

    for name in sorted(names, reverse=True):
        raw_pdfs = []
        raw_event_dir = RAW_DOCS_DIR / name
        if raw_event_dir.is_dir():
            raw_pdfs = sorted(p.name for p in raw_event_dir.glob("*.pdf"))
        events.append({
            "name": name,
            "has_merged_pdf": (MERGED_PDF_DIR / f"{name}.pdf").exists(),
            "has_markdown": (DOCS_DIR / f"{name}.md").exists(),
            "raw_pdfs": raw_pdfs,
        })
    return render_template("index.html", events=events)


@app.route("/docs/<event_name>")
def view_doc(event_name):
    md_path = DOCS_DIR / f"{event_name}.md"
    if not md_path.exists():
        return "Document not found", 404
    content = md_path.read_text(encoding="utf-8")
    html = markdown.markdown(content, extensions=["tables", "fenced_code"])
    has_pdf = (MERGED_PDF_DIR / f"{event_name}.pdf").exists()
    return render_template("doc.html", event_name=event_name, content=html, has_pdf=has_pdf)


@app.route("/pdf/<event_name>")
def view_pdf(event_name):
    pdf_path = MERGED_PDF_DIR / f"{event_name}.pdf"
    if not pdf_path.exists():
        return "PDF not found", 404
    return send_file(pdf_path, mimetype="application/pdf")


@app.route("/pdf/<event_name>/<doc_name>")
def view_raw_pdf(event_name, doc_name):
    pdf_path = RAW_DOCS_DIR / event_name / doc_name
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return "PDF not found", 404
    return send_file(pdf_path, mimetype="application/pdf")


@app.route("/admin")
def admin():
    return render_template("admin.html", scripts=SCRIPTS)


@app.route("/admin/run/<script_key>")
def run_script(script_key):
    if script_key not in SCRIPTS:
        return "Unknown script", 404

    script_path = BASE_DIR / SCRIPTS[script_key]["script"]

    def generate():
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(BASE_DIR),
        )
        for line in process.stdout:
            yield f"data: {line.rstrip()}\n\n"
        process.wait()
        yield f"data: --- exit code {process.returncode} ---\n\n"
        yield "data: __DONE__\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
