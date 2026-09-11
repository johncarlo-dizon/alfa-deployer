import tkinter as tk
from tkinter import ttk, messagebox

from log_manager import read_full_log, clear_full_log


def show_log_history_window(parent_root):
    win = tk.Toplevel(parent_root)
    win.title("Deployment Logs History")
    win.configure(bg="#f4f4f4")

    window_width = 720
    window_height = 520
    center_x = int((win.winfo_screenwidth() / 2) - (window_width / 2))
    center_y = int((win.winfo_screenheight() / 2) - (window_height / 2))
    win.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

    top_frame = tk.Frame(win, bg="#f4f4f4")
    top_frame.pack(fill="x", padx=8, pady=6)

    tk.Label(top_frame, text="Full Detailed Deployment Logs", font=("Segoe UI", 9, "bold"), bg="#f4f4f4").pack(side="left")

    text_frame = tk.Frame(win, bg="#f4f4f4")
    text_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    log_text = tk.Text(text_frame, font=("Consolas", 8), wrap="word")
    scroll = ttk.Scrollbar(text_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=scroll.set)

    log_text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    def load_content():
        log_text.config(state="normal")
        log_text.delete("1.0", tk.END)
        log_text.insert("1.0", read_full_log())
        log_text.config(state="disabled")
        log_text.see(tk.END)

    def do_clear():
        if messagebox.askyesno("Clear Log History", "This will permanently delete the saved log history file. Continue?"):
            if clear_full_log():
                load_content()
            else:
                messagebox.showerror("Error", "Could not clear the log file.")

    tk.Button(top_frame, text="🗑️ Clear History", font=("Segoe UI", 8), bg="#D9534F", fg="white", command=do_clear).pack(side="right")

    load_content()
