import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = Path("build/local_media_curator.spec")
BUILD_SCRIPT = Path("scripts/build_windows.ps1")
_BANNED = ("photos/", "phototakeplan/", "lightphotosprt/")


def _spec_binary_filter(platform: str):
    tree = ast.parse(SPEC.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_filter_windows_root_icu"
    )
    namespace = {"sys": SimpleNamespace(platform=platform)}
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(SPEC), "exec"), namespace)
    return namespace[function.name]


def test_spec_filters_only_root_icu_on_windows() -> None:
    filter_binaries = _spec_binary_filter("win32")
    root_icu = ("icuuc.dll", "external-icuuc.dll", "BINARY")
    root_data = ("icudt78.dll", "external-icudt78.dll", "BINARY")
    nested_qt = ("PySide6/icuuc.dll", "bundled-icuuc.dll", "BINARY")
    nested_data = ("nested/icudt78.dll", "bundled-icudt78.dll", "BINARY")
    other = ("PySide6/Qt6Core.dll", "Qt6Core.dll", "BINARY")

    assert filter_binaries([root_icu, root_data, nested_qt, nested_data, other]) == [
        nested_qt,
        nested_data,
        other,
    ]


def test_spec_does_not_filter_icu_on_non_windows() -> None:
    filter_binaries = _spec_binary_filter("linux")
    binaries = [("icuuc.dll", "icuuc.dll", "BINARY")]
    assert filter_binaries(binaries) is binaries


def test_spec_registers_root_icu_filter() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "a.binaries = _filter_windows_root_icu(a.binaries)" in text


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
