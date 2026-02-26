# Contributing to bookfix

## Prerequisites

- [Git](https://git-scm.com/)
- Python 3.12 or later

## Checking Out the Code

```bash
git clone https://github.com/elharo/bookfix.git
cd bookfix
```

## Setting Up the Development Environment

Create and activate a virtual environment, then install the required dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the virtual environment with:

```bat
.venv\Scripts\activate
```

## Running the Tests

With the virtual environment activated:

```bash
python -m pytest
```
