import os
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime as dt

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
}
assert set(USD_PER_INPUT_TOKEN.keys()) == set(USD_PER_OUTPUT_TOKEN.keys())

DATA_DIRECTORY = Path.home() / ".chatgpt-gui"


def load_key():
    if "OPENAI_API_KEY" not in os.environ:
        api_key_path = os.path.join(os.path.dirname(__file__), ".api_key")
        with open(api_key_path, "r") as f:
            os.environ["OPENAI_API_KEY"] = f.read().strip()


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

    def __init__(self, input, output, model):
        self.input = input
        self.output = output
        self.model = model

        self.messages = []

        timestamp = dt.now().replace(microsecond=0).isoformat()
        os.makedirs(DATA_DIRECTORY, exist_ok=True)
        self.file = DATA_DIRECTORY / f"{timestamp}.json"

        self.client = openai.OpenAI()

    def main(self):
        price = 0
        while prompt := self.input():
            self.messages.append({"role": "user", "content": prompt})

            response = self.client.responses.create(
                model=self.model, input=self.messages
            )

            content = response.output_text.strip()
            self.messages.append({"role": "assistant", "content": content})
            serialized = [dict(m) for m in self.messages]
            with open(self.file, "w") as f:
                json.dump(serialized, f, sort_keys=True, indent=4)

            usage = response.usage
            input_tokens, output_tokens = (
                usage.input_tokens,
                usage.output_tokens,
            )

            if self.model in USD_PER_INPUT_TOKEN and self.model in USD_PER_OUTPUT_TOKEN:
                price += USD_PER_INPUT_TOKEN[self.model] * input_tokens
                price += USD_PER_OUTPUT_TOKEN[self.model] * output_tokens
            else:
                price = "N/A"

            self.output(content, Info(input_tokens, output_tokens, price))


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
    price : float
        the total price of the interaction
    """

    input_tokens: int
    output_tokens: int
    price: float

    def __repr__(self):
        return (
            f"Input tokens: {self.input_tokens}, "
            f"Output tokens: {self.output_tokens}, "
            f"Total price: {self.price:.3f} USD"
        )
