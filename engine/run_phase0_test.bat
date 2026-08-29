@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
echo Installing Python packages (first run only)...
%PY% -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
%PY% check_phase0.py
echo.
pause
