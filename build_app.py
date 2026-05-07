"""Build VideoDownloader.exe using PyInstaller."""

import io
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "VideoDownloader.spec"

FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)


def run(cmd):
    print(f">> {' '.join(str(c) for c in cmd)}")
    subprocess.check_call(cmd)


def clean():
    for path in (DIST, BUILD, SPEC):
        if path.is_dir():
            shutil.rmtree(path)
            print(f"Removed: {path}")
        elif path.is_file():
            path.unlink()
            print(f"Removed: {path}")


def fetch_ffmpeg():
    """Download ffmpeg.exe from BtbN static builds and return its path."""
    dest = ROOT / "ffmpeg.exe"
    if dest.exists():
        print(f"ffmpeg.exe already present, skipping download.")
        return dest

    print(f"Downloading ffmpeg from {FFMPEG_URL} ...")
    with urllib.request.urlopen(FFMPEG_URL) as resp:
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        ffmpeg_entry = next(
            n for n in zf.namelist()
            if n.endswith("bin/ffmpeg.exe")
        )
        dest.write_bytes(zf.read(ffmpeg_entry))

    print(f"ffmpeg.exe saved to {dest}")
    return dest


def main():
    print("=== Video Downloader — Build ===\n")

    # Install PyInstaller if missing
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

    clean()

    ffmpeg_exe = fetch_ffmpeg()

    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "VideoDownloader",
        "--collect-all", "yt_dlp",
        "--hidden-import", "bs4",
        "--hidden-import", "requests",
        "--add-binary", f"{ffmpeg_exe};.",
        str(ROOT / "main.py"),
    ])

    exe = DIST / "VideoDownloader.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / 1024 / 1024
        print(f"\n Build complete!")
        print(f" Output : {exe}")
        print(f" Size   : {size_mb:.1f} MB")
    else:
        print("\n Build failed — exe not found.")
        sys.exit(1)

    # Remove intermediate build folder, keep only dist/
    if BUILD.is_dir():
        shutil.rmtree(BUILD)
    if SPEC.is_file():
        SPEC.unlink()
    ffmpeg_exe.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
