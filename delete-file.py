#!/usr/bin/env python3
import argparse

from openai import OpenAI

from core import load_key

parser = argparse.ArgumentParser(description="Delete OpenAI files by ID")
parser.add_argument("ids", nargs="+", metavar="FILE_ID", help="File ID(s) to delete")
args = parser.parse_args()

load_key()
client = OpenAI()
for file_id in args.ids:
    client.files.delete(file_id)
