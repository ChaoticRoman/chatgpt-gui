# ChatGPT Python Clients

Python CLI and GUI clients for OpenAI's ChatGPT. Simple, no arguments required to get started.

## Installation

**Note:** Prefer your distribution packages if possible.

For the CLI client:

```bash
pip install openai rich
```

For the GUI client (Tkinter is often part of the standard Python installation):

```bash
pip install openai tkinterweb mistletoe pygments
```

## Usage

### API Key

Expects `.api_key` file in the repo directory with your OpenAI API key. The filename is
in `.gitignore` already.

Conversations are automatically saved as JSON files in `~/.chatgpt-gui/`.

### CLI Client

```bash
./cli.py
```

Quit with `q`, `x`, `exit`, `quit`, `Ctrl+C`, or `Ctrl+D`.

#### Options

| Flag | Description |
|------|-------------|
| `-m`, `--multiline` | Multiline input mode — type your message, then enter `SEND` to submit |
| `-b`, `--batch-mode` | Non-interactive mode for pipes and redirection (pricing info goes to stderr) |
| `-M`, `--model` | Select a specific model |
| `-w`, `--web-search` | Enable web search with source extraction |
| `-p`, `--prepend` | Prepend a file's contents to the first message |
| `-i`, `--image` | Image file to include with the first message |
| `-d`, `--debug` | Pretty-print raw API responses to stderr |
| `-l`, `--list-known` | List models with known pricing |
| `-L`, `--list-all` | List all available models |
| `-lf`, `--list-files` | List uploaded files |

#### Batch Mode Examples

```bash
./cli.py -b <<< "Tell a joke" > joke.txt
./cli.py -b < prompt.txt > output.txt
./cli.py -b --prepend summarize_prompt.txt < article.txt
```

More useful example to review patch of PR for currently checked out branch in the current
directory (expects `gh` client installed):

```bash
alias review='gh pr diff --patch | gpt -b -p $HOME/.pr-review'
```

The `.pr-review` file contains:

```
Summarize and review the following patch:
```

### GUI Client

```bash
./gui.py
```

Browse past conversations and chat interactively with full Markdown rendering and syntax
highlighting.

- **Resizable panes** — drag the separators between panels to adjust layout
- **Sortable conversation list** — click the column header to toggle sort order
- **Keyboard shortcuts** — `Enter` to send, `Shift+Enter` for a new line

### Other Tools

- **`whisper.py`** — transcribe audio using OpenAI's Whisper API
- **`dale.py`** — generate images using DALL-E 3

## Development

Format, lint, and test with:

```bash
make format
make lint
make test
```

Run a single test suite:

```bash
python -m pytest tests/e2e_test.py::TestBatchMode -v
```

Run a single test case:

```bash
python -m pytest tests/e2e_test.py::TestBatchMode::test_batch_basic -v
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## Support

If you encounter any issues or have any questions, please open an issue on GitHub.
