import os
import uuid
from dataclasses import dataclass
from pathlib import Path
import json
import sys
from datetime import datetime as dt
from pprint import pprint

import openai

# Best in non-agentic coding per https://livebench.ai/ (2026-01-08)
DEFAULT_MODEL = "gpt-5.2-codex"

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
        os.makedirs(DATA_DIRECTORY, exist_ok=True)
        self.file = DATA_DIRECTORY / f"{timestamp}-{uuid.uuid4().hex[:8]}.json"

        self.client = openai.OpenAI()

    def _compute_price(self, input_tokens, output_tokens, web_search_calls=0):
        if self.model in USD_PER_INPUT_TOKEN and self.model in USD_PER_OUTPUT_TOKEN:
            return (
                USD_PER_INPUT_TOKEN[self.model] * input_tokens
                + USD_PER_OUTPUT_TOKEN[self.model] * output_tokens
                + USD_PER_WEB_SEARCH_CALL * web_search_calls
            )
        return None

    def _upload_file(self, path, purpose):
        """Upload a file and return the file ID."""
        assert purpose in ("vision", "user_data")
        with open(path, "rb") as f:
            file = self.client.files.create(file=f, purpose=purpose)
        if os.environ.get("CHATGPT_CLI_LOG_UPLOADS"):
            print(f"uploaded:{file.id}", file=sys.stderr)
        return file.id

    def _delete_file(self, file_id):
        """Delete a previously uploaded file."""
        self.client.files.delete(file_id)

    def send(self, prompt, image_path=None, file_paths=None):
        """Send a message and get response. Returns (content, Info)."""
        content = []
        if image_path:
            self._image_file_id = self._upload_file(image_path, "vision")
            content.append({"type": "input_image", "file_id": self._image_file_id})
        for path in file_paths or []:
            file_id = self._upload_file(path, "user_data")
            self._file_ids.append(file_id)
            content.append({"type": "input_file", "file_id": file_id})
        content.append({"type": "input_text", "text": prompt})
        self.messages.append({"role": "user", "content": content})

        kwargs = dict(model=self.model, input=self.messages)
        if self.web_search:
            kwargs["tools"] = [{"type": "web_search"}]
            kwargs["include"] = ["web_search_call.action.sources"]

        response = self.client.responses.create(**kwargs)

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

    def main(self, image_path=None, file_paths=None):
        self._image_file_id = None
        self._file_ids = []
        price = 0
        total_web_search_calls = 0
        try:
            while prompt := self.input():
                content, info = self.send(
                    prompt, image_path=image_path, file_paths=file_paths
                )
                image_path = None  # only attach files to the first message
                file_paths = None
                if info.price is not None:
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
            if self._image_file_id:
                self._delete_file(self._image_file_id)
            for file_id in self._file_ids:
                self._delete_file(file_id)

    def one_shot(self, image_path=None, file_paths=None):
        self._image_file_id = None
        self._file_ids = []
        prompt = self.input()
        if not prompt:
            return
        try:
            content, info = self.send(
                prompt, image_path=image_path, file_paths=file_paths
            )
            self.output(content, info)
        finally:
            if self._image_file_id:
                self._delete_file(self._image_file_id)
            for file_id in self._file_ids:
                self._delete_file(file_id)

    def list_files(self):
        """Return list of (id, filename, bytes) tuples for uploaded files."""
        return [(f.id, f.filename, f.bytes) for f in self.client.files.list().data]

    def list_models(self):
        return sorted([m["id"] for m in self.client.models.list().to_dict()["data"]])


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
