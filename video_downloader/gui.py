"""GUI for Video Downloader using tkinter."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .downloader import Downloader, QUALITY_FORMATS

DEFAULT_OUTPUT = os.path.join(os.path.expanduser("~"), "Downloads")

STATUS_ICON = {
    "Pending":     "⏳",
    "Downloading": "⬇",
    "Done":        "✓",
    "Failed":      "✗",
    "Cancelled":   "–",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Downloader")
        self.resizable(True, False)
        self._urls = []
        self.downloader = Downloader(
            on_progress=self._on_progress,
            on_log=self._on_log,
            on_item_done=self._on_item_done,
            on_all_done=self._on_all_done,
        )
        self._build_ui()

    # ------------------------------------------------------------------  UI

    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}
        self.columnconfigure(1, weight=1)

        # URL input area
        tk.Label(self, text="URLs (one per line):").grid(
            row=0, column=0, sticky="nw", **pad
        )
        url_frame = tk.Frame(self)
        url_frame.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)
        url_frame.columnconfigure(0, weight=1)
        url_sb = tk.Scrollbar(url_frame)
        url_sb.pack(side="right", fill="y")
        self.url_box = tk.Text(url_frame, height=5, width=62, yscrollcommand=url_sb.set,
                               wrap="none", font=("Consolas", 9))
        self.url_box.pack(side="left", fill="both", expand=True)
        url_sb.config(command=self.url_box.yview)

        btn_url = tk.Frame(self)
        btn_url.grid(row=0, column=3, sticky="n", padx=(0, 10), pady=4)
        tk.Button(btn_url, text="Paste", width=8, command=self._paste_urls).pack(pady=2)
        tk.Button(btn_url, text="Clear", width=8, command=self._clear_urls).pack(pady=2)

        # Output folder
        tk.Label(self, text="Save to:").grid(row=1, column=0, sticky="w", **pad)
        self.out_var = tk.StringVar(value=DEFAULT_OUTPUT)
        tk.Entry(self, textvariable=self.out_var, width=62, state="readonly").grid(
            row=1, column=1, columnspan=2, sticky="ew", **pad
        )
        tk.Button(self, text="Browse", width=8, command=self._browse).grid(
            row=1, column=3, padx=(0, 10), pady=4
        )

        # Quality
        tk.Label(self, text="Quality:").grid(row=2, column=0, sticky="w", **pad)
        self.fmt_var = tk.StringVar(value="Best (auto)")
        ttk.Combobox(
            self, textvariable=self.fmt_var,
            values=list(QUALITY_FORMATS.keys()), state="readonly", width=30,
        ).grid(row=2, column=1, sticky="w", **pad)

        # Action buttons
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=6)
        self.dl_btn = tk.Button(btn_frame, text="Download All", width=16,
                                bg="#2196F3", fg="white", command=self._start_download)
        self.dl_btn.pack(side="left", padx=8)
        self.cancel_btn = tk.Button(btn_frame, text="Cancel", width=10,
                                    state="disabled", command=self._cancel)
        self.cancel_btn.pack(side="left", padx=8)

        # Queue table
        tk.Label(self, text="Queue:").grid(row=4, column=0, sticky="nw", padx=10)
        q_frame = tk.Frame(self)
        q_frame.grid(row=4, column=1, columnspan=3, sticky="ew", padx=10, pady=2)
        q_frame.columnconfigure(0, weight=1)
        q_sb = tk.Scrollbar(q_frame)
        q_sb.pack(side="right", fill="y")
        self.queue_tree = ttk.Treeview(
            q_frame, columns=("status", "url"), show="headings",
            height=5, yscrollcommand=q_sb.set,
        )
        self.queue_tree.heading("status", text="Status", anchor="w")
        self.queue_tree.heading("url", text="URL", anchor="w")
        self.queue_tree.column("status", width=100, stretch=False)
        self.queue_tree.column("url", width=480)
        self.queue_tree.pack(side="left", fill="both", expand=True)
        q_sb.config(command=self.queue_tree.yview)

        # Progress bar
        self.progress = ttk.Progressbar(self, length=580, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=4, padx=10, pady=4, sticky="ew")

        # Log
        tk.Label(self, text="Log:").grid(row=6, column=0, sticky="nw", padx=10)
        log_frame = tk.Frame(self)
        log_frame.grid(row=7, column=0, columnspan=4, padx=10, pady=(0, 10))
        log_sb = tk.Scrollbar(log_frame)
        log_sb.pack(side="right", fill="y")
        self.log_box = tk.Text(log_frame, height=8, width=76, state="disabled",
                               yscrollcommand=log_sb.set, bg="#1e1e1e", fg="#d4d4d4",
                               font=("Consolas", 9))
        self.log_box.pack(side="left")
        log_sb.config(command=self.log_box.yview)

    # ------------------------------------------------------------------  helpers

    def _paste_urls(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_box.insert("end", text + "\n")
        except tk.TclError:
            pass

    def _clear_urls(self):
        self.url_box.delete("1.0", "end")

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.out_var.get())
        if folder:
            self.out_var.set(folder)

    def _get_urls(self):
        raw = self.url_box.get("1.0", "end").strip().splitlines()
        return [u.strip() for u in raw if u.strip()]

    def _set_queue(self, urls):
        for row in self.queue_tree.get_children():
            self.queue_tree.delete(row)
        self._tree_ids = []
        for url in urls:
            iid = self.queue_tree.insert("", "end", values=(f"{STATUS_ICON['Pending']} Pending", url))
            self._tree_ids.append(iid)

    def _update_queue_row(self, idx, status):
        iid = self._tree_ids[idx]
        icon = STATUS_ICON.get(status, "")
        self.queue_tree.item(iid, values=(f"{icon} {status}", self._urls[idx]))
        self.queue_tree.see(iid)

    # ------------------------------------------------------------------  actions

    def _start_download(self):
        urls = self._get_urls()
        if not urls:
            messagebox.showwarning("No URLs", "Please enter at least one video URL.")
            return
        out = self.out_var.get().strip()
        if not os.path.isdir(out):
            messagebox.showwarning("Invalid folder", "Output folder does not exist.")
            return

        self._urls = urls
        self._set_queue(urls)
        self._log_clear()
        self._log(f"Starting {len(urls)} download(s) → {out}")
        self.progress["value"] = 0
        self.dl_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.downloader.start(urls, out, self.fmt_var.get())

    def _cancel(self):
        self.downloader.cancel()
        self._log("Cancelling...")
        self.cancel_btn.config(state="disabled")

    # ------------------------------------------------------------------  callbacks (worker thread → after())

    def _on_progress(self, pct):
        self.after(0, lambda: self.progress.configure(value=pct))

    def _on_log(self, msg):
        self.after(0, lambda: self._log(msg))

    def _on_item_done(self, idx, success, msg):
        status = "Done" if success else ("Cancelled" if msg == "Cancelled" else "Failed")

        def _update():
            self._update_queue_row(idx, status)
            label = "✓" if success else "✗"
            self._log(f"  [{label}] {self._urls[idx][:60]}  — {msg}")

        self.after(0, _update)

    def _on_all_done(self):
        def _update():
            self.dl_btn.config(state="normal")
            self.cancel_btn.config(state="disabled")
            done = sum(
                1 for iid in self._tree_ids
                if "Done" in self.queue_tree.item(iid)["values"][0]
            )
            total = len(self._urls)
            self._log(f"\nFinished: {done}/{total} succeeded.")
            messagebox.showinfo("Done", f"{done}/{total} downloads completed.\nSaved to: {self.out_var.get()}")
        self.after(0, _update)

    # ------------------------------------------------------------------  log

    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _log_clear(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
