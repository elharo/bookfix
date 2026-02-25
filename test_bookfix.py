"""pytest unit tests for bookfix.py"""

import io
import pytest
from pypdf import PdfWriter, PdfReader
from pypdf import DocumentInformation
from pypdf.generic import NameObject, DictionaryObject, NumberObject, DecodedStreamObject

from bookfix import get_pdf_metadata, get_title, get_authors, has_cover, read_title, read_author, main


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


# --- main --dryrun flag ---

def test_main_dryrun_prints_dryrun_message(tmp_path, capsys) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(make_pdf(title="My Book", author="Jane Doe").read())
    main(["--dryrun", str(pdf_path)])
    captured = capsys.readouterr()
    assert "dry run" in captured.out.lower()


def test_main_dryrun_does_not_modify_file(tmp_path) -> None:
    pdf_bytes = make_pdf(title="My Book", author="Jane Doe").read()
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(pdf_bytes)
    main(["--dryrun", str(pdf_path)])
    assert pdf_path.read_bytes() == pdf_bytes


def test_main_without_dryrun_runs_normally(tmp_path, capsys) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(make_pdf(title="My Book", author="Jane Doe").read())
    main([str(pdf_path)])
    captured = capsys.readouterr()
    assert "My Book" in captured.out
    assert "Jane Doe" in captured.out
