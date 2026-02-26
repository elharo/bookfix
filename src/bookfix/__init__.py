"""bookfix: fills in missing cover author and title in book PDFs."""

import argparse
import io
import json
import urllib.parse
import urllib.request
import re

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf import DocumentInformation
from typing import Optional


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
    image = Image.open(io.BytesIO(cover_image_bytes))
    image_pdf_buf = io.BytesIO()
    image.save(image_pdf_buf, format="PDF")
    image_pdf_buf.seek(0)
    cover_reader = PdfReader(image_pdf_buf)
    writer = PdfWriter()
    writer.add_page(cover_reader.pages[0])
    for page in reader.pages:
        writer.add_page(page)
    return writer


# Matches 'by <Name>' where each name component starts with a capital letter.
_AUTHOR_PATTERN = re.compile(r'\bby\s+([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*)')

# Matches publisher-like words that indicate a line is a publisher name, not an author.
_PUBLISHER_KEYWORDS = re.compile(
    r'\b(publishers?|publishing|press|corporation|corp\.?|inc\.?|ltd\.?)\b',
    re.IGNORECASE,
)

# Matches institutional affiliation lines like "Department of Mathematics, Harvard University"
# or lines starting with "Department of".
_AFFILIATION_PATTERN = re.compile(
    r'(?:,\s*\w[\w\s]*(university|college|institute|department)'
    r'|\bDepartment\s+of\b)',
    re.IGNORECASE,
)


def _is_spaced_text(line: str) -> bool:
    """Return True if the line appears to be spaced-out text (e.g., 'L Y N N H.')."""
    tokens = line.split()
    if len(tokens) < 4:
        return False
    short_tokens = sum(1 for t in tokens if len(t) <= 2)
    return short_tokens / len(tokens) > 0.5


def read_title(reader: PdfReader) -> str:
    """Read the title from the PDF document content by returning the first non-empty line
    that does not appear to be a spaced-out author byline, affiliation, or publisher name."""
    max_pages = min(len(reader.pages), 5)
    for i in range(max_pages):
        text = reader.pages[i].extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if _is_spaced_text(line):
                continue
            if _PUBLISHER_KEYWORDS.search(line):
                continue
            if _AFFILIATION_PATTERN.search(line):
                continue
            return line
    return "Unknown Title"


def read_author(reader: PdfReader) -> str:
    """Read the author from the PDF document content by scanning for 'by <Name>' patterns,
    excluding publisher names."""
    max_pages = min(len(reader.pages), 5)
    for i in range(max_pages):
        text = reader.pages[i].extract_text() or ""
        for match in _AUTHOR_PATTERN.finditer(text):
            author = match.group(1)
            if not _PUBLISHER_KEYWORDS.search(author):
                return author
    return "Unknown Author"


def fix_pdf(filename: str, dryrun: bool) -> None:
    """Fix missing title, author, and cover in a PDF file.

    If dryrun is True, print what would be changed without modifying the file.
    """
    reader = PdfReader(filename)
    metadata = reader.metadata
    title = get_title(metadata)
    authors = get_authors(metadata)

    updates: dict[str, str] = {}
    if authors == "Unknown Author":
        extracted_author = read_author(reader)
        if extracted_author != "Unknown Author":
            updates["/Author"] = extracted_author

    if updates:
        authors = updates.get("/Author", authors)

    cover_missing = not has_cover(reader)
    cover_image_bytes: Optional[bytes] = None
    if cover_missing:
        cover_image_bytes = fetch_cover_image(title, authors)

    if not dryrun and (updates or cover_image_bytes):
        if cover_image_bytes:
            writer = add_cover(reader, cover_image_bytes)
        else:
            writer = PdfWriter()
            writer.append(filename)
        if updates:
            writer.add_metadata(updates)
        with open(filename, "wb") as f:
            writer.write(f)

    if dryrun:
        print(title)
        print(authors)
        if cover_missing:
            if cover_image_bytes:
                print("Cover found")
            else:
                print("Cover not found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the title and author(s) of a PDF file.")
    parser.add_argument("filename", help="Path to the PDF file")
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Print what would be changed without modifying the file.",
    )
    args = parser.parse_args()
    try:
        fix_pdf(args.filename, args.dryrun)
    except FileNotFoundError:
        parser.error(f"File not found: {args.filename}")


if __name__ == "__main__":
    main()
