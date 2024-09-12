import os
import json
import tkinter as tk
from tkinter import Listbox, Scrollbar, Text, END, RIGHT, Y, LEFT, BOTH

from core import DATA_DIRECTORY


class JsonViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("JSON Viewer")
        self.geometry("800x600")

        # Create the left frame for the list of files
        self.left_frame = tk.Frame(self)
        self.left_frame.pack(side=LEFT, fill=tk.Y)

        # Create the right frame for the file content
        self.right_frame = tk.Frame(self)
        self.right_frame.pack(side=LEFT, fill=BOTH, expand=True)

        # Listbox to display the list of JSON files
        self.file_listbox = Listbox(self.left_frame, width=40)
        self.file_listbox.pack(side=LEFT, fill=tk.Y)

        # Scrollbar for the listbox
        self.scrollbar = Scrollbar(self.left_frame)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        # Attach the scrollbar to the listbox
        self.file_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.file_listbox.yview)

        # Text widget to display the content of the selected file
        self.file_content_text = Text(self.right_frame, wrap=tk.WORD)
        self.file_content_text.pack(fill=BOTH, expand=True)

        # Load the list of JSON files
        self.load_json_files()

        # Bind the listbox selection event to a function
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

    def load_json_files(self):
        """Load the list of JSON files from the hardcoded folder."""
        if os.path.exists(DATA_DIRECTORY):
            json_files = [f for f in os.listdir(DATA_DIRECTORY) if f.endswith(".json")]
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

            # Read and display the content of the selected file
            try:
                with open(file_path, "r") as file:
                    file_content = json.load(file)
                    formatted_content = json.dumps(file_content, indent=4)

                    # Clear the text widget and insert the new content
                    self.file_content_text.delete(1.0, END)
                    self.file_content_text.insert(END, formatted_content)
            except Exception as e:
                self.file_content_text.delete(1.0, END)
                self.file_content_text.insert(END, f"Error reading file: {e}")


if __name__ == "__main__":
    app = JsonViewerApp()
    app.mainloop()
