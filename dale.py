#!/usr/bin/env python3
import os
import time

from openai import OpenAI

from core import load_key

load_key()
client = OpenAI()

prompt = input("Prompt: ")
print(f'Your prompt is "{prompt}".')

response = client.images.generate(
    model="dall-e-3",
    prompt=prompt,
    size="1024x1024",
    quality="standard",
    n=1,
)

url = response.data[0].url
timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
filename = f"output-{timestamp}.png"

os.system(f'wget -O "{filename}" "{url}"')
