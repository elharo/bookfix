# bookfix

bookfix is a command-line tool that reads PDF files and prints their title and author(s).

## Installation

Install the required dependencies:

```
pip install -r requirements.txt
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