#!/usr/bin/env python3
import sys

from openai import OpenAI

from libopenai.auth import ensure_key

ensure_key()
client = OpenAI()

with open(sys.argv[1], "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )

print(transcription.text)
