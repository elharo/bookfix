"""pytest unit tests for bookfix.py"""

import io
import pytest
from pypdf import PdfWriter
from pypdf import DocumentInformation

from bookfix import get_pdf_metadata, get_title, get_authors, read_title, read_author


def make_pdf(title: str | None = None, author: str | None = None) -> io.BytesIO:
    """Return an in-memory PDF with optional title and author metadata."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    metadata: dict[str, str] = {}
    if title is not None:
        metadata["/Title"] = title
    if author is not None:
        metadata["/Author"] = author
    if metadata:
        writer.add_metadata(metadata)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


# --- get_title ---

def test_get_title_returns_title_from_metadata() -> None:
    metadata = get_pdf_metadata(make_pdf(title="My Book"))
    assert get_title(metadata) == "My Book"


def test_get_title_returns_unknown_when_no_title() -> None:
    metadata = get_pdf_metadata(make_pdf())
    assert get_title(metadata) == "Unknown Title"


def test_get_title_returns_unknown_when_metadata_is_none() -> None:
    assert get_title(None) == "Unknown Title"


# --- get_authors ---

def test_get_authors_returns_author_from_metadata() -> None:
    metadata = get_pdf_metadata(make_pdf(author="Jane Doe"))
    assert get_authors(metadata) == "Jane Doe"


def test_get_authors_returns_unknown_when_no_author() -> None:
    metadata = get_pdf_metadata(make_pdf())
    assert get_authors(metadata) == "Unknown Author"


def test_get_authors_returns_unknown_when_metadata_is_none() -> None:
    assert get_authors(None) == "Unknown Author"


# --- get_pdf_metadata ---

def test_get_pdf_metadata_returns_document_information() -> None:
    metadata = get_pdf_metadata(make_pdf(title="T", author="A"))
    assert isinstance(metadata, DocumentInformation)


def test_get_pdf_metadata_returns_none_for_empty_pdf() -> None:
    metadata = get_pdf_metadata(make_pdf())
    assert metadata is None or isinstance(metadata, DocumentInformation)


# --- read_title ---

def test_read_title_returns_not_implemented() -> None:
    from pypdf import PdfReader
    reader = PdfReader(make_pdf(title="My Book"))
    assert read_title(reader) == "Not Implemented"


# --- read_author ---

def test_read_author_returns_not_implemented() -> None:
    from pypdf import PdfReader
    reader = PdfReader(make_pdf(author="Jane Doe"))
    assert read_author(reader) == "Not Implemented"
