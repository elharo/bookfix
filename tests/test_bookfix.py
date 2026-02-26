"""pytest unit tests for bookfix.py"""

import io
import json
import os
import tempfile
import unittest.mock
import pytest
from pypdf import PdfWriter, PdfReader
from pypdf import DocumentInformation
from pypdf.generic import NameObject, DictionaryObject, NumberObject, DecodedStreamObject
from PIL import Image
from unittest.mock import patch

from bookfix import get_pdf_metadata, get_title, get_authors, has_cover, read_title, read_author, fetch_cover_image, add_cover, main


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


def make_pdf_file(title: str | None = None, author: str | None = None) -> str:
    """Write a PDF to a temp file and return the filename.

    The caller is responsible for deleting the file using os.unlink().
    """
    buffer = make_pdf(title=title, author=author)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as file:
        file.write(buffer.read())
        return file.name


# --- main() --dryrun ---

def test_main_dryrun_does_not_modify_file() -> None:
    """Test that --dryrun does not modify the PDF file on disk."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        last_modified_time_before = os.path.getmtime(path)
        with patch("sys.argv", ["bookfix", "--dryrun", path]):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_no_cover()):
                main()
        last_modified_time_after = os.path.getmtime(path)
        assert last_modified_time_before == last_modified_time_after
    finally:
        os.unlink(path)


def test_main_dryrun_prints_title_and_author(capsys: pytest.CaptureFixture) -> None:
    """Test that --dryrun prints the title and author from metadata."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        with patch("sys.argv", ["bookfix", "--dryrun", path]):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_no_cover()):
                main()
        captured = capsys.readouterr()
        assert "My Book" in captured.out
        assert "Jane Doe" in captured.out
    finally:
        os.unlink(path)


def test_main_dryrun_prints_extracted_author_when_metadata_missing(
    capsys: pytest.CaptureFixture,
) -> None:
    """Test that --dryrun prints the would-be-written author extracted from content."""
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
    content = b"BT /F1 12 Tf 100 700 Td (by Jane Doe) Tj ET"
    stream = DecodedStreamObject()
    stream.set_data(content)
    page[NameObject("/Contents")] = stream
    writer.add_metadata({"/Title": "My Book"})

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as file:
        writer.write(file)
        path = file.name
    try:
        with patch("sys.argv", ["bookfix", "--dryrun", path]):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_no_cover()):
                main()
        captured = capsys.readouterr()
        assert "Jane Doe" in captured.out
    finally:
        os.unlink(path)


def test_main_without_dryrun_writes_missing_author_to_file() -> None:
    """Test that without --dryrun, a missing author extracted from content is written to the file."""
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
    content = b"BT /F1 12 Tf 100 700 Td (by Jane Doe) Tj ET"
    stream = DecodedStreamObject()
    stream.set_data(content)
    page[NameObject("/Contents")] = stream
    writer.add_metadata({"/Title": "My Book"})

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        writer.write(f)
        path = f.name
    try:
        with patch("sys.argv", ["bookfix", path]):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_no_cover()):
                main()
        reader = PdfReader(path)
        metadata = reader.metadata
        assert metadata is not None
        assert metadata.author == "Jane Doe"
    finally:
        os.unlink(path)


def _fake_urlopen_with_cover(cover_bytes: bytes):
    """Return a fake urlopen that returns a cover image for cover URLs."""
    search_response = json.dumps({"docs": [{"cover_i": 99999}]}).encode()

    def fake_urlopen(url):
        mock_response = unittest.mock.MagicMock()
        if "search.json" in url:
            mock_response.read.return_value = search_response
        else:
            mock_response.read.return_value = cover_bytes
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = unittest.mock.MagicMock(return_value=False)
        return mock_response

    return fake_urlopen


def _fake_urlopen_no_cover():
    """Return a fake urlopen that returns no cover (empty docs)."""
    search_response = json.dumps({"docs": []}).encode()

    def fake_urlopen(url):
        mock_response = unittest.mock.MagicMock()
        mock_response.read.return_value = search_response
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = unittest.mock.MagicMock(return_value=False)
        return mock_response

    return fake_urlopen


def test_main_dryrun_prints_cover_found_when_cover_missing_and_found(
    capsys: pytest.CaptureFixture,
) -> None:
    """Test that --dryrun prints 'Cover found' when PDF has no cover but one is available."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        with patch("sys.argv", ["bookfix", "--dryrun", path]):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                side_effect=_fake_urlopen_with_cover(make_jpeg_bytes()),
            ):
                main()
        captured = capsys.readouterr()
        assert "Cover found" in captured.out
    finally:
        os.unlink(path)


def test_main_dryrun_prints_cover_not_found_when_cover_missing_and_not_found(
    capsys: pytest.CaptureFixture,
) -> None:
    """Test that --dryrun prints 'Cover not found' when PDF has no cover and none is available."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        with patch("sys.argv", ["bookfix", "--dryrun", path]):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                side_effect=_fake_urlopen_no_cover(),
            ):
                main()
        captured = capsys.readouterr()
        assert "Cover not found" in captured.out
    finally:
        os.unlink(path)


def test_main_dryrun_does_not_modify_file_when_cover_found(
    capsys: pytest.CaptureFixture,
) -> None:
    """Test that --dryrun does not modify the file even when a cover is found."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        last_modified_time_before = os.path.getmtime(path)
        with patch("sys.argv", ["bookfix", "--dryrun", path]):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                side_effect=_fake_urlopen_with_cover(make_jpeg_bytes()),
            ):
                main()
        last_modified_time_after = os.path.getmtime(path)
        assert last_modified_time_before == last_modified_time_after
    finally:
        os.unlink(path)


def test_main_adds_cover_to_pdf_when_missing() -> None:
    """Test that without --dryrun, a missing cover is added to the PDF file."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        reader_before = PdfReader(path)
        assert not has_cover(reader_before)
        with patch("sys.argv", ["bookfix", path]):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                side_effect=_fake_urlopen_with_cover(make_jpeg_bytes()),
            ):
                main()
        reader_after = PdfReader(path)
        assert has_cover(reader_after)
    finally:
        os.unlink(path)


def test_main_does_not_add_cover_when_cover_not_found() -> None:
    """Test that without --dryrun, the PDF is not modified when no cover is found."""
    path = make_pdf_file(title="My Book", author="Jane Doe")
    try:
        last_modified_time_before = os.path.getmtime(path)
        with patch("sys.argv", ["bookfix", path]):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                side_effect=_fake_urlopen_no_cover(),
            ):
                main()
        last_modified_time_after = os.path.getmtime(path)
        assert last_modified_time_before == last_modified_time_after
    finally:
        os.unlink(path)
