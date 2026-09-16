import importlib.util
from pathlib import Path

import pytest

SPEC = Path("build/local_media_curator.spec")
BUILD_SCRIPT = Path("scripts/build_windows.ps1")
_BANNED = ("photos/", "phototakeplan/", "lightphotosprt/")


def test_spec_is_one_folder_and_excludes_protected_dirs() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "COLLECT" in text
    assert "EXE(" in text
    for banned in _BANNED:
        assert banned not in text.replace("\\", "/")


def test_spec_uses_package_main_entry_and_empty_datas() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "local_media_curator.__main__:main" in text
    assert "exclude_binaries=True" in text
    assert "datas=[]" in text.replace(" ", "")


def test_build_script_invokes_pyinstaller_spec() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "python -m PyInstaller build/local_media_curator.spec" in text
    for banned in _BANNED:
        assert banned not in text.replace("\\", "/")


@pytest.mark.skipif(
    importlib.util.find_spec("PyInstaller") is None,
    reason="PyInstaller is not installed",
)
def test_pyinstaller_is_importable_when_present() -> None:
    spec = importlib.util.find_spec("PyInstaller")
    assert spec is not None
