"""Stage 2: turn extracted sources into a chapter/section tree.

Single PDF: prefer the PDF's own table of contents (levels 1-2); without one,
fall back to fixed-size page chunks. Folder / multi-file upload: each file
becomes a top-level chapter, chunked into readable leaves. Either way the
derive stage sees the same level-1 chapters with level-2 leaves."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentSection

MAX_SECTION_PAGES = 15
MAX_SECTION_CHARS = 24_000
FALLBACK_CHUNK_PAGES = 10


def _page_text(pages: list[str], start: int, end: int) -> str:
    return "\n".join(pages[start : end + 1])[:MAX_SECTION_CHARS]


def _segment_pdf(db: Session, doc: Document, source: dict, sections: list[DocumentSection]) -> None:
    """Single-PDF segmentation: TOC-driven when available, else page chunks."""
    pages: list[str] = source["pages"]
    n = len(pages)
    toc = [(lvl, title.strip(), page) for lvl, title, page in source.get("toc", []) if lvl <= 2]

    if len(toc) >= 3:
        # Page ranges: each entry runs until the next entry of same-or-higher level.
        entries = [(lvl, title, max(0, page - 1)) for lvl, title, page in toc]
        current_chapter: DocumentSection | None = None
        for i, (lvl, title, start) in enumerate(entries):
            end = n - 1
            for lvl2, _t2, start2 in entries[i + 1 :]:
                if lvl2 <= lvl:
                    end = max(start, start2 - 1)
                    break
            end = min(end, start + MAX_SECTION_PAGES - 1, n - 1)
            section = DocumentSection(
                document_id=doc.id,
                parent_id=current_chapter.id if (lvl == 2 and current_chapter) else None,
                level=lvl,
                position=i,
                title=title[:200],
                page_start=start,
                page_end=end,
                text=_page_text(pages, start, end),
            )
            db.add(section)
            db.flush()
            if lvl == 1:
                current_chapter = section
            sections.append(section)
    else:
        chapter = DocumentSection(
            document_id=doc.id, level=1, position=0, title=doc.title or doc.filename,
            page_start=0, page_end=n - 1, text="",
        )
        db.add(chapter)
        db.flush()
        sections.append(chapter)
        for i, start in enumerate(range(0, n, FALLBACK_CHUNK_PAGES)):
            end = min(start + FALLBACK_CHUNK_PAGES - 1, n - 1)
            section = DocumentSection(
                document_id=doc.id, parent_id=chapter.id, level=2, position=i + 1,
                title=f"Pages {start + 1}–{end + 1}",
                page_start=start, page_end=end,
                text=_page_text(pages, start, end),
            )
            db.add(section)
            sections.append(section)


def _segment_file_as_chapter(
    db: Session, doc: Document, source: dict, position: int, sections: list[DocumentSection]
) -> None:
    """Folder upload: one file → one chapter titled by its path, with leaves."""
    pages: list[str] = source["pages"]
    label = source["filename"]
    is_pdf = source["kind"] == "pdf"
    chapter = DocumentSection(
        document_id=doc.id, level=1, position=position, title=label[:200],
        page_start=0, page_end=(len(pages) - 1 if is_pdf and pages else 0), text="",
    )
    db.add(chapter)
    db.flush()
    sections.append(chapter)

    leaves: list[DocumentSection] = []
    if is_pdf:
        n = len(pages)
        for i, start in enumerate(range(0, n, FALLBACK_CHUNK_PAGES)):
            end = min(start + FALLBACK_CHUNK_PAGES - 1, n - 1)
            leaves.append(DocumentSection(
                document_id=doc.id, parent_id=chapter.id, level=2, position=i,
                title=f"Pages {start + 1}–{end + 1}",
                page_start=start, page_end=end, text=_page_text(pages, start, end),
            ))
    else:
        text = pages[0] if pages else ""
        chunks = [text[i : i + MAX_SECTION_CHARS] for i in range(0, len(text), MAX_SECTION_CHARS)] or [""]
        for i, chunk in enumerate(chunks):
            title = label if len(chunks) == 1 else f"{label} (part {i + 1})"
            leaves.append(DocumentSection(
                document_id=doc.id, parent_id=chapter.id, level=2, position=i,
                title=title[:200], page_start=0, page_end=0, text=chunk,
            ))
    for leaf in leaves:
        db.add(leaf)
    sections.extend(leaves)


def build_sections(db: Session, doc: Document, extracted: dict) -> list[DocumentSection]:
    existing = db.scalars(
        select(DocumentSection).where(DocumentSection.document_id == doc.id)
    ).all()
    if existing:
        return existing  # checkpoint: already segmented

    sources = extracted.get("sources")
    if not sources:  # very old cached shape without per-source split
        sources = [{
            "filename": doc.filename, "kind": "pdf",
            "pages": extracted.get("pages", []), "toc": extracted.get("toc", []),
        }]

    sections: list[DocumentSection] = []
    if len(sources) == 1 and sources[0]["kind"] == "pdf":
        _segment_pdf(db, doc, sources[0], sections)
    else:
        for pos, source in enumerate(sources):
            _segment_file_as_chapter(db, doc, source, pos, sections)
    db.commit()
    return sections
