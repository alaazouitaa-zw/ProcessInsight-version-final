@echo off
REM ============================================================================
REM SETUP & RUN SCRIPT - ProcessInsight Distillation Module
REM ============================================================================

echo.
echo ============================================================================
echo ProcessInsight - Module de Distillation Avancee (Version 2.0.0)
echo ============================================================================
echo.

REM Check Python
echo [1/4] Verifying Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    exit /b 1
)
echo OK - Python installed

REM Install dependencies
echo.
echo [2/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo OK - Dependencies installed

REM Run tests
echo.
echo [3/4] Running integration tests...
python integration_test.py
if errorlevel 1 (
    echo ERROR: Integration tests failed
    exit /b 1
)
echo OK - All tests passed

REM Start application
echo.
echo [4/4] Starting application...
echo ============================================================================
echo Application starting on http://localhost:5000
echo Press Ctrl+C to stop
echo ============================================================================
echo.

python app.py
