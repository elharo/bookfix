"""bookfix: fills in missing cover author and title in book PDFs."""

import argparse
import io
import json
import os
import sys
import urllib.parse
import urllib.request
import re

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf import DocumentInformation
from typing import Optional

# Default URL for a locally running Ollama instance (OpenAI-compatible API).
_DEFAULT_LLM_URL = "http://localhost:11434/v1"
# A sensible default open-weight model available in Ollama.
_DEFAULT_MODEL = "llama3.2"


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


def read_title(reader: PdfReader) -> str:
    """Read the title from the PDF document content by returning the first non-empty line."""
    max_pages = min(len(reader.pages), 5)
    for i in range(max_pages):
        text = reader.pages[i].extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            if line:
                return line
    return "Unknown Title"


# Matches 'by <Name>' where each name component starts with a capital letter.
_AUTHOR_PATTERN = re.compile(r'\bby\s+([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*)')


def read_author(reader: PdfReader) -> str:
    """Read the author from the PDF document content by scanning for 'by <Name>' patterns."""
    max_pages = min(len(reader.pages), 5)
    for i in range(max_pages):
        text = reader.pages[i].extract_text() or ""
        match = _AUTHOR_PATTERN.search(text)
        if match:
            return match.group(1)
    return "Unknown Author"


def is_llm_available(
    base_url: str = _DEFAULT_LLM_URL,
    api_key: Optional[str] = None,
) -> bool:
    """Return True if the LLM service at base_url is reachable.

    A connection-level failure (e.g., Ollama not running) returns False.
    Any other response (including authentication errors) means the service
    is up and returns True.
    """
    from openai import OpenAI, APIConnectionError

    resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY") or "ollama"
    client = OpenAI(base_url=base_url, api_key=resolved_api_key)
    try:
        client.models.list()
        return True
    except APIConnectionError:
        return False
    except Exception:  # noqa: BLE001 – auth errors etc. mean the server is up
        return True


def ask_llm_for_metadata(
    text: str,
    model: str = _DEFAULT_MODEL,
    base_url: str = _DEFAULT_LLM_URL,
    api_key: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Ask an LLM to identify the title and author from PDF text.

    Uses the OpenAI-compatible chat API, which is supported by Ollama (local),
    OpenAI, and many other model providers.  Returns (title, author), either of
    which may be None if the LLM cannot determine it.

    The ``api_key`` defaults to the ``OPENAI_API_KEY`` environment variable when
    not supplied explicitly.  When talking to a local Ollama instance, the value
    is not checked, but a non-empty placeholder is still required by the client.
    """
    from openai import OpenAI

    resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY") or "ollama"

    client = OpenAI(base_url=base_url, api_key=resolved_api_key)

    prompt = (
        "From the following text extracted from a PDF, identify the book's title"
        " and author(s).\n\n"
        f"Text:\n{text[:3000]}\n\n"
        "Respond ONLY with a JSON object using exactly these keys:\n"
        '{"title": "...", "author": "..."}\n'
        "Use null for any value you cannot determine."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        # Use `or None` to convert empty-string results to None as well as missing keys.
        title = result.get("title") or None
        author = result.get("author") or None
        return title, author
    except Exception:  # noqa: BLE001 – treat all LLM errors as unavailable
        return None, None


def fix_pdf(
    filename: str,
    dryrun: bool,
    model: str = _DEFAULT_MODEL,
    llm_url: str = _DEFAULT_LLM_URL,
    api_key: Optional[str] = None,
) -> None:
    """Fix missing title, author, and cover in a PDF file.

    If dryrun is True, print what would be changed without modifying the file.
    The LLM identified by *model* at *llm_url* is used to extract missing
    metadata from the PDF text.  Falls back to regex heuristics when the LLM
    is unavailable.
    """
    reader = PdfReader(filename)
    metadata = reader.metadata
    title = get_title(metadata)
    authors = get_authors(metadata)

    updates: dict[str, str] = {}
    needs_title = title == "Unknown Title"
    needs_author = authors == "Unknown Author"

    if needs_title or needs_author:
        max_pages = min(len(reader.pages), 5)
        pdf_text = "\n".join(
            reader.pages[i].extract_text() or "" for i in range(max_pages)
        )

        if is_llm_available(base_url=llm_url, api_key=api_key):
            llm_title, llm_author = ask_llm_for_metadata(
                pdf_text, model=model, base_url=llm_url, api_key=api_key
            )
        else:
            print(
                f"LLM at {llm_url} is not available; falling back to text heuristics.",
                file=sys.stderr,
            )
            llm_title, llm_author = None, None

        if needs_title:
            resolved_title = llm_title or read_title(reader)
            if resolved_title != "Unknown Title":
                updates["/Title"] = resolved_title

        if needs_author:
            resolved_author = llm_author or read_author(reader)
            if resolved_author != "Unknown Author":
                updates["/Author"] = resolved_author

    if updates:
        authors = updates.get("/Author", authors)
        title = updates.get("/Title", title)

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
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help=(
            f"LLM model to use for metadata extraction (default: {_DEFAULT_MODEL})."
            " Any model available at the configured --llm-url may be specified."
        ),
    )
    parser.add_argument(
        "--llm-url",
        default=_DEFAULT_LLM_URL,
        dest="llm_url",
        help=(
            f"Base URL of the OpenAI-compatible LLM API (default: {_DEFAULT_LLM_URL})."
            " Use this to point at a remote OpenAI endpoint or another local server."
        ),
    )
    parser.add_argument(
        "--api-key",
        default=None,
        dest="api_key",
        help=(
            "API key for the LLM service.  Defaults to the OPENAI_API_KEY"
            " environment variable.  Not required for local Ollama instances."
        ),
    )
    args = parser.parse_args()
    try:
        fix_pdf(
            args.filename,
            args.dryrun,
            model=args.model,
            llm_url=args.llm_url,
            api_key=args.api_key,
        )
    except FileNotFoundError:
        parser.error(f"File not found: {args.filename}")


if __name__ == "__main__":
    main()
