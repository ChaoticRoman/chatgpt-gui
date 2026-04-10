import pytest

import core


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Give each test its own DATA_DIRECTORY.

    Prevents cross-test JSON file pollution when tests run in parallel:
    - monkeypatch.setenv propagates to child subprocesses (cli.py reads the env var)
    - monkeypatch.setattr patches the already-imported module object for in-process tests
    Both are restored automatically after each test.
    """
    monkeypatch.setenv("CHATGPT_GUI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(core, "DATA_DIRECTORY", tmp_path)
    yield
