#!/usr/bin/env python3
import os
import asyncio
import openai
from tqdm import tqdm

MODEL = "gpt-4"

os.chdir(os.path.dirname(__file__))

with open('.api_key', 'r') as f:
    openai.api_key = f.read().strip()

messages = [
        {"role": "system", "content": ""},
#        {"role": "system", "content": "You are a helpful assistant."},
#        {"role": "assistant", "content": "Who's there?"},
#        {"role": "user", "content": "Orange."},
]


def user_input_dict(prompt):
    return {"role": "user", "content": prompt}


async def get_response_async():
    loop = asyncio.get_event_loop()
    response_future = loop.run_in_executor(None, lambda: openai.ChatCompletion.create(
        model=MODEL, messages=messages, temperature=0.1))

    # Display dotting
    pbar = tqdm(total=1, bar_format='{desc}', position=0, leave=True)
    x = 0
    while not response_future.done():
        pbar.set_description_str("." * x, refresh=True)
        x += 1
        await asyncio.sleep(0.5)

    pbar.close()

    return await response_future


price = 0

loop = asyncio.get_event_loop()

while True:
    user_input = input("You: ")
    if not user_input:
        continue  # accidental empty input, next try
    if user_input in ('q', 'x', 'quit', 'exit'):
        break

    messages.append(user_input_dict(user_input))

    response = loop.run_until_complete(get_response_async())

    message = response.choices[0]["message"]
    messages.append(message)
    print(MODEL + ":", message["content"].strip())

    usage = response.usage
    prompt_tokens, completion_tokens, total_tokens = (
        usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)

    # GPT-4 prices in USD, source: https://openai.com/pricing#language-models
    price += 0.03 / 1e3 * prompt_tokens + 0.06 / 1e3 * completion_tokens

    info = (
        f'Last prompt / response: {prompt_tokens} / {completion_tokens} tokens, '
        f'Total price: {price:.3f} USD')
    print(info)
