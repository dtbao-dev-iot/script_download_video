"""Core download logic using yt-dlp."""

import threading
import yt_dlp
from .extractor import find_video_urls


QUALITY_FORMATS = {
    "Best (auto)":      "bestvideo+bestaudio/best",
    "1080p":            "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":             "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":             "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":             "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "Audio only (MP3)": "bestaudio/best",
}


class Downloader:
    def __init__(self, on_progress=None, on_log=None, on_item_done=None, on_all_done=None):
        self.on_progress = on_progress      # callback(pct: float)
        self.on_log = on_log                # callback(msg: str)
        self.on_item_done = on_item_done    # callback(index: int, success: bool, msg: str)
        self.on_all_done = on_all_done      # callback()
        self._thread = None
        self._cancelled = False

    # ------------------------------------------------------------------

    def _progress_hook(self, d):
        if self._cancelled:
            raise yt_dlp.utils.DownloadError("Cancelled by user")
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            if total:
                pct = downloaded / total * 100
                if self.on_progress:
                    self.on_progress(pct)
                if self.on_log:
                    self.on_log(f"  {pct:.1f}%  speed: {speed}  eta: {eta}")
        elif status == "finished":
            if self.on_log:
                self.on_log("  Post-processing...")

    def _ydl_opts(self, output_dir, fmt):
        is_audio = fmt == "Audio only (MP3)"
        opts = {
            "format": QUALITY_FORMATS[fmt],
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": False,
        }
        if is_audio:
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        return opts

    def _download_one(self, url, output_dir, fmt):
        """Try yt-dlp; on Unsupported URL, fall back to page scraper. Returns (success, msg)."""
        opts = self._ydl_opts(output_dir, fmt)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True, "Done"
        except yt_dlp.utils.DownloadError as e:
            if self._cancelled:
                return False, "Cancelled"
            if "Unsupported URL" not in str(e):
                return False, str(e)

        # Fallback: scrape page for video URL
        if self.on_log:
            self.on_log("  yt-dlp unsupported — scraping page...")
        candidates = find_video_urls(url, log=self.on_log)
        if not candidates:
            return False, "No video stream found on page"

        opts["http_headers"] = {"Referer": url}
        for candidate in candidates:
            if self._cancelled:
                return False, "Cancelled"
            if self.on_log:
                self.on_log(f"  Trying: {candidate[:72]}...")
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([candidate])
                return True, "Done"
            except Exception:
                continue
        return False, "All candidate URLs failed"

    # ------------------------------------------------------------------

    def _run(self, urls, output_dir, fmt):
        self._cancelled = False
        for idx, url in enumerate(urls):
            if self._cancelled:
                if self.on_item_done:
                    self.on_item_done(idx, False, "Cancelled")
                continue
            if self.on_log:
                self.on_log(f"\n[{idx + 1}/{len(urls)}] {url}")
            if self.on_progress:
                self.on_progress(0.0)

            success, msg = self._download_one(url, output_dir, fmt)

            if self.on_progress:
                self.on_progress(100.0 if success else 0.0)
            if self.on_item_done:
                self.on_item_done(idx, success, msg)

        if self.on_all_done:
            self.on_all_done()

    def start(self, urls, output_dir, fmt="Best (auto)"):
        """urls: list[str]. Returns False if already running."""
        if self._thread and self._thread.is_alive():
            return False
        self._thread = threading.Thread(
            target=self._run, args=(urls, output_dir, fmt), daemon=True
        )
        self._thread.start()
        return True

    def cancel(self):
        self._cancelled = True
