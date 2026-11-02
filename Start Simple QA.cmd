@echo off
cd /d "%~dp0"
start "" /b ".venv\Scripts\pythonw.exe" simple_local.py
exit /b
