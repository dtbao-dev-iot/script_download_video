"""GUI for Video Downloader using tkinter."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .downloader import Downloader, QUALITY_FORMATS

DEFAULT_OUTPUT = os.path.join(os.path.expanduser("~"), "Downloads")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Downloader")
        self.resizable(False, False)
        self.downloader = Downloader(
            on_progress=self._on_progress,
            on_log=self._on_log,
            on_finish=self._on_finish,
        )
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # URL
        tk.Label(self, text="Video URL:").grid(row=0, column=0, sticky="w", **pad)
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(self, textvariable=self.url_var, width=55)
        url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)
        tk.Button(self, text="Paste", command=self._paste_url).grid(row=0, column=3, **pad)

        # Output folder
        tk.Label(self, text="Save to:").grid(row=1, column=0, sticky="w", **pad)
        self.out_var = tk.StringVar(value=DEFAULT_OUTPUT)
        tk.Entry(self, textvariable=self.out_var, width=55, state="readonly").grid(
            row=1, column=1, columnspan=2, sticky="ew", **pad
        )
        tk.Button(self, text="Browse", command=self._browse).grid(row=1, column=3, **pad)

        # Quality
        tk.Label(self, text="Quality:").grid(row=2, column=0, sticky="w", **pad)
        self.fmt_var = tk.StringVar(value="Best (auto)")
        ttk.Combobox(
            self, textvariable=self.fmt_var,
            values=list(QUALITY_FORMATS.keys()), state="readonly", width=30,
        ).grid(row=2, column=1, sticky="w", **pad)

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=5)
        self.dl_btn = tk.Button(btn_frame, text="Download", width=15, bg="#2196F3", fg="white",
                                command=self._start_download)
        self.dl_btn.pack(side="left", padx=8)
        self.cancel_btn = tk.Button(btn_frame, text="Cancel", width=10, state="disabled",
                                    command=self._cancel)
        self.cancel_btn.pack(side="left", padx=8)

        # Progress bar
        self.progress = ttk.Progressbar(self, length=520, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=4, padx=10, pady=4, sticky="ew")

        # Log area
        tk.Label(self, text="Log:").grid(row=5, column=0, sticky="nw", padx=10)
        log_frame = tk.Frame(self)
        log_frame.grid(row=6, column=0, columnspan=4, padx=10, pady=(0, 10))
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        self.log_box = tk.Text(log_frame, height=10, width=68, state="disabled",
                               yscrollcommand=scrollbar.set, bg="#1e1e1e", fg="#d4d4d4",
                               font=("Consolas", 9))
        self.log_box.pack(side="left")
        scrollbar.config(command=self.log_box.yview)

    def _paste_url(self):
        try:
            self.url_var.set(self.clipboard_get())
        except tk.TclError:
            pass

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.out_var.get())
        if folder:
            self.out_var.set(folder)

    def _start_download(self):
        url = self.url_var.get().strip()
        out = self.out_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a video URL.")
            return
        if not os.path.isdir(out):
            messagebox.showwarning("Invalid folder", "Output folder does not exist.")
            return

        self._log_clear()
        self._log(f"Starting download: {url}")
        self.progress["value"] = 0
        self.dl_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.downloader.start(url, out, self.fmt_var.get())

    def _cancel(self):
        self.downloader.cancel()
        self._log("Cancelling...")
        self.cancel_btn.config(state="disabled")

    # --- callbacks (called from worker thread, must use after()) ---

    def _on_progress(self, pct):
        self.after(0, lambda: self.progress.configure(value=pct))

    def _on_log(self, msg):
        self.after(0, lambda: self._log(msg))

    def _on_finish(self, success, msg):
        def _update():
            self._log(msg)
            self.dl_btn.config(state="normal")
            self.cancel_btn.config(state="disabled")
            if success:
                self.progress["value"] = 100
                messagebox.showinfo("Done", f"Saved to: {self.out_var.get()}")
            else:
                self.progress["value"] = 0
        self.after(0, _update)

    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _log_clear(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
