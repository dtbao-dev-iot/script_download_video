"""Build VideoDownloader.exe using PyInstaller."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "VideoDownloader.spec"


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


def main():
    print("=== Video Downloader — Build ===\n")

    # Install PyInstaller if missing
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

    clean()

    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",            # single .exe
        "--windowed",           # no console window
        "--name", "VideoDownloader",
        "--collect-all", "yt_dlp",      # include all yt-dlp extractors
        "--hidden-import", "bs4",
        "--hidden-import", "requests",
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


if __name__ == "__main__":
    main()
