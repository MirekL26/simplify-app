@echo off
REM Cloud B1 Simplifier - Start script (Windows)
cd /d "%~dp0"

if not exist "venv\" (
    echo Error: Virtual environment not found
    echo Create it: python -m venv venv && venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check port from env or default
if "%SIMPLIFIER_PORT%"=="" set SIMPLIFIER_PORT=8890

REM Check if already running
curl -s --max-time 2 http://localhost:%SIMPLIFIER_PORT%/health >nul 2>&1
if %errorlevel% equ 0 (
    echo Server already running on port %SIMPLIFIER_PORT%
    start http://localhost:%SIMPLIFIER_PORT%
    pause
    exit /b 0
)

echo Starting server on http://localhost:%SIMPLIFIER_PORT%
echo Press Ctrl+C to stop
echo.

REM Open browser after delay
start /b cmd /c "timeout /t 2 >nul && start http://localhost:%SIMPLIFIER_PORT%"

REM Run server
venv\Scripts\python -m src.main

pause
