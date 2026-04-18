#!/usr/bin/env python3
import sys

from libopenai.auth import initialize_client

MODEL = "gpt-5.4"

client = initialize_client()

prompt = " ".join(sys.argv[1:])

# System message can provide further control over tone and task
# There is a way how to send more advanced discussion too
messages = [
    # {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": prompt},
    # {"role": "user", "content": "Knock knock."},
    # {"role": "assistant", "content": "Who's there?"},
    # {"role": "user", "content": "Orange."},
    # ... And model would proceed with "Orange who?"
]

response = client.responses.create(
    model=MODEL,
    input=messages,
)

print(response.model)
print(response.output_text.strip())
print(response.usage)
