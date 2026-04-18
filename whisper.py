#!/usr/bin/env python3
import sys
from libopenai.auth import initialize_client

client = initialize_client()

with open(sys.argv[1], "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )

print(transcription.text)
