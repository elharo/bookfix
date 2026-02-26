"""bookfix: reads PDF metadata and prints the title and author(s)."""

import argparse
import re
from typing import Optional

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

# Matches 'by <Name>' where each name component starts with a capital letter.
_AUTHOR_PATTERN = re.compile(r'\bby\s+([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*)')

def read_title(reader: PdfReader) -> str:
    """Read the title from the PDF document. Not yet implemented."""
    return "Not Implemented"


def read_author(reader: PdfReader) -> str:
    """Read the author from the PDF document content by scanning for 'by <Name>' patterns."""
    max_pages = min(len(reader.pages), 5)
    for i in range(max_pages):
        text = reader.pages[i].extract_text() or ""
        match = _AUTHOR_PATTERN.search(text)
        if match:
            return match.group(1)
    return "Unknown Author"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the title and author(s) of a PDF file.")
    parser.add_argument("filename", help="Path to the PDF file")
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Print what would be changed without modifying the file.",
    )
    args = parser.parse_args()

    reader = PdfReader(args.filename)
    metadata = reader.metadata
    title = get_title(metadata)
    authors = get_authors(metadata)

    updates: dict[str, str] = {}
    if authors == "Unknown Author":
        extracted_author = read_author(reader)
        if extracted_author != "Unknown Author":
            updates["/Author"] = extracted_author

    if not args.dryrun and updates:
        writer = PdfWriter()
        writer.append(args.filename)
        writer.add_metadata(updates)
        with open(args.filename, "wb") as f:
            writer.write(f)
        authors = updates.get("/Author", authors)

    print(title)
    print(authors)


if __name__ == "__main__":
    main()
