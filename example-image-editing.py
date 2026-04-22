"""Minimal example: edit an input image using the image_generation tool."""

import base64

from libopenai.auth import initialize_client
from libopenai.constants import DEFAULT_MODEL
from libopenai.files import Files

client = initialize_client()
files_api = Files(client)

file_id = files_api.upload_file("tests/test.png", "vision")

response = client.responses.create(
    model=DEFAULT_MODEL,
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Add mountains to background."},
                {"type": "input_image", "file_id": file_id},
            ],
        }
    ],
    tools=[{"type": "image_generation"}],
)

for i, item in enumerate(response.output):
    if item.type != "image_generation_call":
        continue
    with open(f"output{i}.png", "wb") as f:
        f.write(base64.b64decode(item.result))
