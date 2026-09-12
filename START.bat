@echo off
echo ============================================
echo  MahaSankh AI Design Studio - Starting...
echo ============================================

REM Install dependencies if needed
pip install -r backend\requirements.txt

REM Start FastAPI backend
echo.
echo [1/2] Starting FastAPI backend on http://localhost:8000
start "MahaSankh Backend" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Open frontend in browser
echo [2/2] Opening Studio in browser...
start "" "http://localhost:8000"

echo.
echo ============================================
echo  DONE! 
echo  Studio UI: http://localhost:8000
echo  API Docs:  http://localhost:8000/docs
echo ============================================
pause
