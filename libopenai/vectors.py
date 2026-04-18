import sys
import time

from .auth import initialize_client


class Vectors:
    def __init__(self, client=None):
        self.client = initialize_client(client)

    def create_vector_store(self, name):
        """Create a new vector store and return its ID."""
        vs = self.client.vector_stores.create(name=name)
        return vs.id

    def wait_for_vector_store(self, vs_id):
        """Block until a vector store has finished indexing."""
        print("Processing...", end="", file=sys.stderr, flush=True)
        while True:
            vs = self.client.vector_stores.retrieve(vs_id)
            if vs.status == "completed":
                break
            print(".", end="", file=sys.stderr, flush=True)
            time.sleep(1)
        print(" done.", file=sys.stderr)

    def delete_vector_store(self, vs_id):
        """Delete a vector store by ID."""
        print(f"Deleting {vs_id}...", end="", file=sys.stderr, flush=True)
        self.client.vector_stores.delete(vs_id)
        print(" done.", file=sys.stderr)

    def list_vector_stores(self):
        """Return list of (id, name, status, created_at) tuples for vector stores."""
        return [
            (vs.id, vs.name or "", vs.status, vs.created_at)
            for vs in self.client.vector_stores.list().data
        ]

    def list_vector_store_files(self, vs_id):
        """Return list of (id, status, created_at) tuples for files in a vector store."""
        return [
            (f.id, f.status, f.created_at)
            for f in self.client.vector_stores.files.list(vector_store_id=vs_id).data
        ]

    def add_vector_store_file(self, vs_id, file_id):
        """Add a file to a vector store."""
        self.client.vector_stores.files.create(vector_store_id=vs_id, file_id=file_id)

    def delete_vector_store_file(self, vs_id, file_id):
        """Remove a file from a vector store."""
        print(f"Deleting {file_id}...", end="", file=sys.stderr, flush=True)
        self.client.vector_stores.files.delete(vector_store_id=vs_id, file_id=file_id)
        print(" done.", file=sys.stderr)
