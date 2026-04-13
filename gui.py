#!/usr/bin/env python3
import os
import json
import queue
import threading
import tkinter as tk
from pathlib import Path
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
from tkinter import font as tkfont
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

        ttk.Style().configure("File.Treeview", font="TkFixedFont")

        # Horizontal paned window: file list | conversation
        # Status bar at the very bottom showing last response info
        self.status_bar = tk.Label(
            self,
            text="",
            anchor="w",
            justify="left",
            font=tkfont.nametofont("TkFixedFont"),
            relief="sunken",
            bd=1,
            padx=4,
            pady=2,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.hpaned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5)
        self.hpaned.pack(fill=BOTH, expand=True)

        # Left: new conversation button + file table with scrollbar
        self.left_frame = tk.Frame(self.hpaned)
        self.new_conv_button = Button(
            self.left_frame,
            text="New Conversation",
            command=self.new_conversation,
            font=("TkDefaultFont", 10, "bold"),
        )
        self.new_conv_button.pack(side=tk.TOP, fill=tk.X)
        self.table_frame = tk.Frame(self.left_frame)
        self.table_frame.pack(side=tk.TOP, fill=BOTH, expand=True)
        self.file_table = ttk.Treeview(
            self.table_frame,
            columns=("file",),
            show="headings",
            selectmode="browse",
            style="File.Treeview",
        )
        self.file_table.heading("file", text="Conversation", command=self.toggle_sort)
        self.file_table.column("file", anchor="w")
        self.file_table.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar = Scrollbar(self.table_frame, command=self.file_table.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.file_table.config(yscrollcommand=self.scrollbar.set)
        self.file_table.tag_configure("unsaved", foreground="gray")
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

        # Core and conversation state:
        #   _cores       — one live GptCore (with its thread) per file path; reused on
        #                  switch-back so in-progress requests survive navigation
        #   _busy_paths  — file paths whose cores are currently waiting for a response
        #   _drafts      — unsent input text saved per file path across switches
        #   _sash_pos    — vpaned sash position saved while the input area is collapsed
        self.current_file_path = None
        self.gpt_core = None
        self._cores = {}
        self._busy_paths = set()
        self._drafts = {}
        self._sash_pos = None

        # Load the list of JSON files
        self.load_json_files()

        # Bind the table selection event to a function
        self.file_table.bind("<<TreeviewSelect>>", self.on_file_select)

        # Auto-select the first conversation, or open a ghost if there are none
        children = self.file_table.get_children()
        if children and os.path.exists(DATA_DIRECTORY):
            self.file_table.selection_set(children[0])
        else:
            self.new_conversation()

        # Set initial left-pane width after the first render (scrollbar width then known)
        self.after(0, self._fit_left_pane)

        # Killing with CTRL+C in the console
        self.check()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _fit_left_pane(self):
        self.update_idletasks()
        fixed = tkfont.nametofont("TkFixedFont")
        widths = [
            fixed.measure(self.file_table.item(i)["values"][0])
            for i in self.file_table.get_children()
        ]
        fallback = fixed.measure("2026-04-13T10:30:00-abc123.json")
        col_w = (max(widths) if widths else fallback) + 16
        sb_w = self.scrollbar.winfo_width() or 17
        self.file_table.column("file", width=col_w)
        self.hpaned.sash_place(0, col_w + sb_w, 0)

    def _on_close(self):
        for core in self._cores.values():
            core._input_queue.put(None)
        self.destroy()

    def load_json_files(self):
        """Load the list of JSON files from the hardcoded folder."""
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        if os.path.exists(DATA_DIRECTORY):
            for file in sorted(
                [f for f in os.listdir(DATA_DIRECTORY) if f.endswith(".json")],
                reverse=self.sort_descending,
            ):
                self.file_table.insert("", END, values=(file,))
        # Re-add unsaved conversations that exist in memory but not yet on disk
        for core in getattr(self, "_cores", {}).values():
            if not Path(core.file).exists():
                pos = 0 if self.sort_descending else END
                self.file_table.insert(
                    "", pos, values=(Path(core.file).name,), tags=("unsaved",)
                )

    def toggle_sort(self):
        """Toggle sort order and reload file list."""
        self.sort_descending = not self.sort_descending
        self.load_json_files()

    def _save_draft(self):
        """Persist the current input box contents for the active conversation."""
        if self.gpt_core:
            self._drafts[str(self.gpt_core.file)] = self.input_text.get("1.0", "end-1c")

    def _restore_draft(self, file_path):
        """Populate the input box with any saved draft for file_path."""
        self.input_text.delete("1.0", END)
        draft = self._drafts.get(str(file_path), "")
        if draft:
            self.input_text.insert("1.0", draft)

    def on_file_select(self, event):
        """Display the content of the selected JSON file."""
        selection = self.file_table.selection()
        if not selection:
            return

        file_name = self.file_table.item(selection[0])["values"][0]
        file_path = os.path.join(DATA_DIRECTORY, file_name)

        # Skip reinit when this is already the active conversation (e.g. after
        # _select_file_in_list is called programmatically for a new conversation)
        if self.gpt_core and Path(file_path) == Path(self.gpt_core.file):
            return

        self._save_draft()
        self.current_file_path = file_path

        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                file_content = json.load(f)
            self.initialize_gpt_core(file_content, file_path)
            self.display_conversation(file_content)
        else:
            # Unsaved new conversation: restore state from the in-memory core
            self.initialize_gpt_core([], file_path)
            self.display_conversation(self.gpt_core.messages)

        # Restore draft unconditionally so the input is correct when busy state ends
        self._restore_draft(file_path)
        if str(file_path) in self._busy_paths:
            self._set_ui_busy()
        else:
            self._set_ui_idle()

    def display_conversation(self, messages):
        """Display conversation messages as formatted HTML."""
        formatted_content = markdown(format_json(messages), CustomPygmentsRenderer)
        self.file_content_text.load_html(formatted_content)

    def initialize_gpt_core(self, existing_messages, file_path):
        """Attach to an existing GptCore for this conversation, or start a new one."""
        key = str(file_path)
        if key in self._cores:
            self.gpt_core = self._cores[key]
            return
        load_key()
        core = GptCore(input=None, output=None, model=DEFAULT_MODEL)
        core.messages = [
            {"role": m["role"], "content": m["content"]} for m in existing_messages
        ]
        core.file = file_path
        self._launch_core(core)

    def new_conversation(self):
        """Start a blank conversation — GptCore.__init__ sets messages=[] and a fresh file path."""
        self._save_draft()
        load_key()
        core = GptCore(input=None, output=None, model=DEFAULT_MODEL)
        self._launch_core(core)
        self._set_ui_idle()
        self.input_text.delete("1.0", END)
        self.file_table.selection_remove(*self.file_table.selection())
        # Add a gray placeholder entry so the user can navigate back before the first save
        file_name = Path(core.file).name
        pos = 0 if self.sort_descending else END
        self.file_table.insert("", pos, values=(file_name,), tags=("unsaved",))
        self._select_file_in_list(file_name)
        self.display_conversation([])

    def _launch_core(self, core):
        """Wire up GUI callbacks to a GptCore instance and start its main loop thread.

        Each core owns its queue (core._input_queue) and thread (core._thread).
        Closures capture the specific core instance so that responses from a
        previous session on the same conversation are silently ignored.
        """
        core._input_queue = queue.Queue()
        self.gpt_core = core
        self._cores[str(core.file)] = core

        def gui_input():
            # Blocks until send_message() puts a prompt (or None) in the queue.
            return core._input_queue.get()

        def gui_output(content, info):
            # Called from the background thread; schedule GUI update on main thread.
            def update():
                self._busy_paths.discard(str(core.file))
                self.status_bar.config(text=repr(info))
                # Guard: skip display/UI updates if the user switched away.
                if self.gpt_core is core:
                    self.display_conversation(core.messages)
                    self._set_ui_idle()
                    self.input_text.focus()
                    # Scroll after a short delay to let tkinterweb finish layout
                    self.after(100, lambda: self.file_content_text.yview_moveto(1.0))
                    self._select_file_in_list(Path(core.file).name)

            self.after(0, update)

        def on_save():
            # Called from the background thread after every _save(); schedule a
            # list refresh on the main thread so new conversations appear immediately.
            self.after(0, lambda: self._refresh_list_if_new(core))

        core.input = gui_input
        core.output = gui_output
        core.save_callback = on_save

        core._thread = threading.Thread(target=core.main, daemon=True)
        core._thread.start()

    def _set_ui_busy(self):
        self._sash_pos = self.vpaned.sash_coord(0)
        self.input_row.pack_forget()
        self.progress_bar.pack(fill=tk.X, expand=True)
        self.progress_bar.start(10)
        # Collapse the input pane to just the progress bar height.
        # update_idletasks() flushes the pack changes so winfo_height() is accurate.
        self.vpaned.paneconfigure(self.input_frame, minsize=1)
        self.update_idletasks()
        pb_h = self.progress_bar.winfo_height() or 20
        self.vpaned.sash_place(0, self._sash_pos[0], self.vpaned.winfo_height() - pb_h)

    def _set_ui_idle(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.input_row.pack(side=tk.TOP, fill=BOTH, expand=True)
        self.vpaned.paneconfigure(self.input_frame, minsize=60)
        if self._sash_pos is not None:
            self.vpaned.sash_place(0, self._sash_pos[0], self._sash_pos[1])
            self._sash_pos = None

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
        self._busy_paths.add(str(self.gpt_core.file))
        self._set_ui_busy()

        # Unblock the gui_input() callback in the background thread
        self.gpt_core._input_queue.put(user_message)

    def _refresh_list_if_new(self, core):
        """On first save of a new conversation, clear the gray 'unsaved' tag."""
        file_name = Path(core.file).name
        for item in self.file_table.get_children():
            row = self.file_table.item(item)
            if row["values"][0] == file_name and "unsaved" in row["tags"]:
                self.file_table.item(item, tags=())
                return
        # Fallback: file appeared without going through new_conversation (shouldn't happen)
        if file_name not in {
            self.file_table.item(i)["values"][0] for i in self.file_table.get_children()
        }:
            active_name = Path(self.gpt_core.file).name if self.gpt_core else None
            self.load_json_files()
            if active_name:
                self._select_file_in_list(active_name)

    def _select_file_in_list(self, filename):
        """Select the row matching filename in the treeview."""
        for item in self.file_table.get_children():
            if self.file_table.item(item)["values"][0] == filename:
                self.file_table.selection_set(item)
                self.file_table.see(item)
                break

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
