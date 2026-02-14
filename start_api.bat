@echo off
echo ========================================
echo   News Scraper RD API - Starting Server
echo ========================================
echo.

echo [1/3] Activating virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Please run: python -m venv venv
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)

echo [2/3] Verifying dependencies...
python -c "import uvicorn, fastapi" 2>nul
if errorlevel 1 (
    echo ERROR: Missing dependencies. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Could not install dependencies.
        pause
        exit /b 1
    )
)

echo [3/3] Starting API server...
echo.
echo ========================================
echo   API available at: http://localhost:8000
echo   Documentation: http://localhost:8000/docs
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo ERROR: The server stopped unexpectedly.
    pause
)
