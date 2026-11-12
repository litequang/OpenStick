@echo off
cd /d "%~dp0"
if exist "dist\UZ801-OpenStick-Manager.exe" (
  "dist\UZ801-OpenStick-Manager.exe" %*
) else (
  if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uz801_manager %*
  ) else (
    echo Chua co ban build. Xem README.md de cai dat moi truong Python.
    pause
  )
)
