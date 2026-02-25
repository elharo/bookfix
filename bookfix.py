"""bookfix: reads PDF metadata and prints the title and author(s)."""

import argparse
import io
from typing import Optional

import requests
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

def read_title(reader: PdfReader) -> str:
    """Read the title from the PDF document. Not yet implemented."""
    return "Not Implemented"


def read_author(reader: PdfReader) -> str:
    """Read the author from the PDF document. Not yet implemented."""
    return "Not Implemented"


def fetch_cover_image(title: str, author: str) -> Optional[bytes]:
    """Search Open Library for the book and return cover image bytes, or None if not found."""
    params = {"title": title, "author": author, "limit": 1}
    response = requests.get("https://openlibrary.org/search.json", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    docs = data.get("docs")
    if not docs:
        return None

    cover_id = docs[0].get("cover_i")
    if not cover_id:
        return None

    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    img_response = requests.get(cover_url, timeout=10)
    img_response.raise_for_status()
    return img_response.content


def add_cover(reader: PdfReader) -> PdfWriter:
    """Find a cover image for the book online and return a new PDF with it as the first page."""
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))

    metadata = reader.metadata
    title = get_title(metadata)
    author = get_authors(metadata)

    image_bytes = fetch_cover_image(title, author)
    if image_bytes is not None:
        img = Image.open(io.BytesIO(image_bytes))
        img_pdf_buf = io.BytesIO()
        img.save(img_pdf_buf, format="PDF")
        img_pdf_buf.seek(0)
        cover_reader = PdfReader(img_pdf_buf)
        writer.insert_page(cover_reader.pages[0], index=0)

    return writer


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the title and author(s) of a PDF file.")
    parser.add_argument("filename", help="Path to the PDF file")
    args = parser.parse_args()

    metadata = get_pdf_metadata(args.filename)
    print(get_title(metadata))
    print(get_authors(metadata))


if __name__ == "__main__":
    main()
