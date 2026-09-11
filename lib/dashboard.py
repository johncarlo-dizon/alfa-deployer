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


class AlfaDeployDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("AlfaDeploy — File Deployer")
        adjust_window_geometry(self.root)
        self.root.configure(bg="#f4f4f4")

        self.stores = load_stores()
        self.store_vars = {}
        self.deploy_files = []  # list of {"path","name","run_as_admin","replace_if_exists"}
        self.log_queue = queue.Queue()
        self.failed_stores = []
        self.success_stores = []

        main_container = tk.Frame(self.root, bg="#f4f4f4")
        main_container.pack(fill="both", expand=True, padx=10, pady=8)

        top_row = tk.Frame(main_container, bg="#f4f4f4")
        top_row.pack(fill="both", expand=False, pady=(0, 4))
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)

        self._build_files_panel(top_row)
        self._build_commands_panel(top_row)

        bottom_row = tk.Frame(main_container, bg="#f4f4f4")
        bottom_row.pack(fill="both", expand=True, pady=(4, 0))
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=1)
        bottom_row.grid_rowconfigure(0, weight=1)

        self._build_store_panel(bottom_row)
        self._build_log_panel(bottom_row)

        self.populate_store_checkboxes()

    # ---------- Files To Deploy ----------
    def _build_files_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" Files To Deploy ", font=("Segoe UI", 9, "bold"), bg="#f4f4f4", padx=8, pady=4)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        btn_row = tk.Frame(frame, bg="#f4f4f4")
        btn_row.pack(fill="x", pady=(0, 4))
        tk.Button(btn_row, text="Choose File", font=("Segoe UI", 8, "bold"), bg="#007ACC", fg="white", command=self.choose_files).pack(side="left")
        tk.Button(btn_row, text="Remove Selected", font=("Segoe UI", 8), command=self.remove_selected_file).pack(side="left", padx=4)
        tk.Label(btn_row, text="(double-click a file for options)", font=("Segoe UI", 7, "italic"), fg="#777777", bg="#f4f4f4").pack(side="left", padx=6)

        list_frame = tk.Frame(frame, bg="#f4f4f4")
        list_frame.pack(fill="both", expand=True)

        self.files_listbox = tk.Listbox(list_frame, font=("Consolas", 9), height=8, selectmode="extended")
        files_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=files_scroll.set)
        self.files_listbox.pack(side="left", fill="both", expand=True)
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
        outer = tk.Frame(parent, bg="#f4f4f4")
        outer.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        cmd_frame = tk.LabelFrame(outer, text=" Commands ", font=("Segoe UI", 9, "bold"), bg="#f4f4f4", padx=8, pady=4)
        cmd_frame.pack(fill="x")

        header_row = tk.Frame(cmd_frame, bg="#f4f4f4")
        header_row.pack(fill="x")
        self.run_after_deploy_var = tk.BooleanVar(value=False)
        tk.Checkbutton(header_row, text="Run After Deploy", variable=self.run_after_deploy_var, bg="#f4f4f4", font=("Segoe UI", 8)).pack(side="right")

        self.command_text = tk.Text(cmd_frame, height=4, font=("Consolas", 8))
        self.command_text.pack(fill="x", pady=(4, 0))

        dir_frame = tk.LabelFrame(outer, text=" Remote Directory ", font=("Segoe UI", 9, "bold"), bg="#f4f4f4", padx=8, pady=4)
        dir_frame.pack(fill="x", pady=(4, 0))
        self.remote_dir_entry = tk.Entry(dir_frame, font=("Segoe UI", 9))
        self.remote_dir_entry.insert(0, DEFAULT_REMOTE_DIR)
        self.remote_dir_entry.pack(fill="x")

    # ---------- Store List ----------
    def _build_store_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" Store List ", font=("Segoe UI", 9, "bold"), bg="#f4f4f4", padx=8, pady=2)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctrl_row = tk.Frame(frame, bg="#f4f4f4")
        ctrl_row.pack(fill="x", pady=(0, 2))
        tk.Button(ctrl_row, text="Select All", font=("Segoe UI", 8), command=self.select_all_stores).pack(side="left", padx=2)
        tk.Button(ctrl_row, text="Deselect All", font=("Segoe UI", 8), command=self.deselect_all_stores).pack(side="left", padx=2)
        tk.Button(ctrl_row, text="🔄 Reload stores.txt", font=("Segoe UI", 8), command=self.reload_stores_list).pack(side="right", padx=2)
        tk.Button(ctrl_row, text="📜 Logs History", font=("Segoe UI", 8), command=self.open_logs_history).pack(side="right", padx=2)
        tk.Button(ctrl_row, text="✏️ Edit stores.txt", font=("Segoe UI", 8), command=self.open_store_editor).pack(side="right", padx=2)

        list_container = tk.Frame(frame, bg="#f4f4f4")
        list_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_container, bg="#ffffff", highlightthickness=1, highlightbackground="#ccc")
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")

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

        deploy_btn_frame = tk.Frame(frame, bg="#f4f4f4")
        deploy_btn_frame.pack(fill="x", pady=(4, 0))
        self.deploy_btn = tk.Button(
            deploy_btn_frame, text="🚀 Deploy", font=("Segoe UI", 9, "bold"),
            bg="#28A745", fg="white", pady=4, command=self.deploy
        )
        self.deploy_btn.pack(fill="x")

    def populate_store_checkboxes(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.store_vars.clear()

        if not self.stores:
            tk.Label(self.scrollable_frame, text="No stores found in stores.txt", bg="#ffffff", fg="red").pack(anchor="w", padx=5, pady=2)
            return

        grouped = {}
        for s in self.stores:
            grouped.setdefault(s.get("dc", "Ungrouped"), []).append(s)

        for dc_name in sorted(grouped.keys()):
            dc_stores = grouped[dc_name]

            dc_header = tk.Frame(self.scrollable_frame, bg="#e9ecef")
            dc_header.pack(fill="x", pady=(6, 2))

            dc_var = tk.BooleanVar(value=True)

            def make_toggle_dc(dc_stores=dc_stores, dc_var=dc_var):
                def toggle_dc():
                    new_val = dc_var.get()
                    for s in dc_stores:
                        self.store_vars[s["ip"]].set(new_val)
                return toggle_dc

            tk.Checkbutton(
                dc_header, text=f"  {dc_name}  ({len(dc_stores)} store{'s' if len(dc_stores) != 1 else ''})",
                variable=dc_var, bg="#e9ecef", activebackground="#e9ecef",
                font=("Segoe UI", 8, "bold"), anchor="w", command=make_toggle_dc()
            ).pack(fill="x", padx=2)

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
                    variable=var, bg="#ffffff", activebackground="#ffffff", anchor="w"
                ).pack(fill="x", anchor="w", padx=20, pady=1)

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
        frame = tk.LabelFrame(parent, text=" Log Results ", font=("Segoe UI", 9, "bold"), bg="#f4f4f4", padx=8, pady=2)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        progress_frame = tk.Frame(frame, bg="#f4f4f4")
        progress_frame.pack(fill="x", pady=(0, 4))
        self.status_label = tk.Label(progress_frame, text="Idle — ready to deploy", font=("Segoe UI", 8, "italic"), fg="#555555", bg="#f4f4f4")
        self.status_label.pack(anchor="w")
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")

        log_container = tk.Frame(frame, bg="#f4f4f4")
        log_container.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_container, font=("Consolas", 8), wrap="word", state="disabled")
        log_scroll = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        self.log_text.tag_configure("failed", foreground="#D9534F")

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
        run_after_deploy = self.run_after_deploy_var.get()

        if not messagebox.askyesno(
            "Confirm Deploy",
            f"This will upload {len(self.deploy_files)} file(s) to {remote_dir} on {len(selected_stores)} store PC(s)."
            + ("\nA post-deploy command will also run." if run_after_deploy and post_command else "")
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

        start_deployment(selected_stores, self.deploy_files, remote_dir, post_command, run_after_deploy, self.log_queue)
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
