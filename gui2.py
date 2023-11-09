import tkinter as tk
from tkinter import scrolledtext
import core

class GptGui:
    def __init__(self, root):
        self.core = core.GptCore(self.gui_input, self.gui_output)

        self.root = root
        self.root.title("GPT-4 GUI")

        self.text_area = scrolledtext.ScrolledText(root)
        self.text_area.pack(padx=10, pady=10)

        self.entry_text = tk.StringVar()
        self.entry = tk.Entry(root, textvariable=self.entry_text)
        self.entry.bind("<Return>", self.send_message)
        self.entry.pack(padx=10, pady=10)

        self.send_button = tk.Button(root, text="Send", command=self.send_message)
        self.send_button.pack(padx=10, pady=10)

        self.message_queue = []

    def gui_input(self):
        if self.message_queue:
            return self.message_queue.pop(0)

    def gui_output(self, msg, info):
        self.text_area.insert(tk.END, f"\n{msg}\n{info}\n")
        self.text_area.see(tk.END)

    def send_message(self, event=None):
        message = self.entry_text.get()
        self.entry_text.set("")
        self.message_queue.append(message)
        self.core.main()

    def run(self):
        self.root.mainloop()

def main():
    root = tk.Tk()
    gui = GptGui(root)
    gui.run()

if __name__ == "__main__":
    main()
