#!/usr/bin/env python3
"""
Release script.

Usage:
    python docs/scripts/release.py

Workflow:
    1. Validates working directory is clean
    2. Reads current version from version.h or __init__.py/version.py
    3. Prompts for new version
    4. Validates CHANGELOG entry exists
    5. Updates version file (version.h or __init__.py/version.py)
    6. Updates README.md badge
    7. Commits, pushes branch, tags, pushes tag -> triggers CI/CD release
"""

import re
import subprocess
import sys
from pathlib import Path

# ─── Project configuration (set during project setup) ────────────────────────
# LANGUAGE:      "c"       -> C/C++ project (version.h)
#                "python"  -> Python project (version.py or __init__.py)
# PROJECT_TYPE:  "firmware-dev"         -> version format VYY.MM.PP, tag V26.04.00
#                "firmware-dev-layered" -> version format VYY.MM.PP, tag V26.04.00
#                "firmware-libs"        -> version format VXX.YY.ZZ, tag V00.01.00
# PYTHON_PROJECT_TYPE: "package" or "script" (only when LANGUAGE == "python")
# PROJECT_NAME: snake_case project name (only when LANGUAGE == "python" and package)
LANGUAGE = "python"
PROJECT_TYPE = "firmware-dev"
PYTHON_PROJECT_TYPE = "package"
PROJECT_NAME = "script_download_video"
# ─────────────────────────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).parent.parent.parent

if LANGUAGE == "c":
    if PROJECT_TYPE == "firmware-dev":
        VERSION_PATTERN = re.compile(r"^V\d{2}\.\d{2}\.\d{2}$")
        VERSION_FILE_PATH = REPO_DIR / "configs_tool" / "version.h"
        MAJOR_DEFINE = "FW_VERSION_MAJOR"
        MINOR_DEFINE = "FW_VERSION_MINOR"
        PATCH_DEFINE = "FW_VERSION_PATCH"
        STRING_DEFINE = "FW_VERSION_STRING"
        VERSION_HINT = "VXX.YY.ZZ  (e.g. V26.04.00)"
    elif PROJECT_TYPE == "firmware-dev-layered":
        VERSION_PATTERN = re.compile(r"^V\d{2}\.\d{2}\.\d{2}$")
        VERSION_FILE_PATH = REPO_DIR / "6_Configs" / "version.h"
        MAJOR_DEFINE = "FW_VERSION_MAJOR"
        MINOR_DEFINE = "FW_VERSION_MINOR"
        PATCH_DEFINE = "FW_VERSION_PATCH"
        STRING_DEFINE = "FW_VERSION_STRING"
        VERSION_HINT = "VXX.YY.ZZ  (e.g. V26.04.00)"
    else:  # firmware-libs
        VERSION_PATTERN = re.compile(r"^V\d{2}\.\d{2}\.\d{2}$")
        VERSION_FILE_PATH = REPO_DIR / "version.h"
        MAJOR_DEFINE = "LIB_VERSION_MAJOR"
        MINOR_DEFINE = "LIB_VERSION_MINOR"
        PATCH_DEFINE = "LIB_VERSION_PATCH"
        STRING_DEFINE = "LIB_VERSION_STRING"
        VERSION_HINT = "VXX.YY.ZZ  (e.g. V00.01.00)"
else:  # python
    VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
    VERSION_HINT = "MAJOR.MINOR.PATCH  (e.g. 1.2.0)"
    if PYTHON_PROJECT_TYPE == "package":
        VERSION_FILE_PATH = REPO_DIR / "video_downloader" / "__init__.py"
    else:
        VERSION_FILE_PATH = REPO_DIR / "src" / "version.py"

CHANGELOG_DIR = REPO_DIR / "docs" / "CHANGELOG"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_DIR, check=check, capture_output=True, text=True)


def current_version() -> str:
    """Read current version from the project version file."""
    if not VERSION_FILE_PATH.exists():
        print(f"ERROR: version file not found at {VERSION_FILE_PATH}")
        sys.exit(1)

    content = VERSION_FILE_PATH.read_text(encoding="utf-8")

    if LANGUAGE == "c":
        # Try direct string format (legacy or manual override)
        match = re.search(rf'#define\s+{STRING_DEFINE}\s+"([^"]+)"', content)
        if match:
            return f"V{match.group(1)}"
        # Fallback: reconstruct from MAJOR/MINOR/PATCH defines
        major = re.search(rf"#define\s+{MAJOR_DEFINE}\s+(\S+)", content)
        minor = re.search(rf"#define\s+{MINOR_DEFINE}\s+(\S+)", content)
        patch = re.search(rf"#define\s+{PATCH_DEFINE}\s+(\S+)", content)
        if major and minor and patch:
            return f"V{major.group(1)}.{minor.group(1)}.{patch.group(1)}"
    else:
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)

    print(f"ERROR: Could not parse version from {VERSION_FILE_PATH}")
    sys.exit(1)


def current_branch() -> str:
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def tag_name(version: str) -> str:
    """Return the git tag string for a version."""
    if LANGUAGE == "c":
        return version  # already starts with V
    return f"v{version}"


def check_git_clean() -> None:
    result = run(["git", "status", "--porcelain"])
    changes = [l for l in result.stdout.splitlines() if not l.startswith("??")]
    if changes:
        print("ERROR: Working directory has uncommitted changes. Commit or stash them first.")
        print("\n".join(changes))
        sys.exit(1)


def check_tag_exists(tag: str) -> None:
    result = run(["git", "tag", "--list", tag])
    if result.stdout.strip():
        print(f"ERROR: Tag '{tag}' already exists.")
        sys.exit(1)


def check_changelog(version: str) -> Path:
    changelog = CHANGELOG_DIR / f"{version}.md"
    if not changelog.exists():
        print(f"ERROR: docs/CHANGELOG/{version}.md not found.")
        print("       Create the changelog file before releasing.")
        sys.exit(1)
    return changelog


def prompt_version() -> str:
    current = current_version()
    print(f"Current version : {current}")
    print(f"Format required : {VERSION_HINT}")
    print()

    while True:
        version = input("New version     : ").strip()
        if not VERSION_PATTERN.match(version):
            print(f"  ERROR: '{version}' does not match {VERSION_HINT} -- try again.")
            continue
        if version == current:
            print(f"  ERROR: '{version}' is the same as the current version -- try again.")
            continue
        return version


def parse_version(version: str) -> tuple[str, str, str]:
    """Return (major, minor, patch) strings."""
    if LANGUAGE == "c":
        parts = version.lstrip("V").split(".")
    else:
        parts = version.split(".")
    return parts[0], parts[1], parts[2]


def update_version_py(version: str) -> None:
    if not VERSION_FILE_PATH.exists():
        print(f"  WARN version file not found at {VERSION_FILE_PATH} -- skipped.")
        return

    content = VERSION_FILE_PATH.read_text(encoding="utf-8")
    new_content = re.sub(
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{version}"',
        content,
    )

    if new_content == content:
        print(f"  WARN Could not find __version__ in {VERSION_FILE_PATH.relative_to(REPO_DIR)} -- skipped.")
        return

    VERSION_FILE_PATH.write_text(new_content, encoding="utf-8")
    print(f"  OK  Updated {VERSION_FILE_PATH.relative_to(REPO_DIR)}: {version}")


def update_version_file(version: str) -> None:
    update_version_py(version)


def update_readme_badge(old_version: str, new_version: str) -> None:
    readme = REPO_DIR / "README.md"
    if not readme.exists():
        print("  WARN README.md not found -- badge update skipped.")
        return

    content = readme.read_text(encoding="utf-8")
    old_badge = f"version-{old_version}-blue"
    new_badge = f"version-{new_version}-blue"

    if old_badge not in content:
        print(f"  WARN README.md badge not found for {old_version} -- skipped.")
        return

    readme.write_text(content.replace(old_badge, new_badge, 1), encoding="utf-8")
    print(f"  OK  Updated README.md badge: {old_version} -> {new_version}")


def confirm(version: str, tag: str, branch: str, changelog: Path) -> None:
    rel_changelog = changelog.relative_to(REPO_DIR)
    version_file_rel = (
        VERSION_FILE_PATH.relative_to(REPO_DIR)
        if VERSION_FILE_PATH.exists()
        else f"version file ({VERSION_FILE_PATH.name} not found)"
    )
    print()
    print("-" * 50)
    print(f"  Language     : {LANGUAGE}")
    print(f"  Version      : {version}")
    print(f"  Tag          : {tag}")
    print(f"  Commit msg   : chore: release {version}")
    print(f"  Files staged : README.md  {rel_changelog}  {version_file_rel}")
    print(f"  Push branch  : git push origin {branch}")
    print(f"  Push tag     : git push origin {tag}")
    print("-" * 50)
    answer = input("Proceed? (yes / no): ").strip().lower()
    if answer != "yes":
        print("Aborted.")
        sys.exit(0)


def main() -> None:
    print("=== Release ===")
    print(f"    Language     : {LANGUAGE}")
    print(f"    Project type : {PYTHON_PROJECT_TYPE}")
    print()

    check_git_clean()

    old_version = current_version()
    version = prompt_version()
    tag = tag_name(version)
    branch = current_branch()

    check_tag_exists(tag)
    changelog = check_changelog(version)
    confirm(version, tag, branch, changelog)

    print()

    # Update version file
    update_version_file(version)

    # Update README.md badge
    update_readme_badge(old_version, version)

    # Stage files and commit
    files_to_stage = [
        "README.md",
        str(changelog.relative_to(REPO_DIR)),
        str(VERSION_FILE_PATH.relative_to(REPO_DIR)) if VERSION_FILE_PATH.exists() else None,
    ]
    files_to_stage = [f for f in files_to_stage if f is not None]
    run(["git", "add"] + files_to_stage)
    run(["git", "commit", "-m", f"chore: release {version}"])
    print(f"  OK  Committed release files")

    # Push branch
    run(["git", "push", "origin", branch])
    print(f"  OK  Pushed branch: {branch}")

    # Tag and push tag -> triggers CI/CD release
    run(["git", "tag", tag])
    print(f"  OK  Tagged: {tag}")

    run(["git", "push", "origin", tag])
    print(f"  OK  Pushed tag: {tag}")

    print()
    print(f"Release {version} triggered. CI/CD will create the release automatically.")


if __name__ == "__main__":
    main()
