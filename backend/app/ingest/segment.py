"""Stage 2: turn extracted pages into a chapter/section tree.

Prefer the PDF's own table of contents (levels 1-2). Without one, fall back
to fixed-size page chunks — the LLM derive stage can still find topics in
them, just with less structure to lean on."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentSection

MAX_SECTION_PAGES = 15
MAX_SECTION_CHARS = 24_000
FALLBACK_CHUNK_PAGES = 10


def _page_text(pages: list[str], start: int, end: int) -> str:
    return "\n".join(pages[start : end + 1])[:MAX_SECTION_CHARS]


def build_sections(db: Session, doc: Document, extracted: dict) -> list[DocumentSection]:
    existing = db.scalars(
        select(DocumentSection).where(DocumentSection.document_id == doc.id)
    ).all()
    if existing:
        return existing  # checkpoint: already segmented

    pages: list[str] = extracted["pages"]
    n = len(pages)
    toc = [(lvl, title.strip(), page) for lvl, title, page in extracted.get("toc", []) if lvl <= 2]

    sections: list[DocumentSection] = []
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
    db.commit()
    return sections
