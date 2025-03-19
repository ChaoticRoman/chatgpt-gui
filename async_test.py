import asyncio

from openai import AsyncOpenAI

from core import load_key

load_key()

aclient = AsyncOpenAI()


async def async_streaming_chat_completion(messages):
    response = await aclient.chat.completions.create(model="gpt-3.5-turbo",
    messages=messages,
    stream=True)

    async for chunk in response:
        if content := chunk.choices[0].delta.content:
            print(content, end='')
    print()

async def main():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give me a ten suggestions how to improve my focus."}
    ]
    await async_streaming_chat_completion(messages)

if __name__ == "__main__":
    asyncio.run(main())
