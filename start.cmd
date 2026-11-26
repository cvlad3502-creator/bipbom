@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv" (
  echo Создаю виртуальное окружение...
  py -m venv .venv || goto :err
)

echo Проверяю зависимости...
".venv\Scripts\python.exe" -c "import aiogram" 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :err
)

if "%BOT_TOKEN%"=="" (
  set /p BOT_TOKEN=Вставьте токен от @BotFather и нажмите Enter: 
)
if "%ADMIN_ID%"=="" (
  set /p ADMIN_ID=Ваш Telegram ID для админки (можно пусто): 
)

if "%WEBAPP_URL%"=="" if exist ".webapp_url" (
  set /p WEBAPP_URL=<.webapp_url
)

".venv\Scripts\python.exe" -u bot.py
goto :end

:err
echo.
echo Не удалось подготовить окружение. Проверьте, что установлен Python 3.10+ (py в PATH).

:end
pause
