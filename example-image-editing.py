import base64

from libopenai.auth import initialize_client
from libopenai.files import Files

client = initialize_client()
files_api = Files(client)

prompt = "Add mountains to background."

file_id1 = files_api.upload_file("tests/test.png", "vision")

response = client.responses.create(
    model="gpt-5.4",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "file_id": file_id1,
                },
                #                {
                #                    "type": "input_image",
                #                    "file_id": file_id2,
                #                }
            ],
        }
    ],
    tools=[{"type": "image_generation"}],
)

image_generation_calls = [
    output for output in response.output if output.type == "image_generation_call"
]

image_data = [output.result for output in image_generation_calls]

for i, d in enumerate(image_data):
    image_base64 = d
    with open(f"output{i}.png", "wb") as f:
        f.write(base64.b64decode(image_base64))

try:
    print(response.output.content)
except AttributeError:
    print("No output")
