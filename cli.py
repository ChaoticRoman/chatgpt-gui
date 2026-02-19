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
        "-M",
        "--model",
        default=core.DEFAULT_MODEL,
        help=f"Use different model than {core.DEFAULT_MODEL}",
    )
    parser.add_argument(
        "-p",
        "--prepend",
        metavar="FILE",
        help="Plain text file whose contents will be prepended to the first user message.",
    )
    args = parser.parse_args()

    if args.multiline:
        input_f = cli_input_multiline
    else:
        input_f = cli_input

    if args.prepend:
        with open(args.prepend, "r") as f:
            prefix = f.read()

        original_input_f = input_f

        def input_f_with_prepend():
            msg = original_input_f()
            if msg is not None:
                msg = prefix + "\n" + msg
            return msg

        # Replace input_f for the first call only
        first_call = [True]

        def input_f():
            if first_call[0]:
                first_call[0] = False
                return input_f_with_prepend()
            return original_input_f()

    core.load_key()
    core.GptCore(input_f, cli_output, model=args.model).main()


if __name__ == "__main__":
    main()
