import anthropic

with open(".api_key_claude") as f:
    api_key = f.read().strip()

client = anthropic.Anthropic(
    api_key=api_key,
)
message = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1000,
    temperature=0,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Tell a joke."
                }
            ]
        }
    ]
)
answer = message.to_dict()["content"][0]["text"]

print(answer)
