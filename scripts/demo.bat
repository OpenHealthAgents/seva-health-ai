@echo off
REM ==============================================================================
REM SevaHealth AI - Challenge Demo Windows Batch Runner (`.\scripts\demo.bat`)
REM ==============================================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\demo.py" %*
) else (
    python "scripts\demo.py" %*
)
