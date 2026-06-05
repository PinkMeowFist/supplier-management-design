@echo off
cd /d "%~dp0"
echo 正在启动供应商管理系统...
echo.
start /min python app.py
timeout /t 3 /nobreak >nul
start http://localhost:5000
exit
