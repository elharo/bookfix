# bookfix

bookfix is a command-line tool that reads PDF files and updates titles, authors, and cover
based on the content of the PDF.

## Installation

Create and activate a virtual environment, then install the package:

```
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows, activate the virtual environment with:

```
.venv\Scripts\activate
```

## Usage

```
bookfix <path-to-pdf>
```

For example:

```
bookfix mybook.pdf
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to set up the development environment and run the tests.
