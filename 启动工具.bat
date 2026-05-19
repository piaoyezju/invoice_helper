@echo off
cd /d "%~dp0"
python main.py
if %errorlevel% neq 0 (
  echo.
  echo Failed. Please install dependencies:
  echo   pip install PyMuPDF
  echo.
  pause
)
