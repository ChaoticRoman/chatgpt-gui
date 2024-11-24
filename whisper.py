#!/usr/bin/env python3
import sys

from openai import OpenAI

from core import load_key

load_key()
client = OpenAI()

with open(sys.argv[1], "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )

print(transcription.text)
