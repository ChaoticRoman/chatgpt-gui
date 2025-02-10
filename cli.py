#!/usr/bin/env python3
import argparse

# importing readline adds history and navigation to input builtin
import readline  # noqa F401

import core


def check_exit(user_input):
    return user_input in ("q", "x", "quit", "exit")


def cli_input():
    try:
        user_input = input("> ")
    except (KeyboardInterrupt, EOFError):
        print()
        return None
    else:
        if check_exit(user_input):
            return None
        return user_input


def cli_input_multiline():
    user_input = []
    while True:
        try:
            line = input("> ")
        except (KeyboardInterrupt, EOFError):
            print()
            return None

        else:
            if line == "SEND":
                break
            user_input.append(line)

    user_input = "\n".join(user_input)

    if check_exit(user_input):
        return None

    return user_input


def cli_output(msg, info):
    print(msg)
    print(info)


def main():
    parser = argparse.ArgumentParser(description="Interact with OpenAI's GPT-4 model.")
    parser.add_argument(
        "-m",
        "--multiline",
        action="store_true",
        help='Enable multiline input mode. Input "SEND" when you are done.',
    )
    parser.add_argument(
        "--o3-mini",
        action="store_true",
        help="Use o3-mini instead of o1.",
    )
    args = parser.parse_args()

    if args.multiline:
        input_f = cli_input_multiline
    else:
        input_f = cli_input

    model = "o3-mini" if args.o3_mini else "o1"

    core.load_key()
    core.GptCore(input_f, cli_output, model=model).main()


if __name__ == "__main__":
    main()
