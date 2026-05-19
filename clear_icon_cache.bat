@echo off
taskkill /f /im explorer.exe >nul 2>&1
del /f /q "%LocalAppData%\IconCache.db" >nul 2>&1
del /f /q "%LocalAppData%\Microsoft\Windows\Explorer\iconcache*" >nul 2>&1
del /f /q "%LocalAppData%\Microsoft\Windows\Explorer\thumbcache*" >nul 2>&1
start explorer.exe
echo Done.
pause
