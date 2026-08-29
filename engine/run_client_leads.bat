@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

if exist ".env" goto run

echo -------------------------------------------------------------
echo   First run: I need your Adzuna keys (one time only).
echo   Get them at developer.adzuna.com  ^>  API Access Details
echo -------------------------------------------------------------
echo.
set /p AID=Paste your Adzuna Application ID and press Enter:
set /p AKEY=Paste your Adzuna Application Key and press Enter:
> .env  echo ADZUNA_APP_ID=!AID!
>> .env echo ADZUNA_APP_KEY=!AKEY!
>> .env echo COMPANIES_HOUSE_API_KEY=
echo.
echo Saved. (You will not be asked again.)
echo.

:run
%PY% -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
%PY% client_leads.py
echo.
echo ============================================================
echo  Your call list is in the  output  folder:
echo    client_leads_(today).csv     - open this and start calling
echo ============================================================
pause
