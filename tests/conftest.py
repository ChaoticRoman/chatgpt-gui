import pytest

from core import DATA_DIRECTORY


@pytest.fixture(autouse=True)
def cleanup_conversation_files():
    """Remove conversation files created during a test."""
    before = set(DATA_DIRECTORY.glob("*.json"))
    yield
    for f in set(DATA_DIRECTORY.glob("*.json")) - before:
        f.unlink()
