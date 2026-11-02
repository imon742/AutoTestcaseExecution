@echo off
cd /d "%~dp0"
start "" /b ".venv\Scripts\pythonw.exe" launch_assistant.pyw
exit /b
