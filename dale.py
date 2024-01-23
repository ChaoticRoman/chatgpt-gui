import os

from openai import OpenAI

from core import load_key

load_key()
client = OpenAI()

response = client.images.generate(
  model="dall-e-3",
  prompt="Bender plays table foosball against guy in Guy Fawkes in his mask, cartoon styled with score 40 to 35 for Bender",
  size="1024x1024",
  quality="standard",
  n=1,
)

url = response.data[0].url
print(url)
os.system(f'wget "{url}"')
