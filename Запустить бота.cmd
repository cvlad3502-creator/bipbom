@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  py -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

start "" ".venv\Scripts\pythonw.exe" tray.py
exit
