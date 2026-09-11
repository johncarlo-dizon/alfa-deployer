import tkinter as tk
from tkinter import ttk, messagebox

from data_store import read_stores_raw, write_stores_raw


def show_store_editor_window(parent_root, on_save=None):
    """Opens an editable view of stores.txt. If on_save is given, it's
    called after a successful save so the caller can reload its store
    list/checkboxes without needing to know how."""
    win = tk.Toplevel(parent_root)
    win.title("Edit stores.txt")
    win.configure(bg="#f4f4f4")

    window_width = 720
    window_height = 520
    center_x = int((win.winfo_screenwidth() / 2) - (window_width / 2))
    center_y = int((win.winfo_screenheight() / 2) - (window_height / 2))
    win.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

    top_frame = tk.Frame(win, bg="#f4f4f4")
    top_frame.pack(fill="x", padx=8, pady=6)

    tk.Label(
        top_frame, text="Editing stores.txt — DC section header, then ip,user,pwd,name,code,pos",
        font=("Segoe UI", 8, "bold"), bg="#f4f4f4"
    ).pack(side="left")

    text_frame = tk.Frame(win, bg="#f4f4f4")
    text_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    editor = tk.Text(text_frame, font=("Consolas", 9), wrap="none", undo=True)
    v_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=editor.yview)
    h_scroll = ttk.Scrollbar(text_frame, orient="horizontal", command=editor.xview)
    editor.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    editor.grid(row=0, column=0, sticky="nsew")
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll.grid(row=1, column=0, sticky="ew")
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)

    editor.insert("1.0", read_stores_raw())

    btn_frame = tk.Frame(win, bg="#f4f4f4")
    btn_frame.pack(fill="x", padx=8, pady=(0, 8))

    def do_save():
        content = editor.get("1.0", tk.END)
        if content.endswith("\n"):
            content = content[:-1]
        try:
            write_stores_raw(content)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save stores.txt:\n{e}")
            return
        if on_save:
            on_save()
        messagebox.showinfo("Saved", "stores.txt updated and store list reloaded.")

    def do_close():
        win.destroy()

    tk.Button(btn_frame, text="💾 Save", font=("Segoe UI", 9, "bold"), bg="#28A745", fg="white", padx=15, pady=3, command=do_save).pack(side="left", padx=2)
    tk.Button(btn_frame, text="Close", font=("Segoe UI", 9), padx=15, pady=3, command=do_close).pack(side="left", padx=2)
