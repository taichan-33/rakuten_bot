@echo off
chcp 65001 >nul
set PYTHONPATH=.
if exist venv\Scripts\python.exe (
    venv\Scripts\python -m app.main
) else (
    echo [ERROR] Virtual environment (venv) not found.
    echo Please run 'python -m venv venv' and install requirements.
    pause
)
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Application exited with error.
    pause
)
