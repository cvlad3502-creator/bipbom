@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0webapp.ps1" %*
if errorlevel 1 goto :err
exit /b 0

:err
echo.
echo Не удалось поднять WebApp. Подробности выше.
exit /b 1
