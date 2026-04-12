#!/usr/bin/env python3
import argparse
import multiprocessing
import os
import random
import string
import time

from openai import OpenAI

from core import load_key

load_key()
client = OpenAI()


def generate(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    url = response.data[0].url
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    rnd = "".join(random.choices(string.ascii_lowercase, k=6))
    filename = f"output-{timestamp}-{rnd}.png"

    os.system(f'wget -O "{filename}" "{url}"')


def main():
    parser = argparse.ArgumentParser(description="Generate images using DALL-E 3.")
    parser.add_argument("prompt", help="Image generation prompt.")
    parser.add_argument(
        "-n",
        "--amount",
        type=int,
        default=1,
        metavar="N",
        help="Number of images to generate (default: 1).",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Number of parallel workers (default: 1).",
    )
    args = parser.parse_args()

    prompts = [args.prompt] * args.amount
    if args.jobs > 1:
        with multiprocessing.Pool(args.jobs) as pool:
            pool.map(generate, prompts)
    else:
        for p in prompts:
            generate(p)


if __name__ == "__main__":
    main()
