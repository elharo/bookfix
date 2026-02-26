# bookfix

bookfix is a command-line tool that reads PDF files and updates title, authors, and cover
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

## LLM Usage

bookfix uses a large language model (LLM) to identify missing title and author information
from PDF text. You can supply an LLM in one of two ways:

### Option 1: Local model with Ollama

[Ollama](https://ollama.com) lets you run open-weight models on your own machine.

1. [Install Ollama](https://ollama.com/download) for your operating system.
2. Pull the default model:
   ```
   ollama pull llama3.2
   ```
3. Ollama starts automatically as a background service. bookfix will connect to it
   at `http://localhost:11434/v1` without any additional configuration.

To use a different model, pass `--model`:
```
bookfix --model mistral mybook.pdf
```

### Option 2: Cloud service with an API key

Any OpenAI-compatible cloud service works. For example, you can sign up for an
[OpenAI API key](https://platform.openai.com/signup).

Set your key as an environment variable:
```
export OPENAI_API_KEY=your-api-key-here
```

Then point bookfix at the cloud endpoint with `--llm-url` and choose the model:
```
bookfix --llm-url https://api.openai.com/v1 --model gpt-4o mybook.pdf
```

You can also pass the key directly with `--api-key` instead of using the environment variable.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to set up the development environment and run the tests.
