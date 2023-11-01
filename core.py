import os
from dataclasses import dataclass

import openai

MODEL = "gpt-4"
TEMPERATURE = 0.0

api_key_path = os.path.join(os.path.dirname(__file__), '.api_key')
with open(api_key_path, 'r') as f:
    openai.api_key = f.read().strip()


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
    def __init__(self, input, output):
        self.input = input
        self.output = output

        self.messages = []

    def main(self):
        price = 0
        while prompt := self.input():
            self.messages.append({"role": "user", "content": prompt})

            response = openai.ChatCompletion.create(
                model=MODEL, messages=self.messages, temperature=TEMPERATURE)

            message = response.choices[0]["message"]
            self.messages.append(message)

            content = message["content"].strip()

            usage = response.usage
            prompt_tokens, completion_tokens = (
                usage.prompt_tokens, usage.completion_tokens)
            # GPT-4 prices in USD, source:
            # https://openai.com/pricing#language-models
            price += 0.03 / 1e3 * prompt_tokens + 0.06 / 1e3 * completion_tokens  # noqa: E501

            self.output(content, Info(prompt_tokens, completion_tokens, price))


@dataclass
class Info:
    """
    A class to represent the information about the interaction with the model.

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
            f'Prompt tokens: {self.prompt_tokens}, '
            f'Completion tokens: {self.completion_tokens}, '
            f'Total price: {self.price:.3f} USD')
