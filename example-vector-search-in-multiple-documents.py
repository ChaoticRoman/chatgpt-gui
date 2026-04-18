#!/usr/bin/env python3
"""Playing with example here:

https://developers.openai.com/cookbook/examples/file_search_responses

Demonstrates vector search across multiple documents: uploads two fruit-themed
PDFs from the tests/ directory, queries about the fruits mentioned in them,
then cleans up the vector store and uploaded files.
"""

import os
import time

from openai import OpenAI

from libopenai.auth import ensure_key

ensure_key()
client = OpenAI()

# Create vector store

vector_store = client.vector_stores.create(name="fruit_docs_example")
print(f"Vector store created: id={vector_store.id} name={vector_store.name!r}")

# Upload both test PDFs

script_dir = os.path.dirname(os.path.abspath(__file__))
pdf_paths = [
    os.path.join(script_dir, "tests", "test1.pdf"),
    os.path.join(script_dir, "tests", "test2.pdf"),
]

uploaded_file_ids = []
for path in pdf_paths:
    file_response = client.files.create(file=open(path, "rb"), purpose="assistants")
    client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=file_response.id,
    )
    uploaded_file_ids.append(file_response.id)
    print(f"Uploaded: {os.path.basename(path)} → file_id={file_response.id}")

# Wait for vector store processing to complete

print("Waiting for vector store to finish processing...", end="", flush=True)
while True:
    vs = client.vector_stores.retrieve(vector_store.id)
    if vs.status == "completed":
        break
    print(".", end="", flush=True)
    time.sleep(2)
print(" done.")

# Query about the fruits mentioned in the documents

query = "What fruits are described in the documents? Summarise what each document says about its fruit."

response = client.responses.create(
    input=query,
    model="gpt-5.4",
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": [vector_store.id],
        }
    ],
    tool_choice="required",
    include=["file_search_call.results"],
)


def render_output_item(o) -> str:
    t = getattr(o, "type", None)

    if t == "message":
        parts = []
        for part in getattr(o, "content", []) or []:
            if getattr(part, "type", None) == "output_text":
                parts.append(part.text)
            else:
                parts.append(f"[{getattr(part, 'type', 'unknown_part')}] {part}")
        return "[Message]\n" + "\n".join(parts).strip()

    if t == "file_search_call":
        queries = getattr(o, "queries", [])
        status = getattr(o, "status", None)
        return f"[File search]\nstatus={status} queries={queries}"

    if t == "reasoning":
        return (
            "[Reasoning]\n"
            + "\n".join(f"[Summary]\n{s.text}" for s in o.summary).strip()
        )

    return f"[{t or 'unknown'}] {o!r}"


for item in response.output:
    print(render_output_item(item).strip() + "\n")

# Cleanup: delete the vector store and uploaded files

client.vector_stores.delete(vector_store.id)
print(f"\nDeleted vector store: {vector_store.id}")
for file_id in uploaded_file_ids:
    client.files.delete(file_id)
    print(f"Deleted file: {file_id}")
