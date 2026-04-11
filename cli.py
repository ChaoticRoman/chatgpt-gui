#!/usr/bin/env python3
import argparse
from functools import partial
import sys

# importing readline adds history and navigation to input builtin
import readline  # noqa F401

from rich.console import Console
from rich.markdown import Markdown

import core

console = Console()


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


def cli_output(msg, info, rich=False):
    if rich and sys.stdout.isatty():
        console.print(Markdown(msg))
    else:
        print(msg)
    print(info)


def main():
    parser = argparse.ArgumentParser(description="Interact with OpenAI's LLMs.")
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
        "-b",
        "--batch-mode",
        action="store_true",
        help="No prompt, pricing info in stderr, quit after first response. For use with pipes/redirection.",
    )
    parser.add_argument(
        "-p",
        "--prepend",
        metavar="FILE",
        help="Plain text file whose contents will be prepended to the first user message.",
    )
    parser.add_argument(
        "-i",
        "--image",
        metavar="FILE",
        help="Image file to include.",
    )
    parser.add_argument(
        "-f",
        "--file",
        nargs="+",
        metavar="FILE",
        help="Document(s) to include.",
    )
    parser.add_argument(
        "-vf",
        "--vectorize-file",
        nargs="+",
        metavar="FILE",
        help="Document(s) to upload to a vector store for semantic file search.",
    )
    parser.add_argument(
        "-r",
        "--rich",
        action="store_true",
        help="Render Markdown with rich text formatting in the terminal.",
    )
    parser.add_argument(
        "-w",
        "--web-search",
        action="store_true",
        help="Enable web search tool.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Pretty print raw OpenAI responses to stderr.",
    )
    parser.add_argument(
        "-l",
        "--list-known",
        action="store_true",
        help="List models with pricing records available.",
    )
    parser.add_argument(
        "-L",
        "--list-all",
        action="store_true",
        help="List all models available.",
    )
    parser.add_argument(
        "-lf",
        "--list-files",
        action="store_true",
        help="List uploaded files.",
    )
    parser.add_argument(
        "-lv",
        "--list-vector-stores",
        action="store_true",
        help="List vector stores.",
    )
    args = parser.parse_args()

    list_opts = [
        args.list_known,
        args.list_all,
        args.list_files,
        args.list_vector_stores,
    ]
    if (
        any(list_opts)
        and (
            args.multiline
            or args.model != core.DEFAULT_MODEL
            or args.batch_mode
            or args.prepend
            or args.image
            or args.file
            or args.vectorize_file
            or args.rich
            or args.web_search
            or args.debug
        )
    ) or sum(list_opts) > 1:
        parser.error(
            "-l/--list-known, -L/--list-all, -lf/--list-files, and -lv/--list-vector-stores "
            "cannot be combined with each other or other options."
        )

    if args.list_known:
        [print(m) for m in sorted(core.USD_PER_INPUT_TOKEN.keys())]
        return

    core.load_key()

    if args.list_all:
        [print(m) for m in core.GptCore(None, None, None).list_models()]
        return

    if args.list_files:
        files = core.GptCore(None, None, None).list_files()
        if not files:
            print("No files.")
            return
        id_w = max(len(f[0]) for f in files)
        name_w = max(len(f[1]) for f in files)
        for fid, name, size in files:
            print(f"{fid:<{id_w}}  {name:<{name_w}}  {size:>10}")
        return

    if args.list_vector_stores:
        stores = core.GptCore(None, None, None).list_vector_stores()
        if not stores:
            print("No vector stores.")
            return
        id_w = max(len(s[0]) for s in stores)
        name_w = max(len(s[1]) for s in stores)
        for vsid, name, status in stores:
            print(f"{vsid:<{id_w}}  {name:<{name_w}}  {status}")
        return

    if args.batch_mode:
        prompt = sys.stdin.read().strip()

        if args.prepend:
            with open(args.prepend, "r") as f:
                prompt = f.read() + "\n" + prompt

        def batch_input():
            return prompt

        def batch_output(msg, info):
            print(msg)
            print(info, file=sys.stderr)

        core.GptCore(
            batch_input,
            batch_output,
            args.model,
            web_search=args.web_search,
            debug=args.debug,
        ).one_shot(
            image_path=args.image,
            file_paths=args.file,
            vectorize_file_paths=args.vectorize_file,
        )
        return

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

    output_f = partial(cli_output, rich=args.rich)

    core.GptCore(
        input_f,
        output_f,
        model=args.model,
        web_search=args.web_search,
        debug=args.debug,
    ).main(
        image_path=args.image,
        file_paths=args.file,
        vectorize_file_paths=args.vectorize_file,
    )


if __name__ == "__main__":
    main()
