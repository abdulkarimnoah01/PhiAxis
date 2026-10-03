@echo off
rem Double-click to install or update PhiAxis for every Houdini 20.5 - 22 on this PC.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
