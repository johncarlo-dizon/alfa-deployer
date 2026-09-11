import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import DEFAULT_REMOTE_DIR
from data_store import load_stores
from ui_utils import adjust_window_geometry
from log_manager import append_full_log
from log_history_window import show_log_history_window
from store_editor_window import show_store_editor_window
from file_options_dialog import show_file_options_dialog
from deploy_worker import start_deployment


# ---------------------------------------------------------------------------
# Theme constants (UI only — no functional meaning) — dark theme
# ---------------------------------------------------------------------------
COLOR_BG = "#14161f"              # app background
COLOR_PANEL = "#1c1f2b"           # card/body background
COLOR_PANEL_ALT = "#11131b"       # header strip / secondary surfaces (darker than body)
COLOR_PANEL_ALT_TEXT = "#c9cde0"  # text on the header strip / secondary surfaces
COLOR_FIELD = "#242838"           # inputs (listbox/text/entry) — slightly lighter than panel
COLOR_BORDER = "#2e3346"
COLOR_TEXT = "#e7e9f5"
COLOR_TEXT_MUTED = "#8b90a8"
COLOR_ACCENT = "#9b6bff"          # violet accent
COLOR_ACCENT_DARK = "#7f4ff2"
COLOR_SUCCESS = "#2fbf6d"
COLOR_SUCCESS_DARK = "#239c58"
COLOR_DANGER = "#f0546a"
COLOR_WARNING = "#e0a53d"

FONT_BASE = ("Segoe UI", 8)
FONT_BASE_BOLD = ("Segoe UI", 8, "bold")
FONT_HEADER = ("Segoe UI Semibold", 8, "bold")
FONT_SMALL = ("Segoe UI", 7)
FONT_SMALL_BOLD = ("Segoe UI", 7, "bold")
FONT_SMALL_ITALIC = ("Segoe UI", 7, "italic")
FONT_MONO = ("Consolas", 8)
FONT_MONO_SMALL = ("Consolas", 7)

# Compact spacing scale used throughout (kept in one place so density is easy to tune)
PAD_OUTER = 8
PAD_PANEL_X = 6
PAD_PANEL_Y = 4
PAD_ROW = 3


def _style_button(btn, bg, fg="white", hover=None, active=None):
    """Give a tk.Button flat, modern styling with a hover effect."""
    hover = hover or bg
    active = active or bg
    btn.configure(
        bg=bg, fg=fg, activebackground=active, activeforeground=fg,
        relief="flat", bd=0, cursor="hand2", padx=10, pady=5,
        highlightthickness=0,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


class AlfaDeployDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("AlfaDeploy — File Deployer")
        adjust_window_geometry(self.root)
        self._compact_window_height()
        self.root.configure(bg=COLOR_BG)

        self._init_ttk_style()

        self.stores = load_stores()
        self.store_vars = {}
        self.deploy_files = []  # list of {"path","name","run_as_admin","replace_if_exists"}
        self.log_queue = queue.Queue()
        self.failed_stores = []
        self.success_stores = []

        main_container = tk.Frame(self.root, bg=COLOR_BG)
        main_container.pack(fill="both", expand=True, padx=PAD_OUTER, pady=6)

        top_row = tk.Frame(main_container, bg=COLOR_BG)
        top_row.pack(fill="both", expand=False, pady=(0, 5))
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)

        self._build_files_panel(top_row)
        self._build_commands_panel(top_row)

        bottom_row = tk.Frame(main_container, bg=COLOR_BG)
        bottom_row.pack(fill="both", expand=True, pady=(5, 0))
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=1)
        bottom_row.grid_rowconfigure(0, weight=1)

        self._build_store_panel(bottom_row)
        self._build_log_panel(bottom_row)

        self.populate_store_checkboxes()

    # ---------- Window sizing (UI only) ----------
    def _compact_window_height(self):
        """Shrinks the height that adjust_window_geometry set, keeping width/position.
        Purely cosmetic — does not change adjust_window_geometry's own behavior."""
        self.root.update_idletasks()
        try:
            geo = self.root.geometry()  # "WxH+X+Y"
            size_part, sep, pos_part = geo.partition("+")
            width_str, height_str = size_part.split("x")
            width, height = int(width_str), int(height_str)
            compact_height = max(540, int(height * 0.72))
            new_geo = f"{width}x{compact_height}+{pos_part}" if pos_part else f"{width}x{compact_height}"
            self.root.geometry(new_geo)
            self.root.minsize(width, min(540, compact_height))
        except Exception:
            pass

    # ---------- ttk theming ----------
    def _init_ttk_style(self):
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
        style.configure("Horizontal.TProgressbar", troughcolor=COLOR_FIELD,
                         background=COLOR_ACCENT, bordercolor=COLOR_FIELD,
                         lightcolor=COLOR_ACCENT, darkcolor=COLOR_ACCENT, thickness=8)

    def _panel(self, parent, title):
        """A card-style LabelFrame replacement with a compact dark header strip."""
        outer = tk.Frame(parent, bg=COLOR_BORDER, bd=0)
        inner = tk.Frame(outer, bg=COLOR_PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        header = tk.Frame(inner, bg=COLOR_PANEL_ALT)
        header.pack(fill="x")
        accent_strip = tk.Frame(header, bg=COLOR_ACCENT, width=3)
        accent_strip.pack(side="left", fill="y")
        tk.Label(header, text=title.strip().upper(), font=FONT_HEADER, bg=COLOR_PANEL_ALT,
                 fg=COLOR_PANEL_ALT_TEXT, anchor="w", padx=8, pady=3).pack(side="left", fill="x")

        body = tk.Frame(inner, bg=COLOR_PANEL, padx=PAD_PANEL_X, pady=PAD_PANEL_Y)
        body.pack(fill="both", expand=True)
        return outer, body

    # ---------- Files To Deploy ----------
    def _build_files_panel(self, parent):
        outer, body = self._panel(parent, "Files To Deploy")
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        btn_row = tk.Frame(body, bg=COLOR_PANEL)
        btn_row.pack(fill="x", pady=(0, PAD_ROW))
        choose_btn = tk.Button(btn_row, text="＋ Choose File", font=FONT_SMALL_BOLD, command=self.choose_files)
        _style_button(choose_btn, COLOR_ACCENT, hover=COLOR_ACCENT_DARK)
        choose_btn.configure(padx=8, pady=2)
        choose_btn.pack(side="left")

        remove_btn = tk.Button(btn_row, text="Remove Selected", font=FONT_SMALL, command=self.remove_selected_file)
        _style_button(remove_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
        remove_btn.configure(padx=8, pady=2)
        remove_btn.pack(side="left", padx=4)

        tk.Label(btn_row, text="(double-click a file for options)", font=FONT_SMALL_ITALIC,
                 fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL).pack(side="left", padx=4)

        list_frame = tk.Frame(body, bg=COLOR_PANEL, highlightthickness=1, highlightbackground=COLOR_BORDER)
        list_frame.pack(fill="both", expand=True)

        self.files_listbox = tk.Listbox(
            list_frame, font=FONT_MONO, height=4, selectmode="extended",
            bg=COLOR_FIELD, fg=COLOR_TEXT, relief="flat", bd=0,
            highlightthickness=0, selectbackground=COLOR_ACCENT, selectforeground="white",
            activestyle="none",
        )
        files_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=files_scroll.set)
        self.files_listbox.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=3)
        files_scroll.pack(side="right", fill="y")
        self.files_listbox.bind("<Double-Button-1>", self.open_file_options)

    def choose_files(self):
        paths = filedialog.askopenfilenames(title="Choose files to deploy")
        for path in paths:
            name = os.path.basename(path)
            if any(f["path"] == path for f in self.deploy_files):
                continue
            self.deploy_files.append({
                "path": path, "name": name,
                "run_as_admin": False, "replace_if_exists": True
            })
        self.refresh_files_listbox()

    def remove_selected_file(self):
        selected = list(self.files_listbox.curselection())
        for idx in reversed(selected):
            del self.deploy_files[idx]
        self.refresh_files_listbox()

    def refresh_files_listbox(self):
        self.files_listbox.delete(0, tk.END)
        for f in self.deploy_files:
            tags = []
            if f.get("run_as_admin"):
                tags.append("admin")
            if not f.get("replace_if_exists", True):
                tags.append("no-replace")
            suffix = f"  [{', '.join(tags)}]" if tags else ""
            self.files_listbox.insert(tk.END, f["name"] + suffix)

    def open_file_options(self, event):
        selected = self.files_listbox.curselection()
        if not selected:
            return
        idx = selected[0]
        show_file_options_dialog(self.root, self.deploy_files[idx])
        self.refresh_files_listbox()

    # ---------- Commands ----------
    def _build_commands_panel(self, parent):
        outer_wrap = tk.Frame(parent, bg=COLOR_BG)
        outer_wrap.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        cmd_outer, cmd_body = self._panel(outer_wrap, "Commands")
        cmd_outer.pack(fill="x")

        header_row = tk.Frame(cmd_body, bg=COLOR_PANEL)
        header_row.pack(fill="x")
        self.execution_order_var = tk.StringVar(value="files_first")
        order_frame = tk.Frame(header_row, bg=COLOR_PANEL)
        order_frame.pack(side="right")
        tk.Label(order_frame, text="Order:", font=FONT_SMALL, bg=COLOR_PANEL, fg=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 4))
        tk.Radiobutton(order_frame, text="Files First", variable=self.execution_order_var,
                       value="files_first", bg=COLOR_PANEL, fg=COLOR_TEXT, font=FONT_SMALL,
                       selectcolor=COLOR_PANEL, activebackground=COLOR_PANEL).pack(side="left")
        tk.Radiobutton(order_frame, text="Commands First", variable=self.execution_order_var,
                       value="commands_first", bg=COLOR_PANEL, fg=COLOR_TEXT, font=FONT_SMALL,
                       selectcolor=COLOR_PANEL, activebackground=COLOR_PANEL).pack(side="left", padx=(4, 0))

        text_wrap = tk.Frame(cmd_body, bg=COLOR_PANEL, highlightthickness=1, highlightbackground=COLOR_BORDER)
        text_wrap.pack(fill="x", pady=(3, 0))
        self.command_text = tk.Text(text_wrap, height=2, font=FONT_MONO_SMALL, bg=COLOR_FIELD,
                                     fg=COLOR_TEXT, relief="flat", bd=0, highlightthickness=0,
                                     insertbackground=COLOR_TEXT, padx=4, pady=3)
        self.command_text.pack(fill="x")

        dir_outer, dir_body = self._panel(outer_wrap, "Remote Directory")
        dir_outer.pack(fill="x", pady=(4, 0))
        entry_wrap = tk.Frame(dir_body, bg=COLOR_PANEL, highlightthickness=1, highlightbackground=COLOR_BORDER)
        entry_wrap.pack(fill="x")
        self.remote_dir_entry = tk.Entry(entry_wrap, font=FONT_BASE, bg=COLOR_FIELD, fg=COLOR_TEXT,
                                          relief="flat", bd=0, insertbackground=COLOR_TEXT)
        self.remote_dir_entry.insert(0, DEFAULT_REMOTE_DIR)
        self.remote_dir_entry.pack(fill="x", ipady=2, padx=4)

    # ---------- Store List ----------
    def _build_store_panel(self, parent):
        outer, body = self._panel(parent, "Store List")
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctrl_row = tk.Frame(body, bg=COLOR_PANEL)
        ctrl_row.pack(fill="x", pady=(0, PAD_ROW))

        select_btn = tk.Button(ctrl_row, text="Select All", font=FONT_SMALL, command=self.select_all_stores)
        _style_button(select_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
        select_btn.configure(padx=6, pady=1)
        select_btn.pack(side="left", padx=(0, 3))

        deselect_btn = tk.Button(ctrl_row, text="Deselect All", font=FONT_SMALL, command=self.deselect_all_stores)
        _style_button(deselect_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
        deselect_btn.configure(padx=6, pady=1)
        deselect_btn.pack(side="left", padx=3)

        reload_btn = tk.Button(ctrl_row, text="🔄 Reload", font=FONT_SMALL, command=self.reload_stores_list)
        _style_button(reload_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
        reload_btn.configure(padx=6, pady=1)
        reload_btn.pack(side="right", padx=2)

        logs_btn = tk.Button(ctrl_row, text="📜 Logs", font=FONT_SMALL, command=self.open_logs_history)
        _style_button(logs_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
        logs_btn.configure(padx=6, pady=1)
        logs_btn.pack(side="right", padx=2)

        edit_btn = tk.Button(ctrl_row, text="✏️ Edit", font=FONT_SMALL, command=self.open_store_editor)
        _style_button(edit_btn, COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, hover="#323b54")
        edit_btn.configure(padx=6, pady=1)
        edit_btn.pack(side="right", padx=2)

        list_container = tk.Frame(body, bg=COLOR_PANEL)
        list_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_container, bg=COLOR_FIELD, highlightthickness=1, highlightbackground=COLOR_BORDER)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLOR_FIELD)

        self.store_canvas = canvas
        self.store_canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_scrollable_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(self.store_canvas_window, width=event.width)

        scrollable_frame.bind("<Configure>", _on_scrollable_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.scrollable_frame = scrollable_frame

        deploy_btn_frame = tk.Frame(body, bg=COLOR_PANEL)
        deploy_btn_frame.pack(fill="x", pady=(5, 0))
        self.deploy_btn = tk.Button(
            deploy_btn_frame, text="🚀 Deploy", font=("Segoe UI", 9, "bold"),
            command=self.deploy
        )
        _style_button(self.deploy_btn, COLOR_SUCCESS, hover=COLOR_SUCCESS_DARK)
        self.deploy_btn.configure(pady=4)
        self.deploy_btn.pack(fill="x")

    def populate_store_checkboxes(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.store_vars.clear()

        if not self.stores:
            tk.Label(self.scrollable_frame, text="No stores found in stores.txt", bg=COLOR_FIELD,
                     fg=COLOR_DANGER, font=FONT_BASE).pack(anchor="w", padx=8, pady=6)
            return

        grouped = {}
        for s in self.stores:
            grouped.setdefault(s.get("dc", "Ungrouped"), []).append(s)

        for dc_name in sorted(grouped.keys()):
            dc_stores = grouped[dc_name]

            dc_header = tk.Frame(self.scrollable_frame, bg=COLOR_PANEL_ALT)
            dc_header.pack(fill="x", pady=(3, 1))

            dc_var = tk.BooleanVar(value=True)

            def make_toggle_dc(dc_stores=dc_stores, dc_var=dc_var):
                def toggle_dc():
                    new_val = dc_var.get()
                    for s in dc_stores:
                        self.store_vars[s["ip"]].set(new_val)
                return toggle_dc

            tk.Checkbutton(
                dc_header, text=f"  {dc_name}  ({len(dc_stores)} store{'s' if len(dc_stores) != 1 else ''})",
                variable=dc_var, bg=COLOR_PANEL_ALT, fg=COLOR_PANEL_ALT_TEXT, activebackground=COLOR_PANEL_ALT,
                selectcolor=COLOR_PANEL_ALT, font=FONT_SMALL_BOLD, anchor="w", command=make_toggle_dc(),
                relief="flat", bd=0, padx=2, pady=1
            ).pack(fill="x", padx=1)

            for s in dc_stores:
                var = tk.BooleanVar(value=True)
                ip = s["ip"]
                self.store_vars[ip] = var
                label_bits = [s.get("name") or ip]
                if s.get("code"):
                    label_bits.append(f"[{s['code']}]")
                label_bits.append(f"({ip})")
                tk.Checkbutton(
                    self.scrollable_frame, text=" ".join(label_bits),
                    variable=var, bg=COLOR_FIELD, fg=COLOR_TEXT, activebackground=COLOR_FIELD,
                    selectcolor=COLOR_PANEL_ALT, anchor="w", font=FONT_BASE, relief="flat", bd=0,
                    padx=0, pady=0
                ).pack(fill="x", anchor="w", padx=18, pady=0)

        self.scrollable_frame.update_idletasks()
        self.store_canvas.configure(scrollregion=self.store_canvas.bbox("all"))
        self.store_canvas.yview_moveto(0)

    def select_all_stores(self):
        for var in self.store_vars.values():
            var.set(True)

    def deselect_all_stores(self):
        for var in self.store_vars.values():
            var.set(False)

    def reload_stores_list(self):
        self.stores = load_stores()
        self.populate_store_checkboxes()
        self.append_log("System: Reloaded stores.txt successfully.")

    def open_logs_history(self):
        show_log_history_window(self.root)

    def open_store_editor(self):
        show_store_editor_window(self.root, on_save=self.reload_stores_list)

    def get_selected_stores(self):
        return [s for s in self.stores if self.store_vars.get(s["ip"], tk.BooleanVar()).get()]

    # ---------- Log Results ----------
    def _build_log_panel(self, parent):
        outer, body = self._panel(parent, "Log Results")
        outer.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        progress_frame = tk.Frame(body, bg=COLOR_PANEL)
        progress_frame.pack(fill="x", pady=(0, PAD_ROW))
        self.status_label = tk.Label(progress_frame, text="Idle — ready to deploy", font=FONT_SMALL_ITALIC,
                                      fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL)
        self.status_label.pack(anchor="w", pady=(0, 2))
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate",
                                         style="Horizontal.TProgressbar")
        self.progress.pack(fill="x")

        log_container = tk.Frame(body, bg=COLOR_FIELD, highlightthickness=1, highlightbackground=COLOR_BORDER)
        log_container.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_container, font=FONT_MONO_SMALL, wrap="word", state="disabled",
                                 bg=COLOR_FIELD, fg=COLOR_TEXT, relief="flat", bd=0,
                                 highlightthickness=0, padx=4, pady=4)
        log_scroll = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        self.log_text.tag_configure("failed", foreground=COLOR_DANGER)

    def append_log(self, text, tag=None):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text + "\n", tag) if tag else self.log_text.insert(tk.END, text + "\n")
        self.log_text.config(state="disabled")
        self.log_text.see(tk.END)

    def log_both(self, text, tag=None):
        self.append_log(text, tag)
        append_full_log(text)

    # ---------- Deploy ----------
    def deploy(self):
        selected_stores = self.get_selected_stores()
        if not selected_stores:
            messagebox.showwarning("Selection Error", "Please select at least one store PC to deploy to.")
            return
        if not self.deploy_files:
            messagebox.showwarning("Files Error", "Add at least one file to the deploy list first.")
            return

        remote_dir = self.remote_dir_entry.get().strip() or DEFAULT_REMOTE_DIR
        post_command = self.command_text.get("1.0", tk.END).strip()
        execution_order = self.execution_order_var.get()

        order_note = ""
        if post_command:
            order_note = (
                "\nOrder: files will upload first, then the command runs."
                if execution_order == "files_first"
                else "\nOrder: the command runs first, then files upload."
            )

        if not messagebox.askyesno(
            "Confirm Deploy",
            f"This will upload {len(self.deploy_files)} file(s) to {remote_dir} on {len(selected_stores)} store PC(s)."
            + order_note
            + "\n\nProceed?"
        ):
            return

        self.failed_stores = []
        self.success_stores = []
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")
        self.deploy_btn.config(state="disabled", text="⏳ Deploying...")
        self.progress.config(mode="determinate", maximum=len(selected_stores), value=0)
        self.status_label.config(text=f"Starting deployment to {len(selected_stores)} store(s)...")

        self.log_both("\n==================================================")
        self.log_both(f"--- STARTING DEPLOY TO {len(selected_stores)} STORE(S) ---")
        self.log_both("==================================================")

        start_deployment(selected_stores, self.deploy_files, remote_dir, post_command, execution_order, self.log_queue)
        self.root.after(100, self.poll_log_queue)

    def poll_log_queue(self):
        try:
            while True:
                kind, payload, tag = self.log_queue.get_nowait()
                if kind == "log":
                    self.log_both(payload, tag)
                elif kind == "detail":
                    append_full_log(payload)
                elif kind == "status":
                    self.status_label.config(text=payload)
                elif kind == "progress":
                    self.progress.step(payload)
                elif kind == "failed_store":
                    if payload not in self.failed_stores:
                        self.failed_stores.append(payload)
                elif kind == "success_store":
                    if payload not in self.success_stores:
                        self.success_stores.append(payload)
                elif kind == "done":
                    self.log_both("\n==================================================")
                    self.log_both("--- DEPLOYMENT FINISHED ---")
                    if self.success_stores:
                        self.log_both(f"Stores completed successfully ({len(self.success_stores)}):")
                        for s in self.success_stores:
                            self.log_both(f"  ✓ {s}")
                    if self.failed_stores:
                        self.log_both(f"Stores with errors ({len(self.failed_stores)}):", tag="failed")
                        for s in self.failed_stores:
                            self.log_both(f"  ✗ {s}", tag="failed")
                    if not self.success_stores and not self.failed_stores:
                        self.log_both("No stores were processed.")
                    self.log_both("==================================================\n")
                    self.status_label.config(text="Deployment finished.")
                    self.deploy_btn.config(state="normal", text="🚀 Deploy")
                    messagebox.showinfo("Deploy Finished", "Deployment completed! Check results log below.")
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll_log_queue)