#!/usr/bin/env python3
import os
import readline

import core


def cli_input():
    user_input = input("> ")
    if user_input in ('q', 'x', 'quit', 'exit'):
        return None
    return user_input


def cli_output(msg, info):
    print(msg)
    print(info)


core.GptCore(cli_input, cli_output).main()
