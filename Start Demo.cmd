@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" demo_run.py explore
echo.
echo Review the report path printed above. Press any key to close.
pause >nul
