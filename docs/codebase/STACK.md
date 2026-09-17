# Technology Stack

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language | Python | `pyproject.toml`, `src/local_media_curator/` |
| Runtime + version | Python `>=3.12`; the repository does not pin one exact patch version | `pyproject.toml` (`requires-python`) |
| Package manager | pip-compatible Python packaging through setuptools | `pyproject.toml`, `README.md` install commands |
| Module/build system | `src` layout with setuptools; Windows one-folder PyInstaller build | `pyproject.toml`, `build/local_media_curator.spec`, `scripts/build_windows.ps1` |

### 2) Production Frameworks and Dependencies

| Dependency | Version | Role in system | Evidence |
|------------|---------|----------------|----------|
| PySide6 | unpinned in manifest `[TODO: choose a supported version policy]` | Qt desktop UI, model/view, threads, undo stack | `pyproject.toml`, `src/local_media_curator/ui/`, `src/local_media_curator/media/*loader.py` |
| Pillow | unpinned in manifest `[TODO: choose a supported version policy]` | Image metadata extraction, EXIF transpose, thumbnail and preview decoding | `pyproject.toml`, `src/local_media_curator/media/metadata.py`, `thumbnail_service.py`, `image_loader.py` |
| Python `sqlite3` | standard library | Project metadata persistence, migrations, repositories | `src/local_media_curator/db/connection.py`, `migrations.py`, `repositories.py` |

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| pytest | Test runner | `pyproject.toml`, `tests/` |
| pytest-qt | Qt test integration and `qtbot` fixture | `pyproject.toml`, `tests/*.py` using `qtbot` |
| PyInstaller | Optional Windows packaging tool | `pyproject.toml`, `build/local_media_curator.spec`, `scripts/build_windows.ps1` |
| setuptools | Build backend and package discovery | `pyproject.toml` |

### 4) Key Commands

```text
python -m pip install -e ".[dev]"
python -m local_media_curator
python -m pytest
python -m pip install -e ".[packaging]"
powershell -File scripts/build_windows.ps1
```

No repository linter or formatter command is configured. `[TODO]` Add and document one only if the project adopts a formatting/linting gate.

### 5) Environment and Config

- Config sources: `pyproject.toml`, `build/local_media_curator.spec`, `scripts/build_windows.ps1`, and runtime project-folder paths in `src/local_media_curator/services/project_service.py`.
- Required environment variables: none found in the source/config search; `[TODO]` confirm this remains intentional.
- Deployment/runtime constraints: Windows 10/11 is the stated target; packaging is one-folder and the executable entry is `local_media_curator.__main__:main`.
- Dependency-resolution status on this machine: the checked-in `.venv` exists but did not contain the declared runtime/dev/packaging packages; a system `pytest 8.2.2` was present, but collection failed because `PySide6` was unavailable.

### 6) Evidence

- `pyproject.toml`
- `README.md`
- `src/local_media_curator/app.py`
- `src/local_media_curator/db/connection.py`
- `build/local_media_curator.spec`
- `scripts/build_windows.ps1`

