"""Core download logic using yt-dlp."""

import threading
import yt_dlp
from .extractor import find_video_urls


QUALITY_FORMATS = {
    "Best (auto)":    "bestvideo+bestaudio/best",
    "1080p":          "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":           "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":           "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":           "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "Audio only (MP3)": "bestaudio/best",
}


class Downloader:
    def __init__(self, on_progress=None, on_log=None, on_finish=None):
        self.on_progress = on_progress  # callback(percent: float)
        self.on_log = on_log            # callback(msg: str)
        self.on_finish = on_finish      # callback(success: bool, msg: str)
        self._thread = None
        self._cancelled = False

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
                    self.on_log(f"Downloading... {pct:.1f}%  Speed: {speed}  ETA: {eta}")
        elif status == "finished":
            if self.on_log:
                self.on_log("Post-processing...")

    def _run(self, url, output_dir, fmt):
        self._cancelled = False
        is_audio = fmt == "Audio only (MP3)"
        ydl_opts = {
            "format": QUALITY_FORMATS[fmt],
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": False,
        }
        if is_audio:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if self.on_progress:
                self.on_progress(100.0)
            if self.on_finish:
                self.on_finish(True, "Download completed!")
        except yt_dlp.utils.DownloadError as e:
            if self._cancelled:
                if self.on_finish:
                    self.on_finish(False, "Cancelled.")
                return
            # yt-dlp doesn't support this URL – try scraping the page
            if "Unsupported URL" in str(e):
                self._try_scrape_fallback(url, ydl_opts)
            else:
                if self.on_finish:
                    self.on_finish(False, f"Error: {e}")
        except Exception as e:
            if self.on_finish:
                self.on_finish(False, f"Unexpected error: {e}")

    def _try_scrape_fallback(self, page_url, ydl_opts):
        if self.on_log:
            self.on_log("yt-dlp does not support this site. Trying to scrape video URL...")
        candidates = find_video_urls(page_url, log=self.on_log)
        if not candidates:
            if self.on_finish:
                self.on_finish(False, "Could not find any video stream on this page.")
            return
        if self.on_log:
            self.on_log(f"Found {len(candidates)} candidate URL(s). Trying to download...")
        for candidate in candidates:
            if self._cancelled:
                if self.on_finish:
                    self.on_finish(False, "Cancelled.")
                return
            if self.on_log:
                self.on_log(f"Trying: {candidate[:80]}...")
            opts = dict(ydl_opts)
            opts["http_headers"] = {"Referer": page_url}
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([candidate])
                if self.on_progress:
                    self.on_progress(100.0)
                if self.on_finish:
                    self.on_finish(True, "Download completed!")
                return
            except Exception:
                continue
        if self.on_finish:
            self.on_finish(False, "All candidate URLs failed. The site may require login or uses DRM.")

    def start(self, url, output_dir, fmt="Best (auto)"):
        if self._thread and self._thread.is_alive():
            return False
        self._thread = threading.Thread(target=self._run, args=(url, output_dir, fmt), daemon=True)
        self._thread.start()
        return True

    def cancel(self):
        self._cancelled = True
