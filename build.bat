@echo off
cd /d "%~dp0"
echo Building...
pyinstaller --noconfirm --onefile --windowed --name "InvoiceTool" --icon "icon.ico" --add-data "invoice_merger.py;." --add-data "icon.ico;." --add-data "icon.png;." --hidden-import invoice_merger --hidden-import fitz --hidden-import fitz.fitz --hidden-import PIL --hidden-import PIL._tkinter_finder main.py
if %errorlevel% neq 0 (
  echo Build failed.
  pause
  exit /b 1
)
echo Done: dist\InvoiceTool.exe
pause
