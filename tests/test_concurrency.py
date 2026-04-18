from unittest.mock import patch
from datetime import datetime

import libopenai.core as core_module


class TestConcurrency:
    """Tests verifying safe parallel execution."""

    def test_concurrent_sessions_have_unique_export_files(self):
        """Two GptCore instances created at the same second must not share a JSON export path."""

        # Freeze time so both instances see the exact same timestamp — exposes the collision.
        fixed = datetime(2026, 4, 10, 12, 0, 0)
        with patch("libopenai.core.dt") as mock_dt, patch("openai.OpenAI"):
            mock_dt.now.return_value = fixed
            c1 = core_module.GptCore()
            c2 = core_module.GptCore()

        assert c1.file
        assert c1.file != c2.file
