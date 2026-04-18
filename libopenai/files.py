import os
import sys
from pathlib import Path

from .auth import initialize_client


class Files:
    def __init__(self, client=None):
        self.client = initialize_client(client)

    def list_files(self):
        """Return list of (id, filename, bytes, purpose, created_at, expires_at) tuples."""
        return [
            (
                f.id,
                f.filename,
                f.bytes,
                f.purpose,
                f.created_at,
                getattr(f, "expires_at", None),
            )
            for f in self.client.files.list().data
        ]

    def upload_file(self, path, purpose):
        """Upload a file and return the file ID."""
        assert purpose in ("vision", "user_data", "assistants")
        print(f"Uploading {Path(path).name}...", end="", file=sys.stderr, flush=True)
        with open(path, "rb") as f:
            file = self.client.files.create(file=f, purpose=purpose)
        print(" done.", file=sys.stderr)
        if os.environ.get("CHATGPT_CLI_LOG_UPLOAD_IDS"):
            print(f"uploaded:{file.id}", file=sys.stderr)
        return file.id

    def delete_file(self, file_id):
        """Delete a previously uploaded file."""
        print(f"Deleting {file_id}...", end="", file=sys.stderr, flush=True)
        self.client.files.delete(file_id)
        print(" done.", file=sys.stderr)
