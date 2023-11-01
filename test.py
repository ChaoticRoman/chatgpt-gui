#!/usr/bin/env python3
import openai
import os
import sys

MODEL = "gpt-4"

os.chdir(os.path.dirname(__file__))

with open('.api_key', 'r') as f:
    openai.api_key = f.read().strip()

prompt = " ".join(sys.argv[1:])

# System message can provide further control over tone and task
# There is a way how to send more advanced discussion too
messages = [
#        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
#        {"role": "user", "content": "Knock knock."},
#        {"role": "assistant", "content": "Who's there?"},
#        {"role": "user", "content": "Orange."},  # And model would proceed with "Orange who?"
]

response = openai.ChatCompletion.create(
    model=MODEL, messages=messages, temperature=0.1)

print(response.choices[0]["message"]["content"].strip())
