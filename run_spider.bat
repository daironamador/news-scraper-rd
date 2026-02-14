@echo off
echo ========================================
echo   News Scraper RD - Run Spider
echo ========================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Run: python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Available spiders:
echo.
python -m scrapy list
echo.

set /p SPIDER="Spider name to run: "
echo.
echo Running spider: %SPIDER%
echo ========================================
echo.

python -m scrapy crawl %SPIDER%

if errorlevel 1 (
    echo.
    echo ERROR: The spider failed.
) else (
    echo.
    echo Scraping completed.
)

echo.
pause
