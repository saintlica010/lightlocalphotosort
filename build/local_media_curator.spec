# -*- mode: python ; coding: utf-8 -*-
# Entry: local_media_curator.__main__:main
# One-folder (COLLECT) Windows build. Do not add user media trees to datas/binaries.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


def _filter_windows_root_icu(binaries):
    """Drop only externally discovered ICU binaries at the bundle root."""
    if sys.platform != "win32":
        return binaries

    filtered = []
    for entry in binaries:
        target = str(entry[0]).replace("\\", "/").lstrip("/")
        name = target.casefold()
        is_root_icu = "/" not in target and (
            name == "icuuc.dll"
            or (name.startswith("icudt") and name.endswith(".dll"))
        )
        if not is_root_icu:
            filtered.append(entry)
    return filtered


spechome = Path(SPECPATH).resolve()
root = spechome.parent
src = root / "src"
sys.path.insert(0, str(src))

entry = src / "local_media_curator" / "__main__.py"

a = Analysis(
    [str(entry)],
    pathex=[str(src)],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules("local_media_curator"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = _filter_windows_root_icu(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="local_media_curator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="local_media_curator",
)
