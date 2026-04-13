# OpenAI API Clients

Python CLI and GUI clients to interact with OpenAI's API.

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

Expects an `OPENAI_API_KEY` environment variable, or a `.api_key` file in the repo
directory as a fallback. The filename is in `.gitignore` already.

Conversations are automatically saved as JSON files in `~/.chatgpt-gui/`. Override the
location with the `CHATGPT_GUI_DATA_DIR` environment variable:

```bash
export CHATGPT_GUI_DATA_DIR=/path/to/your/data
```

### CLI Client

```bash
./cli.py
```

Quit with `q`, `x`, `exit`, `quit`, `Ctrl+C`, or `Ctrl+D`.

#### Options

| Flag | Description |
|------|-------------|
| `-m`, `--multiline` | Multiline input mode — type your message, then enter `SEND` to submit |
| `-b`, `--batch-mode` | Non-interactive mode for pipes and redirection |
| `-M`, `--model` | Select a specific model |
| `-w`, `--web-search` | Enable web search with source extraction |
| `-p`, `--prepend` | Prepend a string (followed by two newlines) to the first message |
| `-pf`, `--prepend-file` | Prepend a file's contents to the first message |
| `-i`, `--image` | Image file to include |
| `-f`, `--file` | Document(s) to include |
| `-vf`, `--vectorize-file` | Document(s) to upload to a vector store for semantic file search |
| `-vs`, `--vector-store` | Use a pre-existing vector store by ID for semantic file search |
| `-r`, `--rich` | Render Markdown with rich text formatting in the terminal |
| `-d`, `--debug` | Pretty-print raw API responses to stderr |
| `-l`, `--list-known` | List models with known pricing |
| `-L`, `--list-all` | List all available models |

#### File Management

```bash
./cli.py files list                   # list uploaded files
./cli.py files add report.pdf         # upload a file, prints the file ID
./cli.py files delete FILE_ID ...     # delete one or more files by ID
./cli.py files purge                  # delete all uploaded files
```

#### Vector Store Management

```bash
./cli.py vectors list                                           # list vector stores
./cli.py vectors create NAME                                    # create an empty vector store, prints the vector store ID
./cli.py vectors create NAME doc1.pdf doc2.pdf                  # create a vector store, upload and index files, prints the ID
./cli.py vectors create NAME doc.pdf --no-wait                  # same but return immediately without waiting for indexing
./cli.py vectors delete VECTOR_STORE_ID                         # delete a vector store
./cli.py vectors purge                                          # delete all vector stores
./cli.py vectors files list VECTOR_STORE_ID                     # list files in a vector store
./cli.py vectors files add VECTOR_STORE_ID file1.pdf ...        # upload and add file(s) to a vector store
./cli.py vectors files add-id VECTOR_STORE_ID FILE_ID ...       # add already-uploaded file(s) to a vector store by ID
./cli.py vectors files delete VECTOR_STORE_ID FILE_ID ...       # remove one or more files from a vector store
```

#### Batch Mode Examples

```bash
./cli.py -b <<< "Tell a joke" > joke.txt
./cli.py -b < prompt.txt > output.txt
./cli.py -b --prepend-file summarize_prompt.txt < article.txt
./cli.py -b -p "Summarize the following text:" < article.txt
./cli.py -b -f report.pdf <<< "Summarize this document"
./cli.py -b -f cv.pdf job.pdf <<< "Is this candidate a good fit?"
./cli.py -b -vf contracts/*.pdf <<< "Which contracts mention arbitration?"
./cli.py -vf docs/*.pdf  # interactive Q&A session across a document collection
./cli.py -vs vs_abc123   # interactive Q&A using a pre-existing vector store
```

The tool is quite powerful with `guake` drop-down terminal and alias like this:

```bash
alias gpt='$HOME/projects/chatgpt-gui/cli.py'
```

More useful example to review patch of PR for currently checked out branch in the current
directory (expects `gh` client installed):

```bash
alias review='gh pr diff --patch | gpt -b -pf $HOME/.pr-review'
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
- **`dale.py`** — generate images using DALL-E 3 (`./dale.py "prompt" [-n N] [-j N]`)

## Development

Install test dependencies:

```bash
pip install pytest pytest-xdist
```

Format, lint, and test with:

```bash
make format
make lint
make test   # sequential
make xtest  # parallel (16 workers)
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
