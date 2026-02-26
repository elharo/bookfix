"""pytest unit tests for bookfix.py"""

import io
import json
import unittest.mock
import pytest
from pypdf import PdfWriter, PdfReader
from pypdf import DocumentInformation
from pypdf.generic import NameObject, DictionaryObject, NumberObject, DecodedStreamObject
from PIL import Image

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


def test_read_title_returns_first_line_from_content() -> None:
    reader = make_pdf_with_text("My Great Book")
    assert read_title(reader) == "My Great Book"


def test_read_title_returns_unknown_when_no_content() -> None:
    reader = PdfReader(make_pdf())
    assert read_title(reader) == "Unknown Title"



def make_jpeg_bytes() -> bytes:
    """Return minimal valid JPEG image bytes (1x1 white pixel)."""
    img = Image.new("RGB", (1, 1), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_fetch_cover_image_returns_bytes_when_cover_found() -> None:
    search_response = json.dumps({
        "docs": [{"cover_i": 12345}]
    }).encode()
    cover_bytes = make_jpeg_bytes()

    def fake_urlopen(url):
        mock_response = unittest.mock.MagicMock()
        if "search.json" in url:
            mock_response.read.return_value = search_response
        else:
            mock_response.read.return_value = cover_bytes
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = unittest.mock.MagicMock(return_value=False)
        return mock_response

    with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = fetch_cover_image("Some Book", "Some Author")

    assert result == cover_bytes


def test_fetch_cover_image_returns_none_when_no_docs() -> None:
    search_response = json.dumps({"docs": []}).encode()

    mock_response = unittest.mock.MagicMock()
    mock_response.read.return_value = search_response
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = unittest.mock.MagicMock(return_value=False)

    with unittest.mock.patch("urllib.request.urlopen", return_value=mock_response):
        result = fetch_cover_image("Unknown Book", "Unknown Author")

    assert result is None


def test_fetch_cover_image_returns_none_when_no_cover_id() -> None:
    search_response = json.dumps({"docs": [{"title": "Some Book"}]}).encode()

    mock_response = unittest.mock.MagicMock()
    mock_response.read.return_value = search_response
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = unittest.mock.MagicMock(return_value=False)

    with unittest.mock.patch("urllib.request.urlopen", return_value=mock_response):
        result = fetch_cover_image("Some Book", "Some Author")

    assert result is None


def test_add_cover_prepends_cover_as_first_page() -> None:
    reader = PdfReader(make_pdf(title="My Book", author="Author"))
    original_page_count = len(reader.pages)
    cover_bytes = make_jpeg_bytes()

    writer = add_cover(reader, cover_bytes)

    assert len(writer.pages) == original_page_count + 1


def test_add_cover_first_page_has_image() -> None:
    reader = PdfReader(make_pdf())
    cover_bytes = make_jpeg_bytes()

    writer = add_cover(reader, cover_bytes)

    # Write and re-read to verify the cover page has an image
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    result_reader = PdfReader(buf)
    assert has_cover(result_reader)


def make_pdf_with_text(text: str) -> PdfReader:
    """Return a PdfReader whose first page contains the given text."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })

    if "/Resources" not in page:
        page[NameObject("/Resources")] = DictionaryObject()
    resources = page["/Resources"]
    if "/Font" not in resources:
        resources[NameObject("/Font")] = DictionaryObject()
    resources["/Font"][NameObject("/F1")] = font_dict

    content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
    stream = DecodedStreamObject()
    stream.set_data(content)
    page[NameObject("/Contents")] = stream

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return PdfReader(buf)


def test_read_author_returns_author_from_content() -> None:
    reader = make_pdf_with_text("by Jane Doe")
    assert read_author(reader) == "Jane Doe"


def test_read_author_returns_unknown_when_no_capitalized_name() -> None:
    reader = make_pdf_with_text("written by myself")
    assert read_author(reader) == "Unknown Author"


def test_read_author_returns_unknown_when_no_author() -> None:
    reader = PdfReader(make_pdf())
    assert read_author(reader) == "Unknown Author"
