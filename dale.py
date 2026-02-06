#!/usr/bin/env python3
import os
import time

# import multiprocessing
import random
import string

from openai import OpenAI

from core import load_key

load_key()
client = OpenAI()


def generate(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    url = response.data[0].url
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    rnd = "".join(random.choices(string.ascii_lowercase, k=6))
    filename = f"output-{timestamp}-{rnd}.png"

    os.system(f'wget -O "{filename}" "{url}"')


prompt = input("Prompt: ")
amount = int(input("Amount: "))
# p = multiprocessing.Pool(10)
for _ in range(amount):
    generate(prompt)
