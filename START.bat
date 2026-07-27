@echo off
echo ============================================
echo  MahaSankh AI Design Studio - Starting...
echo ============================================

REM Install dependencies if needed
cd backend
pip install -r requirements.txt

REM Start FastAPI backend
echo.
echo [1/2] Starting FastAPI backend on http://localhost:8000
start "MahaSankh Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Open frontend in browser
echo [2/2] Opening UI in browser...
start "" "%~dp0frontend\index.html"

echo.
echo ============================================
echo  DONE! 
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo  UI:       frontend/index.html
echo ============================================
pause
