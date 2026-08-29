@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

if exist ".env" goto run

echo -------------------------------------------------------------
echo   First run: a few one-time questions.
echo -------------------------------------------------------------
echo.
echo 1) ADZUNA  (get these at developer.adzuna.com ^> API Access Details)
set /p AID=   Application ID:
set /p AKEY=   Application Key:
echo.
echo 2) EMAIL   (optional - press Enter to skip and just save files)
echo    To send, you need a Gmail / Google Workspace App Password.
echo    See EMAIL_SETUP.md for the 4 steps to create one.
set /p SU=   Address the email is SENT FROM (e.g. aisha@lumorarecruitment.com):
set /p SP=   App Password (16 letters, no spaces):
echo.

>  .env echo ADZUNA_APP_ID=!AID!
>> .env echo ADZUNA_APP_KEY=!AKEY!
>> .env echo COMPANIES_HOUSE_API_KEY=
>> .env echo REPORT_TO=aisha@lumorarecruitment.com
>> .env echo SMTP_HOST=smtp.gmail.com
>> .env echo SMTP_PORT=587
>> .env echo SMTP_USER=!SU!
>> .env echo SMTP_PASSWORD=!SP!
echo Saved settings to .env  (you will not be asked again).
echo.

:run
%PY% -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
%PY% client_leads.py
echo.
echo ============================================================
echo  Results emailed to aisha@lumorarecruitment.com (if set up)
echo  and saved in the  output  folder:
echo    fresh_roles_(today).csv   - work from this
echo ============================================================
pause
