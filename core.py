import os
from dataclasses import dataclass

import openai

MODEL = "gpt-4"

os.chdir(os.path.dirname(__file__))

with open('.api_key', 'r') as f:
    openai.api_key = f.read().strip()


class GptCore:
    def __init__(self, input, output):
        self.input = input
        self.output = output

        self.messages = []

    def main(self):
        price = 0
        while prompt := self.input():
            self.messages.append({"role": "user", "content": prompt})

            response = openai.ChatCompletion.create(
                model=MODEL, messages=self.messages, temperature=0)

            message = response.choices[0]["message"]
            self.messages.append(message)

            content = message["content"].strip()

            usage = response.usage
            prompt_tokens, completion_tokens = (
                usage.prompt_tokens, usage.completion_tokens)
            # GPT-4 prices in USD, source: https://openai.com/pricing#language-models
            price += 0.03 / 1e3 * prompt_tokens + 0.06 / 1e3 * completion_tokens

            self.output(content, Info(prompt_tokens, completion_tokens, price))


@dataclass
class Info:
    prompt_tokens: int
    completion_tokens: int
    price: float

    def __repr__(self):
        return (
            f'Prompt tokens: {self.prompt_tokens}, '
            f'Completion tokens: {self.completion_tokens}, '
            f'Total price: {self.price:.3f} USD')
