import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
import json
import sys
from datetime import datetime as dt
from pprint import pprint

import openai

# Best in non-agentic coding per https://livebench.ai/ (2026-01-08)
DEFAULT_MODEL = "gpt-5.4"

# Prices in USD, source: https://openai.com/api/pricing/
USD_PER_INPUT_TOKEN = {
    "o1": 15e-6,
    "o3-pro": 20e-6,
    "o3-mini": 1.1e-6,
    "o4-mini": 1.1e-6,
    "gpt-5": 1.25e-6,
    "gpt-5.1": 1.25e-6,
    "gpt-5.2": 1.75e-6,
    "gpt-5.2-codex": 1.75e-6,
    "gpt-5.3-codex": 1.75e-6,
    "gpt-5.4": 2.5e-6,
    "gpt-5.4-pro": 30e-6,
}
USD_PER_OUTPUT_TOKEN = {
    "o1": 60e-6,
    "o3-pro": 80e-6,
    "o3-mini": 4.4e-6,
    "o4-mini": 4.4e-6,
    "gpt-5": 10e-6,
    "gpt-5.1": 10e-6,
    "gpt-5.2": 14e-6,
    "gpt-5.2-codex": 14e-6,
    "gpt-5.3-codex": 14e-6,
    "gpt-5.4": 15e-6,
    "gpt-5.4-pro": 180e-6,
}
assert set(USD_PER_INPUT_TOKEN.keys()) == set(USD_PER_OUTPUT_TOKEN.keys())

USD_PER_WEB_SEARCH_CALL = 0.01

DATA_DIRECTORY = Path(
    os.environ.get("CHATGPT_GUI_DATA_DIR", Path.home() / ".chatgpt-gui")
).expanduser()


def load_key():
    if "OPENAI_API_KEY" not in os.environ:
        api_key_path = os.path.join(os.path.dirname(__file__), ".api_key")
        with open(api_key_path, "r") as f:
            os.environ["OPENAI_API_KEY"] = f.read().strip()


def _extract_sources(response):
    """Extract web search sources from a response."""
    sources = []
    seen_urls = set()
    for item in response.output:
        if getattr(item, "type", None) == "web_search_call":
            action = getattr(item, "action", None)
            if action:
                for source in getattr(action, "sources", []):
                    url = getattr(source, "url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        sources.append(
                            {
                                "title": getattr(source, "title", url),
                                "url": url,
                            }
                        )
    return sources


class GptCore:
    """
    A class to interact with OpenAI's GPT-4 model.

    Attributes
    ----------
    input : function
        a function to get user input, takes no arguments, returns str or None
    output : function
        a function to output the model's response and info, takes str and Info
        object, returns None

    Methods
    -------
    main():
        The main loop to interact with the model.
    """

    def __init__(self, input, output, model, web_search=False, debug=False):
        self.input = input
        self.output = output
        self.model = model
        self.web_search = web_search
        self.debug = debug

        self.messages = []

        timestamp = dt.now().replace(microsecond=0).isoformat()
        self.conversation_id = f"{timestamp}-{uuid.uuid4().hex[:6]}"
        os.makedirs(DATA_DIRECTORY, exist_ok=True)
        self.file = DATA_DIRECTORY / f"{self.conversation_id}.json"

        self.client = openai.OpenAI()

    def _compute_price(self, input_tokens, output_tokens, web_search_calls=0):
        if self.model in USD_PER_INPUT_TOKEN and self.model in USD_PER_OUTPUT_TOKEN:
            return (
                USD_PER_INPUT_TOKEN[self.model] * input_tokens
                + USD_PER_OUTPUT_TOKEN[self.model] * output_tokens
                + USD_PER_WEB_SEARCH_CALL * web_search_calls
            )
        return None

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
        self.client.files.delete(file_id)

    def _setup_vector_store(self, file_paths):
        """Upload files to a new vector store and wait for processing to complete."""
        vector_store = self.client.vector_stores.create(name=self.conversation_id)
        self._vector_store_id = vector_store.id
        if os.environ.get("CHATGPT_CLI_LOG_UPLOAD_IDS"):
            print(f"vector_store:{vector_store.id}", file=sys.stderr)
        for path in file_paths:
            file_id = self.upload_file(path, "assistants")
            self._vector_files.append((Path(path).name, file_id))
            self.add_vector_store_file(vector_store.id, file_id)
        print("Processing...", end="", file=sys.stderr, flush=True)
        while True:
            vs = self.client.vector_stores.retrieve(vector_store.id)
            if vs.status == "completed":
                break
            print(".", end="", file=sys.stderr, flush=True)
            time.sleep(2)
        print(" done.", file=sys.stderr)

    def _teardown_vector_store(self):
        """Delete the vector store and its files, printing progress."""
        if self._vector_store_id:
            print("Deleting vector store...", end="", file=sys.stderr, flush=True)
            self.delete_vector_store(self._vector_store_id)
            print(" done.", file=sys.stderr)
            for name, file_id in self._vector_files:
                print(f"Deleting {name}...", end="", file=sys.stderr, flush=True)
                self.delete_file(file_id)
                print(" done.", file=sys.stderr)

    def _teardown(self):
        """Delete all uploaded files and the vector store."""
        for name, file_id in self._images + self._files:
            print(f"Deleting {name}...", end="", file=sys.stderr, flush=True)
            self.delete_file(file_id)
            print(" done.", file=sys.stderr)
        self._teardown_vector_store()

    def send(self, prompt, image_path=None, file_paths=None):
        """Send a message and get response. Returns (content, Info)."""
        content = []
        if image_path:
            name = Path(image_path).name
            file_id = self.upload_file(image_path, "vision")
            self._images.append((name, file_id))
            content.append({"type": "input_image", "file_id": file_id})
        for path in file_paths or []:
            name = Path(path).name
            file_id = self.upload_file(path, "user_data")
            self._files.append((name, file_id))
            content.append({"type": "input_file", "file_id": file_id})
        content.append({"type": "input_text", "text": prompt})
        self.messages.append({"role": "user", "content": content})

        tools = []
        includes = []
        if self.web_search:
            tools.append({"type": "web_search"})
            includes.append("web_search_call.action.sources")
        if self._vector_store_id:
            tools.append(
                {"type": "file_search", "vector_store_ids": [self._vector_store_id]}
            )

        kwargs = dict(model=self.model, input=self.messages)
        if tools:
            kwargs["tools"] = tools
        if includes:
            kwargs["include"] = includes

        response = self.client.responses.create(**kwargs)  # pyright: ignore

        if self.debug:
            pprint(response.to_dict(), stream=sys.stderr)

        content = (response.output_text or "").strip()
        self.messages.append({"role": "assistant", "content": content})

        if self.web_search:
            sources = _extract_sources(response)
            if sources:
                content += "\n\n**Sources:**\n" + "\n".join(
                    f"- [{s['title']}]({s['url']})" for s in sources
                )
        serialized = [dict(m) for m in self.messages]
        with open(self.file, "w") as f:
            json.dump(serialized, f, sort_keys=True, indent=4)

        usage = response.usage
        input_tokens, output_tokens = usage.input_tokens, usage.output_tokens
        web_search_calls = sum(
            1
            for item in response.output
            if getattr(item, "type", None) == "web_search_call"
        )
        step_price = self._compute_price(input_tokens, output_tokens, web_search_calls)

        return content, Info(input_tokens, output_tokens, web_search_calls, step_price)

    def main(self, image_path=None, file_paths=None, vectorize_file_paths=None):
        self._images = []
        self._files = []
        self._vector_store_id = None
        self._vector_files = []
        price = 0.0
        total_web_search_calls = 0
        try:
            if vectorize_file_paths:
                self._setup_vector_store(vectorize_file_paths)
            while prompt := self.input():
                content, info = self.send(
                    prompt, image_path=image_path, file_paths=file_paths
                )
                image_path = None  # only attach files to the first message
                file_paths = None
                if price is not None and info.price is not None:
                    price += info.price
                else:
                    price = None
                total_web_search_calls += info.web_search_calls
                self.output(
                    content,
                    Info(
                        info.input_tokens,
                        info.output_tokens,
                        total_web_search_calls,
                        price,
                    ),
                )
        finally:
            self._teardown()

    def one_shot(self, image_path=None, file_paths=None, vectorize_file_paths=None):
        self._images = []
        self._files = []
        self._vector_store_id = None
        self._vector_files = []
        prompt = self.input()
        if not prompt:
            return
        try:
            if vectorize_file_paths:
                self._setup_vector_store(vectorize_file_paths)
            content, info = self.send(
                prompt, image_path=image_path, file_paths=file_paths
            )
            self.output(content, info)
        finally:
            self._teardown()

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

    def create_vector_store(self, name):
        """Create a new vector store and return its ID."""
        vs = self.client.vector_stores.create(name=name)
        return vs.id

    def delete_vector_store(self, vs_id):
        """Delete a vector store by ID."""
        self.client.vector_stores.delete(vs_id)

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
        self.client.vector_stores.files.delete(vector_store_id=vs_id, file_id=file_id)

    def list_models(self):
        return sorted([m["id"] for m in self.client.models.list().to_dict()["data"]])  # type: ignore


@dataclass
class Info:
    """
    A class representing the information about the interaction with the model.

    Attributes
    ----------
    input_tokens : int
        the number of tokens in the input
    output_tokens : int
        the number of tokens in the output
    web_search_calls : int
        the number of web search calls made
    price : float | None
        the total price of the interaction
    """

    input_tokens: int
    output_tokens: int
    web_search_calls: int
    price: float | None

    def __repr__(self):
        price_repr = f"{self.price:.3f} USD" if self.price is not None else "N/A"
        parts = [
            f"Input tokens: {self.input_tokens}",
            f"Output tokens: {self.output_tokens}",
        ]
        if self.web_search_calls:
            parts.append(f"Web searches: {self.web_search_calls}")
        parts.append(f"Total price: {price_repr}")
        return ", ".join(parts)
