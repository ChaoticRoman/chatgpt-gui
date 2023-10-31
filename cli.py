#!/usr/bin/env python3
import argparse
import os
import readline

import core


def check_exit(user_input):
    return user_input in ('q', 'x', 'quit', 'exit')


def cli_input():
    user_input = input("> ")
    if check_exit(user_input):
        return None
    return user_input


def cli_input_multiline():
    user_input = []
    while True:
        line = input("> ")
        if line == "SEND":
            break
        user_input.append(line)
    user_input = '\n'.join(user_input)

    if check_exit(user_input):
        return None

    return user_input


def cli_output(msg, info):
    print(msg)
    print(info)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-m', '--multiline', action='store_true',
        help='Multiline mode, input SEND when you are happy.')
    args = parser.parse_args()

    if args.multiline:
        input_f = cli_input_multiline
    else:
        input_f = cli_input

    core.GptCore(input_f, cli_output).main()


if __name__ == "__main__":
    main()
