@echo off
cd /d "%~dp0"
echo ============================================
echo   Lumora API
echo ============================================
echo.
echo Installing components (only takes time on the first run)...
call npm install
if errorlevel 1 (
  echo.
  echo npm install failed. Is Node.js installed? See SETUP.md step 1.
  pause
  exit /b 1
)
echo.
echo Starting... when you see "running", open http://localhost:3000
echo Close this window to stop.
echo.
call npm start
pause
