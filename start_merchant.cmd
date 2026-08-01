@echo off
set PATH=D:\Program Files\nodejs;%APPDATA%\npm;%PATH%
cd /d "C:\Users\29947\Desktop\homework\e_commerce_project_claude"
echo Starting Merchant on http://localhost:3001...
pnpm --filter frontend-merchant dev
pause