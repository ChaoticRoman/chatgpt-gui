import os
import uuid
from dataclasses import dataclass
from pathlib import Path
import json
import sys
from datetime import datetime as dt
from pprint import pprint

from .pricing import USD_PER_TOKEN, USD_PER_WEB_SEARCH_CALL
from .constants import DEFAULT_MODEL, DATA_DIRECTORY
from .auth import initialize_client
from .files import Files
from .vectors import Vectors


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
    A class to interact with OpenAI's API.

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

    def __init__(
        self,
        input=None,
        output=None,
        model=DEFAULT_MODEL,
        web_search=False,
        debug=False,
        client=None,
    ):  # noqa: A002 (input is a callback, not the builtin)
        self.input = input
        self.output = output
        self.model = model
        self.web_search = web_search
        self.debug = debug

        self.messages = []
        self._images = []
        self._files = []
        self._vector_store_id = None
        self._vector_store_owned = False
        self._vector_files = []

        timestamp = dt.now().replace(microsecond=0).isoformat()
        self.conversation_id = f"{timestamp}-{uuid.uuid4().hex[:6]}"
        os.makedirs(DATA_DIRECTORY, exist_ok=True)
        self.file = DATA_DIRECTORY / f"{self.conversation_id}.json"

        self.save_callback = None

        self.client = initialize_client(client)
        self.files_api = Files(self.client)
        self.vectors_api = Vectors(self.client)

    def _compute_price(self, input_tokens, output_tokens, web_search_calls=0):
        if self.model in USD_PER_TOKEN:
            return (
                USD_PER_TOKEN[self.model].input * input_tokens
                + USD_PER_TOKEN[self.model].output * output_tokens
                + USD_PER_WEB_SEARCH_CALL * web_search_calls
            )
        return None

    def _setup_vector_store(self, file_paths):
        """Upload files to a new vector store and wait for processing to complete."""
        self._vector_store_id = self.vectors_api.create_vector_store(
            name=self.conversation_id
        )
        self._vector_store_owned = True
        if os.environ.get("CHATGPT_CLI_LOG_UPLOAD_IDS"):
            print(f"vector_store:{self._vector_store_id}", file=sys.stderr)
        for path in file_paths:
            file_id = self.files_api.upload_file(path, "assistants")
            self._vector_files.append((Path(path).name, file_id))
            self.vectors_api.add_vector_store_file(self._vector_store_id, file_id)
        self.vectors_api.wait_for_vector_store(self._vector_store_id)

    def _teardown_vector_store(self):
        """Delete the vector store and its files."""
        if self._vector_store_id and self._vector_store_owned:
            self.vectors_api.delete_vector_store(self._vector_store_id)
            for _, file_id in self._vector_files:
                self.files_api.delete_file(file_id)

    def _teardown_files(self):
        """Delete all uploaded user files and the vector store."""
        for _, file_id in self._images + self._files:
            self.files_api.delete_file(file_id)
        self._teardown_vector_store()

    def _save(self):
        with open(self.file, "w") as f:
            json.dump([dict(m) for m in self.messages], f, sort_keys=True, indent=4)
        if self.save_callback:
            self.save_callback()

    def send(self, prompt, image_path=None, file_paths=None):
        """Send a message and get response. Returns (content, Info)."""
        content = []
        if image_path:
            name = Path(image_path).name
            file_id = self.files_api.upload_file(image_path, "vision")
            self._images.append((name, file_id))
            content.append({"type": "input_image", "file_id": file_id})
        for path in file_paths or []:
            name = Path(path).name
            file_id = self.files_api.upload_file(path, "user_data")
            self._files.append((name, file_id))
            content.append({"type": "input_file", "file_id": file_id})
        content.append({"type": "input_text", "text": prompt})
        self.messages.append({"role": "user", "content": content})
        self._save()

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
        self._save()

        usage = response.usage
        input_tokens, output_tokens = usage.input_tokens, usage.output_tokens
        web_search_calls = sum(
            1
            for item in response.output
            if getattr(item, "type", None) == "web_search_call"
        )
        step_price = self._compute_price(input_tokens, output_tokens, web_search_calls)

        return content, Info(input_tokens, output_tokens, web_search_calls, step_price)

    def _init_session(
        self, image_path, file_paths, vectorize_file_paths, vector_store_id
    ):
        """Reset per-session state and populate the attachment slots."""
        self._images = []
        self._files = []
        self._vector_store_id = vector_store_id or None
        self._vector_store_owned = False
        self._vector_files = []
        self._next_image_path = image_path
        self._next_file_paths = file_paths
        self._next_vectorize_paths = vectorize_file_paths

    def _consume_attachments(self):
        """Set up any pending vector store and files, then return and clear the per-message slots."""
        if self._next_vectorize_paths:
            if not self._vector_store_id:
                self._setup_vector_store(self._next_vectorize_paths)
            else:
                for path in self._next_vectorize_paths:
                    file_id = self.files_api.upload_file(path, "assistants")
                    self.vectors_api.add_vector_store_file(
                        self._vector_store_id, file_id
                    )
                self.vectors_api.wait_for_vector_store(self._vector_store_id)
            self._next_vectorize_paths = None
        image_path, file_paths = self._next_image_path, self._next_file_paths
        self._next_image_path = None
        self._next_file_paths = None
        return image_path, file_paths

    def main(
        self,
        image_path=None,
        file_paths=None,
        vectorize_file_paths=None,
        vector_store_id=None,
        one_shot=False,
    ):
        if not self.input or not self.output:
            raise RuntimeError("Calling main without input/output callback set.")
        self._init_session(
            image_path, file_paths, vectorize_file_paths, vector_store_id
        )
        price = 0.0
        total_web_search_calls = 0
        try:
            while prompt := self.input():
                img, fps = self._consume_attachments()
                content, info = self.send(prompt, image_path=img, file_paths=fps)
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
                if one_shot:
                    break
        finally:
            self._teardown_files()

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
