# script_download_video

A Python GUI application for downloading videos from multiple URLs.

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

script_download_video is a Python project following project conventions.

- **Project type**: package
- **Version**: 0.1.0
- **Author**: baotd
- **Copyright**: baotd

## Prerequisites

- Python >= 3.9, pip
- Optional: ruff, pytest for quality checks

## Build & Installation

```bash
# Clone the repository
git clone <repo-url>
cd script_download_video
```

**For Python projects:**
```bash
pip install -e .        # development mode
# or
pip install -r requirements.txt
```

## Quick Start

```python
from video_downloader import gui

gui.run()
```

## Testing

```bash
pytest tests/
```

## Project Structure

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for the full folder layout and architecture.

## Coding Style

This project follows project coding conventions:
- **Python**: snake_case, Google-style docstrings, 4-space indent, line length 100

Formatters and linters are configured in `ruff.toml`.

## Git Workflow

- Main branch: `main` (production), `developing` (integration)
- Feature branches: `feature/<ticket>-<description>`
- Commit format: `feat(scope): description` — Conventional Commits
- Never commit directly to `main` or `developing` — use pull requests

## Contributing

1. Create a feature branch from `developing`
2. Follow the coding style defined in this project
3. Run pre-commit hooks: `python docs/scripts/setup.py`
4. Submit a pull request with a clear description

## Version Convention

- **Python** (`package`, `script`): SemVer `MAJOR.MINOR.PATCH` (e.g. `0.1.0`)

Version is defined in `video_downloader/__init__.py`.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---
*Generated with project setup skill.*
