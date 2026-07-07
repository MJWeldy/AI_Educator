"""Stage 1: pull text, page count, and table of contents out of the PDF."""

import json
from pathlib import Path

import fitz  # PyMuPDF

from ..config import settings
from ..models import Document


def extract(doc: Document) -> dict:
    """Returns {"page_count", "toc": [[level, title, page], ...], "pages": [str]},
    cached on disk so re-runs are free."""
    cache_dir = Path(settings.extracted_dir) / str(doc.id)
    cache_file = cache_dir / "extract.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    pdf = fitz.open(doc.stored_path)
    pages = [page.get_text("text") for page in pdf]
    result = {
        "page_count": len(pages),
        "toc": pdf.get_toc(simple=True) or [],
        "title": (pdf.metadata or {}).get("title") or "",
        "pages": pages,
    }
    pdf.close()

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(result))
    return result
