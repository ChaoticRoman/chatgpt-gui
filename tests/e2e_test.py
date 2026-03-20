#!/usr/bin/env python3
"""E2E tests for the CLI application.

These tests call the real OpenAI API, so OPENAI_API_KEY must be set.
Uses a cheap model with very short prompts to minimize cost.
"""

import os
import subprocess
import sys
import tempfile

import pytest

CLI = os.path.join(os.path.dirname(__file__), "..", "cli.py")
TEST_MODEL = "gpt-5-nano"


def run_cli(stdin_text, extra_args=None, timeout=30, model=TEST_MODEL):
    """Run cli.py with given stdin and return (stdout, stderr, returncode)."""
    cmd = [sys.executable, CLI, "-M", model]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.stderr, result.returncode


def get_responses(stdout):
    return [
        stripped
        for line in stdout.split("\n")
        if (stripped := line.replace("> ", ""))
        and not line.startswith("Input tokens: ")
    ]


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
        assert "Input tokens" not in stdout

    def test_exit_exit(self):
        stdout, stderr, rc = run_cli("exit\n")
        assert rc == 0
        assert "Input tokens" not in stdout


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
        assert get_responses(stdout)[1].lower() == "banana"

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
        assert get_responses(stdout)[1] == "Zephyrine"


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
    """Test the --prepend flag that prepends file content to the first message."""

    def test_prepend_adds_context(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("The password is 'swordfish'.")
            f.flush()
            try:
                stdin_text = "What is the password? Reply with just the word.\n"
                stdout, stderr, rc = run_cli(
                    stdin_text,
                    extra_args=["-b", "-p", f.name],
                )
                assert rc == 0
                assert get_responses(stdout)[0] == "swordfish"
            finally:
                os.unlink(f.name)

    def test_prepend_only_first_turn(self):
        """Prepend should only apply to the first message."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("CONTEXT: The color is red. I am mentioning Peter as well.")
            f.flush()
            try:
                stdin_text = (
                    "What color did the context mention? Reply with just the color.\n"
                    "How many times did I mention Peter before? Reply with just number.\n"
                    "q\n"
                )
                stdout, stderr, rc = run_cli(
                    stdin_text,
                    extra_args=["-p", f.name],
                )
                assert rc == 0
                responses = get_responses(stdout)
                assert responses[0].lower() == "red"
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
        stdin_text = "Count non-empty lines in this prompt.\nReply with just the count.\nSEND\nq\n"
        stdout, stderr, rc = run_cli(stdin_text, extra_args=["-m"])
        assert rc == 0
        assert get_responses(stdout)[0] == "2"


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
        """Verify pricing info appears in interactive mode output."""
        stdout, stderr, rc = run_cli("Say ok.\nq\n")
        assert rc == 0
        assert "Input tokens:" in stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
