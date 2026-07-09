"""The ingestion state machine. Document.status tracks the stage; every stage
checkpoints its own outputs, so a crashed or restarted job resumes where it
stopped and the LLM cache makes re-runs nearly free."""

from ..db import SessionLocal
from ..jobs import handler, set_progress
from ..models import Document, Job
from . import derive, extract, generate, readings, segment


@handler("ingest_document")
async def ingest_document(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        doc_id = job.payload["document_id"]

    def progress(stage: str, current: int, total: int, message: str = "") -> None:
        with SessionLocal() as pdb:
            set_progress(pdb, job_id, stage, current, total, message)

    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise ValueError(f"document {doc_id} not found")

        if doc.status in ("uploaded", "extracting", "failed"):
            doc.status = "extracting"
            db.commit()
            progress("extracting text", 0, 1)
            extracted = extract.extract(doc)
            doc.page_count = extracted["page_count"]
            if not doc.title:
                doc.title = extracted.get("title") or doc.filename.rsplit(".", 1)[0]
            doc.status = "segmenting"
            db.commit()
        else:
            extracted = extract.extract(doc)

        if doc.status == "segmenting":
            progress("segmenting into sections", 0, 1)
            segment.build_sections(db, doc, extracted)
            doc.status = "deriving"
            db.commit()

    if _status(doc_id) == "deriving":
        with SessionLocal() as db:
            doc = db.get(Document, doc_id)
            await derive.derive_topics(db, doc, progress=progress)
            readings.attach_readings(db, doc)
            doc.status = "generating"
            db.commit()

    if _status(doc_id) == "generating":
        with SessionLocal() as db:
            doc = db.get(Document, doc_id)
            await generate.generate_content(db, doc, progress=progress)
            doc.status = "review"
            db.commit()
    progress("ready for review", 1, 1)


def _status(doc_id: int) -> str:
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        return doc.status if doc else "missing"
