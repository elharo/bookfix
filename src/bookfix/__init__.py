"""bookfix: reads PDF metadata and prints the title and author(s)."""

import argparse
import io
import json
import urllib.parse
import urllib.request
from typing import Optional

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf import DocumentInformation


def get_pdf_metadata(filename: str) -> Optional[DocumentInformation]:
    """Open a PDF file and return its metadata dictionary."""
    reader = PdfReader(filename)
    return reader.metadata


def get_title(metadata: Optional[DocumentInformation]) -> str:
    """Return the PDF title, or 'Unknown Title' if not present."""
    if metadata and metadata.title:
        return metadata.title
    return "Unknown Title"


def get_authors(metadata: Optional[DocumentInformation]) -> str:
    """Return the PDF author(s), or 'Unknown Author' if not present."""
    if metadata and metadata.author:
        return metadata.author
    return "Unknown Author"


def has_cover(reader: PdfReader) -> bool:
    """Return True if the first page of the PDF appears to be a cover page."""
    if not reader.pages:
        return False
    return len(reader.pages[0].images) > 0


def fetch_cover_image(title: str, author: str) -> Optional[bytes]:
    """Search Open Library for a book cover and return the image bytes, or None if not found."""
    query = urllib.parse.urlencode({"title": title, "author": author, "fields": "cover_i", "limit": "1"})
    search_url = f"https://openlibrary.org/search.json?{query}"
    with urllib.request.urlopen(search_url) as response:
        data = json.loads(response.read())
    docs = data.get("docs", [])
    if not docs or "cover_i" not in docs[0]:
        return None
    cover_id = docs[0]["cover_i"]
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    with urllib.request.urlopen(cover_url) as response:
        return response.read()


def add_cover(reader: PdfReader, cover_image_bytes: bytes) -> PdfWriter:
    """Return a new PdfWriter with the cover image prepended as the first page."""
    img = Image.open(io.BytesIO(cover_image_bytes))
    img_pdf_buf = io.BytesIO()
    img.save(img_pdf_buf, format="PDF")
    img_pdf_buf.seek(0)
    cover_reader = PdfReader(img_pdf_buf)
    writer = PdfWriter()
    writer.add_page(cover_reader.pages[0])
    for page in reader.pages:
        writer.add_page(page)
    return writer

def read_title(reader: PdfReader) -> str:
    """Read the title from the PDF document. Not yet implemented."""
    return "Not Implemented"


def read_author(reader: PdfReader) -> str:
    """Read the author from the PDF document. Not yet implemented."""
    return "Not Implemented"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the title and author(s) of a PDF file.")
    parser.add_argument("filename", help="Path to the PDF file")
    args = parser.parse_args()

    metadata = get_pdf_metadata(args.filename)
    print(get_title(metadata))
    print(get_authors(metadata))


if __name__ == "__main__":
    main()
