@echo off
set PATH=D:\Program Files\nodejs;%APPDATA%\npm;%PATH%
cd /d "C:\Users\29947\Desktop\homework\e_commerce_project_claude"
echo Starting Admin on http://localhost:3002...
pnpm --filter frontend-admin dev
pause