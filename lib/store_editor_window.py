import tkinter as tk
from tkinter import ttk, messagebox

from data_store import read_stores_raw, write_stores_raw

# ---------------------------------------------------------------------------
# Theme constants (kept in sync with the main dashboard's dark palette)
# ---------------------------------------------------------------------------
COLOR_BG = "#14161f"
COLOR_PANEL = "#1c1f2b"
COLOR_PANEL_ALT = "#11131b"
COLOR_PANEL_ALT_TEXT = "#c9cde0"
COLOR_FIELD = "#242838"
COLOR_BORDER = "#2e3346"
COLOR_TEXT = "#e7e9f5"
COLOR_TEXT_MUTED = "#8b90a8"
COLOR_ACCENT = "#9b6bff"
COLOR_SUCCESS = "#2fbf6d"
COLOR_SUCCESS_DARK = "#239c58"

FONT_LABEL = ("Segoe UI", 8, "bold")
FONT_BTN = ("Segoe UI", 9, "bold")
FONT_BTN_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 9)


def _init_ttk_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            background=COLOR_FIELD, troughcolor=COLOR_PANEL_ALT,
            bordercolor=COLOR_PANEL_ALT, arrowcolor=COLOR_TEXT_MUTED,
            relief="flat", borderwidth=0, gripcount=0,
        )
        style.map(
            f"{orient}.TScrollbar",
            background=[("active", COLOR_ACCENT), ("pressed", COLOR_ACCENT)],
            arrowcolor=[("active", COLOR_TEXT)],
        )


def _style_button(btn, bg, fg="white", hover=None):
    hover = hover or bg
    btn.configure(bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                  relief="flat", bd=0, cursor="hand2", highlightthickness=0)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def show_store_editor_window(parent_root, on_save=None):
    """Opens an editable view of stores.txt. If on_save is given, it's
    called after a successful save so the caller can reload its store
    list/checkboxes without needing to know how."""
    win = tk.Toplevel(parent_root)
    win.title("Edit stores.txt")
    win.configure(bg=COLOR_BG)
    _init_ttk_style()

    window_width = 720
    window_height = 440
    center_x = int((win.winfo_screenwidth() / 2) - (window_width / 2))
    center_y = int((win.winfo_screenheight() / 2) - (window_height / 2))
    win.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

    top_frame = tk.Frame(win, bg=COLOR_PANEL_ALT)
    top_frame.pack(fill="x")
    accent_strip = tk.Frame(top_frame, bg=COLOR_ACCENT, width=3)
    accent_strip.pack(side="left", fill="y")

    tk.Label(
        top_frame, text="EDITING STORES.TXT — DC section header, then ip,user,pwd,name,code,pos",
        font=FONT_LABEL, bg=COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, padx=8, pady=5
    ).pack(side="left", fill="x")

    text_frame = tk.Frame(win, bg=COLOR_BG, highlightthickness=1, highlightbackground=COLOR_BORDER)
    text_frame.pack(fill="both", expand=True, padx=8, pady=6)

    editor = tk.Text(text_frame, font=FONT_MONO, wrap="none", undo=True,
                      bg=COLOR_FIELD, fg=COLOR_TEXT, relief="flat", bd=0,
                      highlightthickness=0, insertbackground=COLOR_TEXT,
                      padx=6, pady=6)
    v_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=editor.yview)
    h_scroll = ttk.Scrollbar(text_frame, orient="horizontal", command=editor.xview)
    editor.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    editor.grid(row=0, column=0, sticky="nsew")
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll.grid(row=1, column=0, sticky="ew")
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)

    editor.insert("1.0", read_stores_raw())

    btn_frame = tk.Frame(win, bg=COLOR_BG)
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

    save_btn = tk.Button(btn_frame, text="💾 Save", font=FONT_BTN, padx=15, pady=3, command=do_save)
    _style_button(save_btn, COLOR_SUCCESS, hover=COLOR_SUCCESS_DARK)
    save_btn.pack(side="left", padx=2)

    close_btn = tk.Button(btn_frame, text="Close", font=FONT_BTN_SMALL, padx=15, pady=3, command=do_close)
    _style_button(close_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
    close_btn.pack(side="left", padx=2)