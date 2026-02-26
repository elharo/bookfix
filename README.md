# bookfix

bookfix is a command-line tool that reads PDF files and prints their title and author(s).

## Installation

Create and activate a virtual environment, then install the required dependencies:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the virtual environment with:

```
.venv\Scripts\activate
```

## Usage

```
python bookfix.py <path-to-pdf>
```

For example:

```
python bookfix.py mybook.pdf
```

This prints the title and author(s) of the PDF to standard output.

## Running the Tests

```
pytest
```