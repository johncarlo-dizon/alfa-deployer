import tkinter as tk


def show_file_options_dialog(parent_root, file_entry):
    """Modal dialog for one queued file's per-file deploy options.
    file_entry is a dict with at least {"name", "run_as_admin",
    "replace_if_exists"} — this function edits it in place and blocks
    until the dialog is closed."""
    win = tk.Toplevel(parent_root)
    win.title(file_entry["name"])
    win.configure(bg="#FFFFFF")
    win.resizable(False, False)
    win.transient(parent_root)
    win.grab_set()

    window_width = 340
    window_height = 220
    center_x = int((win.winfo_screenwidth() / 2) - (window_width / 2))
    center_y = int((win.winfo_screenheight() / 2) - (window_height / 2))
    win.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

    tk.Label(
        win, text=file_entry["name"], font=("Segoe UI", 10, "bold"),
        bg="#FFFFFF", wraplength=300
    ).pack(pady=(14, 10))

    admin_var = tk.BooleanVar(value=file_entry.get("run_as_admin", False))
    replace_var = tk.BooleanVar(value=file_entry.get("replace_if_exists", True))

    opts_frame = tk.Frame(win, bg="#FFFFFF")
    opts_frame.pack(pady=4)

    tk.Checkbutton(
        opts_frame, text="Run as Administrator", variable=admin_var,
        bg="#FFFFFF", anchor="w", font=("Segoe UI", 9)
    ).pack(anchor="w", pady=3)

    tk.Checkbutton(
        opts_frame, text="Replace the old if already exist", variable=replace_var,
        bg="#FFFFFF", anchor="w", font=("Segoe UI", 9)
    ).pack(anchor="w", pady=3)

    def do_ok():
        file_entry["run_as_admin"] = admin_var.get()
        file_entry["replace_if_exists"] = replace_var.get()
        win.destroy()

    tk.Button(
        win, text="OK", font=("Segoe UI", 9, "bold"), bg="#28A745", fg="white",
        padx=20, pady=3, bd=0, command=do_ok
    ).pack(pady=(14, 10))

    win.wait_window()
