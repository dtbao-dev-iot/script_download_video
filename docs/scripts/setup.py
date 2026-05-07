#!/usr/bin/env python3
"""Project setup script.

Configures git hooks path and ensures executable permissions.
Auto-detects LLVM / clang-format on Windows and updates the pre-commit hook.
If clang-format is missing, attempts automatic installation via choco/winget/apt.
Run this after cloning the repository.

Usage:
    python docs/scripts/setup.py
"""

import os
import platform
import re
import subprocess
import sys


def run_cmd(cmd, cwd=None):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def find_cmd(cmd_name):
    """Check if a command exists in PATH."""
    check = "where" if platform.system().lower() == "windows" else "which"
    rc, _, _ = run_cmd(f"{check} {cmd_name}")
    return rc == 0


def install_clang_format_windows():
    """Try to install LLVM (includes clang-format) on Windows."""
    if find_cmd("choco"):
        print("[setup] Attempting install via Chocolatey: choco install llvm -y ...")
        rc, _, err = run_cmd("choco install llvm -y")
        if rc == 0:
            print("[setup] LLVM installed via Chocolatey.")
            return True
        else:
            print(f"[setup] Chocolatey install failed: {err}")

    if find_cmd("winget"):
        print("[setup] Attempting install via winget: winget install LLVM.LLVM ...")
        rc, _, err = run_cmd("winget install LLVM.LLVM")
        if rc == 0:
            print("[setup] LLVM installed via winget.")
            return True
        else:
            print(f"[setup] winget install failed: {err}")

    return False


def install_clang_format_linux():
    """Try to install clang-format on Linux."""
    if find_cmd("apt"):
        print("[setup] Attempting install via apt: sudo apt install -y clang-format ...")
        rc, _, err = run_cmd("sudo apt install -y clang-format")
        if rc == 0:
            print("[setup] clang-format installed via apt.")
            return True
        else:
            print(f"[setup] apt install failed: {err}")

    return False


def auto_install_clang_format():
    """Auto-install clang-format using the best available package manager."""
    system = platform.system().lower()
    if system == "windows":
        return install_clang_format_windows()
    elif system in ("linux", "darwin"):
        return install_clang_format_linux()
    return False


def find_clang_format():
    """Find clang-format binary.

    Returns the absolute path if found, otherwise None.
    On Windows also searches common LLVM installation directories.
    """
    # 1) Check if clang-format is already in PATH
    rc, stdout, _ = run_cmd("clang-format --version")
    if rc == 0:
        # Resolve to absolute path via 'where' (Windows) or 'which' (Unix)
        locate_cmd = "where clang-format" if platform.system().lower() == "windows" else "which clang-format"
        rc2, loc, _ = run_cmd(locate_cmd)
        if rc2 == 0 and loc:
            return loc.splitlines()[0].strip()
        return "clang-format"

    # 2) On Windows, search common installation paths
    if platform.system().lower() == "windows":
        candidates = [
            r"C:\Program Files\LLVM\bin\clang-format.exe",
            r"C:\Program Files (x86)\LLVM\bin\clang-format.exe",
            r"C:\ProgramData\chocolatey\bin\clang-format.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\LLVM\bin\clang-format.exe"),
            r"C:\msys64\mingw64\bin\clang-format.exe",
            r"C:\msys64\clang64\bin\clang-format.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return os.path.abspath(path)

    return None


def win_to_bash_path(win_path):
    """Convert a Windows path to Git Bash style (e.g. C:\foo -> /c/foo)."""
    win_path = win_path.replace("\\", "/")
    if len(win_path) >= 2 and win_path[1] == ":":
        drive = win_path[0].lower()
        win_path = f"/{drive}" + win_path[2:]
    return win_path


def update_precommit_hook(repo_root, clang_path):
    """Update .githooks/pre-commit to use the detected clang-format path."""
    hook_path = os.path.join(repo_root, ".githooks", "pre-commit")
    if not os.path.isfile(hook_path):
        print("[setup] Warning: pre-commit hook not found, skipping clang-format setup")
        return

    with open(hook_path, "r", encoding="utf-8") as f:
        content = f.read()

    bash_path = win_to_bash_path(clang_path)
    new_line = f'CLANG_FORMAT="{bash_path}"'

    # Already points to the same path?
    if bash_path in content:
        print(f"[setup] pre-commit hook already uses {bash_path}")
        return

    # Replace the fallback detection line with the hardcoded path
    old_pattern = 'CLANG_FORMAT=$(command -v clang-format 2>/dev/null || true)'
    if old_pattern in content:
        content = content.replace(old_pattern, new_line)
    else:
        # If the hook was already modified with a different path, try to replace any
        # CLANG_FORMAT=... line that looks like a hardcoded path
        content = re.sub(
            r'^CLANG_FORMAT=.*$',
            new_line,
            content,
            flags=re.MULTILINE
        )

    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[setup] Updated pre-commit hook to use {bash_path}")


def main():
    # script is in <repo>/docs/scripts/, so repo root is two levels up
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    githooks_dir = os.path.join(repo_root, ".githooks")

    # Check if inside a git repository
    rc, _, _ = run_cmd("git rev-parse --git-dir", cwd=repo_root)
    if rc != 0:
        print("[setup] ERROR: Not inside a git repository.")
        sys.exit(1)

    # Check if .githooks directory exists
    if not os.path.isdir(githooks_dir):
        print(f"[setup] ERROR: .githooks/ directory not found at {githooks_dir}")
        sys.exit(1)

    # Configure core.hooksPath
    rc, _, err = run_cmd("git config core.hooksPath .githooks", cwd=repo_root)
    if rc != 0:
        print(f"[setup] ERROR: Failed to set core.hooksPath: {err}")
        sys.exit(1)
    print("[setup] Configured core.hooksPath -> .githooks")

    # Ensure executable permissions on Unix-like systems
    system = platform.system().lower()
    if system in ("linux", "darwin"):
        hooks = ["pre-commit", "commit-msg", "pre-push", "post-commit"]
        for hook in hooks:
            hook_path = os.path.join(githooks_dir, hook)
            if os.path.exists(hook_path):
                if not os.access(hook_path, os.X_OK):
                    os.chmod(hook_path, 0o755)
                    print(f"[setup] Made {hook} executable")
                else:
                    print(f"[setup] {hook} already executable")
            else:
                print(f"[setup] Warning: {hook} not found in .githooks/")
    else:
        print("[setup] Skipping chmod on Windows (Git for Windows handles executable bit)")

    # Detect and configure clang-format for pre-commit
    clang_path = find_clang_format()
    if clang_path:
        print(f"[setup] clang-format found: {clang_path}")
        if platform.system().lower() == "windows":
            update_precommit_hook(repo_root, clang_path)
    else:
        print("[setup] WARNING: clang-format not found. Attempting automatic installation ...")
        if auto_install_clang_format():
            # Re-detect after installation
            clang_path = find_clang_format()
            if clang_path:
                print(f"[setup] clang-format now available: {clang_path}")
                if platform.system().lower() == "windows":
                    update_precommit_hook(repo_root, clang_path)
            else:
                print("[setup] Installation reported success but clang-format still not found.")
                print("  You may need to restart your terminal or add LLVM to PATH.")
        else:
            print("[setup] Automatic installation failed.")
            print("  Install on Linux : sudo apt install clang-format")
            print("  Install on Windows: choco install llvm")
            print("    or download from https://releases.llvm.org/")

    print("[setup] Done. Hooks are active.")


if __name__ == "__main__":
    main()
