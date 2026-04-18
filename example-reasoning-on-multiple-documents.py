#!/usr/bin/env python3
from libopenai.auth import initialize_client

client = initialize_client()

# Upload
apple = client.files.create(
    file=open("./tests/test1.pdf", "rb"),
    purpose="user_data",
)
banana = client.files.create(
    file=open("./tests/test2.pdf", "rb"),
    purpose="user_data",
)

# Propmpt
response = client.responses.create(
    model="gpt-5.4",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_file",
                    "file_id": apple.id,
                },
                {
                    "type": "input_file",
                    "file_id": banana.id,
                },
                {
                    "type": "input_text",
                    "text": "Are we mixing apples and bananas?",
                },
            ],
        }
    ],
)
print(response.output_text)

# Delete
client.files.delete(apple.id)
client.files.delete(banana.id)
