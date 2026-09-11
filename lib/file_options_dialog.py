import tkinter as tk

# ---------------------------------------------------------------------------
# Theme constants (kept in sync with the main dashboard's dark palette)
# ---------------------------------------------------------------------------
COLOR_BG = "#14161f"
COLOR_TEXT = "#e7e9f5"
COLOR_ACCENT = "#9b6bff"
COLOR_SUCCESS = "#2fbf6d"
COLOR_SUCCESS_DARK = "#239c58"


def _style_button(btn, bg, fg="white", hover=None):
    hover = hover or bg
    btn.configure(bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                  relief="flat", bd=0, cursor="hand2", highlightthickness=0)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def show_file_options_dialog(parent_root, file_entry):
    """Modal dialog for one queued file's per-file deploy options.
    file_entry is a dict with at least {"name", "run_as_admin",
    "replace_if_exists"} — this function edits it in place and blocks
    until the dialog is closed."""
    win = tk.Toplevel(parent_root)
    win.title(file_entry["name"])
    win.configure(bg=COLOR_BG)
    win.resizable(False, False)
    win.transient(parent_root)
    win.grab_set()

    window_width = 320
    window_height = 170
    center_x = int((win.winfo_screenwidth() / 2) - (window_width / 2))
    center_y = int((win.winfo_screenheight() / 2) - (window_height / 2))
    win.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

    tk.Label(
        win, text=file_entry["name"], font=("Segoe UI", 9, "bold"),
        bg=COLOR_BG, fg=COLOR_ACCENT, wraplength=290
    ).pack(pady=(10, 6))

    admin_var = tk.BooleanVar(value=file_entry.get("run_as_admin", False))
    replace_var = tk.BooleanVar(value=file_entry.get("replace_if_exists", True))

    opts_frame = tk.Frame(win, bg=COLOR_BG)
    opts_frame.pack(pady=2)

    tk.Checkbutton(
        opts_frame, text="Run as Administrator", variable=admin_var,
        bg=COLOR_BG, fg=COLOR_TEXT, activebackground=COLOR_BG, activeforeground=COLOR_TEXT,
        selectcolor="#242838", anchor="w", font=("Segoe UI", 8)
    ).pack(anchor="w", pady=2)

    tk.Checkbutton(
        opts_frame, text="Replace the old if already exist", variable=replace_var,
        bg=COLOR_BG, fg=COLOR_TEXT, activebackground=COLOR_BG, activeforeground=COLOR_TEXT,
        selectcolor="#242838", anchor="w", font=("Segoe UI", 8)
    ).pack(anchor="w", pady=2)

    def do_ok():
        file_entry["run_as_admin"] = admin_var.get()
        file_entry["replace_if_exists"] = replace_var.get()
        win.destroy()

    ok_btn = tk.Button(win, text="OK", font=("Segoe UI", 9, "bold"), padx=18, pady=2, command=do_ok)
    _style_button(ok_btn, COLOR_SUCCESS, hover=COLOR_SUCCESS_DARK)
    ok_btn.pack(pady=(10, 8))

    win.wait_window()