#!/usr/bin/env python3
import os
import readline

import openai

MODEL = "gpt-4"

os.chdir(os.path.dirname(__file__))

with open('.api_key', 'r') as f:
    openai.api_key = f.read().strip()

messages = [
        {"role": "system", "content": "You are a helpful assistant."},
#        {"role": "assistant", "content": "Who's there?"},
#        {"role": "user", "content": "Orange."},
#        And model would proceed with "Orange who?"...
]


def user_input_dict(prompt):
    return {"role": "user", "content": prompt}


while True:
    user_input = input("> ")
    if not user_input:
        continue  # accidental empty input maybe...
    if user_input in ('q', 'x', 'quit', 'exit'):
        break
    
    messages.append(user_input_dict(user_input))

    response = openai.ChatCompletion.create(
        model=MODEL, messages=messages, temperature=0.1)

    message = response.choices[0]["message"]
    print('>>', message["content"].strip())
    
    messages.append(message)
