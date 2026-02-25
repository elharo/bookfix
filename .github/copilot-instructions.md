# Copilot Instructions

This repository contains **bookfix**, a Python command-line tool that reads PDF files and fills in missing details (author, title, and cover).

## Project Overview

- **Language**: Python
- **Main module**: `bookfix.py`
- **Tests**: `test_bookfix.py` (pytest)
- **Dependencies**: `pypdf`, `pytest` (see `requirements.txt`)

## Code Style

- Use type hints for all function signatures.
- Write docstrings for all public functions.
- Follow PEP 8 conventions.

## Testing

- Tests use `pytest` and are located in `test_bookfix.py`.
- Use `pypdf.PdfWriter` to create in-memory PDF fixtures for tests rather than relying on files on disk.
- Run tests with: `pytest`
- Use test first programming. Make sure you have a failing test before fixing a bug or implementing a new feature.

## Key Patterns

- `get_pdf_metadata(filename)` opens a PDF and returns its `DocumentInformation` (or `None`).
- `get_title(metadata)` and `get_authors(metadata)` extract fields, returning fallback strings when data is absent.
- Always handle the case where metadata is `None` or a field is missing.
