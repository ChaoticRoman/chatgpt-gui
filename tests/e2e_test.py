#!/usr/bin/env python3
"""E2E tests for the CLI application.

These tests call the real OpenAI API, so OPENAI_API_KEY must be set.
Uses a cheap model with very short prompts to minimize cost.
"""

import os
import subprocess
import sys
import tempfile
import time

import pytest

from core import USD_PER_INPUT_TOKEN

CLI = os.path.join(os.path.dirname(__file__), "..", "cli.py")
TEST_MODEL = "gpt-5.4-mini"


def run_cli(
    stdin_text,
    extra_args=None,
    timeout=60,
    model: str | None = TEST_MODEL,
    extra_env=None,
):
    """Run cli.py with given stdin and return (stdout, stderr, returncode)."""
    cmd = [sys.executable, CLI]
    if model:
        cmd.extend(["-M", model])
    if extra_args:
        cmd.extend(extra_args)
    env = {**os.environ, **(extra_env or {})}
    result = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return result.stdout, result.stderr, result.returncode


def get_responses(stdout):
    """Get response from cli output as list of lines, removing spurious ">"s
    from prefilled input, lowercased for convenience."""
    return [
        stripped.lower()
        for line in stdout.split("\n")
        if (stripped := line.replace("> ", ""))
    ]


def parse_file_ids(list_files_stdout):
    """Return the set of file IDs from 'files list' output."""
    ids = set()
    for line in list_files_stdout.splitlines():
        first = line.split()[0] if line.split() else ""
        if first.startswith("file-"):
            ids.add(first)
    return ids


def parse_uploaded_ids(stderr):
    """Return file IDs emitted by core when CHATGPT_CLI_LOG_UPLOAD_IDS is set."""
    ids = set()
    for line in stderr.splitlines():
        if line.startswith("uploaded:"):
            ids.add(line.split(":", 1)[1])
    return ids


def parse_logged_vs_ids(stderr):
    """Return vector store IDs emitted by core when CHATGPT_CLI_LOG_UPLOAD_IDS is set."""
    ids = set()
    for line in stderr.splitlines():
        if line.startswith("vector_store:"):
            ids.add(line.split(":", 1)[1])
    return ids


def parse_listed_vs_ids(list_vs_stdout):
    """Return the set of vector store IDs from vectors list output."""
    ids = set()
    for line in list_vs_stdout.splitlines():
        first = line.split()[0] if line.split() else ""
        if first.startswith("vs_"):
            ids.add(first)
    return ids


class TestSingleTurn:
    """Single-turn conversations: one prompt then exit."""

    def test_basic_response(self):
        stdout, stderr, rc = run_cli("What is 2+2? Answer with just the number.\n")
        assert rc == 0
        assert get_responses(stdout)[0] == "4"

    def test_exit_q(self):
        """Typing 'q' should exit cleanly with no API call."""
        stdout, stderr, rc = run_cli("q\n")
        assert rc == 0
        # No response content expected
        assert "Input tokens" not in stderr

    def test_exit_exit(self):
        stdout, stderr, rc = run_cli("exit\n")
        assert rc == 0
        assert "Input tokens" not in stderr


class TestMultiturn:
    """Multi-turn conversations that rely on conversation history."""

    def test_context_carries_over(self):
        """Ask the model to remember a secret word, then ask for it back."""
        stdin_text = (
            "Our word is 'banana'. Acknowledged?\n"
            "What is our word? Reply with just the word.\n"
            "q\n"
        )
        stdout, stderr, rc = run_cli(stdin_text)
        assert rc == 0
        assert get_responses(stdout)[1] == "banana"

    def test_arithmetic_context(self):
        """Build up context across turns with simple arithmetic."""
        stdin_text = (
            "Remember: x=7. Just reply OK.\n"
            "Remember: y=3. Just reply OK.\n"
            "What is x+y? Reply with just the number.\n"
            "q\n"
        )
        stdout, stderr, rc = run_cli(stdin_text)
        assert rc == 0
        assert get_responses(stdout)[2] == "10"

    def test_name_recall(self):
        """Tell the model a name and ask it back in the next turn."""
        stdin_text = (
            "My name is Zephyrine. Just say hello.\n"
            "What is my name? Reply with just the name.\n"
            "q\n"
        )
        stdout, stderr, rc = run_cli(stdin_text)
        assert rc == 0
        assert get_responses(stdout)[1] == "zephyrine"


class TestBatchMode:
    """Batch mode: reads stdin, prints response to stdout, info to stderr."""

    def test_batch_basic(self):
        stdout, stderr, rc = run_cli(
            "What is 3+5? Answer with just the number.",
            extra_args=["-b"],
        )
        assert rc == 0
        assert get_responses(stdout)[0] == "8"
        # Pricing info goes to stderr in batch mode
        assert "Input tokens" in stderr

    def test_batch_with_pipe_content(self):
        """Simulate piping content, e.g. echo "text" | cli.py -b"""
        stdout, stderr, rc = run_cli(
            "Count the words in: 'one two three'. Reply with just the number.",
            extra_args=["-b"],
        )
        assert rc == 0
        assert get_responses(stdout)[0] == "3"


class TestPrepend:
    """Test the --prepend and --prepend-file flags."""

    def test_prepend_adds_context(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("The password is 'swordfish'.")
            f.flush()
            try:
                stdin_text = "What is the password? Reply with just the word.\n"
                stdout, stderr, rc = run_cli(
                    stdin_text,
                    extra_args=["-b", "-pf", f.name],
                )
                assert rc == 0
                assert get_responses(stdout)[0] == "swordfish"
            finally:
                os.unlink(f.name)

    def test_prepend_string_adds_context(self):
        stdin_text = "What is my name? Reply with just the name.\n"
        stdout, stderr, rc = run_cli(
            stdin_text,
            extra_args=["-b", "-p", "My name is Gandalf."],
        )
        assert rc == 0
        assert get_responses(stdout)[0] == "gandalf"

    def test_prepend_only_first_turn(self):
        """Prepend should only apply to the first message."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("CONTEXT: The color is red. I am mentioning Peter as well.")
            f.flush()
            try:
                stdin_text = (
                    "What color did the context mention? Reply with just the color.\n"
                    "How many times did the context mention Peter before? Reply with just number.\n"
                    "q\n"
                )
                stdout, stderr, rc = run_cli(
                    stdin_text,
                    extra_args=["-pf", f.name],
                )
                assert rc == 0
                responses = get_responses(stdout)
                assert responses[0] == "red"
                assert responses[1] == "1"
            finally:
                os.unlink(f.name)


class TestMultilineInput:
    """Test multiline input mode where SEND terminates input."""

    def test_multiline_basic(self):
        # In multiline mode, lines are collected until "SEND"
        stdin_text = "What is\n2+2?\nAnswer with just the number.\nSEND\nq\n"
        stdout, stderr, rc = run_cli(stdin_text, extra_args=["-m"])
        assert rc == 0
        assert get_responses(stdout)[0] == "4"

    def test_multiline_preserves_newlines(self):
        """Multiline input should preserve newlines in the prompt."""
        stdin_text = "Just making line.\n\nAnd another.\n\nCount non-empty lines in this prompt. Reply with just the count.\nSEND\nq\n"
        stdout, stderr, rc = run_cli(stdin_text, extra_args=["-m"])
        assert rc == 0
        assert int(get_responses(stdout)[0]) > 1


class TestModelFlag:
    """Test the -M flag for model selection."""

    def test_invalid_model(self):
        """Prompting with invalid model name should fail."""
        stdout, stderr, rc = run_cli(
            "Say hi.\n",
            model="foo",
        )
        assert "model_not_found" in stderr
        assert rc == 1


class TestWebSearch:
    """Test web search functionality. Limited to one test due to API cost."""

    def test_web_search_batch(self):
        """Web search should return a response with sources and search count."""
        stdout, stderr, rc = run_cli(
            "What is the current population of Iceland? Just the number.",
            extra_args=["-b", "-w"],
        )
        assert rc == 0
        assert len(stdout.strip()) > 0
        assert "Web searches:" in stderr


class TestDebugMode:
    """Test debug mode that prints raw responses to stderr."""

    def test_debug_prints_to_stderr(self):
        """Debug flag should print raw response dict to stderr."""
        stdout, stderr, rc = run_cli(
            "Say ok.\nq\n",
            extra_args=["-d"],
        )
        assert rc == 0
        assert "output_text" in stderr

    def test_debug_batch_mode(self):
        """Debug flag should work in batch mode too."""
        stdout, stderr, rc = run_cli(
            "Say ok.",
            extra_args=["-b", "-d"],
        )
        assert rc == 0
        assert "output_text" in stderr
        assert get_responses(stdout)[0]


class TestEdgeCases:
    """Edge cases and robustness tests."""

    def test_empty_input_exits(self):
        """EOF on empty input should exit cleanly."""
        stdout, stderr, rc = run_cli("")
        assert rc == 0

    def test_unicode_input(self):
        stdout, stderr, rc = run_cli(
            "What letter comes after \u00e9 in the French alphabet? Just the letter.\n"
        )
        assert rc == 0
        # Just verify no crash with unicode

    def test_very_short_prompt(self):
        """Single character prompt."""
        stdout, stderr, rc = run_cli(
            "Hi\nq\n",
        )
        assert rc == 0
        assert len(stdout.strip()) > 0

    def test_pricing_info_displayed(self):
        """Verify pricing info appears in stderr."""
        stdout, stderr, rc = run_cli("Say ok.\nq\n")
        assert rc == 0
        assert "Input tokens:" in stderr


def assert_files_cleaned_up(stderr):
    """Assert that all uploaded files (logged in stderr) have been deleted."""
    uploaded = parse_uploaded_ids(stderr)
    assert uploaded, "Expected files to be uploaded"
    current_files, _, rc = run_cli(None, extra_args=["files", "list"], model=None)
    assert rc == 0
    assert not (uploaded & parse_file_ids(current_files)), (
        f"Files not cleaned up: {uploaded}"
    )


class TestImageInput:
    """Test image input. Limited to one test due to API cost."""

    def test_image_input(self):
        """There is a word on the image, it should be recognized and deleted."""
        stdout, stderr, rc = run_cli(
            "What is the word on picture. Reply the word only.",
            extra_args=["-b", "-i", "tests/test.png"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
        )
        assert rc == 0
        assert "tag" in get_responses(stdout)[0]
        assert_files_cleaned_up(stderr)

    def test_image_multiturn(self):
        """Ask about image background in one turn, then the text in the next."""
        stdin_text = (
            "What is the background color? Reply just the color.\n"
            "What word is on the image? Reply the word only.\n"
            "q\n"
        )
        stdout, stderr, rc = run_cli(
            stdin_text,
            extra_args=["-i", "tests/test.png"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
        )
        assert rc == 0
        responses = get_responses(stdout)
        assert responses[0] == "white"
        assert "tag" in responses[1]
        assert_files_cleaned_up(stderr)


class TestFileInput:
    """Test PDF document input."""

    def _assert_cleanup(self, stderr):
        assert_files_cleaned_up(stderr)

    def test_single_pdf(self):
        """A single PDF should be read and deleted after use."""
        stdout, stderr, rc = run_cli(
            "What fruit is mentioned? Reply with just the fruit.",
            extra_args=["-b", "-f", "tests/test1.pdf"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
        )
        assert rc == 0
        assert "orange" in get_responses(stdout)[0]

        uploaded = parse_uploaded_ids(stderr)
        assert len(uploaded) == 1, f"Expected 2 uploaded files, got: {uploaded}"
        self._assert_cleanup(stderr)

    def test_multiple_pdfs(self):
        """Multiple PDFs should all be read and deleted after use."""
        stdout, stderr, rc = run_cli(
            "What fruits and what colors are mentioned? Reply with just fruits and colors.",
            extra_args=["-b", "-f", "tests/test1.pdf", "tests/test2.pdf"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
        )
        assert rc == 0
        response = get_responses(stdout)[0]
        assert "orange" in response
        assert "avocado" in response
        assert "red" in response
        assert "brown" in response

        uploaded = parse_uploaded_ids(stderr)
        assert len(uploaded) == 2, f"Expected 2 uploaded files, got: {uploaded}"
        self._assert_cleanup(stderr)

    def test_available_across_turns(self):
        """Vector store should be searchable on every turn, not just the first."""
        stdin_text = (
            "What fruit do documents mention? Reply just fruit.\n"
            "And what color are there? Reply just color.\n"
            "q\n"
        )
        stdout, stderr, rc = run_cli(
            stdin_text,
            extra_args=["-f", "tests/test1.pdf"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
            timeout=180,
        )
        assert rc == 0
        responses = get_responses(stdout)
        assert "orange" in responses[0]
        assert "red" in responses[1]

        uploaded = parse_uploaded_ids(stderr)
        assert len(uploaded) == 1, f"Expected uploaded file, got: {uploaded}"
        self._assert_cleanup(stderr)


class TestVectorizeFile:
    """Test vectorized file search with -vf/--vectorize-file."""

    def _assert_cleanup(self, stderr):
        uploaded = parse_uploaded_ids(stderr)
        assert uploaded, "Expected files to be uploaded"
        vs_ids = parse_logged_vs_ids(stderr)
        assert vs_ids, "Expected a vector store to be created"

        current_files, _, rc = run_cli(None, extra_args=["files", "list"], model=None)
        assert rc == 0
        assert not (uploaded & parse_file_ids(current_files)), (
            f"Files not cleaned up: {uploaded}"
        )

        current_vs, _, rc = run_cli(None, extra_args=["vectors", "list"], model=None)
        assert rc == 0
        assert not (vs_ids & parse_listed_vs_ids(current_vs)), (
            f"Vector stores not cleaned up: {vs_ids}"
        )

    def test_single_pdf(self):
        """Single PDF vectorized: model can answer and resources are cleaned up."""
        stdout, stderr, rc = run_cli(
            "What fruit is mentioned? Reply with just the fruit.",
            extra_args=["-b", "-vf", "tests/test1.pdf"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
            timeout=120,
        )
        assert rc == 0
        assert get_responses(stdout)[0] == "orange"
        self._assert_cleanup(stderr)

    def test_multiple_pdfs(self):
        """Multiple PDFs vectorized: model can query both and resources are cleaned up."""
        stdout, stderr, rc = run_cli(
            "What fruits are mentioned across all documents? Reply just fruits.",
            extra_args=["-b", "-vf", "tests/test1.pdf", "tests/test2.pdf"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
            timeout=120,
        )
        assert rc == 0
        response = get_responses(stdout)[0]
        assert "orange" in response
        assert "avocado" in response
        self._assert_cleanup(stderr)

    def test_available_across_turns(self):
        """Vector store should be searchable on every turn, not just the first."""
        stdin_text = (
            "What fruits do documents mention? Reply just fruits.\n"
            "And what color are there? Reply just colors.\n"
            "q\n"
        )
        stdout, stderr, rc = run_cli(
            stdin_text,
            extra_args=["-vf", "tests/test1.pdf", "tests/test2.pdf"],
            extra_env={"CHATGPT_CLI_LOG_UPLOAD_IDS": "1"},
            timeout=180,
        )
        assert rc == 0
        responses = get_responses(stdout)
        assert "orange" in responses[0]
        assert "avocado" in responses[0]
        assert "red" in responses[1]
        assert "brown" in responses[1]
        self._assert_cleanup(stderr)


class TestVectorStore:
    """Test -vs/--vector-store: use a pre-existing vector store."""

    def _setup(self):
        """Create a vector store with test1.pdf already indexed; return vs_id."""
        stdout, _, rc = run_cli(
            None,
            extra_args=["vectors", "create", "test-vs-flag", "tests/test1.pdf"],
            model=None,
            timeout=120,
        )
        assert rc == 0
        vs_id = stdout.strip()
        assert vs_id.startswith("vs_")
        return vs_id

    def _teardown(self, vs_id):
        files, _, _ = run_cli(
            None, extra_args=["vectors", "files", "list", vs_id], model=None
        )
        run_cli(None, extra_args=["vectors", "delete", vs_id], model=None)
        for file_id in (
            line.split()[0]
            for line in files.splitlines()
            if line.split() and line.split()[0].startswith("file-")
        ):
            run_cli(None, extra_args=["files", "delete", file_id], model=None)

    def _assert_vs_survives(self, vs_id):
        """Verify the vector store was NOT deleted by the CLI session."""
        current_vs, _, rc = run_cli(None, extra_args=["vectors", "list"], model=None)
        assert rc == 0
        assert vs_id in parse_listed_vs_ids(current_vs), (
            f"Vector store {vs_id} was deleted but should have been preserved"
        )

    def test_batch_query(self):
        """Content from a pre-existing vector store is accessible in batch mode."""
        vs_id = self._setup()
        try:
            stdout, _, rc = run_cli(
                "What fruit is mentioned? Reply with just the fruit.",
                extra_args=["-b", "-vs", vs_id],
                timeout=60,
            )
            assert rc == 0
            assert "orange" in get_responses(stdout)[0]
            self._assert_vs_survives(vs_id)
        finally:
            self._teardown(vs_id)

    def test_available_across_turns(self):
        """Pre-existing vector store is searchable across interactive turns."""
        vs_id = self._setup()
        try:
            stdin_text = (
                "What fruit do documents mention? Reply just the fruit.\n"
                "What color is mentioned? Reply just the color.\n"
                "q\n"
            )
            stdout, _, rc = run_cli(
                stdin_text,
                extra_args=["-vs", vs_id],
                timeout=120,
            )
            assert rc == 0
            responses = get_responses(stdout)
            assert "orange" in responses[0]
            assert "red" in responses[1]
            self._assert_vs_survives(vs_id)
        finally:
            self._teardown(vs_id)


class TestVectorsCreate:
    """Test 'vectors create' with file upload and --no-wait."""

    def test_create_with_files_waits_and_is_queryable(self):
        """Creating a VS with files should index them and make content searchable."""
        stdout, _, rc = run_cli(
            None,
            extra_args=["vectors", "create", "test-vs-create", "tests/test1.pdf"],
            model=None,
            timeout=120,
        )
        assert rc == 0
        vs_id = stdout.strip()
        assert vs_id.startswith("vs_")
        try:
            stdout, _, rc = run_cli(
                "What fruit is mentioned? Reply with just the fruit.",
                extra_args=["-b", "-vs", vs_id],
                timeout=60,
            )
            assert rc == 0
            assert "orange" in get_responses(stdout)[0]
        finally:
            files, _, _ = run_cli(
                None, extra_args=["vectors", "files", "list", vs_id], model=None
            )
            run_cli(None, extra_args=["vectors", "delete", vs_id], model=None)
            for file_id in (
                line.split()[0]
                for line in files.splitlines()
                if line.split() and line.split()[0].startswith("file-")
            ):
                run_cli(None, extra_args=["files", "delete", file_id], model=None)

    def test_no_wait_returns_before_completion(self):
        """--no-wait should return the VS ID immediately without blocking."""
        stdout, _, rc = run_cli(
            None,
            extra_args=[
                "vectors",
                "create",
                "test-vs-nowait",
                "tests/test1.pdf",
                "--no-wait",
            ],
            model=None,
            timeout=30,
        )
        assert rc == 0
        vs_id = stdout.strip()
        assert vs_id.startswith("vs_")
        run_cli(None, extra_args=["vectors", "delete", vs_id], model=None)


class TestFilesSubcommand:
    """Test 'files list', 'files add', and 'files delete' subcommands."""

    def test_list_add_delete(self):
        # Upload a file; file ID must appear on stdout
        stdout, _, rc = run_cli(
            None, extra_args=["files", "add", "tests/test1.pdf"], model=None
        )
        assert rc == 0
        file_id = stdout.strip()
        assert file_id

        try:
            # Newly uploaded file must appear in the listing
            stdout, _, rc = run_cli(None, extra_args=["files", "list"], model=None)
            assert rc == 0
            assert file_id in parse_file_ids(stdout)

            # Delete it
            _, _, rc = run_cli(
                None, extra_args=["files", "delete", file_id], model=None
            )
            assert rc == 0

            # Must no longer appear in the listing
            stdout, _, rc = run_cli(None, extra_args=["files", "list"], model=None)
            assert rc == 0
            assert file_id not in parse_file_ids(stdout)
        except Exception:
            run_cli(None, extra_args=["files", "delete", file_id], model=None)
            raise


class TestVectorsSubcommand:
    """Test 'vectors list', 'vectors create', 'vectors delete', and 'vectors files' subcommands."""

    def test_list_create_delete(self):
        # Create a vector store
        stdout, _, rc = run_cli(
            None, extra_args=["vectors", "create", "test-vs"], model=None
        )
        assert rc == 0
        vs_id = stdout.strip()
        assert vs_id.startswith("vs_")

        try:
            time.sleep(5)
            # Newly created store must appear in listing
            stdout, _, rc = run_cli(None, extra_args=["vectors", "list"], model=None)
            assert rc == 0
            assert vs_id in parse_listed_vs_ids(stdout)

            # Delete it
            _, _, rc = run_cli(
                None, extra_args=["vectors", "delete", vs_id], model=None
            )
            assert rc == 0

            # Must no longer appear in listing
            stdout, _, rc = run_cli(None, extra_args=["vectors", "list"], model=None)
            assert rc == 0
            assert vs_id not in parse_listed_vs_ids(stdout)
        except Exception:
            run_cli(None, extra_args=["vectors", "delete", vs_id], model=None)
            raise

    def test_files_add_id_list_delete(self):
        # Upload a file to use
        stdout, _, rc = run_cli(
            None, extra_args=["files", "add", "tests/test1.pdf"], model=None
        )
        assert rc == 0
        file_id = stdout.strip()
        assert file_id.startswith("file-")

        # Create a vector store
        stdout, _, rc = run_cli(
            None, extra_args=["vectors", "create", "test-vs-files"], model=None
        )
        assert rc == 0
        vs_id = stdout.strip()
        assert vs_id.startswith("vs_")

        try:
            # Add file to vector store by ID
            _, _, rc = run_cli(
                None,
                extra_args=["vectors", "files", "add-id", vs_id, file_id],
                model=None,
            )
            assert rc == 0

            time.sleep(5)
            # File must appear in vector store file listing
            stdout, _, rc = run_cli(
                None, extra_args=["vectors", "files", "list", vs_id], model=None
            )
            assert rc == 0
            assert file_id in stdout

            # Remove file from vector store
            _, _, rc = run_cli(
                None,
                extra_args=["vectors", "files", "delete", vs_id, file_id],
                model=None,
            )
            assert rc == 0

            # File must no longer appear in listing
            stdout, _, rc = run_cli(
                None, extra_args=["vectors", "files", "list", vs_id], model=None
            )
            assert rc == 0
            assert file_id not in stdout
        finally:
            run_cli(None, extra_args=["vectors", "delete", vs_id], model=None)
            run_cli(None, extra_args=["files", "delete", file_id], model=None)

    def test_files_add_by_path(self):
        """'vectors files add' uploads a file by path and adds it to the vector store."""
        # Create a vector store
        stdout, _, rc = run_cli(
            None, extra_args=["vectors", "create", "test-vs-add-path"], model=None
        )
        assert rc == 0
        vs_id = stdout.strip()
        assert vs_id.startswith("vs_")

        try:
            # Add file by path (upload + add)
            _, _, rc = run_cli(
                None,
                extra_args=["vectors", "files", "add", vs_id, "tests/test1.pdf"],
                model=None,
                timeout=60,
            )
            assert rc == 0

            time.sleep(5)
            # File must appear in vector store file listing
            stdout, _, rc = run_cli(
                None, extra_args=["vectors", "files", "list", vs_id], model=None
            )
            assert rc == 0
            file_ids = [
                line.split()[0]
                for line in stdout.splitlines()
                if line.split() and line.split()[0].startswith("file-")
            ]
            assert file_ids, "Expected at least one file in vector store"
        finally:
            files, _, _ = run_cli(
                None, extra_args=["vectors", "files", "list", vs_id], model=None
            )
            run_cli(None, extra_args=["vectors", "delete", vs_id], model=None)
            for fid in (
                line.split()[0]
                for line in files.splitlines()
                if line.split() and line.split()[0].startswith("file-")
            ):
                run_cli(None, extra_args=["files", "delete", fid], model=None)


class TestConcurrency:
    """Tests verifying safe parallel execution."""

    def test_concurrent_sessions_have_unique_export_files(self, tmp_path):
        """Two GptCore instances created at the same second must not share a JSON export path."""
        from unittest.mock import patch
        from datetime import datetime
        import core as core_module

        # Freeze time so both instances see the exact same timestamp — exposes the collision.
        fixed = datetime(2026, 4, 10, 12, 0, 0)
        with patch("core.dt") as mock_dt, patch("openai.OpenAI"):
            mock_dt.now.return_value = fixed
            c1 = core_module.GptCore(lambda: None, lambda *a: None, "gpt-5.4-mini")
            c2 = core_module.GptCore(lambda: None, lambda *a: None, "gpt-5.4-mini")

        assert c1.file != c2.file


class TestAllModelsSmokeTest:
    """Smoke test: verify every in-code-priced model can handle a minimal prompt."""

    @pytest.mark.parametrize("model", sorted(USD_PER_INPUT_TOKEN.keys()))
    def test_model_responds(self, model):
        stdout, stderr, rc = run_cli(
            "Say ok.",
            extra_args=["-b"],
            model=model,
            timeout=120,
        )
        assert rc == 0
        assert "ok" in get_responses(stdout)[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
