"""bookfix: reads PDF metadata and prints the title and author(s)."""

import argparse
from typing import Optional

from pypdf import PdfReader
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
    """Read the author from the PDF document metadata."""
    return get_authors(reader.metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the title and author(s) of a PDF file.")
    parser.add_argument("filename", help="Path to the PDF file")
    args = parser.parse_args()

    metadata = get_pdf_metadata(args.filename)
    print(get_title(metadata))
    print(get_authors(metadata))


if __name__ == "__main__":
    main()
