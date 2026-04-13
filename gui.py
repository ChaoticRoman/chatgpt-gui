#!/usr/bin/env python3
import os
import json
import queue
import threading
import tkinter as tk
from tkinter import (
    Scrollbar,
    END,
    RIGHT,
    Y,
    LEFT,
    BOTH,
    Text,
    Button,
)
from tkinter import ttk

from tkinterweb import HtmlFrame
from mistletoe import markdown
from mistletoe.contrib.pygments_renderer import PygmentsRenderer

from core import DEFAULT_MODEL, DATA_DIRECTORY, GptCore, load_key


class JsonViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ChatGPT GUI")
        self.geometry("1000x700")
        self.minsize(600, 400)

        # Horizontal paned window: file list | conversation
        self.hpaned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5)
        self.hpaned.pack(fill=BOTH, expand=True)

        # Left: file table with scrollbar
        self.left_frame = tk.Frame(self.hpaned)
        self.file_table = ttk.Treeview(
            self.left_frame, columns=("file",), show="headings", selectmode="browse"
        )
        self.file_table.heading("file", text="Conversation", command=self.toggle_sort)
        self.file_table.column("file", anchor="w")
        self.file_table.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar = Scrollbar(self.left_frame, command=self.file_table.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.file_table.config(yscrollcommand=self.scrollbar.set)
        self.hpaned.add(self.left_frame, minsize=150)
        self.sort_descending = True

        # Right: vertical paned window for content | input
        self.vpaned = tk.PanedWindow(self.hpaned, orient=tk.VERTICAL, sashwidth=5)
        self.hpaned.add(self.vpaned, minsize=300)

        self.file_content_text = HtmlFrame(self.vpaned, messages_enabled=False)
        self.vpaned.add(self.file_content_text, minsize=100)

        # Input frame at the bottom (inside vertical paned window)
        self.input_frame = tk.Frame(self.vpaned)
        self.vpaned.add(self.input_frame, minsize=60)

        self.input_row = tk.Frame(self.input_frame)
        self.input_row.pack(side=tk.TOP, fill=BOTH, expand=True)

        self.input_text = Text(self.input_row, height=3)
        self.input_text.pack(side=LEFT, fill=BOTH, expand=True)

        self.send_button = Button(
            self.input_row, text="Send", command=self.send_message
        )
        self.send_button.pack(side=RIGHT)

        # Progress bar shown while waiting for a response; hidden at rest
        self.progress_bar = ttk.Progressbar(self.input_frame, mode="indeterminate")

        # Bind Enter key to send message (Shift+Enter for newline)
        self.input_text.bind("<Return>", self.on_enter)

        # Core and conversation state
        self.current_file_path = None
        self.gpt_core = None
        self._input_queue = queue.Queue()
        self._gpt_thread = None

        # Load the list of JSON files
        self.load_json_files()

        # Bind the table selection event to a function
        self.file_table.bind("<<TreeviewSelect>>", self.on_file_select)

        # Auto-select the first conversation
        children = self.file_table.get_children()
        if children:
            self.file_table.selection_set(children[0])

        # Killing with CTRL+C in the console
        self.check()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._stop_gpt_thread()
        self.destroy()

    def load_json_files(self):
        """Load the list of JSON files from the hardcoded folder."""
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        if os.path.exists(DATA_DIRECTORY):
            json_files = sorted(
                [f for f in os.listdir(DATA_DIRECTORY) if f.endswith(".json")],
                reverse=self.sort_descending,
            )
            for file in json_files:
                self.file_table.insert("", END, values=(file,))
        else:
            self.file_table.insert("", END, values=("Folder not found",))

    def toggle_sort(self):
        """Toggle sort order and reload file list."""
        self.sort_descending = not self.sort_descending
        self.load_json_files()

    def on_file_select(self, event):
        """Display the content of the selected JSON file."""
        selection = self.file_table.selection()
        if selection:
            selected_file = self.file_table.item(selection[0])["values"][0]

            # Construct the full file path
            file_path = os.path.join(DATA_DIRECTORY, selected_file)
            self.current_file_path = file_path

            # Reset UI in case we switched while waiting for a response
            self._set_ui_idle()

            with open(file_path, "r") as file:
                file_content = json.load(file)
                self.display_conversation(file_content)

                # Initialize GptCore for this conversation
                self.initialize_gpt_core(file_content, file_path)

    def display_conversation(self, messages):
        """Display conversation messages as formatted HTML."""
        formatted_content = markdown(format_json(messages), CustomPygmentsRenderer)
        self.file_content_text.load_html(formatted_content)

    def initialize_gpt_core(self, existing_messages, file_path):
        """Start a GptCore.main() loop for this conversation in a background thread.

        The main loop blocks on a queue.Queue for input and calls back into the
        GUI via after(0, ...) for output, keeping the GUI responsive at all times.
        Closures capture the specific queue and core instance so that stale
        responses from a previous conversation are silently ignored.
        """
        self._stop_gpt_thread()
        input_queue = queue.Queue()
        self._input_queue = input_queue

        load_key()

        def gui_input():
            # Blocks until send_message() puts a prompt (or None) in the queue.
            return input_queue.get()

        def gui_output(content, info):
            # Called from the background thread; schedule GUI update on main thread.
            def update():
                # Guard: ignore if the user has already switched to another conversation.
                if self.gpt_core is core:
                    self.display_conversation(core.messages)
                    self._set_ui_idle()
                    self.input_text.focus()

            self.after(0, update)

        core = GptCore(
            input=gui_input,
            output=gui_output,
            model=DEFAULT_MODEL,
        )
        self.gpt_core = core
        core.messages = [
            {"role": m["role"], "content": m["content"]} for m in existing_messages
        ]
        core.file = file_path

        self._gpt_thread = threading.Thread(target=core.main, daemon=True)
        self._gpt_thread.start()

    def _stop_gpt_thread(self):
        """Send a termination signal to the running GptCore main loop."""
        if self._gpt_thread and self._gpt_thread.is_alive():
            self._input_queue.put(None)

    def _set_ui_busy(self):
        self.send_button.config(state="disabled")
        self.input_text.config(state="disabled")
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress_bar.start(10)

    def _set_ui_idle(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.send_button.config(state="normal")
        self.input_text.config(state="normal")

    def on_enter(self, event):
        """Handle Enter key press."""
        # Only send if not holding Shift
        if not event.state & 0x1:  # Check if Shift is not pressed
            self.send_message()
            return "break"  # Prevent default newline behavior

    def send_message(self):
        """Hand the user's message to the waiting GptCore main loop."""
        if not self.gpt_core:
            return

        user_message = self.input_text.get("1.0", "end-1c").strip()
        if not user_message:
            return

        self.display_conversation(
            self.gpt_core.messages + [{"role": "user", "content": user_message}]
        )

        self.input_text.delete("1.0", END)
        self._set_ui_busy()

        # Unblock the gui_input() callback in the background thread
        self._input_queue.put(user_message)

    # context switch to allow code to check CTRL+C in console
    def check(self):
        self.after(250, self.check)


def format_message(message):
    role = message["role"]
    content = extract_content(message["content"])

    if role == "user":
        # our renderer is also HTML interpret, so careful about <>
        # (One would think that this should go to LLM-produced text as well
        # but it almost always format its  correctly )
        content = content.replace("<", "&lt;").replace(">", "&gt;")

        # Prevent newlines entered by user (note that this has to go after the previous line)
        content = content.replace("\n", "<br />\n")

    if role == "assistant":
        # Math symbols formatting that our renderer does not support
        content = content.replace("\\(", "<i>").replace("\\)", "</i>")
        content = content.replace("\\[", "<i>").replace("\\]", "</i>")

    return f"**{role.upper()}:**\n\n{content}"


def extract_content(content):
    # New format is [{"type": "input_text", "text": <CONTENT>}, ...]
    if isinstance(content, list):
        for item in content:
            if (
                isinstance(item, dict)
                and item.get("type") == "input_text"
                and "text" in item
            ):
                return item["text"]

    # Old format is simply <CONTENT>
    return content


def format_json(conversation_json):
    return "\n\n".join([format_message(message) for message in conversation_json])


class CustomPygmentsRenderer(PygmentsRenderer):
    def __init__(self):
        super().__init__()
        self.formatter.nobackground = True
        self.formatter.prestyles = "font-family: monospace, monospace; font-weight: 500"


if __name__ == "__main__":
    app = JsonViewerApp()
    app.mainloop()
