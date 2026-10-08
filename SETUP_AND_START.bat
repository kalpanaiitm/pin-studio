@echo off
REM Pin Studio: double-click to set up (first time) and start the app.
cd /d "%~dp0"
title Pin Studio

set "PY="
if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo Python was not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: creating a private Python environment for Pin Studio...
  "%PY%" -m venv .venv 2>nul || %PY% -m venv .venv
  if errorlevel 1 (
    echo Could not create the environment. Please send a screenshot of this window to Claude.
    pause
    exit /b 1
  )
)

echo Installing or updating packages (first time takes a few minutes)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
  echo Package install failed. Please send a screenshot of this window to Claude.
  pause
  exit /b 1
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo.
  echo Notepad will open. Paste your OpenAI key after OPENAI_API_KEY= then save and close Notepad.
  notepad ".env"
)

echo Starting Pin Studio in your browser...
".venv\Scripts\python.exe" -m streamlit run app.py
pause
