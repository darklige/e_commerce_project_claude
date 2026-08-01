@echo off
set PATH=D:\Program Files\nodejs;%APPDATA%\npm;%PATH%
cd /d "C:\Users\29947\Desktop\homework\e_commerce_project_claude"

echo ===============================================
echo  JD-Clone Project Launcher
echo ===============================================
echo.
echo Starting backend...
echo.
start "Backend" cmd /k "cd backend && ..\.venv\Scripts\python.exe -m uvicorn run_dev:app --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul

echo Starting User Web (port 3000)...
start "User Web" cmd /k "pnpm --filter frontend-user-web dev"
timeout /t 3 /nobreak >nul

echo Starting Merchant (port 3001)...
start "Merchant" cmd /k "pnpm --filter frontend-merchant dev"
timeout /t 3 /nobreak >nul

echo Starting Admin (port 3002)...
start "Admin" cmd /k "pnpm --filter frontend-admin dev"

echo.
echo ===============================================
echo  All services started! 
echo  Backend:  http://localhost:8000/docs
echo  User Web: http://localhost:3000
echo  Merchant: http://localhost:3001
echo  Admin:    http://localhost:3002
echo ===============================================
echo.
pause