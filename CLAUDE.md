# Agents

Read README.md.

## Project overview

Python CLI and GUI clients for OpenAI's ChatGPT. Key files:

- `core.py` — shared library: `GptCore` class, pricing dicts, `Info` dataclass
- `cli.py` — CLI client with interactive, batch, multiline, web-search, debug modes
- `gui.py` — Tkinter GUI client with conversation browser

## Development workflow

### Formatting and linting

This project uses **ruff** with default config (no pyproject.toml/ruff.toml).

```bash
make format   # ruff format .
make lint     # ruff check . && ruff format --diff .
```

**Always run `make format` then `make lint` after editing Python files.**
Fix any lint errors before committing. CI runs ruff on every PR.

### Testing

```bash
make test   # python -m pytest tests/ -v
```

Tests live in `tests/`. The test suite (`tests/e2e_test.py`) calls the **real OpenAI API** — every test run costs money. Be mindful:

- **Do not run the full suite speculatively.** Only run tests when you have a reason to believe something changed that could break them.
- **Run specific tests** when possible: `python -m pytest tests/e2e_test.py::TestClassName::test_name -v`

### Before committing

1. `make format`
2. `make lint` — must pass cleanly

## Code conventions

- No `pyproject.toml` or `setup.py` — this is a flat script-based repo, not a package.
- Imports: stdlib first, then third-party (`openai`, `rich`, etc.), then local (`core`). Ruff enforces this.
- `GptCore` uses an input/output callback pattern — `input()` returns a string or `None`, `output(msg, info)` displays results.

## When adding a new CLI flag

1. Add `argparse` argument in `cli.py:main()`.
2. Wire it through to `GptCore` or handle it in `cli.py`.
3. Update the options table in `README.md`.
4. Consider whether the flag conflicts with list options (`-l`, `-L`, `-lf`) — see the mutual exclusion check in `cli.py`.
5. Add a test in `tests/e2e_test.py` if the flag affects API interaction.

## When fixing a bug or adding a feature

1. Read the relevant code first.
2. Make the change.
3. Update `README.md` if the change is user-visible (new flag, changed behavior, new tool).
4. `make format && make lint`
5. Run relevant tests if applicable (not for cosmetic/doc changes).

## Worktrees

You may be running in a git worktree (e.g. `.claude/worktrees/...`). Your cwd is already set correctly — run `git`, `gh`, and other commands directly without `-C` or `cd`.

## Things to avoid

- Don't add type stubs, docstrings, or comments to code you didn't change.
- Don't restructure into a package — the flat layout is intentional.
- Don't add dependencies without strong justification.
- Don't run `make test` for changes that don't touch core logic — it costs real money.
- Don't modify `tests/conftest.py` cleanup logic without understanding side effects.
