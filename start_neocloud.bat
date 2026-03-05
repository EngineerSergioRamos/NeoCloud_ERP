@echo off
echo ===================================================
echo      NEOCLOUD ERP - ZERO-TOUCH DEV ENVIRONMENT
echo ===================================================

:: Capture the exact absolute path to the NeoCloud_ERP folder
set "PROJECT_ROOT=%~dp0"
:: venv_stable is located one folder up from NeoCloud_ERP
set "VENV_PATH=%~dp0..\venv_stable\Scripts\activate.bat"

:: Ensure the env_prod directory exists so Uvicorn doesn't crash on boot
mkdir "%PROJECT_ROOT%backend\env_prod" 2>nul

:: Start Next.js Frontend
echo [1/3] Booting Next.js Frontend...
start "Next.js UI" cmd /k "cd /d "%PROJECT_ROOT%frontend" && npm run dev"

:: Start AI Orchestrator (CrewAI Bridge)
echo [2/3] Booting AI Orchestrator...
start "AI Orchestrator" cmd /k "cd /d "%PROJECT_ROOT%backend" && call "%VENV_PATH%" && python main.py"

:: Start Live API (FASAR Engine) with Auto-Reload
echo [3/3] Booting Live FastAPI Engine...
start "Live API Backend" cmd /k "cd /d "%PROJECT_ROOT%backend\env_prod" && call "%VENV_PATH%" && uvicorn fasar_calc:app --host 0.0.0.0 --port 8001 --reload"

echo.
echo All systems nominal.
echo Frontend: http://localhost:3000
echo AI Bridge: http://localhost:8000
echo Live API: http://localhost:8001
pause