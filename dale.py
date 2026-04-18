#!/usr/bin/env python3
import argparse
import multiprocessing
import os
import random
import string
import time

from libopenai.auth import initialize_client


def generate(client, prompt):
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
    client = initialize_client()

    if args.jobs > 1:
        with multiprocessing.Pool(args.jobs) as pool:
            pool.map(lambda prompt: generate(client, prompt), prompts)
    else:
        for prompt in prompts:
            generate(client, prompt)


if __name__ == "__main__":
    main()
