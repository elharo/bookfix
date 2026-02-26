# Copilot Instructions

This repository contains **bookfix**, a Python command-line tool that reads PDF files and fills in missing details (author, title, and cover).

## Project Overview

- **Language**: Python
- **Main module**: `src/bookfix/__init__.py`
- **Tests**: `tests/test_bookfix.py` (pytest)
- **Dependencies**: `pypdf`, `Pillow`, `pytest` (see `requirements.txt`)

## Code Style

- Use type hints for all function signatures.
- Write docstrings for all public functions.
- Follow PEP 8 conventions.
- Names should be as descriptive as possible.

    Avoid Abbreviations: "Do not abbreviate by deleting letters within a word." For example, use image instead of img.

    Exceptions: Abbreviations that are "ubiquitous" or "standard" in the industry, such as i for an iteration index or url for uniform resource locator are allowed.
  - In general follow Google Python syle guidelines and best practices,

## Testing

- Tests use `pytest` and are located in `tests/test_bookfix.py`.
- Use `pypdf.PdfWriter` to create in-memory PDF fixtures for tests rather than relying on files on disk.
- Run tests with: `python -m pytest`
- Use test first programming. Make sure you have a failing test before fixing a bug or implementing a new feature.

## Key Patterns

- `get_pdf_metadata(filename)` opens a PDF and returns its `DocumentInformation` (or `None`).
- `get_title(metadata)` and `get_authors(metadata)` extract fields, returning fallback strings when data is absent.
- Always handle the case where metadata is `None` or a field is missing.
