@echo off
set PATH=D:\Program Files\nodejs;%APPDATA%\npm;%PATH%
cd /d "C:\Users\29947\Desktop\homework\e_commerce_project_claude"
echo Starting User Web on http://localhost:3000...
pnpm --filter frontend-user-web dev
pause