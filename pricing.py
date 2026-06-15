#!/usr/bin/env python3
import argparse

from libopenai.pricing import KNOWN_MODELS, USD_PER_TOKEN
from libopenai.constants import DEFAULT_MODEL


def parse_tokens(value):
    multipliers = {"k": 1_000, "m": 1_000_000}
    text = value.strip()
    suffix = text[-1:].lower()
    if suffix in multipliers:
        number, factor = text[:-1], multipliers[suffix]
    else:
        number, factor = text, 1
    try:
        count = float(number) * factor
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid token count: {value!r} "
            "(use a number, optionally suffixed with 'k' or 'M')"
        ) from None
    if count < 0:
        raise argparse.ArgumentTypeError(f"token count must be non-negative: {value!r}")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Compute the price for given input and output token counts."
    )
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        choices=KNOWN_MODELS,
        metavar="MODEL",
        help=f"Model to price for (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "input_tokens",
        type=parse_tokens,
        metavar="INPUT_TOKENS",
        help="Input token count (accepts a 'k' or 'M' suffix, e.g. 1.5k, 2M).",
    )
    parser.add_argument(
        "output_tokens",
        type=parse_tokens,
        metavar="OUTPUT_TOKENS",
        help="Output token count (accepts a 'k' or 'M' suffix, e.g. 1.5k, 2M).",
    )
    args = parser.parse_args()

    pricing = USD_PER_TOKEN[args.model]
    price = pricing.input * args.input_tokens + pricing.output * args.output_tokens
    print(f"{price:.10f}".rstrip("0").rstrip("."))


if __name__ == "__main__":
    main()
