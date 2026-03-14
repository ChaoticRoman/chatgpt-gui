import os
from dataclasses import dataclass
from pathlib import Path
import json
import sys
from datetime import datetime as dt
from pprint import pprint

import openai

DEFAULT_MODEL = "gpt-5.3-codex"

# Prices in USD, source: https://openai.com/api/pricing/
USD_PER_INPUT_TOKEN = {
    "o1": 15e-6,
    "o3-pro": 20e-6,
    "o3-mini": 1.1e-6,
    "o4-mini": 1.1e-6,
    "gpt-5": 1.25e-6,
    "gpt-5.1": 1.25e-6,
    "gpt-5.2": 1.75e-6,
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
    "gpt-5.3-codex": 14e-6,
    "gpt-5.4": 15e-6,
    "gpt-5.4-pro": 180e-6,
}
assert set(USD_PER_INPUT_TOKEN.keys()) == set(USD_PER_OUTPUT_TOKEN.keys())

USD_PER_WEB_SEARCH_CALL = 0.01

DATA_DIRECTORY = Path.home() / ".chatgpt-gui"


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
        self.file = DATA_DIRECTORY / f"{timestamp}.json"

        self.client = openai.OpenAI()

    def _compute_price(self, input_tokens, output_tokens, web_search_calls=0):
        if self.model in USD_PER_INPUT_TOKEN and self.model in USD_PER_OUTPUT_TOKEN:
            return (
                USD_PER_INPUT_TOKEN[self.model] * input_tokens
                + USD_PER_OUTPUT_TOKEN[self.model] * output_tokens
                + USD_PER_WEB_SEARCH_CALL * web_search_calls
            )
        return None

    def send(self, prompt):
        """Send a message and get response. Returns (content, Info)."""
        self.messages.append({"role": "user", "content": prompt})

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

    def main(self):
        price = 0
        total_web_search_calls = 0
        while prompt := self.input():
            content, info = self.send(prompt)
            if info.price is not None:
                price += info.price
            else:
                price = None
            total_web_search_calls += info.web_search_calls
            self.output(
                content,
                Info(
                    info.input_tokens, info.output_tokens, total_web_search_calls, price
                ),
            )

    def one_shot(self):
        prompt = self.input()
        if not prompt:
            return
        content, info = self.send(prompt)
        self.output(content, info)

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
