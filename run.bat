@echo off
rem Double-click to start Rohingya Translate.
rem First run: creates the Python environment in .venv and installs the app (needs internet once).
rem To reinstall later (e.g. after updating the project), delete the .venv folder.
setlocal
cd /d "%~dp0"

if exist ".venv\.installed" goto launch

echo Setting up Rohingya Translate for the first time. This takes a few minutes...
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv 2>nul || py -3.12 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 goto nopython
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto failed
echo done> ".venv\.installed"

:launch
echo Starting Rohingya Translate. Keep this window open; close the app window to quit.
".venv\Scripts\python.exe" -m rohingya_translate.app %*
if errorlevel 1 goto failed
exit /b 0

:nopython
echo.
echo Could not find Python 3.11 or 3.12. Install it from https://www.python.org/downloads/windows/
echo and tick "Add python.exe to PATH" in the installer, then double-click run.bat again.
pause
exit /b 1

:failed
echo.
echo Something went wrong (see the messages above).
pause
exit /b 1
