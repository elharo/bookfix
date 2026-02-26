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

Create and activate a virtual environment, then install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows, activate the virtual environment with:

```bat
.venv\Scripts\activate
```
## Install the requirement.txt

```bash
pip install -r requirements.txt
```

## Running the Tests

With the virtual environment activated:

```bash
python -m pytest
```
