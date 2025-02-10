import os
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime as dt

import openai

MODEL = "o1"
EFFORT = "high"

# Prices in USD, source: https://openai.com/api/pricing/
USD_PER_INPUT_TOKEN = {"o1": 15e-6, "o3-mini": 1.1e-6}
USD_PER_OUTPUT_TOKEN = {"o1": 60e-6, "o3-mini": 4.4e-6}

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

    def __init__(self, input, output, model=MODEL):
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

            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages, reasoning_effort=EFFORT
            )

            message = response.choices[0].message
            self.messages.append(message)
            serialized = [dict(m) for m in self.messages]
            with open(self.file, "w") as f:
                json.dump(serialized, f, sort_keys=True, indent=4)

            content = message.content.strip()

            usage = response.usage
            prompt_tokens, completion_tokens = (
                usage.prompt_tokens,
                usage.completion_tokens,
            )

            if self.model in USD_PER_INPUT_TOKEN and self.model in USD_PER_OUTPUT_TOKEN:
                price += USD_PER_INPUT_TOKEN[self.model] * prompt_tokens
                price += USD_PER_OUTPUT_TOKEN[self.model] * completion_tokens
            else:
                price = "N/A"

            self.output(content, Info(prompt_tokens, completion_tokens, price))


@dataclass
class Info:
    """
    A class representing the information about the interaction with the model.

    Attributes
    ----------
    prompt_tokens : int
        the number of tokens in the prompt
    completion_tokens : int
        the number of tokens in the completion
    price : float
        the total price of the interaction
    """

    prompt_tokens: int
    completion_tokens: int
    price: float

    def __repr__(self):
        return (
            f"Prompt tokens: {self.prompt_tokens}, "
            f"Completion tokens: {self.completion_tokens}, "
            f"Total price: {self.price:.3f} USD"
        )
