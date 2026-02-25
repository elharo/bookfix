"""pytest unit tests for bookfix.py"""

import io
import pytest
from pypdf import PdfWriter, PdfReader
from pypdf import DocumentInformation
from pypdf.generic import NameObject, DictionaryObject, NumberObject, DecodedStreamObject

from bookfix import get_pdf_metadata, get_title, get_authors, has_cover, read_title, read_author, fetch_cover_image, add_cover


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


def test_get_pdf_metadata_returns_document_information() -> None:
    metadata = get_pdf_metadata(make_pdf(title="T", author="A"))
    assert isinstance(metadata, DocumentInformation)


def test_get_pdf_metadata_returns_none_for_empty_pdf() -> None:
    metadata = get_pdf_metadata(make_pdf())
    assert metadata is None or isinstance(metadata, DocumentInformation)


def make_pdf_with_image() -> PdfReader:
    """Return a PdfReader whose first page contains an image (simulates a cover)."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    img_stream = DecodedStreamObject()
    img_stream.set_data(b"\xff\xff\xff")
    img_stream.update({
        NameObject("/Type"): NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(1),
        NameObject("/Height"): NumberObject(1),
        NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
        NameObject("/BitsPerComponent"): NumberObject(8),
    })

    if "/Resources" not in page:
        page[NameObject("/Resources")] = DictionaryObject()
    resources = page["/Resources"]
    if "/XObject" not in resources:
        resources[NameObject("/XObject")] = DictionaryObject()
    resources["/XObject"][NameObject("/Im0")] = img_stream

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return PdfReader(buf)


def test_has_cover_returns_true_when_first_page_has_image() -> None:
    reader = make_pdf_with_image()
    assert has_cover(reader)


def test_has_cover_returns_false_when_first_page_has_no_image() -> None:
    reader = PdfReader(make_pdf())
    assert not has_cover(reader)


def test_has_cover_returns_false_for_empty_pdf() -> None:
    writer = PdfWriter()
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    reader = PdfReader(buf)
    assert not has_cover(reader)


def test_read_title_returns_not_implemented() -> None:
    from pypdf import PdfReader
    reader = PdfReader(make_pdf(title="My Book"))
    assert read_title(reader) == "Not Implemented"


def test_read_author_returns_not_implemented() -> None:
    from pypdf import PdfReader
    reader = PdfReader(make_pdf(author="Jane Doe"))
    assert read_author(reader) == "Not Implemented"


# --- fetch_cover_image ---

def make_jpeg_bytes() -> bytes:
    """Return minimal JPEG image bytes."""
    from PIL import Image
    img = Image.new("RGB", (10, 15), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_fetch_cover_image_returns_bytes_when_cover_found() -> None:
    from unittest.mock import patch, MagicMock
    search_mock = MagicMock()
    search_mock.json.return_value = {"docs": [{"cover_i": 12345}]}
    image_mock = MagicMock()
    image_mock.content = make_jpeg_bytes()

    with patch("bookfix.requests.get", side_effect=[search_mock, image_mock]):
        result = fetch_cover_image("Test Book", "Test Author")

    assert result == image_mock.content


def test_fetch_cover_image_returns_none_when_no_docs() -> None:
    from unittest.mock import patch, MagicMock
    search_mock = MagicMock()
    search_mock.json.return_value = {"docs": []}

    with patch("bookfix.requests.get", return_value=search_mock):
        result = fetch_cover_image("Unknown Book", "Nobody")

    assert result is None


def test_fetch_cover_image_returns_none_when_no_cover_id() -> None:
    from unittest.mock import patch, MagicMock
    search_mock = MagicMock()
    search_mock.json.return_value = {"docs": [{"title": "Test Book"}]}

    with patch("bookfix.requests.get", return_value=search_mock):
        result = fetch_cover_image("Test Book", "Test Author")

    assert result is None


# --- add_cover ---

def test_add_cover_inserts_image_page_at_front() -> None:
    from unittest.mock import patch, MagicMock
    search_mock = MagicMock()
    search_mock.json.return_value = {"docs": [{"cover_i": 99}]}
    image_mock = MagicMock()
    image_mock.content = make_jpeg_bytes()

    reader = PdfReader(make_pdf(title="Test Book", author="Test Author"))
    with patch("bookfix.requests.get", side_effect=[search_mock, image_mock]):
        writer = add_cover(reader)

    assert len(writer.pages) == 2


def test_add_cover_returns_original_pages_when_no_cover_found() -> None:
    from unittest.mock import patch, MagicMock
    search_mock = MagicMock()
    search_mock.json.return_value = {"docs": []}

    reader = PdfReader(make_pdf(title="Test Book", author="Test Author"))
    with patch("bookfix.requests.get", return_value=search_mock):
        writer = add_cover(reader)

    assert len(writer.pages) == 1
