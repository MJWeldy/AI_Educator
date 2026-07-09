"""Stage 1: pull text, page count, and table of contents out of each source
file. A single-PDF upload has one source; a folder upload has several (PDFs plus
text/markdown/code files)."""

import json
from pathlib import Path

import fitz  # PyMuPDF

from ..config import settings
from ..models import Document

# Extensions read as plain text (rendered as one "page"). Everything else that
# isn't a PDF is skipped at upload time, so this list is advisory.
TEXT_SUFFIXES = {
    "txt", "md", "markdown", "rst", "tex", "org", "csv",
    "py", "js", "jsx", "ts", "tsx", "java", "c", "h", "cpp", "cc", "hpp",
    "cs", "go", "rs", "rb", "php", "swift", "kt", "scala", "sh", "bash",
    "sql", "html", "css", "scss", "vue", "json", "yaml", "yml", "toml", "xml",
    "r", "lua", "dart", "ex", "clj",
}


def kind_for(filename: str) -> str | None:
    """"pdf" | "text" for a supported file, else None."""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pdf":
        return "pdf"
    if suffix in TEXT_SUFFIXES:
        return "text"
    return None


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_source(path: str, filename: str, kind: str) -> dict:
    """One file → {filename, kind, pages: [str], toc, title}."""
    if kind == "pdf":
        pdf = fitz.open(path)
        pages = [page.get_text("text") for page in pdf]
        source = {
            "filename": filename,
            "kind": "pdf",
            "pages": pages,
            "toc": pdf.get_toc(simple=True) or [],
            "title": (pdf.metadata or {}).get("title") or "",
        }
        pdf.close()
        return source
    text = _decode(Path(path).read_bytes())
    return {"filename": filename, "kind": "text", "pages": [text], "toc": [], "title": ""}


def extract(doc: Document) -> dict:
    """Returns {"page_count", "title", "sources": [...]}, cached on disk so
    re-runs are free. For a single source the legacy top-level "pages"/"toc"
    keys are included too, so existing single-file consumers keep working."""
    cache_dir = Path(settings.extracted_dir) / str(doc.id)
    cache_file = cache_dir / "extract.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    files = list(doc.files)
    if files:
        specs = [(f.stored_path, f.filename, f.kind) for f in files]
    else:  # legacy single-PDF upload stored on the document itself
        specs = [(doc.stored_path, doc.filename, "pdf")]

    sources = [_extract_source(path, name, kind) for path, name, kind in specs]
    result: dict = {
        "page_count": sum(len(s["pages"]) for s in sources),
        "title": next((s["title"] for s in sources if s.get("title")), ""),
        "sources": sources,
    }
    if len(sources) == 1:
        result["pages"] = sources[0]["pages"]
        result["toc"] = sources[0]["toc"]

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(result))
    return result
