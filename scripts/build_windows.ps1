# One-folder Windows build. Output: dist/local_media_curator/local_media_curator.exe
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m PyInstaller build/local_media_curator.spec
