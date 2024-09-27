import os
import json
import tkinter as tk
from tkinter import Listbox, Scrollbar, Text, END, RIGHT, Y, LEFT, BOTH
import html

from tkinterweb import HtmlFrame
from misaka import Markdown, HtmlRenderer
from pygments import highlight
from pygments.formatters import HtmlFormatter, ClassNotFound
from pygments.lexers import get_lexer_by_name

from core import DATA_DIRECTORY


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

        self.file_content_text = HtmlFrame(self.right_frame, messages_enabled = False)
        self.file_content_text.pack(fill=BOTH, expand=True)

        # Load the list of JSON files
        self.load_json_files()

        # Bind the listbox selection event to a function
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        self.md = Markdown(HighlighterRenderer(), extensions=('fenced-code',))

    def load_json_files(self):
        """Load the list of JSON files from the hardcoded folder."""
        if os.path.exists(DATA_DIRECTORY):
            json_files = sorted(
                [f for f in os.listdir(DATA_DIRECTORY) if f.endswith(".json")])
            print(json_files[-1])
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

            with open(file_path, "r") as file:
                file_content = json.load(file)
                formatted_content = self.md(format_json(file_content))
                # print(formatted_content)
                self.file_content_text.load_html(formatted_content)


class HighlighterRenderer(HtmlRenderer):
    def blockcode(self, text, lang):
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except ClassNotFound:
            lexer = None

        if lexer:
            formatter = HtmlFormatter(full=True, wrapcode=True, nobackground=False,
                                      style="xcode", prestyles="font-family: monospace")
            return highlight(text, lexer, formatter)
        # default
        return '\n<pre style="font-family: monospace">{}</pre>\n'.format(
                            html.escape(text.strip()))


def format_json(j):
    return "\n\n".join(
        [f"**{m["role"].upper()}:**\n\n{m["content"]}" for m in j])


if __name__ == "__main__":
    app = JsonViewerApp()
    app.mainloop()