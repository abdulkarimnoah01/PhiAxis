@echo off
rem Double-click to remove PhiAxis. Your saved settings and presets are kept.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Uninstall %*
