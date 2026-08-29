@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
%PY% -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
%PY% client_leads.py
echo.
echo Your call list is in the "output" folder.
pause
