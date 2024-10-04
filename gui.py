import tkinter as tk
from tkinter import scrolledtext

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.create_widgets()

    def create_widgets(self):
        # Create a frame for the text boxes
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Create a scrollable text box for the chat history
        self.chat_history = scrolledtext.ScrolledText(self.frame, state='disabled')
        self.chat_history.pack(fill=tk.BOTH, expand=True)

        # Create a smaller text box for the chat input
        self.chat_input = tk.Text(self.frame, height=3)
        self.chat_input.pack(fill=tk.X, expand=True)

        # Bind the Enter key to the send_message method
        self.chat_input.bind('<Return>', self.send_message)

    def send_message(self, event):
        # Get the message from the chat input
        message = self.chat_input.get('1.0', tk.END).strip()

        # Clear the chat input
        self.chat_input.delete('1.0', tk.END)

        # Add the message to the chat history
        self.chat_history.configure(state='normal')
        self.chat_history.insert(tk.END, message + '\n')
        self.chat_history.configure(state='disabled')

        # Scroll to the bottom of the chat history
        self.chat_history.yview(tk.END)

root = tk.Tk()
app = ChatApp(root)
root.mainloop()
