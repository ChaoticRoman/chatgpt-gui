#!/usr/bin/env python3
import os
import json
import threading
import tkinter as tk
from tkinter import (
    Listbox,
    Scrollbar,
    END,
    RIGHT,
    Y,
    LEFT,
    BOTH,
    BOTTOM,
    X,
    Text,
    Button,
)

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

        # Left: file list with scrollbar
        self.left_frame = tk.Frame(self.hpaned)
        self.file_listbox = Listbox(self.left_frame, width=30)
        self.file_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar = Scrollbar(self.left_frame)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.file_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.file_listbox.yview)
        self.hpaned.add(self.left_frame, minsize=150)

        # Right: vertical paned window for content | input
        self.vpaned = tk.PanedWindow(self.hpaned, orient=tk.VERTICAL, sashwidth=5)
        self.hpaned.add(self.vpaned, minsize=300)

        self.file_content_text = HtmlFrame(self.vpaned, messages_enabled=False)
        self.vpaned.add(self.file_content_text, minsize=100)

        # Input frame at the bottom (inside vertical paned window)
        self.input_frame = tk.Frame(self.vpaned)
        self.vpaned.add(self.input_frame, minsize=60)

        self.input_text = Text(self.input_frame, height=3)
        self.input_text.pack(side=LEFT, fill=BOTH, expand=True)

        self.send_button = Button(
            self.input_frame, text="Send", command=self.send_message
        )
        self.send_button.pack(side=RIGHT)

        # Bind Enter key to send message (Shift+Enter for newline)
        self.input_text.bind("<Return>", self.on_enter)

        # Core and conversation state
        self.current_file_path = None
        self.gpt_core = None

        # Load the list of JSON files
        self.load_json_files()

        # Bind the listbox selection event to a function
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # Killing with CTRL+C in the console
        self.check()

    def load_json_files(self):
        """Load the list of JSON files from the hardcoded folder."""
        if os.path.exists(DATA_DIRECTORY):
            json_files = sorted(
                [f for f in os.listdir(DATA_DIRECTORY) if f.endswith(".json")]
            )
            for file in json_files:
                self.file_listbox.insert(END, file)
        else:
            self.file_listbox.insert(END, "Folder not found")

    def on_file_select(self, event):
        """Display the content of the selected JSON file."""
        # Get the selected file name
        selected_index = self.file_listbox.curselection()
        if selected_index:
            selected_file = self.file_listbox.get(selected_index)

            # Construct the full file path
            file_path = os.path.join(DATA_DIRECTORY, selected_file)
            self.current_file_path = file_path

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
        """Initialize GptCore with existing conversation."""
        load_key()
        # Extract model from the conversation or use default
        model = DEFAULT_MODEL  # Default model

        # Create GptCore instance
        self.gpt_core = GptCore(
            input=lambda: None,  # Not used in GUI mode
            output=self.handle_output,
            model=model,
        )

        # Load existing messages into GptCore
        self.gpt_core.messages = [
            {"role": m["role"], "content": m["content"]} for m in existing_messages
        ]
        self.gpt_core.file = file_path

    def on_enter(self, event):
        """Handle Enter key press."""
        # Only send if not holding Shift
        if not event.state & 0x1:  # Check if Shift is not pressed
            self.send_message()
            return "break"  # Prevent default newline behavior

    def send_message(self):
        """Send user message and get AI response."""
        if not self.gpt_core:
            return

        # Get user input
        user_message = self.input_text.get("1.0", "end-1c").strip()
        if not user_message:
            return

        self.display_conversation(
            self.gpt_core.messages + [{"role": "user", "content": user_message}]
        )

        # Clear input field
        self.input_text.delete("1.0", END)

        # Disable input while processing
        self.send_button.config(state="disabled")
        self.input_text.config(state="disabled")

        threading.Thread(
            target=self.get_ai_response, args=(user_message,), daemon=True
        ).start()

    def get_ai_response(self, user_message):
        """Get AI response (runs in separate thread)."""
        try:
            self.gpt_core.send(user_message)

            # Update display with new message
            self.after(0, lambda: self.display_conversation(self.gpt_core.messages))

        finally:
            # Re-enable input
            self.after(0, lambda: self.send_button.config(state="normal"))
            self.after(0, lambda: self.input_text.config(state="normal"))
            self.after(0, lambda: self.input_text.focus())

    def handle_output(self, content, info):
        """Handle output from GptCore (callback)."""
        # This is called by GptCore but we handle display differently in GUI
        pass

    # context switch to allow code to check CTRL+C in console
    def check(self):
        self.after(250, self.check)


def format_json(j):
    return "\n\n".join([f"**{m['role'].upper()}:**\n\n{m['content']}" for m in j])


class CustomPygmentsRenderer(PygmentsRenderer):
    def __init__(self):
        super().__init__()
        self.formatter.nobackground = True
        self.formatter.prestyles = "font-family: monospace, monospace; font-weight: 500"


if __name__ == "__main__":
    app = JsonViewerApp()
    app.mainloop()
