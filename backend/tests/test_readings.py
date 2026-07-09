from app.ingest.readings import reading_for
from app.models import DocumentSection


def _section(title, start, end):
    return DocumentSection(title=title, page_start=start, page_end=end)


def test_named_section_gets_book_and_page_range():
    title, note = reading_for("MacKenzie 2018", _section("11.2 Optimal design", 244, 247))
    assert title == "11.2 Optimal design"
    # 0-based indices → 1-based inclusive human pages.
    assert note == "MacKenzie 2018 · pp. 245–248"


def test_single_page_uses_singular():
    _, note = reading_for("Book", _section("A Section", 9, 9))
    assert note == "Book · p. 10"


def test_page_chunk_title_is_not_duplicated():
    # Fallback "Pages 41–50" titles already encode the range; note is just book.
    title, note = reading_for("Book", _section("Pages 41–50", 40, 49))
    assert title == "Pages 41–50"
    assert note == "Book"


def test_missing_pages_degrade_gracefully():
    title, note = reading_for("Book", _section("Intro", 0, 0))
    assert title == "Intro" and note == "Book"
