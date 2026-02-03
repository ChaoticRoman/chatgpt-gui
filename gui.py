#!/usr/bin/env python3
import os
import json
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

        self.title("JSON Viewer")
        self.geometry("800x600")

        self.left_frame = tk.Frame(self)
        self.left_frame.pack(side=LEFT, fill=tk.Y)

        self.right_frame = tk.Frame(self)
        self.right_frame.pack(side=LEFT, fill=BOTH, expand=True)

        self.file_listbox = Listbox(self.left_frame, width=40)
        self.file_listbox.pack(side=LEFT, fill=tk.Y)
        self.scrollbar = Scrollbar(self.left_frame)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.file_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.file_listbox.yview)

        self.file_content_text = HtmlFrame(self.right_frame, messages_enabled=False)
        self.file_content_text.pack(fill=BOTH, expand=True)

        # Input frame at the bottom
        self.input_frame = tk.Frame(self.right_frame)
        self.input_frame.pack(side=BOTTOM, fill=X)

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
        self.gpt_core.messages = existing_messages.copy()
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

        # Clear input field
        self.input_text.delete("1.0", END)

        # Add user message to conversation
        self.gpt_core.messages.append({"role": "user", "content": user_message})

        # Update display to show user message
        self.display_conversation(self.gpt_core.messages)

        # Disable input while processing
        self.send_button.config(state="disabled")
        self.input_text.config(state="disabled")

        # Get AI response in separate thread to avoid blocking UI
        import threading

        threading.Thread(target=self.get_ai_response, daemon=True).start()

    def get_ai_response(self):
        """Get AI response (runs in separate thread)."""
        try:
            response = self.gpt_core.client.chat.completions.create(
                model=self.gpt_core.model, messages=self.gpt_core.messages
            )

            message = response.choices[0].message
            self.gpt_core.messages.append(dict(message))

            # Save to file
            serialized = [dict(m) for m in self.gpt_core.messages]
            with open(self.gpt_core.file, "w") as f:
                json.dump(serialized, f, sort_keys=True, indent=4)

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
