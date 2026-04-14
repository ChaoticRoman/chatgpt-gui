#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
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


def fmt_ts(ts):
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def print_table(headers, rows, right_align=()):
    widths = [
        max(len(headers[i]), max(len(r[i]) for r in rows)) for i in range(len(headers))
    ]

    def fmt_row(row):
        parts = [
            f"{val:>{widths[i]}}" if i in right_align else f"{val:<{widths[i]}}"
            for i, val in enumerate(row)
        ]
        return "  ".join(parts)

    print(fmt_row(headers))
    for row in rows:
        print(fmt_row(row))


def cli_output(msg, info, rich=False):
    if rich and sys.stdout.isatty():
        console.print(Markdown(msg))
    else:
        print(msg)
    print(info, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Interact with OpenAI's LLMs.")
    subparsers = parser.add_subparsers(dest="command")

    files_parser = subparsers.add_parser("files", help="Manage uploaded files.")
    files_sub = files_parser.add_subparsers(dest="files_command")
    files_sub.add_parser("list", help="List uploaded files.")
    files_add_parser = files_sub.add_parser("add", help="Upload file(s).")
    files_add_parser.add_argument(
        "files", nargs="+", metavar="FILE", help="File(s) to upload."
    )
    files_del_parser = files_sub.add_parser("delete", help="Delete file(s) by ID.")
    files_del_parser.add_argument(
        "ids", nargs="+", metavar="FILE_ID", help="File ID(s) to delete."
    )
    files_sub.add_parser("purge", help="Delete all uploaded files.")

    vectors_parser = subparsers.add_parser("vectors", help="Manage vector stores.")
    vectors_sub = vectors_parser.add_subparsers(dest="vectors_command")
    vectors_sub.add_parser("list", help="List vector stores.")
    vectors_create_parser = vectors_sub.add_parser(
        "create", help="Create a vector store."
    )
    vectors_create_parser.add_argument(
        "name", metavar="NAME", help="Name for the vector store."
    )
    vectors_create_parser.add_argument(
        "files", nargs="*", metavar="FILE", help="File(s) to upload and add."
    )
    vectors_create_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately without waiting for indexing to complete.",
    )
    vectors_del_parser = vectors_sub.add_parser(
        "delete", help="Delete a vector store by ID."
    )
    vectors_del_parser.add_argument(
        "id", metavar="VECTOR_STORE_ID", help="Vector store ID to delete."
    )
    vectors_sub.add_parser("purge", help="Delete all vector stores.")
    vectors_files_parser = vectors_sub.add_parser(
        "files", help="Manage files in a vector store."
    )
    vectors_files_sub = vectors_files_parser.add_subparsers(
        dest="vectors_files_command"
    )
    vectors_files_list_parser = vectors_files_sub.add_parser(
        "list", help="List files in a vector store."
    )
    vectors_files_list_parser.add_argument(
        "id", metavar="VECTOR_STORE_ID", help="Vector store ID."
    )
    vectors_files_add_parser = vectors_files_sub.add_parser(
        "add", help="Upload file(s) and add to a vector store."
    )
    vectors_files_add_parser.add_argument(
        "id", metavar="VECTOR_STORE_ID", help="Vector store ID."
    )
    vectors_files_add_parser.add_argument(
        "files", nargs="+", metavar="FILE", help="File path(s) to upload and add."
    )
    vectors_files_add_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately without waiting for indexing to complete.",
    )
    vectors_files_add_id_parser = vectors_files_sub.add_parser(
        "add-id", help="Add already-uploaded file(s) to a vector store by ID."
    )
    vectors_files_add_id_parser.add_argument(
        "id", metavar="VECTOR_STORE_ID", help="Vector store ID."
    )
    vectors_files_add_id_parser.add_argument(
        "file_ids", nargs="+", metavar="FILE_ID", help="File ID(s) to add."
    )
    vectors_files_add_id_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately without waiting for indexing to complete.",
    )
    vectors_files_del_parser = vectors_files_sub.add_parser(
        "delete", help="Remove file(s) from a vector store."
    )
    vectors_files_del_parser.add_argument(
        "id", metavar="VECTOR_STORE_ID", help="Vector store ID."
    )
    vectors_files_del_parser.add_argument(
        "file_ids", nargs="+", metavar="FILE_ID", help="File ID(s) to remove."
    )

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
        help="No prompt, quit after first response. For use with pipes/redirection.",
    )
    parser.add_argument(
        "-p",
        "--prepend",
        metavar="STRING",
        help="String to prepend to the first user message, followed by two newlines.",
    )
    parser.add_argument(
        "-pf",
        "--prepend-file",
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
        "-vs",
        "--vector-store",
        metavar="ID",
        help="Use a pre-existing vector store by ID for semantic file search.",
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
    args = parser.parse_args()

    if args.command == "files":
        core.load_key()
        gpt = core.GptCore(None, None, None)
        if args.files_command == "list":
            files = gpt.list_files()
            if not files:
                return
            rows = [
                (fid, name, str(size), purpose, fmt_ts(created_at), fmt_ts(expires_at))
                for fid, name, size, purpose, created_at, expires_at in files
            ]
            print_table(
                ("ID", "FILENAME", "SIZE", "PURPOSE", "CREATED_AT", "EXPIRES_AT"),
                rows,
                right_align=(2,),
            )
        elif args.files_command == "add":
            for path in args.files:
                file_id = gpt.upload_file(path, "user_data")
                print(file_id)
        elif args.files_command == "delete":
            for file_id in args.ids:
                gpt.delete_file(file_id)
        elif args.files_command == "purge":
            for file_id, *_ in gpt.list_files():
                gpt.delete_file(file_id)
        else:
            files_parser.print_help()
        return

    if args.command == "vectors":
        core.load_key()
        gpt = core.GptCore(None, None, None)
        if args.vectors_command == "list":
            stores = gpt.list_vector_stores()
            if not stores:
                return
            rows = [
                (vsid, name, status, fmt_ts(created_at))
                for vsid, name, status, created_at in stores
            ]
            print_table(("ID", "NAME", "STATUS", "CREATED_AT"), rows)
        elif args.vectors_command == "create":
            vs_id = gpt.create_vector_store(args.name)
            for path in args.files:
                file_id = gpt.upload_file(path, "assistants")
                gpt.add_vector_store_file(vs_id, file_id)
            if args.files and not args.no_wait:
                gpt.wait_for_vector_store(vs_id)
            print(vs_id)
        elif args.vectors_command == "delete":
            gpt.delete_vector_store(args.id)
        elif args.vectors_command == "purge":
            for vsid, *_ in gpt.list_vector_stores():
                gpt.delete_vector_store(vsid)
        elif args.vectors_command == "files":
            if args.vectors_files_command == "list":
                files = gpt.list_vector_store_files(args.id)
                if not files:
                    return
                rows = [
                    (fid, status, fmt_ts(created_at))
                    for fid, status, created_at in files
                ]
                print_table(("ID", "STATUS", "CREATED_AT"), rows)
            elif args.vectors_files_command == "add":
                for path in args.files:
                    file_id = gpt.upload_file(path, "assistants")
                    gpt.add_vector_store_file(args.id, file_id)
                if not args.no_wait:
                    gpt.wait_for_vector_store(args.id)
            elif args.vectors_files_command == "add-id":
                for file_id in args.file_ids:
                    gpt.add_vector_store_file(args.id, file_id)
                if not args.no_wait:
                    gpt.wait_for_vector_store(args.id)
            elif args.vectors_files_command == "delete":
                for file_id in args.file_ids:
                    gpt.delete_vector_store_file(args.id, file_id)
            else:
                vectors_files_parser.print_help()
        else:
            vectors_parser.print_help()
        return

    list_opts = [args.list_known, args.list_all]
    if (
        any(list_opts)
        and (
            args.multiline
            or args.model != core.DEFAULT_MODEL
            or args.batch_mode
            or args.prepend
            or args.prepend_file
            or args.image
            or args.file
            or args.vectorize_file
            or args.vector_store
            or args.rich
            or args.web_search
            or args.debug
        )
    ) or sum(list_opts) > 1:
        parser.error(
            "-l/--list-known and -L/--list-all "
            "cannot be combined with each other or other options."
        )

    if args.list_known:
        for m in core.KNOWN_MODELS:
            print(m)
        return

    core.load_key()

    if args.list_all:
        all_models = core.GptCore(None, None, None).list_models()
        for m in all_models:
            print(m)
        return

    if args.batch_mode:
        prompt = sys.stdin.read().strip()

        if args.prepend:
            prompt = args.prepend + "\n\n" + prompt

        if args.prepend_file:
            with open(args.prepend_file, "r") as f:
                prompt = f.read().strip() + "\n\n" + prompt

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
        ).main(
            image_path=args.image,
            file_paths=args.file,
            vectorize_file_paths=args.vectorize_file,
            vector_store_id=args.vector_store,
            one_shot=True,
        )
        return

    if args.multiline:
        input_f = cli_input_multiline
    else:
        input_f = cli_input

    prefix = ""
    if args.prepend:
        prefix += args.prepend + "\n\n"
    if args.prepend_file:
        with open(args.prepend_file, "r") as f:
            prefix += f.read().strip() + "\n\n"

    if prefix:
        original_input_f = input_f

        def input_f_with_prepend():
            msg = original_input_f()
            if msg is not None:
                msg = prefix + msg
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
        vector_store_id=args.vector_store,
    )


if __name__ == "__main__":
    main()
